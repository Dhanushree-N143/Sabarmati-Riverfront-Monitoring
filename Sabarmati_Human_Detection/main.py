from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import cv2
import numpy as np
import base64
import os
from ultralytics import YOLO

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# === LOAD YOLO MODEL ===
model_path = "yolov8n.pt"
if not os.path.exists(model_path):
    print("⚠️ Model not found. Downloading...")
    model = YOLO("yolov8n.pt") 
else:
    model = YOLO(model_path) 

PERSON_CLASS_ID = 0 

# === LINE COORDINATES (Diagonal) ===
# From Top-Right (1280, 0) to Bottom-Left (0, 720)
LINE_START = (1100, 0)
LINE_END = (450, 720)

def is_left_of_line(cx, cy, p1, p2):
    """
    Returns True if point (cx, cy) is to the LEFT/BOTTOM of the line p1->p2.
    Uses the cross product method.
    """
    x1, y1 = p1
    x2, y2 = p2
    # Cross product logic
    val = (x2 - x1) * (cy - y1) - (y2 - y1) * (cx - x1)
    return val > 0  # Depending on coordinate system, >0 is usually "Left/Bottom"

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🔵 Client Connected")
    try:
        while True:
            data = await websocket.receive_text()
            header, encoded = data.split(",", 1)
            nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Resize to standard 720p for consistent line logic
            frame = cv2.resize(frame, (1280, 720))

            # AI Detection
            results = model(frame, conf=0.35, verbose=False)[0]
            
            danger_humans = 0
            
            # Draw the Boundary Line (Yellow, Thickness 3)
            cv2.line(frame, LINE_START, LINE_END, (0, 255, 255), 3)
            cv2.putText(frame, "SAFE ZONE", (1100, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, "DANGER ZONE", (50, 650), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            for box, cls in zip(results.boxes.xyxy, results.boxes.cls):
                if int(cls) == PERSON_CLASS_ID:
                    x1, y1, x2, y2 = map(int, box)
                    
                    # Calculate Center Point of the Human (cx, cy)
                    cx = (x1 + x2) // 2
                    cy = y2  # Use feet position for more accurate ground location
                    
                    # Check Side
                    if is_left_of_line(cx, cy, LINE_START, LINE_END):
                        # --- LEFT SIDE (DANGER) ---
                        danger_humans += 1
                        color = (0, 0, 255) # Red
                        label = "UNSAFE"
                    else:
                        # --- RIGHT SIDE (SAFE) ---
                        color = (0, 255, 0) # Green
                        label = "SAFE"

                    # Draw Box & Label
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.circle(frame, (cx, cy), 5, (255, 255, 0), -1) # Show center point
                    cv2.putText(frame, label, (x1, y1 - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Encode
            _, buffer = cv2.imencode('.jpg', frame)
            processed_base64 = base64.b64encode(buffer).decode('utf-8')

            await websocket.send_json({
                "image": f"data:image/jpeg;base64,{processed_base64}",
                "humans": danger_humans,  # Only count DANGER humans for the alert
                "danger": danger_humans > 0
            })

    except WebSocketDisconnect:
        print("🔴 Client Disconnected")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)