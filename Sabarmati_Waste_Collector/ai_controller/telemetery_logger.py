# polls ESP32 /telemetry and logs CSV
import requests, time, csv, os

ESP32_TELEMETRY = os.environ.get("ESP32_TELEMETRY", "http://192.168.1.120/telemetry")
OUT_CSV = "telemetry_log.csv"

def poll_loop(interval=5):
    with open(OUT_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ts","ph","turbidity","raw_ph_v","raw_turb_v"])
        while True:
            try:
                r = requests.get(ESP32_TELEMETRY, timeout=3).json()
                ts = r.get("ts", int(time.time()*1000))
                ph = r.get("ph")
                turb = r.get("turbidity")
                raw_ph = r.get("raw_ph_v")
                raw_turb = r.get("raw_turb_v")
                print(time.ctime(), "pH:", ph, "Turb:", turb)
                writer.writerow([ts, ph, turb, raw_ph, raw_turb])
                f.flush()
            except Exception as e:
                print("Telemetry poll error:", e)
            time.sleep(interval)

if __name__ == "__main__":
    poll_loop()
