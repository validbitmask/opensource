# Client.py (Updated)
import xmlrpc.client

# Connect to the remote service
proxy = xmlrpc.client.ServerProxy("http://localhost:8001/")

# Remote Invocation 1: Addition (already there)
num1, num2 = 15, 7
result_add = proxy.addition(num1, num2)
print(f"Invocation: addition({num1}, {num2}) -> Result: {result_add}")

# Remote Invocation 2: Subtraction (NEW CALL)
num5, num6 = 30, 12
result_sub = proxy.subtraction(num5, num6) # <-- This is the missing call!
print(f"Invocation: subtraction({num5}, {num6}) -> Result: {result_sub}")

# Remote Invocation 3: Multiplication (already there)
num3, num4 = 6, 8
result_mult = proxy.multiplication(num3, num4)
print(f"Invocation: multiplication({num3}, {num4}) -> Result: {result_mult}")