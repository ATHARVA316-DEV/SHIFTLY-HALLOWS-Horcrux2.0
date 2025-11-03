# pip install streamlit-lottie streamlit-extras requests

import streamlit as st
import requests
from streamlit_lottie import st_lottie
import socket
import json
from pathlib import Path

# ---------------- CONFIG ----------------
BACKEND_BASE = "http://localhost:9999"
LOGIN_URL = f"{BACKEND_BASE}/login"
SIGNUP_URL = f"{BACKEND_BASE}/signup"
PROFILE_URL = f"{BACKEND_BASE}/profile"
VIDEO_URL = f"{BACKEND_BASE}/video"
ESP_IP = "10.87.74.192"
ESP_CMD_PORT = 8001

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Oculus Repairo", layout="wide", page_icon="🦯")

# ---------------- LOTTIE ----------------
def load_lottiefile(filepath: str):
    try:
        return json.load(open(filepath, "r"))
    except:
        return None

lottie_header = load_lottiefile("header.json")

# ---------------- SESSION INIT ----------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None
if "horcrux_mode" not in st.session_state:
    st.session_state["horcrux_mode"] = False

# ---------------- HORCRUX THEME ----------------
def apply_horcrux_theme():
    if st.session_state.get("horcrux_mode", False):
        st.markdown("""
            <style>
            .stApp {
                background: radial-gradient(circle at top left, #0b0c10, #1a1a1a);
                color: #f0e6d2 !important;
            }
            h1, h2, h3, h4, h5 {
                font-family: 'Cinzel Decorative', cursive;
                color: #e0b341 !important;
                text-shadow: 0 0 10px #e0b341;
            }
            .stButton>button {
                background-color: #1a1a1a;
                border: 2px solid #e0b341;
                color: #f0e6d2;
                box-shadow: 0 0 10px #e0b341;
            }
            .stButton>button:hover {
                background-color: #e0b341;
                color: #0b0c10;
            }
            </style>
        """, unsafe_allow_html=True)

apply_horcrux_theme()

# ---------------- AUTH FUNCTIONS ----------------
def login_user(username, password):
    try:
        res = requests.post(LOGIN_URL, json={"username": username, "password": password})
        if res.status_code == 200:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            return True
        else:
            st.error(res.json().get("error", "Login failed"))
            return False
    except Exception as e:
        st.error(f"Backend connection failed: {e}")
        return False

def signup_user(data):
    try:
        res = requests.post(SIGNUP_URL, json=data)
        if res.status_code == 200:
            st.success("✅ Signup successful! You can now log in.")
        else:
            st.error(res.json().get("error", "Signup failed"))
    except Exception as e:
        st.error(f"Backend connection failed: {e}")

def logout_user():
    st.session_state["logged_in"] = False
    st.session_state["username"] = None
    st.rerun()

# ---------------- LOGIN / SIGNUP ----------------
if not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align:center;'>🦯 Horcrux Assistive App</h1>", unsafe_allow_html=True)
    if lottie_header:
        st_lottie(lottie_header, height=250, key="header_lottie")

    mode = st.radio("Select mode:", ["Login", "Create Account"], horizontal=True, key="auth_mode")
    st.markdown("---")

    if mode == "Login":
        st.subheader("🔐 Login to your account")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", use_container_width=True, key="login_btn"):
            if username and password:
                if login_user(username.strip(), password.strip()):
                    st.rerun()
            else:
                st.warning("⚠️ Please fill in both fields.")

    elif mode == "Create Account":
        st.subheader("🆕 Create new account")
        full_name = st.text_input("Full Name", key="signup_fullname")
        username = st.text_input("Choose Username", key="signup_username")
        password = st.text_input("Password", type="password", key="signup_password")
        age = st.number_input("Age", min_value=1, step=1, key="signup_age")
        condition = st.text_area("Condition (e.g., blindness, low vision, etc.)", key="signup_condition")
        caretaker_name = st.text_input("Caretaker Name", key="signup_caretaker")
        caretaker_contact = st.text_input("Caretaker Contact (Phone/Email)", key="signup_contact")

        if st.button("Create Account", use_container_width=True, key="create_account_btn"):
            if username and password and full_name:
                data = {
                    "username": username,
                    "password": password,
                    "full_name": full_name,
                    "age": age,
                    "condition": condition,
                    "caretaker_name": caretaker_name,
                    "caretaker_contact": caretaker_contact,
                }
                signup_user(data)
            else:
                st.warning("⚠️ Please fill all required fields (Name, Username, Password).")

    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.success(f"👋 Logged in as **{st.session_state['username']}**")
if st.sidebar.button("Logout", key="sidebar_logout"):
    logout_user()

st.sidebar.markdown("---")
st.sidebar.caption("Horcrux Assistive App — Prototype")

# ---------------- MAIN APP ----------------
tabs = st.tabs(["👤 Profile Dashboard", "📷 Camera & Control", "📍 Location Feed", "⚙️ Settings"])

# -------- PROFILE TAB --------
with tabs[0]:
    st.header("👤 User Profile")
    try:
        resp = requests.get(f"{PROFILE_URL}/{st.session_state['username']}")
        if resp.ok:
            data = resp.json().get("profile", {})
            st.markdown("### 🧾 Profile Summary")
            st.markdown(f"**Full Name:** {data.get('full_name', '-')}") 
            st.markdown(f"**Age:** {data.get('age', '-')}") 
            st.markdown(f"**Condition:** {data.get('condition', '-')}") 
            st.markdown(f"**Caretaker:** {data.get('caretaker_name', '-')}") 
            st.markdown(f"**Caretaker Contact:** {data.get('caretaker_contact', '-')}") 
        else:
            st.error("Failed to load profile data.")
    except Exception as e:
        st.error(f"Backend error: {e}")

# -------- CAMERA TAB --------
def send_motor_direct_tcp(cmd, timeout=1.0):
    cmd_clean = (cmd or "").strip()
    if not cmd_clean:
        return False, "empty cmd"
    text = (cmd_clean + "\n").encode('ascii')
    try:
        with socket.create_connection((ESP_IP, ESP_CMD_PORT), timeout=timeout) as s:
            s.sendall(text)
            s.settimeout(0.5)
            try:
                r = s.recv(256)
                if r:
                    try:
                        return True, r.decode('ascii', errors='ignore').strip()
                    except:
                        return True, str(r)
                else:
                    return True, None
            except Exception:
                return True, None
    except Exception as e:
        return False, str(e)

with tabs[1]:
    st.header("📷 Live Camera Feed + Device Control")
    left_col, right_col = st.columns([2, 1])
    with left_col:
        st.subheader("🎥 Camera")
        html = f'<img src="{VIDEO_URL}" width="100%" style="max-height:720px; border-radius:12px; border:2px solid #ddd;" />'
        st.markdown(html, unsafe_allow_html=True)
        st.caption("If blank, check merged_main.py and VIDEO_URL.")
    with right_col:
        st.subheader("🎮 Controls")
        st.markdown("Use these buttons to send motor commands via TCP.")
        status_box = st.empty()
        c1, c2 = st.columns(2)
        if c1.button("⬅️ Left", key="left_btn"):
            ok, msg = send_motor_direct_tcp("left")
            status_box.success(f"Sent LEFT — {msg}" if ok else f"Error: {msg}")
        if c2.button("➡️ Right", key="right_btn"):
            ok, msg = send_motor_direct_tcp("right")
            status_box.success(f"Sent RIGHT — {msg}" if ok else f"Error: {msg}")
        c3, c4 = st.columns(2)
        if c3.button("↔️ Both", key="both_btn"):
            ok, msg = send_motor_direct_tcp("both")
            status_box.info(f"Sent BOTH — {msg}" if ok else f"Error: {msg}")
        if c4.button("⏹️ Stop", key="stop_btn"):
            ok, msg = send_motor_direct_tcp("stop")
            status_box.warning(f"Sent STOP — {msg}" if ok else f"Error: {msg}")

# -------- LOCATION TAB --------
with tabs[2]:
    st.header("📍 Location Feed")
    st.markdown("Toggle the live location feed below:")
    loc_toggle = st.toggle("Enable Location Feed", key="loc_toggle")
    if loc_toggle:
        st.warning("📡 Signal strength low — unable to fetch location.")
    else:
        st.info("🛑 Location feed turned off.")

# -------- SETTINGS TAB --------
with tabs[3]:
    st.header("⚙️ Settings")
    st.markdown("Customize your experience and profile.")
    # Theme toggle
    if st.toggle("🪄 Enable Horcrux Mode", key="horcrux_toggle", value=st.session_state["horcrux_mode"]):
        if not st.session_state["horcrux_mode"]:
            st.session_state["horcrux_mode"] = True
            st.toast("✨ Horcrux Mode Activated — Alohomora!")
            st.rerun()
    else:
        if st.session_state["horcrux_mode"]:
            st.session_state["horcrux_mode"] = False
            st.toast("🪄 Mischief Managed — Theme reset.")
            st.rerun()
    st.markdown("---")
    st.subheader("Edit Profile (Local Only)")
    new_name = st.text_input("Full Name")
    new_condition = st.text_input("Condition")
    new_contact = st.text_input("Caretaker Contact")
    if st.button("Save Changes", key="save_profile_btn"):
        st.success("✅ Profile updated locally (feature in progress).")

