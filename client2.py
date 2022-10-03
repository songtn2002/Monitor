import socket
import sys
import threading
import time
import numpy as np

from PyQt5.QtGui import QIcon, QImage, QPixmap, QPainter, QPen, QColor, QBrush, QFont
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QApplication, \
    QGridLayout, QSystemTrayIcon
from PyQt5.QtCore import Qt, QTimer

window = None
labels = [[None, None, None, None], [None, None, None, None], [None, None, None, None], [None, None, None, None]]
students = []

connect_last_clicked = time.time()

tray_icon = None
SUCCESSFULLY_CONNECTED = 1
CONNECTION_FAILED = 2
CANNOT_CONNECT = 3

def iconShowMessage(message_type):
    if message_type == SUCCESSFULLY_CONNECTED:
        tray_icon.showMessage("Successfully Connected", "Graphics will start to load. You will see your students shortly.", msecs=1000)
    elif message_type == CONNECTION_FAILED:
        tray_icon.showMessage("Connection Failed", "Please re-click the connect button. Sorry for inconvenience...",msecs=1000)
    elif message_type == CANNOT_CONNECT:
        tray_icon.showMessage("Cannot Connect to Server", "Please check your internet connectivity and reconnect",msecs=1000)
    else:
        print("Wrong Message Type")

def printStudents():
    res = "["
    for block in students:
        bStr = "[" + block[0] +"]"
        res += bStr + ", "
    res += "]"
    print(res)

client = None
clientIsOn = False
prev_meeting_id = ""
DISCONNECT_MESSAGE = "!DISCONNECT"
ADDR = ("120.48.128.151", 5051)
#ADDR = ("192.168.50.31", 5051)
MY = "dlskk90105kdlslnvnsl"

def closeClient():
    global client, clientIsOn
    if clientIsOn:
        clientIsOn = False
    if client:
        client.close()

def terminate():
    try:
        closeClient()
    except Exception as err:
        print(err)
    finally:
        sys.exit()

def recvClassroom(client):
    classroom_len = client.recv(4).decode("utf-8")
    classroom_len = int(classroom_len.strip())
    print("classroom length: "+str(classroom_len))
    classroom = []
    prev_over = bytearray()
    for i in range (0, classroom_len):
        b_student = prev_over
        while len(b_student)<240100:
            if len(b_student) == 240000:
                snippet = client.recv(100)
            else:
                snippet = client.recv(1000)
            #print ("snippet length: "+str(len(snippet)))
            b_student = b_student + snippet
        prev_over = b_student[240100:]
        b_student = b_student[0:240100]
        #print("length of student "+str(i+1)+" is: "+str(len(b_student)))
        name = b_student[0:100].decode("utf-8").strip()
        print("name: "+name)
        view = np.frombuffer(b_student[100:], dtype="uint8")
        view = view.reshape(200, 400 , 3)
        classroom.append([name, view])
    return classroom

def reconnect():
    global clientIsOn, connect_last_clicked

    #prohibit violent operations
    if (time.time() - connect_last_clicked) <= 2:
        print("useless click 1 - violent")
        return

    #do nothing if meeting id is blank
    if window.meeting_id_textField.text() == "":
        print("useless click  - blank")
        return

    #do nothing if client is on and meeting id has not yet changed
    #if clientIsOn and window.meeting_id_textField.text() == prev_meeting_id:
    #    print("useless click 3 - still the same meeting id")
    #    return

    connect_last_clicked = time.time() #record this effective clicking
    closeClient()

    #make sure that previous thread exits
    while len(threading.enumerate()) >= 2:
        print("wait for previous connection exit")
        time.sleep(0.01)

    def clientAction():
        global window, students, client, prev_meeting_id, clientIsOn
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(ADDR)

            meeting_id = window.meeting_id_textField.text()

            startString = ("Teacher@"+ meeting_id).encode("utf-8")
            startString = MY.encode("utf-8") + startString
            startString = startString + b" "*(64-len(startString))
            client.send(startString)
        except OSError as ose:
            print(ose)
            iconShowMessage(CANNOT_CONNECT)

            closeClient()
            return
        else:
            clientIsOn = True
            prev_meeting_id = meeting_id

            iconShowMessage(SUCCESSFULLY_CONNECTED)
            print("successfully connected to server")

        parse_error = False
        while True:
            try:
                students = recvClassroom(client)
            except OSError:
                print("[OS Error]: connection aborted")
                iconShowMessage(CONNECTION_FAILED)
                break
            except (UnicodeDecodeError, ValueError):
                print("[PARSE ERROR]: close client and reconnect")
                parse_error = True
                client.close()
                new_thread = threading.Thread(target=clientAction, args=())
                new_thread.start()
                break
            except Exception as exp:
                print(exp)
                break
            printStudents() #print all the student views received

        if not parse_error:
            print("client closed")
            closeClient()

    thread = threading.Thread(target=clientAction, args=())
    thread.start()

class MainWindow(QWidget):

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.main_layout = QVBoxLayout()
        self.top_bar = QHBoxLayout()
        self.bottom_area = QGridLayout()

        self.meeting_id_textField = QLineEdit()
        self.meeting_id_textField.setEchoMode(QLineEdit.Normal)
        self.meeting_id_textField.setMinimumWidth(150)

        self.meeting_id_label = QLabel("meeting_id: ")
        self.meeting_id_label.setBuddy(self.meeting_id_textField)

        self.connect_buttton = QPushButton("connect")
        self.connect_buttton.clicked.connect(reconnect)

        self.top_bar.addWidget(self.meeting_id_label)
        self.top_bar.addWidget(self.meeting_id_textField)
        self.top_bar.addWidget(self.connect_buttton)
        self.top_bar.setAlignment(Qt.AlignTop)

        #initialize all the labels
        for i in range(0, 4):
            for j in range(0, 4):
                label = QLabel()
                label.setFixedWidth(400)
                label.setFixedHeight(200)
                self.bottom_area.addWidget(label, i, j)
                labels[i][j] = label

        self.main_layout.addLayout(self.top_bar)
        self.main_layout.addLayout(self.bottom_area)

        self.setLayout(self.main_layout)

        global tray_icon
        tray_icon = QSystemTrayIcon(self)
        tray_icon.setIcon(QIcon("tray.jpg"))
        tray_icon.show()

        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.updateImages())
        self.timer.start(2000)

    def closeEvent(self, event):
        QWidget.closeEvent(self, event)
        terminate()

    def updateImages(self):
        for x in range(0, 4):
            for y in range(0, 4):
                labels[x][y].clear()
        for i in range (0, len(students)):
            x = int(i/4)
            y = i%4
            image = QImage(students[i][1], 400, 200, QImage.Format_RGB888)

            painter = QPainter(image)
            rectWidth = len(students[i][0])*12+5
            rectHeight = 30
            painter.fillRect(400-rectWidth, 200-rectHeight, rectWidth, rectHeight, 1)
            painter.setFont(QFont("Times", 12, QFont.Bold))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(400-rectWidth, 195, students[i][0])
            labels[x][y].setPixmap(QPixmap.fromImage(image))
            painter.end()


if __name__ == '__main__':
    app = QApplication([])
    app.setApplicationName("Zoom监视器")
    window = MainWindow()
    window.setFixedWidth(1650)
    window.setFixedHeight(900)
    window.setWindowIcon(QIcon("tray.jpg"))
    window.show()
    app.exec_()