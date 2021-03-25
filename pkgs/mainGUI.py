from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from pkgs.vehicle.ui import carUI
from pkgs.palm.main import palmGUI
from pkgs.parcel.main import parcelGUI
from .select_ui import welcomeUI


class mainGUI(QMainWindow):    
    def __init__(self):
        super(mainGUI, self).__init__()
        self.setWindowIcon(QIcon("GUIImg/label.ico"))
        self.setWindowTitle('Vehicle Detector Assistant')
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("QMainWindow {background-color: transparent;}")
        self.startWelcomeTool()
        self.show()


    def startWelcomeTool(self):
        self.welcomeWindow = welcomeUI(self)
        #self.welcomeWindow.pb_close.clicked.connect(self.close)
        #self.welcomeWindow.pb_hide.clicked.connect(self.showMinimized)
        self.welcomeWindow.pb_car_api.clicked.connect(self.startCarAPI)
        self.welcomeWindow.pb_palm_api.clicked.connect(self.startPalmAPI)
        self.welcomeWindow.pb_parcel_api.clicked.connect(self.startParcelAPI)
        self.setCentralWidget(self.welcomeWindow)
        self.setFixedSize(self.welcomeWindow.frame_welcome.width(), self.welcomeWindow.frame_welcome.height())
        self._moveWidgetToCenter()


    def startCarAPI(self):
        self.combineWindow = carUI(self)
        self.combineWindow.pb_return.clicked.connect(self.startWelcomeTool)
        self.setCentralWidget(self.combineWindow)
        self.setFixedSize(self.combineWindow.frame_bnbox.width(), self.combineWindow.frame_bnbox.height())
        self._moveWidgetToCenter()

    
    def startPalmAPI(self):
        self.palmWindow = palmGUI(self)
        self.palmWindow.pb_return.clicked.connect(self.startWelcomeTool)
        self.setCentralWidget(self.palmWindow)
        self.setFixedSize(self.palmWindow.palm_frame.width(), self.palmWindow.palm_frame.height())
        self._moveWidgetToCenter()


    def startParcelAPI(self):
        self.parcelWindow = parcelGUI(self)
        self.parcelWindow.pb_return.clicked.connect(self.startWelcomeTool)
        self.setCentralWidget(self.parcelWindow)
        self.setFixedSize(self.parcelWindow.frame_main.width(), self.parcelWindow.frame_main.height())
        self._moveWidgetToCenter()


    def _moveWidgetToCenter(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

