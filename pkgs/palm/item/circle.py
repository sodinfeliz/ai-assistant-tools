from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class PosCircleItem(QGraphicsEllipseItem):
    
    circle_size = 12

    def __init__(self, x, y, color='red'):
        super(PosCircleItem, self).__init__(
            x-self.circle_size//2,
            y-self.circle_size//2,
            self.circle_size,
            self.circle_size
        )
        self.color = color
    
    def paint(self, painter, option, widget=None):
        qt_colors = {'red': Qt.red, 'blue': Qt.blue}
        painter.setBrush(QBrush(qt_colors[self.color], style = Qt.SolidPattern))
        painter.drawEllipse(self.rect())
