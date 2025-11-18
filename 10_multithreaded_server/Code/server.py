import socket
import threading

def handle_client(conn, addr):
    print(f"Connected to {addr}")

    while True:
        data = conn.recv(1024).decode()
        if not data:
            break
        
        processed = "Processed: " + data
        conn.send(processed.encode())

    conn.close()
    print(f"Connection closed: {addr}")


def start_server():
    host = "127.0.0.1"
    port = 12000  # SAFE PORT

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # IMPORTANT FIX
    server.bind((host, port))
    server.listen(5)

    print(f"Server started on {host}:{port}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()


if __name__ == "__main__":
    start_server()
