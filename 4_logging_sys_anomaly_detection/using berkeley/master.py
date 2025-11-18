import sys
import time
import requests
import threading
from flask import Flask
from datetime import datetime, timezone

app = Flask(__name__)

MASTER_PORT = None

# ----------------------
# Berkeley Algorithm
# ----------------------
def collect_times(servers):
    times = {}
    for s in servers:
        try:
            r = requests.get(f"http://localhost:{s}/time").json()
            times[s] = r["server_time"]
        except:
            times[s] = None
    return times

def berkeley(servers):
    times = collect_times(servers)
    valid = [t for t in times.values() if t is not None]

    if not valid:
        return {}

    avg = sum(valid) / len(valid)
    adjustments = {}

    for s, t in times.items():
        if t is None:
            adjustments[s] = None
            continue

        adj = avg - t
        adjustments[s] = adj
        try:
            requests.post(f"http://localhost:{s}/adjust",
                          json={"adjust_seconds": adj})
        except:
            pass

    return adjustments

def collect_logs(servers):
    merged = []
    for s in servers:
        try:
            server_logs = requests.get(f"http://localhost:{s}/logs").json()
            for entry in server_logs:
                entry["server"] = s
                merged.append(entry)
        except:
            pass

    merged.sort(key=lambda x: x["timestamp"])
    return merged

# ----------------------
# Master Loop
# ----------------------
def master_loop(servers):
    print(f"[MASTER] Started on port {MASTER_PORT}")
    while True:
        print("\n========== BERKELEY SYNC ==========")
        adjustments = berkeley(servers)

        for s, adj in adjustments.items():
            if adj is None:
                print(f"[MASTER] Server {s} unreachable")
            else:
                print(f"[MASTER] Server {s} adjusted by {adj:.6f} seconds")

        print("\n========== MERGED LOGS ==========")
        merged = collect_logs(servers)

        for entry in merged:
            ts = datetime.fromtimestamp(entry["timestamp"], tz=timezone.utc).isoformat()
            print(f"[S{entry['server']}] {ts} → {entry['msg']}")

        print("===================================\n")
        time.sleep(5)

def flask_thread():
    app.run(port=MASTER_PORT, debug=False, use_reloader=False)

# ----------------------
# MAIN
# ----------------------
if __name__ == "__main__":
    MASTER_PORT = int(sys.argv[1])
    servers = list(map(int, sys.argv[2:]))

    threading.Thread(target=flask_thread).start()
    time.sleep(1)

    master_loop(servers)
