import socket

host = "127.0.0.1"
port = 12000

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((host, port))

while True:
    msg = input("Enter message (or exit): ")

    if msg.lower() == "exit":
        break

    client.send(msg.encode())
    print("Server:", client.recv(1024).decode())

client.close()
