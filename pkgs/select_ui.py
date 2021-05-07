from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi


class welcomeUI(QWidget):    
    def __init__(self, parent=None):
        super(welcomeUI, self).__init__(parent)
        loadUi('GUI/widget_welcome.ui', self)
