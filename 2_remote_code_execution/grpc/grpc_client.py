# grpc_client.py
import grpc
import codeexec_pb2
import codeexec_pb2_grpc
from threading import Thread
import random
import time

def worker(cid):
    channel = grpc.insecure_channel('localhost:50051')
    stub = codeexec_pb2_grpc.CodeExecStub(channel)

    for _ in range(4):
        op = random.choice(["Add", "Sort", "Upper", "Reverse"])

        if op == "Add":
            req = codeexec_pb2.TwoNumbers(num1=cid, num2=random.randint(1,10))
            res = stub.Add(req)

        elif op == "Sort":
            nums = [random.randint(1, 100) for _ in range(5)]
            res = stub.Sort(codeexec_pb2.NumberList(nums=nums))

        elif op == "Upper":
            res = stub.Upper(codeexec_pb2.Text(value="hello grpc"))

        else:
            res = stub.Reverse(codeexec_pb2.Text(value="grpc engine"))

        print(f"[CLIENT {cid}] {op} => {res}")
        time.sleep(0.4)

threads = []
for cid in range(1, 6):
    t = Thread(target=worker, args=(cid,))
    t.start()
    threads.append(t)

for t in threads:
    t.join()
