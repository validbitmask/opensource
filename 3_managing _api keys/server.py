# server.py
from flask import Flask, jsonify, request
from threading import Thread, Lock
import time
import uuid

app = Flask(__name__)

# Configuration
KEY_LIFETIME_SECONDS = 5 * 60      # 5 minutes
AUTO_RELEASE_SECONDS = 60          # release blocked keys after 60 seconds if not unblocked
CLEANUP_INTERVAL = 5               # seconds between cleanup loop runs

# Shared state
keys = {}  # key -> {status: 'available'|'blocked', last_keepalive: ts, blocked_at: ts or None}
lock = Lock()

def now():
    return int(time.time())

@app.route('/create', methods=['POST'])
def create_key():
    k = str(uuid.uuid4())
    ts = now()
    with lock:
        keys[k] = {
            'status': 'available',
            'last_keepalive': ts,
            'blocked_at': None
        }
    return jsonify({'key': k, 'expires_in': KEY_LIFETIME_SECONDS}), 201

@app.route('/get', methods=['POST'])
def get_key():
    with lock:
        for k, v in keys.items():
            if v['status'] == 'available':
                v['status'] = 'blocked'
                v['blocked_at'] = now()
                return jsonify({'key': k}), 200
    return jsonify({'error': 'no-available-keys'}), 404

@app.route('/unblock/<k>', methods=['POST'])
def unblock_key(k):
    with lock:
        if k not in keys:
            return jsonify({'error': 'not_found'}), 404
        keys[k]['status'] = 'available'
        keys[k]['blocked_at'] = None
        return jsonify({'key': k, 'status': 'available'}), 200

@app.route('/keepalive/<k>', methods=['POST'])
def keepalive(k):
    with lock:
        if k not in keys:
            return jsonify({'error': 'not_found'}), 404
        keys[k]['last_keepalive'] = now()
        return jsonify({'key': k, 'expires_in': KEY_LIFETIME_SECONDS}), 200

def cleanup_loop():
    while True:
        time.sleep(CLEANUP_INTERVAL)
        ts = now()
        with lock:
            to_delete = []
            for k, v in list(keys.items()):
                # 1) Remove keys expired (no keepalive within lifetime)
                if ts - v['last_keepalive'] > KEY_LIFETIME_SECONDS:
                    to_delete.append(k)
                    continue
                # 2) Auto-release blocked keys older than AUTO_RELEASE_SECONDS
                if v['status'] == 'blocked' and v['blocked_at'] is not None:
                    if ts - v['blocked_at'] > AUTO_RELEASE_SECONDS:
                        v['status'] = 'available'
                        v['blocked_at'] = None
            for k in to_delete:
                del keys[k]

if __name__ == '__main__':
    # start cleanup thread (daemon so it exits with main process)
    cleaner = Thread(target=cleanup_loop, daemon=True)
    cleaner.start()
    # run flask with threaded=True so requests can be handled concurrently
    app.run(host='0.0.0.0', port=5000, threaded=True)
