# Server.py
from xmlrpc.server import SimpleXMLRPCServer

def add(a, b):
    # Demonstrate simple marshaling/unmarshalling
    print(f"Received remote call: ADD({a}, {b})") 
    return a + b

def subtract(a, b):
    print(f"Received remote call: SUBTRACT({a}, {b})")
    return a - b

def multiply(a, b):
    print(f"Received remote call: MULTIPLY({a}, {b})")
    return a * b

# Create server
server = SimpleXMLRPCServer(("localhost", 8001))
server.register_introspection_functions() # Allows client to inspect methods

# Register the remote functions [cite: 65]
server.register_function(add, 'addition')
server.register_function(subtract, 'subtraction')
server.register_function(multiply, 'multiplication')

print("Arithmetic Service listening on port 8001...")
server.serve_forever() # Uncomment to run the server