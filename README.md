# SHIFTLY-HALLOWS-Horcrux2.0
# 🦯 Oculus Repairo - Assistive Navigation System

**Oculus Repairo** is a real-time assistive navigation system designed to help visually impaired individuals navigate their environment safely. The system uses AI-powered depth sensing, obstacle detection, and haptic feedback to provide spatial awareness through connected devices.

---

## 🌟 Features

### Core Functionality
- **Real-time Depth Sensing**: Uses MiDaS ONNX model for depth estimation from live camera feed
- **Intelligent Obstacle Detection**: Divides field of view into three zones (left, center, right) for precise spatial mapping
- **Haptic Feedback System**: Sends real-time alerts to ESP32/ESP8266 wearable devices
- **Live Video Streaming**: MJPEG stream with depth map overlay for monitoring
- **User Authentication**: Secure login/signup with password hashing
- **Profile Management**: Store user information and emergency caretaker contacts
- **GPS Location Tracking**: Multi-source GPS support (GPSD, Serial GPS, IP geolocation)
- **Manual Device Control**: Override automatic alerts with manual motor commands
- **Themed UI**: Optional "Horcrux Mode" with custom styling

### Technical Highlights
- Multi-threaded architecture for concurrent video processing and server operations
- Thread-safe state management for real-time data sharing
- RESTful API for integration with mobile apps and external services
- TCP servers for low-latency device communication
- SQLite database for persistent user data storage

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Oculus Repairo System                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Camera     │───▶│  MiDaS ONNX  │───▶│    Depth     │  │
│  │   Input      │    │   Inference  │    │  Processing  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                   │           │
│                                                   ▼           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │     GPS      │    │   Obstacle   │    │   Haptic     │  │
│  │   Tracking   │    │   Detection  │───▶│   Feedback   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                   │           │
│  ┌──────────────────────────────────────────────┼─────────┐ │
│  │              Backend Server (server.py)       │         │ │
│  │  ┌────────────────────────────────────────────┴───────┐ │ │
│  │  │  Flask HTTP API (Port 9999)                        │ │ │
│  │  │  - Authentication (/login, /signup)                │ │ │
│  │  │  - Video Streaming (/video)                        │ │ │
│  │  │  - Location Services (/location, /set_location)    │ │ │
│  │  │  - Device Control (/esp/cmd)                       │ │ │
│  │  │  - Profile Management (/profile/<username>)        │ │ │
│  │  └────────────────────────────────────────────────────┘ │ │
│  │                                                           │ │
│  │  ┌────────────────────────────────────────────────────┐ │ │
│  │  │  TCP Servers                                        │ │ │
│  │  │  - ESP Server (Port 5001): Obstacle data to device │ │ │
│  │  │  - App Server (Port 5002): Video & GPS to mobile   │ │ │
│  │  └────────────────────────────────────────────────────┘ │ │
│  │                                                           │ │
│  │  ┌────────────────────────────────────────────────────┐ │ │
│  │  │  SQLite Database (users.db)                        │ │ │
│  │  │  - User profiles & authentication                   │ │ │
│  │  └────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │          Frontend Application (app.py)                    │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  Streamlit Web Interface (Port 8501)               │  │ │
│  │  │  - Login/Signup UI                                 │  │ │
│  │  │  - Profile Dashboard                               │  │ │
│  │  │  - Live Camera Feed & Controls                     │  │ │
│  │  │  - Location Feed                                   │  │ │
│  │  │  - Settings & Theme Customization                  │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
└────────────────────────────────────────────────────────────────┘
           │                           │                │
           ▼                           ▼                ▼
    ┌──────────┐              ┌──────────┐      ┌──────────┐
    │   ESP    │              │  Mobile  │      │   Web    │
    │  Device  │              │   App    │      │ Browser  │
    └──────────┘              └──────────┘      └──────────┘
```

---

## 📋 Prerequisites

### Hardware Requirements
- **Webcam/USB Camera**: For video input and depth sensing
- **ESP32/ESP8266 Device**: For haptic feedback (optional)
- **GPS Module**: NEO-6M, NEO-7M, or similar (optional)
- **Minimum RAM**: 4GB (8GB recommended for optimal performance)

### Software Requirements
- **Python**: 3.8 or higher
- **Operating System**: Linux, macOS, or Windows
- **Network**: Local network access for device communication

---

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd oculus-repairo
```

### 2. Install Core Dependencies
```bash
# Core packages
pip install streamlit streamlit-lottie streamlit-extras requests

# Backend packages
pip install opencv-python numpy onnxruntime flask flask-cors werkzeug

# Database (usually pre-installed with Python)
pip install sqlite3
```

### 3. Install Optional GPS Support
```bash
# For GPSD daemon support
pip install gps3

# For direct serial GPS connection
pip install pyserial pynmea2
```

### 4. Download MiDaS Model
```bash
# Create models directory
mkdir -p models

# Download MiDaS v2.1 ONNX model (384x384)
# Option 1: Using wget
wget -O models/midas_v21_384.onnx https://github.com/isl-org/MiDaS/releases/download/v2_1/model-small.onnx

# Option 2: Manual download
# Visit: https://github.com/isl-org/MiDaS/releases
# Download model-small.onnx and save as models/midas_v21_384.onnx
```

### 5. Setup Project Structure
```bash
# Your project should look like this:
oculus-repairo/
├── app.py                 # Streamlit frontend
├── server.py              # Backend server
├── models/
│   └── midas_v21_384.onnx # MiDaS depth model
├── header.json            # Lottie animation (optional)
├── users.db               # Created automatically on first run
└── README.md
```

### 6. Create Lottie Animation (Optional)
```bash
# Download a free Lottie animation from lottiefiles.com
# Save as header.json in the project root
# Or create header.json with: echo '{}' > header.json
```

---

## ⚙️ Configuration

### Backend Configuration (`server.py`)

Edit the configuration section at the top of `server.py`:

```python
# -----------------------
# Model & Video Settings
# -----------------------
MODEL_PATH = "models/midas_v21_384.onnx"  # Path to MiDaS ONNX model
VIDEO_SOURCE = 0                          # 0=default webcam, 1=USB cam, or "/path/to/video.mp4"
TARGET_FPS = 30.0                         # Target frame rate (lower = less CPU usage)
INVERT_DEPTH = False                      # Invert depth map if needed
USE_CUBIC_RESIZE = True                   # Use cubic interpolation (better quality)

# -----------------------
# Server Ports
# -----------------------
ESP_HOST = ""             # Empty = bind to all interfaces
ESP_PORT = 5001           # TCP port for ESP device communication
APP_HOST = ""             # Empty = bind to all interfaces
APP_PORT = 5002           # TCP port for mobile app communication
FLASK_HOST = "0.0.0.0"    # HTTP API host
FLASK_PORT = 9999         # HTTP API port

# -----------------------
# ESP Device Settings
# -----------------------
ESP_CMD_HOST = "10.87.74.192"  # Your ESP device IP address
ESP_CMD_PORT = 8001            # ESP command port

# -----------------------
# Obstacle Detection
# -----------------------
CLOSE_THRESH = 0.70       # Depth threshold (0-1): higher = only very close objects
MIN_BLOB_AREA = 200       # Minimum pixels for obstacle detection
ESP_SEND_INTERVAL = 0.15  # Seconds between updates to ESP device

# -----------------------
# GPS Settings
# -----------------------
GPS_SERIAL_DEVICE = "/dev/ttyUSB0"  # Serial GPS device path (Linux/Mac)
                                     # Windows: "COM3", "COM4", etc.
GPS_BAUDRATE = 9600                 # GPS module baud rate
GPS_POLL_INTERVAL = 2.0             # Seconds between GPS reads

# -----------------------
# Database
# -----------------------
DB_PATH = "users.db"      # SQLite database file path
```

### Frontend Configuration (`app.py`)

Edit the configuration section at the top of `app.py`:

```python
# ---------------- CONFIG ----------------
BACKEND_BASE = "http://localhost:9999"  # Backend server URL
LOGIN_URL = f"{BACKEND_BASE}/login"
SIGNUP_URL = f"{BACKEND_BASE}/signup"
PROFILE_URL = f"{BACKEND_BASE}/profile"
VIDEO_URL = f"{BACKEND_BASE}/video"

ESP_IP = "10.87.74.192"     # Your ESP device IP address
ESP_CMD_PORT = 8001         # ESP command port
```
## 🔌 Hardware Setup


<img width="1204" height="1600" alt="image" src="https://github.com/user-attachments/assets/51168a53-d19c-4fac-8b36-b9abe763bb82" />


*Complete hardware assembly showing ESP32, GPS module, vibration motors, and connections*
### ESP Device Configuration

Your ESP device should be configured to:

1. **Connect to WiFi**: Same network as the server
2. **Listen on TCP Port 5001**: For automatic obstacle data
   - Receives tuples like `(0,1,0)` where 1 = obstacle detected
3. **Listen on TCP Port 8001**: For manual motor commands
   - Receives text commands: "left", "right", "both", "stop"

**Example ESP32 Code Snippet:**
```cpp
// TCP server for obstacle data (port 5001)
WiFiServer obstacleServer(5001);
WiFiClient obstacleClient;

// TCP server for manual commands (port 8001)
WiFiServer commandServer(8001);
WiFiClient commandClient;

void setup() {
  WiFi.begin(ssid, password);
  obstacleServer.begin();
  commandServer.begin();
  
  // Setup motors/vibration
  pinMode(MOTOR_LEFT, OUTPUT);
  pinMode(MOTOR_RIGHT, OUTPUT);
}

void loop() {
  // Check for obstacle data
  if (obstacleServer.hasClient()) {
    obstacleClient = obstacleServer.available();
  }
  if (obstacleClient && obstacleClient.available()) {
    String data = obstacleClient.readStringUntil('\n');
    // Parse tuple: (0,1,0) -> obstacle in center
    processTuple(data);
  }
  
  // Check for manual commands
  if (commandServer.hasClient()) {
    commandClient = commandServer.available();
  }
  if (commandClient && commandClient.available()) {
    String cmd = commandClient.readStringUntil('\n');
    processCommand(cmd);
  }
}
```

---

## 🎯 Usage

### Step 1: Start the Backend Server

```bash
python server.py
```

**Expected Output:**
```
Starting merged MiDaS app with Flask endpoints
MODEL_PATH: models/midas_v21_384.onnx
Available ONNX providers: ['CPUExecutionProvider']
Using provider order: ['CPUExecutionProvider']
model target input: 384
[ESPServer] listening on :5001
[AppServer] listening on :5002
[Flask] starting on 0.0.0.0:9999
```

**What It Does:**
- Initializes SQLite database (`users.db`)
- Loads MiDaS ONNX model for depth estimation
- Opens camera/video source
- Starts Flask HTTP server (port 9999)
- Starts TCP servers for ESP (5001) and App (5002)
- Begins real-time depth processing and obstacle detection
- Opens OpenCV window showing RGB + Depth visualization

### Step 2: Start the Frontend Application

Open a new terminal:

```bash
streamlit run app.py
```

**Expected Output:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.100:8501
```

The web interface will automatically open in your browser.

### Step 3: Create an Account

1. **Select "Create Account"** on the login page
2. **Fill in your details:**
   - **Full Name**: Your full name
   - **Username**: Choose a unique username
   - **Password**: Secure password
   - **Age**: Your age
   - **Condition**: E.g., "Complete blindness", "Low vision", "Peripheral vision loss"
   - **Caretaker Name**: Emergency contact name
   - **Caretaker Contact**: Phone number or email
3. **Click "Create Account"**
4. You'll see a success message

### Step 4: Login

1. **Select "Login"** mode
2. **Enter your username and password**
3. **Click "Login"**
4. You'll be redirected to the main dashboard

### Step 5: Explore the Interface

#### 👤 Profile Dashboard Tab
- View your complete profile information
- See caretaker emergency contact details
- Check your registered condition

#### 📷 Camera & Control Tab
- **Live Video Feed**: See real-time camera feed with depth overlay
  - Left side: Original RGB video
  - Right side: Depth map with obstacle detection zones
- **Manual Controls**: Override automatic alerts
  - ⬅️ **Left**: Activate left haptic motor
  - ➡️ **Right**: Activate right haptic motor
  - ↕️ **Both**: Activate both motors
  - ⏹️ **Stop**: Stop all motors

#### 📍 Location Feed Tab
- Toggle GPS location tracking
- View current coordinates (when available)
- Monitor GPS signal strength

#### ⚙️ Settings Tab
- **Enable Horcrux Mode**: Toggle themed UI
- **Edit Profile**: Update your information (local only in current version)

---

## 🎮 Motor Control System

### Automatic Obstacle Detection

The system continuously analyzes the camera feed and divides it into three zones:

```
┌──────────┬──────────┬──────────┐
│   LEFT   │  CENTER  │  RIGHT   │
│  Zone 0  │  Zone 1  │  Zone 2  │
└──────────┴──────────┴──────────┘
```

**Tuple Format:** `(left, center, right)`
- `(0, 0, 0)`: All clear
- `(1, 0, 0)`: Obstacle on left
- `(0, 1, 0)`: Obstacle in center
- `(0, 0, 1)`: Obstacle on right
- `(1, 1, 1)`: Obstacles everywhere

**Example Scenarios:**
- Walking toward a wall: `(0, 1, 0)` → Center motor vibrates
- Person on your left: `(1, 0, 0)` → Left motor vibrates
- Narrow doorway: `(1, 1, 1)` → Both motors vibrate

### Manual Control Commands

You can override automatic detection using manual controls:

| Command | Action | Use Case |
|---------|--------|----------|
| `left` | Activate left motor | Test left haptic feedback |
| `right` | Activate right motor | Test right haptic feedback |
| `both` | Activate both motors | Test both motors simultaneously |
| `stop` | Stop all motors | Emergency stop or reset |

### Detection Sensitivity Adjustment

Fine-tune obstacle detection in `server.py`:

```python
# More sensitive (detects farther objects)
CLOSE_THRESH = 0.50
MIN_BLOB_AREA = 100

# Less sensitive (only very close objects)
CLOSE_THRESH = 0.80
MIN_BLOB_AREA = 500

# Default (balanced)
CLOSE_THRESH = 0.70
MIN_BLOB_AREA = 200
```

---

## 📡 API Documentation

### Authentication Endpoints

#### POST `/signup`
Create a new user account.

**Request:**
```json
{
  "username": "john_doe",
  "password": "secure_password",
  "full_name": "John Doe",
  "age": 35,
  "condition": "Complete blindness",
  "caretaker_name": "Jane Doe",
  "caretaker_contact": "+1-555-0123"
}
```

**Response (Success):**
```json
{
  "ok": true
}
```

**Response (Error):**
```json
{
  "error": "username exists"
}
```

#### POST `/login`
Authenticate a user.

**Request:**
```json
{
  "username": "john_doe",
  "password": "secure_password"
}
```

**Response (Success):**
```json
{
  "ok": true
}
```

**Response (Error):**
```json
{
  "error": "invalid credentials"
}
```

### Profile Endpoints

#### GET `/profile/<username>`
Retrieve user profile information.

**Response:**
```json
{
  "profile": {
    "username": "john_doe",
    "full_name": "John Doe",
    "age": 35,
    "condition": "Complete blindness",
    "caretaker_name": "Jane Doe",
    "caretaker_contact": "+1-555-0123"
  }
}
```

### Video & Data Endpoints

#### GET `/video`
Stream MJPEG video feed with depth overlay.

**Response:** Multipart MJPEG stream
**Content-Type:** `multipart/x-mixed-replace; boundary=frame`

**Usage:**
```html
<img src="http://localhost:9999/video" />
```

#### GET `/location`
Get current GPS location.

**Response:**
```json
{
  "location": {
    "lat": 37.7749,
    "lon": -122.4194,
    "host_ip": "192.168.1.100",
    "timestamp": 1699999999.123,
    "gps_source": "gpsd",
    "accuracy": 5.2
  }
}
```

#### POST `/set_location`
Manually update location (useful for mobile apps).

**Request:**
```json
{
  "lat": 37.7749,
  "lon": -122.4194,
  "username": "john_doe"
}
```

**Response:**
```json
{
  "ok": true,
  "lat": 37.7749,
  "lon": -122.4194,
  "ts": 1699999999.123
}
```

#### GET `/status`
Get system status including current obstacle tuple and location.

**Response:**
```json
{
  "tuple": [0, 1, 0],
  "location": {
    "lat": 37.7749,
    "lon": -122.4194,
    "host_ip": "192.168.1.100",
    "timestamp": 1699999999.123
  },
  "ts": 1699999999.456
}
```

### Device Control Endpoints

#### POST `/esp/cmd`
Send motor command to ESP device.

**Request:**
```json
{
  "cmd": "left"
}
```

**Accepted Commands:** `left`, `right`, `both`, `stop`

**Response (Success):**
```json
{
  "ok": true,
  "esp_resp": "OK"
}
```

**Response (Error):**
```json
{
  "error": "failed",
  "detail": "connect_failed: [Errno 61] Connection refused"
}
```

---

## 🗄️ Database Schema

### Users Table

```sql
CREATE TABLE users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    age INTEGER,
    condition TEXT,
    caretaker_name TEXT,
    caretaker_contact TEXT
);
```

**Field Descriptions:**
- `username`: Unique identifier (primary key)
- `password_hash`: Werkzeug-hashed password (never stored in plaintext)
- `full_name`: User's full name
- `age`: User's age in years
- `condition`: Visual impairment description
- `caretaker_name`: Emergency contact name
- `caretaker_contact`: Emergency contact phone/email

**Security Notes:**
- Passwords are hashed using `werkzeug.security.generate_password_hash()`
- Database file (`users.db`) should never be committed to version control
- Add `users.db` to `.gitignore`

---

## 🔧 Troubleshooting

### Camera Issues

**Problem:** Camera feed not showing / blank screen

**Solutions:**
1. **Check camera availability:**
   ```bash
   # Linux
   ls /dev/video*
   
   # Test with OpenCV
   python -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL')"
   ```

2. **Try different video sources:**
   ```python
   VIDEO_SOURCE = 0  # Default camera
   VIDEO_SOURCE = 1  # Second camera
   VIDEO_SOURCE = "/dev/video1"  # Specific device (Linux)
   ```

3. **Check camera permissions:**
   ```bash
   # Linux: Add user to video group
   sudo usermod -a -G video $USER
   
   # Logout and login again
   ```

4. **Verify no other app is using the camera:**
   ```bash
   # Linux: Find processes using camera
   lsof /dev/video0
   ```

### ESP Device Connection Issues

**Problem:** ESP device not connecting / timeout errors

**Solutions:**
1. **Verify network connectivity:**
   ```bash
   # Ping ESP device
   ping 10.87.74.192
   
   # Check if ESP is listening
   nc -zv 10.87.74.192 5001
   nc -zv 10.87.74.192 8001
   ```

2. **Check firewall settings:**
   ```bash
   # Linux: Allow ports
   sudo ufw allow 5001/tcp
   sudo ufw allow 8001/tcp
   sudo ufw allow 9999/tcp
   
   # macOS: Check System Preferences → Security & Privacy → Firewall
   ```

3. **Verify ESP configuration:**
   - Ensure ESP is connected to the same network
   - Check ESP serial monitor for connection logs
   - Confirm WiFi credentials are correct
   - Verify ports match in ESP code and server config

4. **Update IP addresses:**
   ```python
   # In server.py
   ESP_CMD_HOST = "YOUR_ESP_IP"
   
   # In app.py
   ESP_IP = "YOUR_ESP_IP"
   ```

### ONNX Runtime Errors

**Problem:** Model loading fails / inference errors

**Solutions:**
1. **Verify model file exists:**
   ```bash
   ls -lh models/midas_v21_384.onnx
   ```

2. **Check ONNX Runtime installation:**
   ```bash
   pip list | grep onnx
   pip install --upgrade onnxruntime
   ```

3. **Try different providers:**
   ```python
   # In server.py, modify choose_session()
   
   # Force CPU only
   sess = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
   
   # Try GPU if available
   sess = ort.InferenceSession(model_path, providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
   ```

4. **Reduce frame size if performance issues:**
   ```python
   TARGET_FPS = 15.0  # Lower FPS
   USE_CUBIC_RESIZE = False  # Faster interpolation
   ```

### GPS Not Working

**Problem:** No GPS coordinates / location unavailable

**Solutions:**
1. **For GPSD:**
   ```bash
   # Install gpsd
   sudo apt-get install gpsd gpsd-clients
   
   # Start gpsd
   sudo systemctl start gpsd
   sudo systemctl enable gpsd
   
   # Test connection
   cgps -s
   ```

2. **For Serial GPS:**
   ```bash
   # Find GPS device
   ls /dev/ttyUSB* /dev/ttyACM*
   
   # Test with screen
   screen /dev/ttyUSB0 9600
   # You should see NMEA sentences
   ```

3. **Check permissions:**
   ```bash
   # Add user to dialout group (Linux)
   sudo usermod -a -G dialout $USER
   ```

4. **Verify GPS has satellite fix:**
   - GPS modules need clear sky view
   - Initial fix can take 1-5 minutes outdoors
   - Check LED indicators on GPS module

5. **Fallback to IP geolocation:**
   - System automatically falls back to IP-based location
   - Less accurate but works indoors
   - Requires internet connection

### Backend Connection Failed

**Problem:** Streamlit can't connect to backend

**Solutions:**
1. **Verify backend is running:**
   ```bash
   # Check if Flask is running
   curl http://localhost:9999/status
   ```

2. **Check port availability:**
   ```bash
   # Linux/Mac
   lsof -i :9999
   
   # Windows
   netstat -ano | findstr :9999
   ```

3. **Update backend URL:**
   ```python
   # In app.py
   BACKEND_BASE = "http://localhost:9999"
   # Or use computer's IP for remote access
   BACKEND_BASE = "http://192.168.1.100:9999"
   ```

4. **Check firewall:**
   ```bash
   # Allow Flask port
   sudo ufw allow 9999/tcp
   ```

### Performance Issues

**Problem:** Low FPS / laggy video

**Solutions:**
1. **Reduce target FPS:**
   ```python
   TARGET_FPS = 15.0  # Lower = less CPU usage
   ```

2. **Lower JPEG quality:**
   ```python
   # In server.py, modify imencode calls
   cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])  # Lower quality
   ```

3. **Disable OpenCV window:**
   ```python
   # Comment out in main loop
   # cv2.imshow("RGB (L) | Depth (R)", combined)
   # if cv2.waitKey(1) & 0xFF == ord('q'):
   #     break
   ```

4. **Use smaller model:**
   - Download MiDaS v2.1 small model (256x256 instead of 384x384)
   - Update MODEL_PATH accordingly

5. **Close unnecessary applications:**
   - Free up RAM and CPU resources
   - Close other video/camera applications

---

## 🔒 Security Best Practices

### For Development
- ✅ Passwords are hashed using Werkzeug's secure hash functions
- ✅ Database file is automatically created with proper schema
- ⚠️ HTTP used by default (not HTTPS)
- ⚠️ No session management or JWT tokens
- ⚠️ No rate limiting on authentication endpoints

### For Production

**Critical Steps:**

1. **Enable HTTPS:**
   ```python
   # Use a reverse proxy like Nginx
   # Or configure Flask with SSL certificates
   flask_app.run(ssl_context=('cert.pem', 'key.pem'))
   ```

2. **Add rate limiting:**
   ```python
   from flask_limiter import Limiter
   limiter = Limiter(flask_app, key_func=lambda: request.remote_addr)
   
   @flask_app.route('/login', methods=['POST'])
   @limiter.limit("5 per minute")
   def login_http():
       # existing code
   ```

3. **Use environment variables:**
   ```python
   import os
   ESP_CMD_HOST = os.getenv('ESP_IP', '10.87.74.192')
   DB_PATH = os.getenv('DB_PATH', 'users.db')
   ```

4. **Add authentication tokens:**
   ```python
   from flask_jwt_extended import JWTManager, create_access_token
   jwt = JWTManager(flask_app)
   ```

5. **Secure database:**
   ```bash
   # Set proper permissions
   chmod 600 users.db
   
   # Backup regularly
   sqlite3 users.db .dump > backup.sql
   ```

6. **Add .gitignore:**
   ```
   users.db
   *.pyc
   __pycache__/
   .env
   *.log
   ```

7. **Change default ports:**
   ```python
   FLASK_PORT = 8443  # Non-standard port
   ESP_PORT = 50001   # High port number
   ```

8. **Input validation:**
   ```python
   import re
   
   def validate_username(username):
       return re.match(r'^[a-zA-Z0-9_]{3,20}$', username) is not None
   ```

---




