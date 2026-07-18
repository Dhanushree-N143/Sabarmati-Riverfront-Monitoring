from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import requests
import logging
import cv2
import numpy as np
import time
import base64

# ================= CRITICAL PATH CALCULATION =================
# Find the absolute path to the directory containing main.py
BASE_DIR = Path(__file__).resolve().parent 
# Calculate the absolute path to the web_ui folder (one level up)
STATIC_DIR = BASE_DIR.parent / "web_ui" 
# ==============================================================

# ================= CONFIGURATION =================
# MOTOR CONTROLLER IP (The device that executes the commands)
ESP32_IP = "192.168.139.88"
ESP32_URL = f"http://{ESP32_IP}/cmd"
# =================================================

# 1. DEFINE THE APP OBJECT FIRST
app = FastAPI()

# 2. MOUNT STATIC FILES ONCE using the ABSOLUTE path
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Global state to hold the latest video frame, command, and count
global_state = {
    "frame": None,
    "latest_command": "S",
    "waste_count": 0,
    "esp32_ip": ESP32_IP
}

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper function to generate the MJPEG stream
def video_generator():
    global global_state
    while True:
        if global_state["frame"] is not None:
            ret, buffer = cv2.imencode('.jpg', global_state["frame"])
            if ret:
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            time.sleep(0.05)

# --- Endpoints for Frontend ---

@app.get("/")
def serve_frontend_redirect():
    """ Serves the main index.html file. """
    try:
        # Use the absolute path to open index.html
        with open(STATIC_DIR / "index.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse("<html><body><h1>Error: index.html not found. Check path.</h1></body></html>", status_code=404)

@app.get("/video_feed")
def video_feed():
    """ Provides the MJPEG stream of the processed frame. """
    return StreamingResponse(video_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/status_data")
def get_status_data():
    """ Provides real-time command, count, and IP data to the frontend script. """
    global global_state
    return {
        "command": global_state["latest_command"],
        "count": global_state["waste_count"],
        "ip": global_state["esp32_ip"]
    }

# --- Endpoint for AI to Send Frames and Count ---
@app.post("/frame_in")
async def receive_frame(frame_data: dict):
    """ Receives the base64 encoded frame and detection count from the AI script. """
    global global_state
    
    try:
        img_bytes = base64.b64decode(frame_data['frame'])
        np_arr = np.frombuffer(img_bytes, np.uint8)
        global_state["frame"] = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        global_state["waste_count"] = frame_data.get("count", 0)

        return {"status": "frame received"}
    except Exception as e:
        return {"status": "error", "detail": f"Frame decode error: {e}"}


# --- Endpoint for AI Controller to Send Command ---
@app.get("/command")
def send_command(c: str):
    """
    Receives command from AI Controller and forwards to ESP32 Motor Controller.
    """
    global global_state
    command_char = c.upper()
    global_state["latest_command"] = command_char 

    if command_char not in ['F', 'L', 'R', 'S']:
        raise HTTPException(status_code=400, detail="Invalid Command")

    try:
        logger.info(f"Sending command {command_char} to ESP32 Motor Controller...")
        response = requests.get(ESP32_URL, params={'c': command_char}, timeout=7.0) 
        
        if response.status_code == 200:
            return {"status": "success", "esp32_response": response.text}
        else:
            return {"status": "error", "esp32_code": response.status_code}
            
    except requests.exceptions.ReadTimeout:
        logger.error("ESP32 Timeout (BUSY) - Boat is executing command.")
        return {"status": "error", "detail": "Boat is busy executing command."}
    except Exception as e:
        logger.error(f"Failed to connect to Motor Controller: {e}")
        return {"status": "error", "detail": "Motor Controller Unreachable"}