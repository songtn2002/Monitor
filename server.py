import datetime
import socket
import threading
import time
import numpy as np

PORT = 5051
SERVER = ""
#SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!DISCONNECT"
MY = "dlskk90105kdlslnvnsl"

classrooms = {}
connected = {}

def removeStudent(meeting_id, name, addr_str):
    if meeting_id == "%prev%" and name == "%prev%":
        print("prev exit")
        return
    classroom = classrooms[meeting_id]
    removeIndex = -1
    for i in range (0, len(classroom)):
        if classroom[i][0] == name and classroom[i][3] == addr_str:
            removeIndex = i
            break
    if removeIndex != -1:
        classroom.pop(removeIndex)
    else:
        print("Cannot find student with name: "+name+" with address: "+addr_str)

def addView (classroom, view):
    found = False
    for i in classroom:
        if i[0] == view[0] and i[3] == view[3]: #if the same name, then change the img and time_stamp
            i[1] = view[1]
            i[2] = view[2]
            found = True
            break
    if found == False:
        classroom.append(view)

def printClassrooms():
    result = "classrooms: {"
    for k in classrooms.keys():
        result += "\""+ k + "\":"+"["
        classroom_size = len(classrooms[k])
        for index in range(0, classroom_size):
            item = classrooms[k][index]
            time_stamp = str(item[2])
            time_stamp = time_stamp.split(".")[0][-4:]
            result += "[" + item[0] +", "+ time_stamp +"], "
        result += "], "
    result += "}"
    print(result)

def printClassroomsThread():
    while True:
        printClassrooms()
        print(f"[ACTIVE CONNECTIONS] {len(threading.enumerate()) - 2}")

        time_stamp = str(time.time())
        time_stamp = time_stamp.split(".")[0][-4:]
        print("[CURRENT TIME]: "+time_stamp)
        time.sleep(2)

printThread = threading.Thread(target=printClassroomsThread, args=())

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")

    msg = conn.recv(64)
    print("Start Message Length: "+str(len(msg)))

    #20 bytes in front as password, check if the password is correct
    MY_rcv = msg[0:20].decode("utf-8")
    if MY_rcv != MY:
        return #if password incorrect, do nothing
    else:
        print("Password Correct!")

    msg = msg[20:]
    msg = msg.decode("utf-8").strip()

    if msg == "Student":#student connection
        handle_student(conn, addr)
    else:#teacher
        handle_teacher(conn, addr, msg)

def connSendClassroom(conn, classroom):
    b_students = []
    for student in classroom:
        name = student[0]
        screen = student[1]

        name = name.encode(FORMAT)
        name = name + b' '*(100-len(name))
        b_student1 = name + screen
        b_students.append(b_student1)
    #first turn all the students into bytes

    #then send them all
    classroom_len = str(len(classroom)).encode(FORMAT)
    classroom_len = classroom_len + b' ' * (4 - len(classroom_len))
    conn.send(classroom_len)
    for b_student2 in b_students:
        for i in range(0, 241):
            sent = b_student2[i*1000: min(len(b_student2), i*1000+1000)]
            conn.send(sent)

def handle_teacher(conn, addr, msg):
    meeting_id = msg.split("@")[1]

    if not (meeting_id in classrooms.keys()):
        classrooms[meeting_id] = []

    while True:
        try:
            connSendClassroom(conn, classrooms[meeting_id])
        except ConnectionError:
            print("connection closed 2")
            break
       
        #sleep for a while
        time.sleep(1.5)

    conn.close()

def recvMessage (conn, msg_len):
    msg = bytearray()
    while len(msg) < msg_len:

        if len(msg) == 0:
            conn.settimeout(10)
        else:
            conn.settimeout(7)
            
        len_to_recv = min(1000, msg_len-len(msg))
        received = conn.recv(len_to_recv)

        if len(received) == 0:
            print("[Received: 0] Not enough bytes received")
            raise ConnectionAbortedError("connection closed on the student client side")
        #print("received: "+str(len(received)))
        msg += received
    return msg

def handle_student(conn, addr):
    meeting_id = "%prev%"
    name = "%prev%"
    while True:
        try:
            msg = recvMessage(conn, 240500)
        except ConnectionError:
            print("student disconnected")
            break
        except socket.timeout:
            print("student disconnected: timeout")
            break
        except Exception as excp:
            print("Exception: "+str(excp))
            break

        meeting_id = msg[0:300].decode(FORMAT).strip()
        name = msg[300:400].decode(FORMAT).strip()
        time_stamp = float(msg[400:500].decode(FORMAT).strip())
        img = msg[500:]
        addr_str = str(addr)
        view = [name, img, time_stamp, addr_str]

        if meeting_id in classrooms.keys():
            addView(classrooms[meeting_id], view)
        else:
            classrooms[meeting_id] = [view]

    print("ready to remove student @classroom: "+meeting_id+" with address @"+addr_str+" of name: "+name)
    removeStudent(meeting_id, name, addr_str)
    conn.close()

def start():
    server.listen()
    printThread.start()
    print(f"[LISTENING] Server is listening on {SERVER}")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

print("[STARTING] server is starting...")
start()