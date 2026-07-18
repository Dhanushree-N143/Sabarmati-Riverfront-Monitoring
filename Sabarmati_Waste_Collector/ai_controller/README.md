AI Controller
-------------
- Install: pip install -r requirements.txt
- Configure env:
  export ESP32_IP=192.168.1.120
  export ROBOFLOW_API_KEY=...
  export ROBOFLOW_MODEL=...
- Run sample video:
  python ai_waste_controller.py --source waste.mp4 --show
- To use live stream:
  python ai_waste_controller.py --source "http://<esp32-cam-ip>/stream" --show
