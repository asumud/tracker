import socket
import json
import time
import math
import subprocess
import os

# ======================
# CONFIG
# ======================
UPDATE_INTERVAL = 300
POSITIONS_FILE = "position.json"

GAZA_LAT = 31.5017
GAZA_LON = 34.4668

# ======================
# HELPERS
# ======================
def haversine_nm(lat1, lon1, lat2, lon2):
    R = 3440.065
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def save_position(data):
    with open(POSITIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ======================
# NMEA READ
# ======================
def read_position():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("localhost", 10111))
        s.settimeout(10)

        while True:
            raw = s.recv(4096).decode(errors="ignore")

            for line in raw.splitlines():
                if "RMC" in line:
                    parts = line.split(",")
                    if len(parts) < 9:
                        continue

                    lat_raw, lat_dir = parts[3], parts[4]
                    lon_raw, lon_dir = parts[5], parts[6]

                    if not lat_raw or not lon_raw:
                        continue

                    lat = float(lat_raw[:2]) + float(lat_raw[2:]) / 60
                    lon = float(lon_raw[:3]) + float(lon_raw[3:]) / 60

                    if lat_dir == "S":
                        lat = -lat
                    if lon_dir == "W":
                        lon = -lon

                    sog = float(parts[7]) if parts[7] else 0.0
                    cog = float(parts[8]) if parts[8] else 0.0

                    return lat, lon, sog, cog

    except Exception as e:
        print("❌ NMEA error:", e)
        return None, None, 0.0, 0.0

# ======================
# GIT PUSH
# ======================
def push_to_git():
    subprocess.run(["git", "add", "-A"])

    commit = subprocess.run(
        ["git", "commit", "-m", "🛰️ Tracker update"],
        capture_output=True,
        text=True
    )

    if "nothing to commit" in commit.stdout.lower():
        return

    subprocess.run(["git", "push", "--force"])
    print("📤 Pushed to GitHub")

# ======================
# MAIN LOOP
# ======================
if __name__ == "__main__":
    print("🚀 Single Vessel Tracker")

    while True:
        lat, lon, sog, hdg = read_position()

        if lat is not None and lon is not None:
            distance_nm = haversine_nm(lat, lon, GAZA_LAT, GAZA_LON)
            eta_hours = distance_nm / sog if sog > 0.5 else None

            data = {
                "id": "al_awda",
                "lat": lat,
                "lon": lon,
                "sog": sog,
                "cog": hdg,
                "distance_nm": round(distance_nm, 2),
                "eta_hours": round(eta_hours, 2) if eta_hours else None,
                "timestamp": time.time()
            }

            save_position(data)
            push_to_git()

            print(f"📍 {round(distance_nm,1)} nm to Gaza")

        else:
            print("⚠️ No valid data")

        time.sleep(UPDATE_INTERVAL)
