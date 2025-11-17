# vector_client.py
import socket, json, time, random, argparse

parser = argparse.ArgumentParser()
parser.add_argument('--id', type=int, required=True, help='client id (1..N-1)')
parser.add_argument('--n', type=int, default=3, help='total processes (incl server)')
parser.add_argument('--host', default='127.0.0.1')
parser.add_argument('--port', type=int, default=6000)
parser.add_argument('--steps', type=int, default=6, help='number of local events to simulate')
args = parser.parse_args()

pid = args.id
N = args.n
vec = [0]*N

def internal_event():
    vec[pid] += 1
    print(f"[P{pid}] internal -> {vec}")

def send_event():
    vec[pid] += 1                     # increment before send
    msg = json.dumps({'id': pid, 'vector': vec})
    try:
        s = socket.socket()
        s.connect((args.host, args.port))
        s.send(msg.encode())
        reply = s.recv(4096).decode()
        s.close()
        server_vec = json.loads(reply)['vector']
        # upon receive of reply: merge then increment own entry (receive event)
        for i in range(N):
            vec[i] = max(vec[i], server_vec[i])
        vec[pid] += 1
        print(f"[P{pid}] sent -> got reply server_vec={server_vec} updated {vec}")
    except Exception as e:
        print("conn err", e)

# simple randomized sequence of events
for step in range(args.steps):
    action = random.choice(['int','send','int'])
    if action == 'int':
        internal_event()
    else:
        send_event()
    time.sleep(random.uniform(0.3,1.0))
print(f"[P{pid}] FINAL {vec}")


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