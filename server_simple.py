import socket
import threading
HEADER = 64
PORT = 5050
ADDR = ("", PORT)
FORMAT = 'utf-8'
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

def handle_client(conn, addr):
    msg = conn.recv(400000)
    print("length of message in bytes: "+str(len(msg)))
    msg = msg.decode("utf-8")
    print("message: "+msg)
    conn.close()

def start():
    server.listen()
    print("")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.activeCount() - 1}")

print("[STARTING] server is starting...")
start()