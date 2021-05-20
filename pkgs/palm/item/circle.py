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
        self.dragging = False

    def mousePressEvent(self, mouseEvent: 'QGraphicsSceneMouseEvent') -> None:
        if mouseEvent.modifiers() == Qt.ShiftModifier and mouseEvent.buttons() == Qt.LeftButton:
            self.mouse_from = mouseEvent.pos()
            self.item_init_x = self.rect().x()
            self.item_init_y = self.rect().y()
            self.dragging = True
        else:
            return super().mousePressEvent(mouseEvent)

    def mouseMoveEvent(self, mouseEvent: 'QGraphicsSceneMouseEvent') -> None:
        if self.dragging:
            move = mouseEvent.pos() - self.mouse_from
            self.setRect(
                self.item_init_x + move.x(),
                self.item_init_y + move.y(),
                self.__class__.circle_size,
                self.__class__.circle_size
            )        
        else:
            return super().mouseMoveEvent(mouseEvent)
        

    def mouseReleaseEvent(self, mouseEvent: 'QGraphicsSceneMouseEvent') -> None:
        self.dragging = False
        return super().mouseReleaseEvent(mouseEvent)
    
    def paint(self, painter, option, widget=None):
        qt_colors = {'red': Qt.red, 'blue': Qt.blue}
        painter.setBrush(QBrush(qt_colors[self.color], style = Qt.SolidPattern))
        painter.drawEllipse(self.rect())
