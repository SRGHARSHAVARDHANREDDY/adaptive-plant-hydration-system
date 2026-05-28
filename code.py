import tkinter as tk
import requests
import pandas as pd
import time
import threading

# ------------------ CONFIG ------------------
BASE_URL = "https://exotic-plant-system-default-rtdb.firebaseio.com"
SECRET = "YOUR_SECRET"

SENSOR_URL = f"{BASE_URL}/sensors.json?auth={SECRET}"
PUMP_URL = f"{BASE_URL}/pumps.json?auth={SECRET}"

CSV_FILE = "plant_specs_combined.csv"
# -------------------------------------------

# Load CSV
df = pd.read_csv(CSV_FILE)

# Get threshold from CSV
def get_threshold(plant_id):
    try:
        plant = df[df["plant_id"] == plant_id].iloc[0]
        return plant["soil_moisture_min"]
    except:
        print(f"Invalid plant_id: {plant_id}")
        return 40  # fallback

# Main system loop
def run_system(plant_ids):
    while True:
        try:
            res = requests.get(SENSOR_URL, timeout=5)

            if res.status_code != 200:
                print("HTTP Error:", res.status_code)
                print(res.text)
                time.sleep(5)
                continue

            data = res.json()

            if not data:
                print("No sensor data")
                time.sleep(5)
                continue

            # ✅ Already in percentage → use directly
            moisture = [
                data.get("moisture1"),
                data.get("moisture2"),
                data.get("moisture3"),
                data.get("moisture4")
            ]

            pumps = {}

            for i in range(4):
                threshold = get_threshold(plant_ids[i])

                # Handle None safely
                if moisture[i] is None:
                    pumps[f"pump{i+1}"] = 0
                    continue

                pumps[f"pump{i+1}"] = 1 if moisture[i] < threshold else 0

            print("\n------------------------")
            print("Moisture %:", moisture)
            print("Plant IDs:", plant_ids)
            print("Pump decisions:", pumps)

            # Send to Firebase
            r = requests.patch(PUMP_URL, json=pumps)

            if r.status_code == 200:
                print("✅ Pumps updated")
            else:
                print("❌ Firebase error:", r.text)

        except Exception as e:
            print("Error:", e)

        time.sleep(5)

# Start system in background thread
def start_system(selected_ids):
    thread = threading.Thread(target=run_system, args=(selected_ids,))
    thread.daemon = True
    thread.start()

# ------------------ TKINTER UI ------------------

root = tk.Tk()
root.title("Smart Irrigation System")

plant_vars = [tk.IntVar(value=1) for _ in range(4)]

tk.Label(root, text="Enter Plant IDs for each sensor").grid(row=0, columnspan=2)

for i in range(4):
    tk.Label(root, text=f"Plant {i+1} ID:").grid(row=i+1, column=0)
    tk.Entry(root, textvariable=plant_vars[i]).grid(row=i+1, column=1)

status_label = tk.Label(root, text="System not started", fg="red")
status_label.grid(row=6, columnspan=2)

def on_start():
    plant_ids = [p.get() for p in plant_vars]
    print("Selected plant IDs:", plant_ids)

    status_label.config(text="System Running...", fg="green")

    start_system(plant_ids)

tk.Button(root, text="Start System", command=on_start).grid(row=5, columnspan=2)

root.mainloop()