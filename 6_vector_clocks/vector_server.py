# vector_server.py
import socket, threading, json, argparse

parser = argparse.ArgumentParser()
parser.add_argument('--n', type=int, default=3, help='total processes (incl server)')
parser.add_argument('--host', default='0.0.0.0')
parser.add_argument('--port', type=int, default=6000)
args = parser.parse_args()

N = args.n
server_id = 0
vec = [0]*N
lock = threading.Lock()

def handle(conn, addr):
    global vec
    data = conn.recv(4096).decode()
    if not data:
        conn.close(); return
    msg = json.loads(data)
    recv_vec, sid = msg['vector'], msg['id']
    with lock:
        # merge then increment server's own entry (receive event at server)
        vec = [max(a,b) for a,b in zip(vec, recv_vec)]
        vec[server_id] += 1
        print(f"Recv from {sid} addr={addr} recv_vec={recv_vec} -> server_vec={vec}")
    # reply with server vector (so client can simulate receive of reply)
    conn.send(json.dumps({'vector':vec}).encode())
    conn.close()

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((args.host, args.port))
s.listen(5)
print(f"Server({server_id}) listening on {args.host}:{args.port} N={N}")

while True:
    c, a = s.accept()
    threading.Thread(target=handle, args=(c,a), daemon=True).start()


"""
----- HOW TO RUN -----

Terminal 1:
    python3 vector_server.py --n 3 --port 6000

Expected short output:
    Server(0) listening on 0.0.0.0:6000
    Recv from 1 recv_vec=[1,0,0] -> server_vec=[2,0,0]
    Recv from 2 recv_vec=[0,1,0] -> server_vec=[2,1,0]

Terminal 2:
    python3 vector_client.py --id 1 --n 3 --host 127.0.0.1 --port 6000

Terminal 3:
    python3 vector_client.py --id 2 --n 3 --host 127.0.0.1 --port 6000

Expected short output:
    [P1] internal -> [0,1,0]
    [P1] send -> merged -> [2,2,0]
    [P1] FINAL [3,2,0]

    [P2] internal -> [0,0,1]
    [P2] send -> merged -> [2,1,2]
    [P2] FINAL [2,1,3]
"""