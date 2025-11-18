import sys
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

MASTER_PORT = None
lamport_clock = 0


# ---------------------------------------------------------
# Lamport Helpers
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
# POLLING SERVERS
# ---------------------------------------------------------
def get_clocks(servers):
    clocks = {}
    for s in servers:
        try:
            my_lc = increment()
            r = requests.get(f"http://localhost:{s}/time", params={"lc": my_lc}).json()
            remote_lc = r["lamport"]
            receive_clock(remote_lc)
            clocks[s] = remote_lc
        except:
            clocks[s] = None
    return clocks


def merge_logs(servers):
    merged = []
    for s in servers:
        try:
            logs = requests.get(f"http://localhost:{s}/logs").json()
            for entry in logs:
                entry["server"] = s
                merged.append(entry)
        except:
            pass

    # Sort by (Lamport Clock, Server ID)
    merged.sort(key=lambda x: (x["lamport"], x["server"]))
    return merged


# ---------------------------------------------------------
# MASTER LOOP
# ---------------------------------------------------------
def master_loop(servers):
    print(f"[MASTER] running on port {MASTER_PORT}")

    while True:
        print("\n========== LAMPORT POLLING ==========")
        clocks = get_clocks(servers)
        for s, lc in clocks.items():
            if lc is None:
                print(f"[MASTER] Server {s} unreachable")
            else:
                print(f"[MASTER] Server {s} LC={lc}")

        print("\n========== MERGED LOGS (LAMPORT ORDER) ==========")
        merged = merge_logs(servers)
        for entry in merged:
            print(f"[S{entry['server']}] LC={entry['lamport']} @ {entry['timestamp']} → {entry['msg']}")

        print("=================================================\n")
        time.sleep(5)


def flask_thread():
    app.run(port=MASTER_PORT, debug=False, use_reloader=False)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    MASTER_PORT = int(sys.argv[1])
    servers = list(map(int, sys.argv[2:]))

    threading.Thread(target=flask_thread).start()
    time.sleep(1)

    master_loop(servers)
