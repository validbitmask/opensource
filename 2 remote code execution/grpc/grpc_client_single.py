# grpc_client_single.py
import grpc
import sys
import codeexec_pb2
import codeexec_pb2_grpc

cid = sys.argv[1]

channel = grpc.insecure_channel("localhost:50051")
stub = codeexec_pb2_grpc.CodeExecStub(channel)

print(f"\n==== CLIENT {cid} Running ====\n")

# ADD
print(f"[CLIENT {cid}] Sending Add")
res = stub.Add(codeexec_pb2.TwoNumbers(num1=10, num2=5))
print("[RESULT]", res.value)

# SORT
print(f"[CLIENT {cid}] Sending Sort")
res = stub.Sort(codeexec_pb2.NumberList(nums=[50, 20, 90, 10]))
print("[RESULT]", list(res.nums))

# REVERSE
print(f"[CLIENT {cid}] Sending Reverse")
res = stub.Reverse(codeexec_pb2.Text(value="grpc engine"))
print("[RESULT]", res.value)

# UPPER
print(f"[CLIENT {cid}] Sending Upper")
res = stub.Upper(codeexec_pb2.Text(value="hello grpc"))
print("[RESULT]", res.value)

print("\n==== CLIENT DONE ====\n")
