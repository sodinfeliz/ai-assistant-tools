from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class PosCircleItem():
    def __init__(self, x, y, color='red'):
        self._set_item(x, y, color)

    def _set_item(self, x, y, color):
        qt_colors = {'red': Qt.red, 'blue': Qt.blue}
        circle = QGraphicsEllipseItem(x-6, y-6, 12, 12)
        circle.setBrush(QBrush(qt_colors[color], style = Qt.SolidPattern))
        self.item =  circle
