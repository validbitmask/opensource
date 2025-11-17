#!/usr/bin/env python3
"""
node.py  — revised

Run:
  Terminal 1: python3 node.py --pid 1
  Terminal 2: python3 node.py --pid 2
  Terminal 3: python3 node.py --pid 3

Requires nodes.json (same format as before).
"""
import socket
import threading
import json
import time
import argparse
from typing import List

# load nodes
with open("nodes.json", "r") as f:
    NODES = json.load(f)


def debug(*args, **kwargs):
    print(*args, **kwargs, flush=True)


class Node:
    def __init__(self, pid: int):
        self.pid = pid
        self.info = next(n for n in NODES if n["pid"] == pid)
        self.host = self.info["host"]
        self.port = self.info["port"]

        self.alive = True
        self.coordinator = None

        self.lock = threading.Lock()
        self.server = None

    def log(self, msg):
        debug(f"[P{self.pid}] {msg}")

    # ----------------------------------------------------------------------
    # Fault-tolerant send functions
    # ----------------------------------------------------------------------

    def send_to(self, node_info, obj: dict) -> bool:
        """Try sending to a node. Return True if delivered; False if failed."""
        try:
            s = socket.socket()
            s.settimeout(1.0)
            s.connect((node_info["host"], node_info["port"]))
            s.send(json.dumps(obj).encode())
            s.close()
            return True
        except Exception:
            return False

    def send_next(self, obj: dict) -> bool:
        """
        Send to the next ALIVE node clockwise.
        If no nodes reachable, return False (caller should handle declaring self coordinator).
        """
        pids = [n["pid"] for n in NODES]
        start_index = pids.index(self.pid)

        for i in range(1, len(NODES)):
            idx = (start_index + i) % len(NODES)
            target = NODES[idx]

            if self.send_to(target, obj):
                return True

        # No reachable node → return False (caller may decide to become coordinator)
        return False

    # ----------------------------------------------------------------------
    # Server / Listener
    # ----------------------------------------------------------------------

    def start_server(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server.bind((self.host, self.port))
            self.server.listen()
        except OSError as e:
            self.log(f"Bind error: {e}")
            raise

        self.log(f"Listening on {self.host}:{self.port}")

        # start heartbeat thread
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()

        # small startup delay → then check if no coordinator and start election
        threading.Thread(target=self.delayed_initial_election, daemon=True).start()

        time.sleep(0.2)

        while True:
            try:
                conn, _ = self.server.accept()
                data = conn.recv(4096).decode()
                conn.close()
                if not data:
                    continue
                try:
                    obj = json.loads(data)
                except Exception:
                    continue
                threading.Thread(target=self.handle_message, args=(obj,), daemon=True).start()
            except KeyboardInterrupt:
                break
            except Exception:
                # continue accepting; don't die on transient errors
                continue

    def delayed_initial_election(self):
        # slightly staggered startup so not everyone starts at once
        time.sleep(0.5 + 0.05 * self.pid)
        with self.lock:
            if self.coordinator is None:
                self.log("Starting initial election (startup)")
                self.initiate_election()

    # ----------------------------------------------------------------------
    # Heartbeat (detect failed coordinator)
    # ----------------------------------------------------------------------

    def heartbeat_loop(self):
        while True:
            time.sleep(3)
            with self.lock:
                coord = self.coordinator

            # nothing to check if no coordinator known or if I'm coordinator
            if coord is None or coord == self.pid:
                continue

            coord_info = next((n for n in NODES if n["pid"] == coord), None)
            if not coord_info:
                # unknown coordinator; try election
                self.log(f"Coordinator P{coord} unknown in config -> starting election")
                # start election synchronously to avoid races
                self.initiate_election()
                continue

            # try pinging coordinator - if connect fails, start election
            try:
                s = socket.socket()
                s.settimeout(1.5)
                s.connect((coord_info["host"], coord_info["port"]))
                # send a simple ping; we don't expect explicit ACK body
                s.send(json.dumps({"type": "PING", "from": self.pid}).encode())
                s.close()
            except Exception:
                # coordinator not responding -> start election immediately
                self.log(f"Coordinator P{coord} not responding → starting election")
                # clear coordinator and synchronously initiate election
                with self.lock:
                    self.coordinator = None
                self.initiate_election()

    # ----------------------------------------------------------------------
    # Election logic
    # ----------------------------------------------------------------------

    def initiate_election(self):
        token = {
            "type": "ELECTION",
            "origin": self.pid,
            "ids": [self.pid],
            "from": self.pid
        }
        self.log("Initiating ELECTION")

        # try to forward; if forwarding fails (no reachable neighbor), declare self coordinator
        ok = self.send_next(token)
        if not ok:
            # no neighbor reachable — become coordinator and broadcast COORDINATOR message
            with self.lock:
                self.coordinator = self.pid
            self.log("No neighbors reachable — declaring self as COORDINATOR")
            coord_msg = {
                "type": "COORDINATOR",
                "origin": self.pid,
                "leader": self.pid,
                "from": self.pid
            }
            # attempt to broadcast; even if broadcast fails, at least local state is set
            self.send_next(coord_msg)

    def handle_message(self, obj: dict):
        mtype = obj.get("type")
        sender = obj.get("from")

        if mtype == "ELECTION":
            origin = obj["origin"]
            ids = obj["ids"]

            self.log(f"Received ELECTION from P{sender}; IDs={ids}")

            # Add self if missing
            if self.pid not in ids:
                ids.append(self.pid)

            # If returned to origin → elect leader
            if origin == self.pid:
                new_leader = max(ids)
                self.log(f"ELECTION complete → new leader: P{new_leader}")

                # Send COORDINATOR message (try to send; if fails, we still set local state)
                msg = {
                    "type": "COORDINATOR",
                    "origin": origin,
                    "leader": new_leader,
                    "from": self.pid
                }
                # set coordinator locally
                with self.lock:
                    self.coordinator = new_leader

                if not self.send_next(msg):
                    # couldn't forward the coordinator message; keep local state and exit
                    self.log("Coordinator announcement could not be forwarded (no neighbors).")
                return

            # otherwise forward election
            forward = {
                "type": "ELECTION",
                "origin": origin,
                "ids": ids,
                "from": self.pid
            }

            time.sleep(0.05)

            if not self.send_next(forward):
                # forwarding failed — likely we're the last reachable node; declare self leader
                self.log("Election forwarding failed. Declaring self as leader.")
                with self.lock:
                    self.coordinator = self.pid
                # and announce ourselves to others (best-effort)
                coord_msg = {
                    "type": "COORDINATOR",
                    "origin": self.pid,
                    "leader": self.pid,
                    "from": self.pid
                }
                self.send_next(coord_msg)
            return

        elif mtype == "COORDINATOR":
            origin = obj["origin"]
            leader = obj["leader"]

            self.log(f"Received COORDINATOR (origin P{origin}) → Leader P{leader}")

            with self.lock:
                self.coordinator = leader

            if origin == self.pid:
                # announcement returned to origin, normal termination
                self.log("Coordinator announcement returned to origin.")
                return

            forward = {
                "type": "COORDINATOR",
                "origin": origin,
                "leader": leader,
                "from": self.pid
            }

            time.sleep(0.02)

            if not self.send_next(forward):
                # couldn't forward further — maybe only survivor(s)
                self.log("Coordinator forwarding failed (no next reachable). Keeping local leader.")
                # ensure local coordinator stays set
                with self.lock:
                    self.coordinator = leader
            return

        elif mtype == "PING":
            # used as heartbeat; nothing to return - connection success is adequate
            # we could optionally respond but current design relies on connect success
            return

        # Ignore unknown messages
        return


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    args = parser.parse_args()

    node = Node(args.pid)
    try:
        node.start_server()
    except KeyboardInterrupt:
        pass
