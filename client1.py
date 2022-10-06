import sys
import threading
import time
import numpy as np
import cv2
from PyQt5 import QtGui
from mss import mss
import PyQt5
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon

from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton, QProgressDialog, \
    QSystemTrayIcon, QAction, QMenu
import socket

client = None
clientIsOn = False
DISCONNECT_MESSAGE = "!DISCONNECT"
ADDR = ("120.48.128.151", 5051)
MY = "dlskk90105kdlslnvnsl"
#ADDR = ("192.168.50.31", 5051)


window = None
app = None
tray_icon = None

idTextField = None
nameTextField = None

start_last_clicked = time.time()
prev_meeting_id = "%prev_meeting_id%"
prev_name = "%prev_name%"

class MainWindow (QWidget):

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.layout = QHBoxLayout()

        global idTextField
        idTextField = QLineEdit()
        idTextField.setEchoMode(QLineEdit.Normal)
        idTextField.setFixedWidth(200)

        label1 = QLabel("Meeting ID: ")#label 1 is Meeting ID Label
        label1.setBuddy(idTextField)

        global nameTextField
        nameTextField = QLineEdit()
        nameTextField.setEchoMode(QLineEdit.Normal)
        nameTextField.setFixedWidth(150)

        label2 = QLabel("Guest Name: ")  # label 1 is Meeting ID Label
        label2.setBuddy(idTextField)

        buttonStart = QPushButton("")
        buttonStart.setIcon(QIcon("start.png"))
        buttonStart.setIconSize(QSize(24, 24))
        buttonStart.clicked.connect(startStreaming)

        buttonStop = QPushButton("")
        buttonStop.setIcon(QIcon("stop.png"))
        buttonStop.setIconSize(QSize(24, 24))
        buttonStop.clicked.connect(closeButton)

        global tray_icon
        tray_icon = QSystemTrayIcon(self)
        tray_icon.setIcon(QIcon("tray.jpg"))

        open_action = QAction("open", self)
        open_action.triggered.connect(self.show)
        close_action = QAction("close", self)
        close_action.triggered.connect(terminate)

        tray_menu = QMenu()
        tray_menu.addAction(open_action)
        tray_menu.addAction(close_action)
        tray_icon.setContextMenu(tray_menu)
        tray_icon.activated.connect(self.show)
        tray_icon.show()

        self.layout.addWidget(label1)
        self.layout.addWidget(idTextField)
        self.layout.addWidget(label2)
        self.layout.addWidget(nameTextField)
        self.layout.addWidget(buttonStart)
        self.layout.addWidget(buttonStop)

        self.setLayout(self.layout)

    def closeEvent(self, event):
        event.ignore()
        terminate()




START_STREAMING = 1
STREAMING_STOPPED = 2
def iconShowMessage(message_type):
    if message_type == START_STREAMING:
        tray_icon.showMessage("Start Streaming", "You are now watched by your teacher. Be careful!", msecs=1500)
    elif message_type == STREAMING_STOPPED:
        tray_icon.showMessage("Stop Streaming", "Phew... You turned off the video stream.",msecs=1500)
    else:
        print("Wrong Message Type")

def terminate():
    try:
        closeClient()
    except Exception as err:
        print(err)
    finally:
        sys.exit()

def closeClient():
    global clientIsOn, client
    if clientIsOn:
        clientIsOn = False
    if client:
        client.close()

def closeButton():
    closeClient()
    iconShowMessage(STREAMING_STOPPED)

def collectMsg(name, meeting_id):
    screen = None

    with mss() as sct:
        # Get information of monitor 2
        monitor_number = 1
        mon = sct.monitors[monitor_number]
        screen = sct.grab(mon)

    screen = np.array(screen)
    screen = cv2.resize(screen, (400, 200))
    screen = cv2.cvtColor(screen, cv2.COLOR_RGBA2RGB)
    screen = screen.tobytes()
    print("screen_length: " + str(len(screen)))

    b_meeting_id = meeting_id.encode("utf-8")
    b_meeting_id = b_meeting_id + b' ' * (300 - len(b_meeting_id))
    print("meeting_id: " + meeting_id)

    b_name = name.encode("utf-8")
    b_name = b_name + b' ' * (100 - len(b_name))
    print("name:" + nameTextField.text())

    timeStamp = str(time.time()).encode("utf-8")
    timeStamp = timeStamp + b' ' * (100 - len(timeStamp))
    print("timeStamp:" + str(time.time()))

    msg = b_meeting_id + b_name + timeStamp + screen
    # print("image size: " + str(len(screen)))
    print("length sent: " + str(len(msg)))
    return msg


def clientSend(client, msg):
    beg = 0
    while beg < len(msg):
        end = beg + 1000
        sent = msg[beg:min(end, len(msg))]
        client.send(sent)
        beg = end

def clientAction(name, meeting_id):
    global client, clientIsOn, prev_name, prev_meeting_id
    clientIsOn = True
    iconShowMessage(START_STREAMING)

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(ADDR)
    print("Connected to ["+str(ADDR)+"]")

    prev_meeting_id = meeting_id
    prev_name = name

    startMsg = "Student".encode("utf-8")
    startMsg = MY.encode("utf-8")+startMsg
    startMsg = startMsg + b" "*(64-len(startMsg))
    client.send(startMsg)

    while clientIsOn:
        time_start_loop = time.time()#record the time when loop is started
        print("loop starts at "+str(time_start_loop))

        msg = collectMsg(name, meeting_id)
        try:
            clientSend(client, msg)
        except OSError:
            print("[OS Error]: client closed")
            break
        except Exception as exp:
            print("client closed with exception @"+str(exp))
            break

        # Keep every loop within 5 seconds
        while time.time() - time_start_loop < 3 and clientIsOn:
            time.sleep(0.1)



def startStreaming():
    global clientIsOn, start_last_clicked, prev_name, prev_meeting_id

    #protection against violent operations
    if (time.time() - start_last_clicked) <= 0.5:
        print("useless click - violent")
        return
    else:
        start_last_clicked = time.time()

    #if meeting_id or name is blank, do nothing
    if nameTextField.text().strip() == "" or idTextField.text().strip() == "":
        print("useless click - blank")
        return

    #if client is on, return
    if clientIsOn:
        print("useless click - client is on")
        return

    #if client is turned off, make sure that previous thread exits
    while len(threading.enumerate()) >= 2:
        print("wait for previous connection exit")
        time.sleep(0.01)

    def securedClientAction(name, meeting_id):  # surround clientAction with try/except
        try:
            clientAction(name, meeting_id) #keep sending to server until stopped
        except Exception as exp:
            print("Exception @"+str(exp))
            print("client closed @ exception")
            closeClient()
        else:
            print("close client just in case")
            closeClient()

    thread = threading.Thread(target=securedClientAction, args=(nameTextField.text(), idTextField.text()))
    thread.start()
    #window.hide()


if __name__ == '__main__':
    app = QApplication([])
    app.setApplicationName("Zoom视频加速器")
    #TODO: set application window icon
    window = MainWindow()
    window.setFixedHeight(80)
    window.setWindowIcon(QIcon("tray.jpg"))
    window.show()
    app.exec_()
