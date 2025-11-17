import sys
import time
import threading
from flask import Flask, request, jsonify
from datetime import datetime, timezone

app = Flask(__name__)

offset = 0.0
logs = []
SERVER_PORT = None

def now():
    return time.time() + offset

def add_log(msg):
    ts = now()
    logs.append({"timestamp": ts, "msg": msg})
    tstr = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    print(f"[SERVER-{SERVER_PORT}] {tstr} → {msg}")

@app.get("/time")
def get_time():
    return jsonify({"server_time": now()})

@app.post("/adjust")
def adjust():
    global offset
    adj = request.get_json().get("adjust_seconds", 0)
    offset += adj
    add_log(f"Clock adjusted by {adj:.6f} seconds")
    return jsonify({"status": "ok"})

@app.get("/logs")
def get_logs():
    return jsonify(logs)

def flask_thread():
    app.run(port=SERVER_PORT, debug=False, use_reloader=False)

if __name__ == "__main__":
    SERVER_PORT = int(sys.argv[1])

    threading.Thread(target=flask_thread).start()
    time.sleep(1)

    add_log("Server started")

    # Generate a log every 4 seconds
    while True:
        time.sleep(4)
        add_log("Local event recorded")
