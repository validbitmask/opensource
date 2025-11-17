import socket
import sys
import time

# ======================================================
# BACKEND SERVER CODE
# ======================================================
def run_server(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("localhost", port))

    print(f"🚀 Backend Server running on port {port}")

    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode()
        print(f"[Server {port}] Received: {msg}")


# ======================================================
# ROUND ROBIN LOAD BALANCER
# ======================================================
def run_load_balancer():
    servers = [
        ("localhost", 9001),
        ("localhost", 9002),
        ("localhost", 9003)
    ]

    index = 0
    load = {9001:0, 9002:0, 9003:0}

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("\n=== ROUND ROBIN LOAD BALANCER STARTED ===\n")

    for req in range(1, 11):
        ip, port = servers[index]

        msg = f"Request {req}"
        sock.sendto(msg.encode(), (ip, port))

        print(f"LB → Sent '{msg}' to Server {port}")

        load[port] += 1
        index = (index + 1) % len(servers)

        time.sleep(0.5)

    print("\n=== FINAL LOAD DISTRIBUTION ===")
    for port, count in load.items():
        print(f"Server {port}: {count} requests")


# ======================================================
# MAIN ENTRY POINT
# ======================================================
if __name__ == "__main__":
    if sys.argv[1] == "server":
        run_server(int(sys.argv[2]))
    else:
        run_load_balancer()

"""
========================================================
ROUND ROBIN LOAD BALANCER — EXECUTION INSTRUCTIONS
========================================================

1️⃣ START BACKEND SERVERS (each in its own terminal)
----------------------------------------------------

Terminal 1:
    python round_robin.py server 9001

Terminal 2:
    python round_robin.py server 9002

Terminal 3:
    python round_robin.py server 9003


2️⃣ START THE LOAD BALANCER (in a separate terminal)
----------------------------------------------------

Terminal 4:
    python round_robin.py lb


3️⃣ EXPECTED OUTPUT
----------------------------------------------------
Load Balancer Terminal:
    === ROUND ROBIN LOAD BALANCER STARTED ===
    LB → Sent 'Request 1' to Server 9001
    LB → Sent 'Request 2' to Server 9002
    LB → Sent 'Request 3' to Server 9003
    LB → Sent 'Request 4' to Server 9001
    ...

Backend Server Terminals:
    [Server 9001] Received: Request 1
    [Server 9002] Received: Request 2
    [Server 9003] Received: Request 3
    [Server 9001] Received: Request 4
    ...


4️⃣ FINAL LOAD DISTRIBUTION (in LB terminal)
----------------------------------------------------
Server 9001: 4 requests
Server 9002: 3 requests
Server 9003: 3 requests


🎯 This completes the ROUND ROBIN load balancing experiment.
"""
