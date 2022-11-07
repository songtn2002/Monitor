import socket
import sys
import threading
import time
import numpy as np
import cv2
from datetime import date

from PyQt5.QtGui import QIcon, QImage, QPixmap, QPainter, QPen, QColor, QBrush, QFont
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QApplication, \
    QGridLayout, QSystemTrayIcon, QErrorMessage, QDialog, QSizePolicy
from PyQt5.QtCore import Qt, QTimer

import platform

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
        bStr = block[0]
        res += bStr + ", "
    res += "]"
    print(res)

client = None
clientIsOn = False
prev_meeting_id = ""
DISCONNECT_MESSAGE = "!DISCONNECT"
#ADDR = ("120.48.128.151", 5051)
ADDR = ("192.168.50.31", 5051)
MY = "dlskk90105kdlslnvnsl"
BLOCK_SIZE = 60000
SYSTEM = platform.system().lower()

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
        while len(b_student) < BLOCK_SIZE:
            snippet = client.recv(1000)
            #print ("snippet length: "+str(len(snippet)))
            b_student = b_student + snippet
        prev_over = b_student[BLOCK_SIZE:]
        b_student = b_student[0:BLOCK_SIZE]
        #print("length of student "+str(i+1)+" is: "+str(len(b_student)))
        name = b_student[0:100].decode("utf-8").strip()
        print("name: "+name)
        view_len = int(b_student[100:200].decode("utf-8").strip())
        print("view_len: "+str(view_len))
        view = np.frombuffer(b_student[-view_len : ], dtype="uint8")
        view = cv2.imdecode(view, cv2.IMREAD_UNCHANGED)
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

        global app
        screen_size = app.primaryScreen().size()
        self.setMaximumSize(screen_size.width(), screen_size.height())
        self.setMinimumSize(1000, 600)

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
                label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.bottom_area.addWidget(label, i, j)
                labels[i][j] = label

        self.main_layout.addLayout(self.top_bar)
        self.main_layout.addLayout(self.bottom_area)

        self.setLayout(self.main_layout)

        global tray_icon
        tray_icon = QSystemTrayIcon(self)
        tray_icon.setIcon(QIcon("Monitor Icon.png"))
        tray_icon.show()

        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.updateImages())
        self.timer.start(1500)

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

            student_screen = students[i][1]

            image = QImage(student_screen, student_screen.shape[1], student_screen.shape[0], QImage.Format_RGB888)

            if not SYSTEM == "darwin": #if operating system is windows or linux
                painter = QPainter(image)
                rectWidth = len(students[i][0])*12+5
                rectHeight = 30
                painter.fillRect(400-rectWidth, 200-rectHeight, rectWidth, rectHeight, 1)
                painter.setFont(QFont("Sans Serif", 12, QFont.Bold))
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(400-rectWidth, 200-6, students[i][0])
            else: #if operating system is Mac
                painter = QPainter(image)
                rectWidth = len(students[i][0]) * 15 + 5
                rectHeight = 30
                painter.fillRect(400 - rectWidth, 200 - rectHeight, rectWidth, rectHeight, 1)
                painter.setFont(QFont("Sans Serif", 30, QFont.Normal))
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(400 - rectWidth, 200 - 6, students[i][0])
            labels[x][y].setPixmap(QPixmap.fromImage(image).scaled(labels[x][y].size()))
            painter.end()

def isExpired(x_year, x_month, x_day):
    today = date.today()
    year = today.year
    month = today.month
    day = today.day
    if year > x_year:
        return True
    elif year == x_year and month > x_month:
        return True
    elif year == x_year and month == x_month and day > x_day:
        return True
    else:
        return False

class ExpireDialog(QDialog):

    def __init__(self, message, parent=None):
        super(ExpireDialog, self).__init__(parent)

        layout = QVBoxLayout()
        self.label = QLabel(message)
        self.label.setAlignment(Qt.AlignHCenter)
        self.buttonOk = QPushButton("OK")
        self.buttonOk.clicked.connect(self.buttonOkAction)
        layout.addWidget(self.label)
        layout.addWidget(self.buttonOk)
        self.setLayout(layout)

        self.setFixedSize(500, 100)

        self.setWindowIcon(QIcon("Monitor Icon.png"))

    def buttonOkAction(self):
        self.hide()
        sys.exit()

if __name__ == '__main__':
    app = QApplication([])
    app.setApplicationName("Monitor班长-老师端")
    if isExpired(2022, 11, 20):
        exp_message = ExpireDialog("你的试用期已到")
        exp_message.show()
    else:
        window = MainWindow()
        window.setWindowIcon(QIcon("Monitor Icon.png"))
        window.show()
    app.exec_()