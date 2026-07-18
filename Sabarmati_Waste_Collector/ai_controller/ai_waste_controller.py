import cv2 
import requests
import time
import base64
import numpy as np
import sys # CRITICAL: For reading command-line arguments

# ================= CONFIGURATION =================
# 1. ROBOFLOW CREDENTIALS
ROBOFLOW_API_KEY = "fGRpIkPIGAX5zi4qpD9f"
ROBOFLOW_MODEL = "marine-debris-detection-orq09"
ROBOFLOW_VERSION = "1"
ROBOFLOW_URL = f"https://detect.roboflow.com/{ROBOFLOW_MODEL}/{ROBOFLOW_VERSION}?api_key={ROBOFLOW_API_KEY}"

# 2. VIDEO SOURCE DEFINITION
# Map index numbers to file paths or webcam ID (0)
VIDEO_SOURCES = {
    1: "waste.mp4",
    2: "waste2.mp4",
    3: "waste3.mp4",
    0: 0, # Laptop Webcam
    # Add ESP32-CAM stream here if needed: 4: "http://192.168.139.xx:8080/stream"
}

# 3. BACKEND CONNECTION (FASTAPI)
BACKEND_CMD_URL = "http://localhost:8000/command?c="
BACKEND_FRAME_URL = "http://localhost:8000/frame_in"

# Logic Settings
CMD_COOLDOWN = 0.5         
CMD_TIMEOUT = 7.0          
CONFIDENCE_THRESHOLD = 0.4 

# =================================================

last_cmd_time = 0
last_cmd = "S"

# --- FUNCTION TO GET VIDEO PATH FROM COMMAND LINE ---
def get_video_path():
    """ Determines the video source based on the argument passed to the script. """
    default_index = 1
    
    # Check if a command-line argument was provided (sys.argv[0] is the script name)
    if len(sys.argv) > 1:
        try:
            # Try to convert the first argument to an integer index
            chosen_index = int(sys.argv[1])
            if chosen_index in VIDEO_SOURCES:
                return chosen_index, VIDEO_SOURCES[chosen_index]
            else:
                print(f"Warning: Index {chosen_index} not found. Using default video 1.")
        except ValueError:
            print("Warning: Invalid video index argument. Using default video 1.")

    return default_index, VIDEO_SOURCES[default_index]
# ----------------------------------------------------


def send_command(cmd):
    """ Sends command to the local FastAPI backend. """
    global last_cmd, last_cmd_time
    
    if cmd == last_cmd and (time.time() - last_cmd_time) < CMD_COOLDOWN:
        return

    try:
        final_cmd = cmd
        if cmd == "C": 
            final_cmd = "F" # Map Center logic to Forward movement
            
        print(f"[AI] Detected: {cmd} -> Sending: {final_cmd}")
        
        requests.get(BACKEND_CMD_URL + final_cmd, timeout=CMD_TIMEOUT) 
        
        last_cmd = cmd
        last_cmd_time = time.time()
    except Exception as e:
        # Ignore frequent errors (e.g., if the ESP32 is busy)
        pass

def get_roboflow_predictions(frame):
    """ Sends frame to Roboflow and returns predictions. """
    try:
        retval, buffer = cv2.imencode('.jpg', frame)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        
        resp = requests.post(ROBOFLOW_URL, data=jpg_as_text, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=5.0)
        
        if resp.status_code == 200:
            return resp.json().get("predictions", [])
        else:
            return []
    except:
        return []

def main():
    # CRITICAL: Determine the video source from the command line
    VIDEO_SOURCE_INDEX, VIDEO_PATH = get_video_path()
    
    cap = cv2.VideoCapture(VIDEO_PATH) 
    
    if not cap.isOpened():
        print(f"Error: Could not open video source: {VIDEO_PATH}. Ensure the file exists or index is correct.")
        return

    print(f"AI Controller Started. Processing frames from source index {VIDEO_SOURCE_INDEX} ({VIDEO_PATH}).")

    while True:
        ret, frame = cap.read()
        if not ret:
            # Loop video file or try reconnecting webcam
            if isinstance(VIDEO_PATH, str):
                 cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            else:
                 cap = cv2.VideoCapture(VIDEO_PATH)
            continue

        height, width, _ = frame.shape
        left_limit = width // 3
        right_limit = 2 * (width // 3)

        # 1. Get AI Predictions
        predictions = get_roboflow_predictions(frame)
        
        target_cmd = "S" 
        max_area = 0
        detection_count = len(predictions) 

        for p in predictions:
            if p['confidence'] < CONFIDENCE_THRESHOLD:
                continue

            # Draw Box & Label on the frame for the dashboard
            x, y, w, h = p['x'], p['y'], p['width'], p['height']
            x1 = int(x - w/2); y1 = int(y - h/2); x2 = int(x + w/2); y2 = int(y + h/2)
            color = (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{p['class']} {int(p['confidence']*100)}%", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Logic: Track the largest object to center
            area = w * h
            if area > max_area:
                max_area = area
                if x < left_limit:
                    target_cmd = "L"
                elif x > right_limit:
                    target_cmd = "R"
                else:
                    target_cmd = "C"

        # 2. Send Frame and COUNT to Backend for Web Display
        retval, buffer = cv2.imencode('.jpg', frame)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')

        try:
            requests.post(BACKEND_FRAME_URL, 
                          json={'frame': jpg_as_text, 'count': detection_count}, 
                          timeout=0.5)
        except Exception:
            pass 

        # 3. Send Command to Backend
        send_command(target_cmd)

        time.sleep(0.05)


if __name__ == "__main__":
    main()