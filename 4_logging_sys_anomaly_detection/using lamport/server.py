import sys
import time
import threading
from flask import Flask, jsonify, request
from datetime import datetime, timezone

app = Flask(__name__)

lamport_clock = 0
logs = []
SERVER_PORT = None


# ---------------------------------------------------------
# Lamport Clock Helpers
# ---------------------------------------------------------
def increment():
    global lamport_clock
    lamport_clock += 1
    return lamport_clock

def receive_clock(remote_clock):
    global lamport_clock
    lamport_clock = max(lamport_clock, remote_clock) + 1
    return lamport_clock


# ---------------------------------------------------------
# Logging Helper
# ---------------------------------------------------------
def add_log(msg):
    lc = increment()
    ts = datetime.now(timezone.utc).isoformat()

    logs.append({"lamport": lc, "timestamp": ts, "msg": msg})
    print(f"[SERVER-{SERVER_PORT}] LC={lc} @ {ts} → {msg}")


# ---------------------------------------------------------
# API ENDPOINTS
# ---------------------------------------------------------
@app.get("/time")
def send_clock():
    # Master polling acts like an incoming message → receive event
    lc = receive_clock(int(request.args.get("lc", 0)))
    return jsonify({"lamport": lc})

@app.get("/logs")
def get_logs():
    return jsonify(logs)


# ---------------------------------------------------------
# SERVER LOOP
# ---------------------------------------------------------
def flask_thread():
    app.run(port=SERVER_PORT, debug=False, use_reloader=False)

if __name__ == "__main__":
    SERVER_PORT = int(sys.argv[1])

    threading.Thread(target=flask_thread).start()
    time.sleep(1)

    add_log("Server started")

    while True:
        time.sleep(4)
        add_log("Local event recorded")
