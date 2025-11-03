#!/usr/bin/env python3
"""
merged_main.py


- Integrates MiDaS ONNX depth + pane detection loop
- Starts ESPServer (TCP) and AppServer (TCP)
- Exposes Flask HTTP endpoints used by Streamlit:
   - /video, /location, /status
   - /signup, /login, /profile/<username>
   - /set_location
   - /esp and /esp/cmd  <-- proxy endpoints to forward motor commands to ESP device
"""
import time
import cv2
import numpy as np
import onnxruntime as ort
import sys
import socket
import threading
import json
import struct
from flask import Flask, Response, request, jsonify
import logging
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS


try:
   from gps3 import gps3
   GPSD_AVAILABLE = True
except Exception:
   GPSD_AVAILABLE = False


try:
   import serial
   import pynmea2
   PYNMEA_AVAILABLE = True
except Exception:
   PYNMEA_AVAILABLE = False


# -----------------------
# Config (edit if needed)
# -----------------------
GPS_SERIAL_DEVICE = "/dev/ttyUSB0"
GPS_BAUDRATE = 9600
GPS_POLL_INTERVAL = 2.0


MODEL_PATH = "models/midas_v21_384.onnx"
VIDEO_SOURCE = 0
TARGET_FPS = 30.0
INVERT_DEPTH = False
USE_CUBIC_RESIZE = True


ESP_HOST = ""
ESP_PORT = 5001
APP_HOST = ""
APP_PORT = 5002


FLASK_HOST = "0.0.0.0"
FLASK_PORT = 9999


CLOSE_THRESH = 0.70
MIN_BLOB_AREA = 200


MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)


ESP_SEND_INTERVAL = 0.15


DB_PATH = "users.db"


# -----------------------
# Shared state
# -----------------------
frame_lock = threading.Lock()
latest_frame_jpg = None
latest_tuple = (0, 0, 0)
latest_location = {'lat': None, 'lon': None, 'host_ip': None, 'timestamp': None}


# -----------------------
# DB helpers
# -----------------------
def init_db(db_path=DB_PATH):
   need_create = not os.path.exists(db_path)
   conn = sqlite3.connect(db_path)
   try:
       cur = conn.cursor()
       cur.execute('''
           CREATE TABLE IF NOT EXISTS users (
               username TEXT PRIMARY KEY,
               password_hash TEXT NOT NULL,
               full_name TEXT,
               age INTEGER,
               condition TEXT,
               caretaker_name TEXT,
               caretaker_contact TEXT
           )
       ''')
       conn.commit()
   finally:
       conn.close()


def db_insert_user(username, password, full_name="", age=None, condition="", caretaker_name="", caretaker_contact=""):
   try:
       conn = sqlite3.connect(DB_PATH)
       cur = conn.cursor()
       pw_hash = generate_password_hash(password)
       cur.execute('''
           INSERT INTO users(username, password_hash, full_name, age, condition, caretaker_name, caretaker_contact)
           VALUES (?, ?, ?, ?, ?, ?, ?)
       ''', (username, pw_hash, full_name, age, condition, caretaker_name, caretaker_contact))
       conn.commit()
       return True, None
   except sqlite3.IntegrityError:
       return False, "username exists"
   except Exception as e:
       return False, str(e)
   finally:
       try: conn.close()
       except: pass


def db_get_user(username):
   conn = sqlite3.connect(DB_PATH)
   conn.row_factory = sqlite3.Row
   try:
       cur = conn.cursor()
       cur.execute('SELECT * FROM users WHERE username = ?', (username,))
       row = cur.fetchone()
       if not row:
           return None
       return dict(row)
   finally:
       conn.close()


init_db()


# -----------------------
# GPS helpers (unchanged)
# -----------------------
def read_gpsd_once(timeout=1.0):
   if not GPSD_AVAILABLE:
       return None
   try:
       gps_socket = gps3.GPSDSocket()
       data_stream = gps3.DataStream()
       gps_socket.connect()
       gps_socket.watch()
       t0 = time.time()
       for new_data in gps_socket:
           if new_data:
               data_stream.unpack(new_data)
               lat = getattr(data_stream.TPV, 'lat', None)
               lon = getattr(data_stream.TPV, 'lon', None)
               epx = getattr(data_stream.TPV, 'epx', None)
               epy = getattr(data_stream.TPV, 'epy', None)
               accuracy = None
               try:
                   if epx is not None and epy is not None:
                       accuracy = max(float(epx), float(epy))
               except:
                   accuracy = None
               if lat is not None and lon is not None:
                   return float(lat), float(lon), accuracy
           if time.time() - t0 > timeout:
               break
   except Exception as e:
       print("[GPSD] error:", e)
   return None


def read_serial_gps_once(devpath=GPS_SERIAL_DEVICE, baud=GPS_BAUDRATE, timeout=1.0):
   if not PYNMEA_AVAILABLE:
       return None
   try:
       ser = serial.Serial(devpath, baudrate=baud, timeout=timeout)
   except Exception as e:
       return None
   t0 = time.time()
   try:
       while True:
           line = ser.readline().decode(errors='ignore').strip()
           if not line:
               if time.time() - t0 > timeout:
                   break
               continue
           try:
               msg = pynmea2.parse(line)
           except pynmea2.ParseError:
               continue
           if isinstance(msg, pynmea2.types.talker.GGA) or msg.sentence_type == "GGA":
               if getattr(msg, 'gps_qual', None) and int(msg.gps_qual) > 0:
                   lat = msg.latitude
                   lon = msg.longitude
                   hdop = getattr(msg, 'horizontal_dil', None)
                   accuracy = float(hdop) if hdop is not None else None
                   return float(lat), float(lon), accuracy
           if getattr(msg, 'sentence_type', None) == 'RMC' or msg.sentence_type == 'RMC':
               if getattr(msg, 'status', None) == 'A':
                   lat = msg.latitude
                   lon = msg.longitude
                   return float(lat), float(lon), None
           if time.time() - t0 > timeout:
               break
   finally:
       try:
           ser.close()
       except:
           pass
   return None


def get_precise_gps():
   try:
       g = read_gpsd_once(timeout=0.8)
       if g:
           lat, lon, acc = g
           return lat, lon, acc, 'gpsd'
   except Exception:
       pass
   try:
       s = read_serial_gps_once(timeout=0.8)
       if s:
           lat, lon, acc = s
           return lat, lon, acc, 'serial'
   except Exception:
       pass
   return None


# -----------------------
# ONNX helpers (unchanged)
# -----------------------
def choose_session(model_path: str):
   available = ort.get_available_providers()
   apple_order = ['MPSExecutionProvider', 'CoreMLExecutionProvider', 'MetalExecutionProvider']
   chosen = []
   for p in apple_order:
       if p in available:
           chosen.append(p)
   if 'CPUExecutionProvider' in available:
       chosen.append('CPUExecutionProvider')
   if not chosen:
       print("No known providers found. Using default provider order.")
       sess = ort.InferenceSession(model_path)
   else:
       providers_to_use = [p for p in chosen if p in available]
       print("Available ONNX providers:", available)
       print("Using provider order:", providers_to_use)
       sess = ort.InferenceSession(model_path, providers=providers_to_use)
   return sess


def infer_model_input_size(sess):
   try:
       inp = sess.get_inputs()[0]
       shape = inp.shape
       dims = [d for d in shape if isinstance(d, int)]
       if len(dims) >= 2:
           h = dims[-2]; w = dims[-1]
           if h == w:
               return int(h)
           else:
               return int(min(h, w))
   except Exception as e:
       print("Could not infer input shape:", e)
   return 256


def preprocess(frame_bgr, target_size):
   img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
   img_resized = cv2.resize(img, (target_size, target_size), interpolation=cv2.INTER_AREA)
   img_resized = (img_resized - MEAN) / STD
   img_chw = np.transpose(img_resized, (2, 0, 1)).astype(np.float32)
   return np.expand_dims(img_chw, 0)


def postprocess_depth(pred, out_w, out_h, invert=False):
   if pred is None:
       return np.zeros((out_h, out_w), dtype=np.float32)
   arr = pred
   if arr.ndim == 4:
       arr = arr[0, 0]
   elif arr.ndim == 3 and arr.shape[0] == 1:
       arr = arr[0]
   elif arr.ndim == 3 and arr.shape[2] == 1:
       arr = arr[:, :, 0]
   interp = cv2.INTER_CUBIC if USE_CUBIC_RESIZE else cv2.INTER_LINEAR
   arr_resized = cv2.resize(arr, (out_w, out_h), interpolation=interp)
   if invert:
       arr_resized = 1.0 / (arr_resized + 1e-6)
   dmin, dmax = float(arr_resized.min()), float(arr_resized.max())
   if dmax - dmin > 1e-6:
       norm = (arr_resized - dmin) / (dmax - dmin)
   else:
       norm = np.zeros_like(arr_resized)
   return norm


def colorize_depth(dmap_01):
   disp = (dmap_01 * 255.0).astype(np.uint8)
   color = cv2.applyColorMap(disp, cv2.COLORMAP_INFERNO)
   return color


def detect_close_panes(dmap, threshold=CLOSE_THRESH, min_area=MIN_BLOB_AREA):
   h, w = dmap.shape
   mask = (dmap >= threshold).astype(np.uint8) * 255
   kernel = np.ones((3,3), np.uint8)
   mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
   contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   blobs = []
   for cnt in contours:
       area = cv2.contourArea(cnt)
       if area < min_area:
           continue
       x,y,ww,hh = cv2.boundingRect(cnt)
       submask = np.zeros_like(mask)
       cv2.drawContours(submask, [cnt], -1, 255, -1)
       mean_depth = cv2.mean(dmap, mask=submask)[0] if dmap.ndim==2 else np.mean(dmap[submask>0])
       M = cv2.moments(cnt)
       if M['m00'] != 0:
           cx = int(M['m10']/M['m00'])
       else:
           cx = x + ww//2
       blobs.append({'area':area, 'mean_depth':mean_depth, 'cx':cx, 'bbox':(x,y,ww,hh)})
   if not blobs:
       return (0,0,0), []
   blobs = sorted(blobs, key=lambda b: b['mean_depth'], reverse=True)
   out = [0,0,0]
   pane_width = w / 3.0
   picks = []
   for b in blobs[:3]:
       pane_idx = int(b['cx'] // pane_width)
       pane_idx = min(max(pane_idx, 0), 2)
       out[pane_idx] = 1
       picks.append((pane_idx, b))
   return tuple(out), picks


def get_location():
   loc = {'timestamp': time.time(), 'lat': None, 'lon': None, 'host_ip': None}
   try:
       s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
       s.connect(("8.8.8.8", 80))
       local_ip = s.getsockname()[0]
       s.close()
       loc['host_ip'] = local_ip
   except:
       loc['host_ip'] = '127.0.0.1'
   try:
       import requests
       r = requests.get('https://ipinfo.io/json', timeout=1.0)
       if r.status_code == 200:
           data = r.json()
           if 'loc' in data:
               lat, lon = data['loc'].split(',')
               loc['lat'] = float(lat); loc['lon'] = float(lon)
   except Exception:
       pass
   return loc


# -----------------------
# TCP servers
# -----------------------
class ESPServer(threading.Thread):
   def __init__(self, host, port):
       super().__init__(daemon=True)
       self.host = host; self.port = port
       self.client = None; self.sock = None; self.lock = threading.Lock(); self.last_sent = 0.0


   def run(self):
       self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
       try:
           self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
           self.sock.bind((self.host, self.port))
           self.sock.listen(1)
           print(f"[ESPServer] listening on {self.host}:{self.port}")
       except Exception as e:
           print("[ESPServer] bind/listen error:", e)
           return
       while True:
           try:
               conn, addr = self.sock.accept()
               print("[ESPServer] ESP connected from", addr)
               # set keepalive so dead connections are detected later at TCP level
               try:
                   conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
               except Exception:
                   pass
               with self.lock:
                   if self.client:
                       try:
                           self.client.close()
                       except:
                           pass
                   self.client = conn
               # do not try to recv() here — keep the socket open and let send_tuple handle errors
               # block here until the socket is closed by other side or send fails
               while True:
                   time.sleep(1.0)
                   with self.lock:
                       if self.client is not conn:
                           break
                       # optionally check socket health by a non-blocking recv peek
                       # but keep it simple for MicroPython clients
               print("[ESPServer] ESP disconnected (handler loop exit)")
               with self.lock:
                   if self.client:
                       try:
                           self.client.close()
                       except:
                           pass
                       self.client = None
           except Exception as e:
               print("[ESPServer] Exception:", e)
               time.sleep(1)


   def send_tuple(self, tpl):
       now = time.time()
       if now - self.last_sent < ESP_SEND_INTERVAL:
           return
       with self.lock:
           if not self.client: return
           try:
               msg = f"{tuple(int(x) for x in tpl)}\n".encode('ascii')
               self.client.sendall(msg)
               self.last_sent = now
           except Exception as e:
               print("[ESPServer] send error:", e)
               try: self.client.close()
               except: pass
               self.client = None


class AppServer(threading.Thread):
   def __init__(self, host, port):
       super().__init__(daemon=True)
       self.host = host; self.port = port; self.client = None; self.sock = None; self.lock = threading.Lock()
   def run(self):
       self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
       try:
           self.sock.bind((self.host, self.port))
           self.sock.listen(1)
           print(f"[AppServer] listening on {self.host}:{self.port}")
       except Exception as e:
           print("[AppServer] bind/listen error:", e)
           return
       while True:
           try:
               conn, addr = self.sock.accept()
               print("[AppServer] App connected from", addr)
               with self.lock:
                   if self.client:
                       try: self.client.close()
                       except: pass
                   self.client = conn
               while True:
                   data = conn.recv(64)
                   if not data:
                       break
               print("[AppServer] App disconnected")
               with self.lock:
                   if self.client:
                       try: self.client.close()
                       except: pass
                       self.client = None
           except Exception as e:
               print("[AppServer] Exception:", e)
               time.sleep(1)
   def send_frame(self, jpeg_bytes):
       with self.lock:
           if not self.client: return
           try:
               ln = struct.pack(">I", len(jpeg_bytes))
               self.client.sendall(b'FRAM' + ln + jpeg_bytes)
           except Exception as e:
               print("[AppServer] send_frame error:", e)
               try: self.client.close()
               except: pass
               self.client = None
   def send_location(self, loc_dict):
       with self.lock:
           if not self.client: return
           try:
               payload = json.dumps(loc_dict).encode('utf-8')
               ln = struct.pack(">I", len(payload))
               self.client.sendall(b'LOC ' + ln + payload)
           except Exception as e:
               print("[AppServer] send_location error:", e)
               try: self.client.close()
               except: pass
               self.client = None


# -----------------------
# Flask HTTP server
# -----------------------
flask_app = Flask("depthsense_flask")
CORS(flask_app)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


# configure the esp command host/port reachable from the backend
ESP_CMD_HOST = "10.87.74.192"   # change to your ESP IP
ESP_CMD_PORT = 8001


def _send_cmd_to_esp(cmd_text, timeout_connect=1.0, timeout_recv=0.5):
   """
   Helper to send plain-text command to ESP command port and return (ok, resp_or_error).
   """
   text = (cmd_text.strip() + "\n").encode('ascii')
   try:
       s = socket.create_connection((ESP_CMD_HOST, ESP_CMD_PORT), timeout=timeout_connect)
   except Exception as e:
       return False, f"connect_failed: {e}"
   try:
       s.sendall(text)
   except Exception as e:
       try:
           s.close()
       except:
           pass
       return False, f"send_failed: {e}"
   # optional response read
   try:
       s.settimeout(timeout_recv)
       resp = s.recv(512)
       try:
           s.close()
       except:
           pass
       # return decoded response
       try:
           return True, resp.decode('ascii', 'ignore')
       except:
           return True, resp.decode('ascii', errors='ignore') if hasattr(resp, 'decode') else True, str(resp)
   except Exception:
       try:
           s.close()
       except:
           pass
       return True, None


@flask_app.route('/esp/cmd', methods=['POST', 'OPTIONS'])
def esp_cmd_proxy():
   """
   Proxy endpoint that forwards motor commands to the ESP command port.
   Accepts JSON or form: { "cmd": "left" }
   Returns JSON with result.
   """
   # Accept CORS preflight
   if request.method == 'OPTIONS':
       return jsonify({"ok": True}), 200


   data = request.get_json(silent=True)
   if not data:
       data = request.form.to_dict() or {}


   cmd = (data.get('cmd') or '').strip()
   if not cmd:
       return jsonify({"error": "missing cmd"}), 400


   ok, resp = _send_cmd_to_esp(cmd)
   if not ok:
       return jsonify({"error": "failed", "detail": resp}), 502
   # success: return the ESP response if present
   return jsonify({"ok": True, "esp_resp": resp}), 200


# Backwards-compatible route - keep your earlier Streamlit MOTOR_URL that used "/esp"
@flask_app.route('/esp', methods=['POST', 'OPTIONS'])
def esp_proxy_backward():
   # accept same payload; mirror behavior of /esp/cmd
   return esp_cmd_proxy()


@flask_app.route('/video')
def video_mjpeg():
   def gen():
       global latest_frame_jpg
       while True:
           with frame_lock:
               b = latest_frame_jpg
           if b is None:
               blank = np.zeros((480,640,3), dtype=np.uint8)
               ret, tmp = cv2.imencode('.jpg', blank, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
               b = tmp.tobytes()
           yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + b + b'\r\n')
           time.sleep(0.03)
   return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')


@flask_app.route('/location')
def location_http():
   with frame_lock:
       loc = latest_location.copy()
   return jsonify({"location": loc})


@flask_app.route('/status')
def status_http():
   with frame_lock:
       tpl = latest_tuple
       loc = latest_location.copy()
   return jsonify({"tuple": tpl, "location": loc, "ts": time.time()})


@flask_app.route('/signup', methods=['POST', 'OPTIONS'])
def signup_http():
   try:
       data_bytes = request.get_data()
       print("[DEBUG] /signup raw body:", data_bytes)
       print("[DEBUG] /signup headers:", dict(request.headers))
   except Exception as e:
       print("[DEBUG] /signup could not read raw body:", e)


   data = request.get_json(silent=True)
   if not data:
       data = request.form.to_dict() or {}


   username = (data.get('username') or '').strip()
   password = data.get('password') or ''
   full_name = data.get('full_name') or ''
   age = data.get('age')
   try:
       if age is not None:
           age = int(age)
   except:
       age = None
   condition = data.get('condition') or ''
   caretaker_name = data.get('caretaker_name') or ''
   caretaker_contact = data.get('caretaker_contact') or ''


   if not username:
       return jsonify({"error": "username required"}), 400
   if not password:
       return jsonify({"error": "password required"}), 400


   ok, err = db_insert_user(username, password, full_name, age, condition, caretaker_name, caretaker_contact)
   if not ok:
       status = 409 if err == "username exists" else 500
       return jsonify({"error": err}), status


   print(f"[INFO] created user: {username}")
   return jsonify({"ok": True}), 200


@flask_app.route('/login', methods=['POST', 'OPTIONS'])
def login_http():
   try:
       data_bytes = request.get_data()
       print("[DEBUG] /login raw body:", data_bytes)
       print("[DEBUG] /login headers:", dict(request.headers))
   except Exception as e:
       print("[DEBUG] /login raw body read failed:", e)


   data = request.get_json(silent=True)
   if not data:
       data = request.form.to_dict() or {}


   username = (data.get('username') or '').strip()
   password = data.get('password') or ''
   if not username or not password:
       return jsonify({"error": "username and password required"}), 400


   user = db_get_user(username)
   if not user:
       return jsonify({"error": "invalid credentials"}), 401


   stored_hash = user.get('password_hash')
   if not check_password_hash(stored_hash, password):
       return jsonify({"error": "invalid credentials"}), 401


   return jsonify({"ok": True}), 200


@flask_app.route('/profile/<username>', methods=['GET'])
def profile_http(username):
   username = username.strip()
   row = db_get_user(username)
   if not row:
       return jsonify({"error": "not found"}), 404
   row.pop('password_hash', None)
   return jsonify({"profile": row})


def run_flask():
   print(f"[Flask] starting on {FLASK_HOST}:{FLASK_PORT}")
   flask_app.run(host=FLASK_HOST, port=FLASK_PORT, threaded=True, debug=False, use_reloader=False)


@flask_app.route('/set_location', methods=['POST', 'OPTIONS'])
def set_location_http():
   try:
       raw = request.get_data()
       print("[DEBUG] /set_location raw body:", raw)
   except Exception as e:
       print("[DEBUG] /set_location couldn't read raw body:", e)


   data = request.get_json(silent=True)
   if not data:
       data = request.form.to_dict() or {}


   lat = data.get('lat')
   lon = data.get('lon')
   try:
       if lat is not None:
           lat = float(lat)
       if lon is not None:
           lon = float(lon)
   except Exception:
       return jsonify({"error": "lat and lon must be numeric"}), 400


   if lat is None or lon is None:
       return jsonify({"error": "lat and lon required"}), 400


   username = data.get('username')
   timestamp = time.time()
   with frame_lock:
       latest_location['lat'] = lat
       latest_location['lon'] = lon
       latest_location['host_ip'] = latest_location.get('host_ip')
       latest_location['timestamp'] = timestamp
       if username:
           latest_location['username'] = username


   print(f"[INFO] location updated via /set_location: {lat},{lon} (user={username})")
   return jsonify({"ok": True, "lat": lat, "lon": lon, "ts": timestamp}), 200


# -----------------------
# Main loop
# -----------------------
def run_servers_and_loop():
   print("Starting merged MiDaS app with Flask endpoints")
   print("MODEL_PATH:", MODEL_PATH)
   sess = None
   try:
       sess = choose_session(MODEL_PATH)
   except Exception as e:
       print("Failed to create ONNX session:", e)
       sys.exit(1)
   target_size = infer_model_input_size(sess)
   print("model target input:", target_size)


   cap = cv2.VideoCapture(VIDEO_SOURCE)
   if not cap.isOpened():
       print("ERROR: Could not open video source:", VIDEO_SOURCE)
       sys.exit(1)


   input_name = sess.get_inputs()[0].name
   output_name = sess.get_outputs()[0].name


   esp_server = ESPServer(ESP_HOST, ESP_PORT)
   esp_server.start()
   app_server = AppServer(APP_HOST, APP_PORT)
   app_server.start()


   flask_thread = threading.Thread(target=run_flask, daemon=True)
   flask_thread.start()


   min_frame_time = 1.0 / max(1.0, TARGET_FPS)
   last_loc_send = 0.0


   try:
       while True:
           loop_start = time.time()
           ret, frame = cap.read()
           if not ret:
               print("No frame, exiting")
               break
           frame = cv2.flip(frame, 1)
           frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
           h0, w0 = frame.shape[:2]


           inp = preprocess(frame, target_size)
           try:
               out = sess.run([output_name], {input_name: inp})
               pred = out[0]
           except Exception as e:
               print("ONNX inference error:", e)
               break
           dmap = postprocess_depth(pred, w0, h0, invert=INVERT_DEPTH)
           depth_viz = colorize_depth(dmap)


           tpl, picks = detect_close_panes(dmap, threshold=CLOSE_THRESH, min_area=MIN_BLOB_AREA)
           with frame_lock:
               global latest_tuple
               latest_tuple = tpl


           esp_server.send_tuple(tpl)


           vis = depth_viz.copy()
           pane_w = w0 // 3
           cv2.line(vis, (pane_w,0), (pane_w,h0), (255,255,255), 2)
           cv2.line(vis, (2*pane_w,0), (2*pane_w,h0), (255,255,255), 2)
           for pane_idx, b in picks:
               x,y,ww,hh = b['bbox']
               color = (0,255,0) if tpl[pane_idx] else (0,0,255)
               cv2.rectangle(vis, (x,y), (x+ww, y+hh), color, 2)
               cv2.putText(vis, f"p{pane_idx}:{b['mean_depth']:.2f}", (x,y-6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color,1)


           combined = np.concatenate((frame, vis), axis=1)
           cv2.putText(combined, f"TUPLE: {tpl}", (10,30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2, cv2.LINE_AA)


           _, jpg = cv2.imencode('.jpg', combined, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
           jpg_bytes = jpg.tobytes()


           with frame_lock:
               global latest_frame_jpg
               latest_frame_jpg = jpg_bytes


           _, cam_jpg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
           app_server.send_frame(cam_jpg.tobytes())


           now = time.time()
           if now - last_loc_send > GPS_POLL_INTERVAL:
               gps_res = get_precise_gps()
               if gps_res:
                   lat, lon, acc, src = gps_res
                   with frame_lock:
                       latest_location['lat'] = lat
                       latest_location['lon'] = lon
                       latest_location['host_ip'] = latest_location.get('host_ip')
                       latest_location['timestamp'] = now
                       latest_location['gps_source'] = src
                       latest_location['accuracy'] = acc
                   print(f"[GPS] precise coords from {src}: {lat},{lon} (acc={acc})")
               else:
                   loc = get_location()
                   with frame_lock:
                       latest_location['lat'] = loc.get('lat')
                       latest_location['lon'] = loc.get('lon')
                       latest_location['host_ip'] = loc.get('host_ip')
                       latest_location['timestamp'] = loc.get('timestamp')
                   print("[GPS] precise not found, used IP fallback:", latest_location.get('host_ip'))
               app_server.send_location(latest_location)
               last_loc_send = now


           cv2.imshow("RGB (L) | Depth (R)", combined)
           if cv2.waitKey(1) & 0xFF == ord('q'):
               break


           elapsed = time.time() - loop_start
           sleep_time = min_frame_time - elapsed
           if sleep_time > 0:
               time.sleep(sleep_time)


   except KeyboardInterrupt:
       print("Interrupted by user")


   finally:
       cap.release()
       cv2.destroyAllWindows()
       print("Shutting down.")


if __name__ == "__main__":
   run_servers_and_loop()

