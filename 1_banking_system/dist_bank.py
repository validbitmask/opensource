# dist_bank.py
# Run multiple instances to simulate servers. Uses Flask and requests.
# pip install flask requests

from flask import Flask, request, jsonify
import threading, requests, time, argparse, sys
from collections import defaultdict
import json

app = Flask(__name__)

# Node runtime state (will be overwritten per instance via args)
NODE_ID = None
PORT = None
PEERS = []  # list of peer base URLs, e.g. http://127.0.0.1:5002
LEADER = None  # leader base URL, e.g. http://127.0.0.1:5003
IS_LEADER = False

# Logical (Lamport) clock
lamport = 0
lamport_lock = threading.Lock()

# Global sequence counter (only meaningful for leader)
seq_counter = 1
seq_lock = threading.Lock()

# Transaction log: list of dicts {seq, lamport, from, to, amount, client_txid}
transaction_log = []
log_lock = threading.Lock()

# Balances
balances = defaultdict(int)
balances_lock = threading.Lock()

# For heartbeat monitoring
last_leader_heartbeat = time.time()
HEARTBEAT_INTERVAL = 1.0
HEARTBEAT_TIMEOUT = 3.0

# Utility functions
def increment_lamport(received=None):
    global lamport
    with lamport_lock:
        if received is None:
            lamport += 1
        else:
            lamport = max(lamport, received) + 1
        return lamport

def apply_transaction_entry(entry):
    """Apply an entry from log to balances (idempotent if applied once)."""
    with balances_lock:
        balances[entry['from']] -= entry['amount']
        balances[entry['to']] += entry['amount']

def append_log(entry):
    with log_lock:
        # prevent duplicates by seq
        existing = next((e for e in transaction_log if e['seq'] == entry['seq']), None)
        if existing is None:
            transaction_log.append(entry)
            transaction_log.sort(key=lambda e: e['seq'])
            apply_transaction_entry(entry)

def broadcast_commit(entry):
    """Leader tells all peers to commit this entry."""
    for p in PEERS:
        try:
            requests.post(p + "/commit", json=entry, timeout=1.0)
        except Exception:
            pass

def get_state_snapshot():
    with log_lock, balances_lock, lamport_lock:
        return {
            "log": list(transaction_log),
            "balances": dict(balances),
            "lamport": lamport,
            "seq_counter": seq_counter
        }

# Flask endpoints

@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "id": NODE_ID,
        "port": PORT,
        "is_leader": IS_LEADER,
        "leader": LEADER,
        "lamport": lamport,
        "seq_counter": seq_counter,
        "balances": dict(balances)
    })

@app.route("/transaction", methods=["POST"])
def transaction():
    """
    Client posts: {from, to, amount, client_txid}
    If leader: assign seq, lamport, commit and broadcast.
    If follower: forward to leader (if known) or start election.
    """
    global seq_counter
    data = request.get_json()
    increment_lamport()
    if IS_LEADER:
        with seq_lock:
            seq = seq_counter
            seq_counter += 1
        entry = {
            "seq": seq,
            "lamport": lamport,
            "from": data['from'],
            "to": data['to'],
            "amount": data['amount'],
            "client_txid": data.get('client_txid')
        }
        append_log(entry)  # apply locally
        # broadcast to followers
        threading.Thread(target=broadcast_commit, args=(entry,)).start()
        return jsonify({"status":"committed","entry":entry}), 200
    else:
        if LEADER:
            try:
                # forward to leader
                r = requests.post(LEADER + "/transaction", json=data, timeout=2.0)
                return (r.text, r.status_code, r.headers.items())
            except Exception:
                # can't reach leader: trigger election
                threading.Thread(target=start_election).start()
                return jsonify({"status":"leader_unreachable","message":"starting election"}), 503
        else:
            # no known leader: start election
            threading.Thread(target=start_election).start()
            return jsonify({"status":"no_leader","message":"starting election"}), 503

@app.route("/commit", methods=["POST"])
def commit():
    """Follower receives commit from leader."""
    entry = request.get_json()
    # update lamport with leader's lamport stamp
    increment_lamport(received=entry.get("lamport"))
    append_log(entry)
    # record heartbeat from leader (commit implies liveness)
    global last_leader_heartbeat
    last_leader_heartbeat = time.time()
    return jsonify({"status":"ok"}), 200

@app.route("/log", methods=["GET"])
def get_log():
    """Return local log and lamport; used by new leader to collect logs."""
    with log_lock, lamport_lock:
        return jsonify({"log": list(transaction_log), "lamport": lamport, "seq_counter": seq_counter}), 200

@app.route("/election", methods=["POST"])
def election_msg():
    """
    Another node started election and contacted us.
    Per Bully algorithm, we reply with "answer" if we have higher ID.
    """
    data = request.get_json()
    caller_id = data['id']
    if NODE_ID > caller_id:
        # reply to caller that this node is alive/higher -> caller should not become leader
        try:
            requests.post(data['reply_to'] + "/answer", json={"id": NODE_ID}, timeout=1.0)
        except:
            pass
        # then start own election
        threading.Thread(target=start_election).start()
        return jsonify({"response":"ok","action":"sent_answer"}), 200
    else:
        return jsonify({"response":"ok","action":"no_answer"}), 200

@app.route("/answer", methods=["POST"])
def answer_msg():
    # Received response from higher node that it's alive.
    # We simply record this and wait for coordinator message.
    # The starter election thread has logic to wait for answers.
    return jsonify({"received":"ok"}), 200

@app.route("/coordinator", methods=["POST"])
def coordinator():
    """A node announces itself as leader (coordinator)."""
    global LEADER, IS_LEADER, seq_counter
    data = request.get_json()
    LEADER = data['leader_url']
    # mark leader state
    old_leader = LEADER
    if LEADER.endswith(str(PORT)):
        # I am the new leader
        IS_LEADER = True
        # reconstruct state by asking peers for logs
        threading.Thread(target=on_become_leader).start()
    else:
        IS_LEADER = False
    return jsonify({"ack":"ok"}), 200

@app.route("/sync_state", methods=["POST"])
def sync_state():
    global lamport, balances, transaction_log, seq_counter

    data = request.json

    # Sync Lamport
    with lamport_lock:
        lamport = max(lamport, data.get("lamport", 0)) + 1

    # Sync balances
    incoming_bal = data.get("balances", {})
    with balances_lock:
        for k, v in incoming_bal.items():
            balances[k] = v

    # Sync log
    incoming_log = data.get("log", [])
    with log_lock:
        for entry in incoming_log:
            if entry not in transaction_log:
                transaction_log.append(entry)

    # Sync sequence counter
    seq_counter = max(seq_counter, data.get("seq_counter", 0))

    print(f"[{NODE_ID}] State sync done")
    return jsonify({"status": "ok"})



# Election functions

def start_election():
    """
    Bully algorithm:
    - Contact all peers with higher ID.
    - If any higher node answers, wait for coordinator message.
    - If none answer within timeout, become coordinator and broadcast.
    """
    global LEADER, IS_LEADER
    print(f"[{NODE_ID}] Starting election")
    # send /election to nodes with higher ID
    higher_peers = []
    for p in PEERS:
        try:
            # obtain their id via /status
            r = requests.get(p + "/status", timeout=1.0)
            jd = r.json()
            peer_id = jd['id']
            if peer_id > NODE_ID:
                higher_peers.append((peer_id, p))
        except:
            pass

    answers = []
    # send election messages to higher peers
    for peer_id, p in higher_peers:
        try:
            requests.post(p + "/election", json={"id": NODE_ID, "reply_to": f"http://127.0.0.1:{PORT}"}, timeout=1.0)
        except:
            pass

    # wait for any answers within a short window
    wait_until = time.time() + 2.0
    answered = False
    # We don't have per-answer bookkeeping; assume if any higher peer responds to /status quickly they're available.
    # Simpler: poll status of higher peers
    while time.time() < wait_until:
        for peer_id, p in higher_peers:
            try:
                r = requests.get(p + "/status", timeout=0.5)
                if r.status_code == 200:
                    answered = True
                    break
            except:
                continue
        if answered:
            break
        time.sleep(0.2)

    if not answered:
        # become coordinator
        LEADER = f"http://127.0.0.1:{PORT}"
        IS_LEADER = True
        print(f"[{NODE_ID}] Becoming leader")
        # announce to all peers
        for p in PEERS:
            try:
                requests.post(p + "/coordinator", json={"leader_url": LEADER}, timeout=1.0)
            except:
                pass
        # As leader, run on_become_leader to collect logs and set state
        threading.Thread(target=on_become_leader).start()
    else:
        print(f"[{NODE_ID}] Higher node exists, waiting for coordinator")

def on_become_leader():
    """Called on node that just declared itself leader: gather logs and reconcile state."""
    global seq_counter, lamport
    print(f"[{NODE_ID}] Running leader reconciliation")
    collected_logs = []
    max_seq = 0
    max_lamport = 0
    # pull logs from peers
    for p in PEERS:
        try:
            r = requests.get(p + "/log", timeout=1.0)
            if r.status_code == 200:
                jd = r.json()
                collected_logs.extend(jd.get("log", []))
                max_lamport = max(max_lamport, jd.get("lamport", 0))
                max_seq = max(max_seq, jd.get("seq_counter", 0) - 1)
        except:
            pass
    # include our own log
    with log_lock:
        collected_logs.extend(transaction_log)
    # deduplicate by seq and sort
    seq_map = {}
    for e in collected_logs:
        seq_map[e['seq']] = e
    merged = [seq_map[k] for k in sorted(seq_map.keys())]
    # rebuild local state
    with log_lock, balances_lock, lamport_lock:
        transaction_log.clear()
        balances.clear()
        for e in merged:
            transaction_log.append(e)
            balances[e['from']] -= e['amount']
            balances[e['to']] += e['amount']
        lamport = max(lamport, max_lamport) + 1
        seq_counter = max(seq_counter, (max(seq_map.keys()) + 1) if seq_map else 1)
    # broadcast a sync to followers (optional)
    snapshot = get_state_snapshot()
    for p in PEERS:
        try:
            requests.post(p + "/sync_state", json=snapshot, timeout=1.0)
        except:
            pass
    print(f"[{NODE_ID}] Leader reconciliation done. seq_counter={seq_counter}, lamport={lamport}")

# Heartbeat thread
def heartbeat_monitor():
    global last_leader_heartbeat
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        if IS_LEADER:
            # as leader, we can optionally send heartbeats by posting to /commit a tiny ping or specific /heartbeat endpoint
            for p in PEERS:
                try:
                    requests.post(p + "/commit", json={"seq": -1, "lamport": increment_lamport(), "from":"__sys__","to":"__sys__","amount":0,"client_txid":"heartbeat"}, timeout=0.5)
                except:
                    pass
        else:
            # follower: check last heartbeat time or ping leader
            if LEADER:
                try:
                    r = requests.get(LEADER + "/status", timeout=1.0)
                    if r.status_code == 200:
                        last_leader_heartbeat = time.time()
                    else:
                        # treat as failure
                        pass
                except:
                    pass
            # if timeout passed, start election
            if time.time() - last_leader_heartbeat > HEARTBEAT_TIMEOUT:
                print(f"[{NODE_ID}] Leader heartbeat timed out. Starting election.")
                last_leader_heartbeat = time.time()
                threading.Thread(target=start_election).start()

# Simple initializer to seed some balances for demo
def seed_demo_accounts():
    with balances_lock:
        balances['A'] = 100
        balances['B'] = 100
        balances['C'] = 100

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--peers", type=str, default="")
    args = parser.parse_args()
    NODE_ID = args.id
    PORT = args.port
    if args.peers:
        PEERS = [p for p in args.peers.split(",") if p]
    # initially unknown leader
    LEADER = None
    IS_LEADER = False

    seed_demo_accounts()

    # start heartbeat monitor thread
    th = threading.Thread(target=heartbeat_monitor, daemon=True)
    th.start()

    # start flask app
    print(f"Starting node {NODE_ID} on port {PORT} with peers {PEERS}")
    # optionally, start election if this node is highest among peers on startup
    def startup_election_check():
        time.sleep(1.0)
        # trivial heuristic: if our ID is the highest among those reachable, become leader
        highest = NODE_ID
        for p in PEERS:
            try:
                r = requests.get(p + "/status", timeout=1.0)
                if r.status_code == 200:
                    jd = r.json()
                    highest = max(highest, jd['id'])
            except:
                pass
        if NODE_ID >= highest:
            threading.Thread(target=start_election).start()
    threading.Thread(target=startup_election_check, daemon=True).start()

    app.run(port=PORT, threaded=True)
