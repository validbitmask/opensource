import socket
import threading
import json
import time
import argparse

# LOAD THE IP ADDRESSES
with open("nodes.json", "r") as f:
    NODES = json.load(f)


class Node:
    def __init__(self, pid):
        self.pid = pid
        self.host = NODES[pid - 1]["host"]
        self.port = NODES[pid - 1]["port"]
        self.coordinator = None
        self.alive = True
        self.got_ok = False        # <-- track if any higher node replied

    # Start the TCP server
    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.port))
        server.listen()

        print(f"[{self.pid}] Listening on {self.host}:{self.port}")
        print(f"[{self.pid}] Starting initial election\n")

        # Start initial election
        threading.Thread(target=self.start_election, daemon=True).start()

        # Start heartbeat thread (check leader every 5s)
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()

        while True:
            try:
                conn, addr = server.accept()
                data = conn.recv(1024).decode()
                if data:
                    self.handle_message(data)
            except Exception as e:
                # you can print(e) for debugging
                break

    # Heartbeat: check if coordinator is alive every 5s
    def heartbeat_loop(self):
        while True:
            time.sleep(5)

            # If no coordinator yet or I am the coordinator -> nothing to check
            if self.coordinator is None or self.coordinator == self.pid:
                continue

            # Find coordinator host/port
            coord_info = next((n for n in NODES if n["pid"] == self.coordinator), None)
            if coord_info is None:
                continue

            try:
                s = socket.socket()
                s.settimeout(2)  # don’t block too long
                s.connect((coord_info["host"], coord_info["port"]))
                # just send a simple ping
                s.send(f"PING {self.pid}".encode())
                s.close()
                # If this works, coordinator is alive
                # print(f"[{self.pid}] Coordinator {self.coordinator} is alive")
            except:
                # Could not reach coordinator -> assume it is down
                print(f"[{self.pid}] Coordinator {self.coordinator} NOT responding -> starting election\n")
                threading.Thread(target=self.start_election, daemon=True).start()

    # send TCP Message
    def send(self, target_pid, message):
        target = NODES[target_pid - 1]
        try:
            s = socket.socket()
            s.connect((target["host"], target["port"]))
            s.send(message.encode())
            s.close()
        except:
            # target might be down
            pass

    # ---------------------------
    # Election Logic
    # ---------------------------
    def start_election(self):
        print(f"[{self.pid}] Initializing election... ")
        higher_nodes = [n["pid"] for n in NODES if n["pid"] > self.pid]

        # Reset OK flag
        self.got_ok = False

        # Send ELECTION to all higher ID nodes
        for hp in higher_nodes:
            print(f"[{self.pid}] -> P{hp}: ELECTION")
            self.send(hp, f"ELECTION {self.pid}")

        # Wait for OK messages
        time.sleep(2)

        # If no OK arrived, declare self coordinator
        if not self.got_ok:
            print(f"[{self.pid}] I am the new COORDINATOR\n")
            self.coordinator = self.pid
            for n in NODES:
                if n["pid"] != self.pid:
                    self.send(n["pid"], f"COORDINATOR {self.pid}")
            return
        else:
            # If got OK from higher node, that node (or someone above it)
            # will take over the election, so just wait.
            print(f"[{self.pid}] Got OK from higher process. Waiting for COORDINATOR...\n")

    # ---------------------------
    # Message Handler
    # ---------------------------
    def handle_message(self, msg):
        parts = msg.split()
        mtype = parts[0]
        sender = int(parts[1])

        if mtype == "ELECTION":
            print(f"[{self.pid}] Received ELECTION from {sender}")
            # SEND OK
            print(f"[{self.pid}] -> [P{sender}]: OK")
            self.send(sender, f"OK {self.pid}")
            # start own election (bully effect)
            threading.Thread(target=self.start_election, daemon=True).start()

        elif mtype == "OK":
            print(f"[{self.pid}] Received OK from {sender}")
            # mark that someone higher is alive
            self.got_ok = True

        elif mtype == "COORDINATOR":
            self.coordinator = sender
            print(f"[{self.pid}] Received COORDINATOR: new Leader = {sender}\n")

        elif mtype == "PING":
            # optional: just to see pings
            # print(f"[{self.pid}] Received PING from {sender}")
            pass


# ---------------------------
# RUN NODE
# ---------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    args = parser.parse_args()

    node = Node(args.pid)
    node.start_server()
