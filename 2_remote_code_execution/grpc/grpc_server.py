# grpc_server.py
import grpc
from concurrent import futures
import threading

import codeexec_pb2
import codeexec_pb2_grpc

class CodeExecServicer(codeexec_pb2_grpc.CodeExecServicer):

    def Add(self, request, context):
        print(f"[THREAD {threading.get_ident()}] Handling Add")
        return codeexec_pb2.Result(value=request.num1 + request.num2)

    def Sort(self, request, context):
        print(f"[THREAD {threading.get_ident()}] Handling Sort")
        nums = sorted(list(request.nums))
        return codeexec_pb2.ListResult(nums=nums)

    def Upper(self, request, context):
        print(f"[THREAD {threading.get_ident()}] Handling Upper")
        return codeexec_pb2.Text(value=request.value.upper())

    def Reverse(self, request, context):
        print(f"[THREAD {threading.get_ident()}] Handling Reverse")
        return codeexec_pb2.Text(value=request.value[::-1])

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    codeexec_pb2_grpc.add_CodeExecServicer_to_server(CodeExecServicer(), server)
    server.add_insecure_port('[::]:50051')
    print("🚀 gRPC Server running on port 50051...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
