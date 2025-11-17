# rpc_client_single.py
import xmlrpc.client
import sys

cid = sys.argv[1]  # get client ID
proxy = xmlrpc.client.ServerProxy("http://localhost:8000/")

print(f"\n==== CLIENT {cid} Running ====\n")

tasks = [
    ("add", [10, 5]),
    ("sort", [5, 3, 9, 1]),
    ("reverse", "client" + cid),
    ("uppercase", "hello rpc")
]

for t, data in tasks:
    print(f"[CLIENT {cid}] → Sending {t}: {data}")
    result = proxy.execute_task(t, data)
    print(f"[CLIENT {cid}] ← Result:", result)
