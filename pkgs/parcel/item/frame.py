import cv2
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi


class LabelFrame(QMainWindow):
    def __init__(self, parent=None):
        super(LabelFrame, self).__init__(parent)
        loadUi('GUI/widget_label.ui', self)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)









