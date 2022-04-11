import socket

HEADER = 64
PORT = 5050
SERVER = "180.76.147.175"
ADDR = (SERVER, PORT)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(ADDR)

def send_data():
    msg = ""
    for i in range (0, 2000):
        msg += str(i)
    #msg是从0开始的连续整数一直到2000拼起来的字符串
    print("message: "+msg)
    print("length of message: "+str(len(msg)))
    msg = msg.encode("utf-8")
    print("number of bytes sent: "+str(len(msg)) )
    client.sendall(msg)
    client.close()

send_data()

