import socket
import sys
import time
import random
import threading

# ======================================================
# BACKEND SERVER (RUN IN MULTIPLE TERMINALS)
# ======================================================
def run_server(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("localhost", port))

    print(f"🚀 Backend Server running on port {port}")

    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode()

        # Health check ping
        if msg == "PING":
            sock.sendto("PONG".encode(), addr)
            continue

        print(f"[Server {port}] Received: {msg}")

        # Simulate processing time (busy)
        time.sleep(random.uniform(0.7, 2.0))

        # Send DONE after processing
        done_msg = f"DONE:{port}"
        sock.sendto(done_msg.encode(), ("localhost", 9999))


# ======================================================
# LOAD BALANCER
# ======================================================
def run_load_balancer():
    # All possible servers
    all_servers = [9001, 9002, 9003]

    # Actual active servers
    active_servers = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.5)

    print("\n🔍 Checking which servers are alive...\n")

    # ======================================================
    # HEALTH CHECK: Ping all servers
    # ======================================================
    for port in all_servers:
        try:
            sock.sendto("PING".encode(), ("localhost", port))
            data, addr = sock.recvfrom(1024)

            if data.decode() == "PONG":
                active_servers.append(port)
                print(f"✅ Server {port} is ACTIVE")

        except:
            print(f"❌ Server {port} is DOWN (ignored)")

    if not active_servers:
        print("\n❌ No servers available. Exiting.")
        return

    print("\nActive Servers:", active_servers)

    # Load states
    active = {port: 0 for port in active_servers}
    load_final = {port: 0 for port in active_servers}

    # Socket to receive DONE
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(("localhost", 9999))

    def done_listener():
        while True:
            data, addr = recv_sock.recvfrom(1024)
            msg = data.decode()

            if msg.startswith("DONE:"):
                port = int(msg.split(":")[1])
                active[port] -= 1
                print(f"[LB] Server {port} finished → active={active[port]}")

    threading.Thread(target=done_listener, daemon=True).start()

    # ======================================================
    # BEGIN LOAD BALANCING
    # ======================================================
    print("\n=== LEAST CONNECTIONS LOAD BALANCER STARTED ===\n")

    for req in range(1, 11):
        best_port = min(active, key=active.get)

        msg = f"Request {req}"
        sock.sendto(msg.encode(), ("localhost", best_port))

        print(f"LB → Sent '{msg}' to Server {best_port}")

        active[best_port] += 1
        load_final[best_port] += 1

        time.sleep(0.3)

    time.sleep(5)

    print("\n=== FINAL LOAD DISTRIBUTION ===")
    for port, count in load_final.items():
        print(f"Server {port}: {count} requests")


# ======================================================
# MAIN ENTRY POINT
# ======================================================
if __name__ == "__main__":
    role = sys.argv[1]

    if role == "server":
        run_server(int(sys.argv[2]))
    else:
        run_load_balancer()

    """
    ===============================
    EXECUTION INSTRUCTIONS (FINAL)
    ===============================

    1) START SERVERS (only those you want)
       Example:
           python least_connection.py server 9001
           python least_connection.py server 9003
       (If 9002 is missing, LB will automatically ignore it)

    2) START LOAD BALANCER:
           python least_connection.py lb

    3) EXPECTED OUTPUT:
       LB checks servers:
           Server 9001 ACTIVE
           Server 9002 DOWN
           Server 9003 ACTIVE

       LB sends requests only to active servers.

       Final distribution printed correctly.
    """
