
# 1. Run:
#       python3 minimal_distributed_kv.py
#
# 2. When prompted:
#       Mode? → type: eventual   or   strong
#       Value to write? → enter an integer
#       If you chose eventual, also enter propagation delay in seconds.


import time

replicas = [{"x": 0} for _ in range(3)]

def show(title):
    print("\n" + title)
    for i, r in enumerate(replicas):
        print(f"  Replica {i}: x = {r['x']}")
    print("-" * 30)

def eventual(write_value: int, delay: float):
    replicas[0]["x"] = write_value
    show("After local write on replica 0 (others stale)")
    print(f"Simulating network delay: sleeping {delay} seconds...")
    time.sleep(delay)
    for r in replicas[1:]:
        r["x"] = replicas[0]["x"]
    show("After propagation (eventual consistency)")

def strong(write_value: int):
    for r in replicas:
        r["x"] = write_value
    show("After synchronous replication (strong consistency)")

if __name__ == "__main__":
    show("Initial state (all replicas identical)")
    mode = input("Mode (eventual/strong): ").strip().lower()
    try:
        val = int(input("Value to write (integer): ").strip())
    except ValueError:
        print("Bad value — must be integer.")
        raise SystemExit(1)

    if mode == "eventual":
        try:
            d = float(input("Propagation delay in seconds (e.g. 2): ").strip())
        except ValueError:
            d = 2.0
        eventual(val, d)
    elif mode == "strong":
        strong(val)
    else:
        print("Unknown mode.")