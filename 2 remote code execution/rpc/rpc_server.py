# rpc_server.py
from xmlrpc.server import SimpleXMLRPCServer
from socketserver import ThreadingMixIn
import threading

class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass

print("🚀 RPC Remote Code Execution Server running on port 8000...")

server = ThreadedXMLRPCServer(("localhost", 8000), allow_none=True)

# --------------------------------------
# REMOTE EXECUTION FUNCTION (WITH THREAD PRINTS)
# --------------------------------------
def execute_task(task_type, data):

    # Print current thread handling request
    print(f"[THREAD {threading.get_ident()}] Handling task: {task_type}")

    if task_type == "add":
        x, y = data
        return x + y

    elif task_type == "sort":
        return sorted(data)

    elif task_type == "reverse":
        return data[::-1]

    elif task_type == "uppercase":
        return data.upper()

    else:
        return "❌ Unknown task"

server.register_function(execute_task, "execute_task")

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\n🛑 Server stopping (Ctrl+C pressed)…")
    server.server_close()
    print("✅ Server closed cleanly.")
