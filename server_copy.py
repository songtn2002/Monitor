import socket
import threading
import numpy as np
import cv2

HEADER = 64
PORT = 5051
SERVER = socket.gethostbyname(socket.gethostname())#TODO: change the ip address of the server
ADDR = (SERVER, PORT)
FORMAT = "utf-8"

classrooms = {}

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(ADDR)

print("Server started@ "+SERVER+" "+"PORT: "+str(PORT))

while True:
    data, addr = server.recvfrom(500000)
    if len(data) < 2000: #teacher connection
        print("Teacher connection")
    else: #student connection
        print("Student connection")
        meeting_id = data[0:300].decode(FORMAT).rstrip() #decode the name string and then strip all the spaces on the right
        name = data[300:400].decode(FORMAT).rstrip()
        timeStamp = data[400:500].decode(FORMAT).rstrip()
        print("Meeting_id: "+meeting_id+" Name: "+name+"timeStamp: "+timeStamp)
        image = np.frombuffer(data[500:])
        image = np.reshape(image, (-1, 4))
        cv2.imwrite("image_received.png", image)
