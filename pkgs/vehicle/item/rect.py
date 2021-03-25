from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class RectItem(QGraphicsRectItem):
    def __init__(self, *args):
        """
        Initialize the shape.
        """
        super().__init__(*args)
        self.current_rect = self.rect()
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)


    def paint(self, painter, option, widget=None):
        """
        Paint the node in the graphic view.
        """
        # drawing the bounding box rect
        # color ver1 before 2020-9-15: (39, 88, 255)
        painter.setPen(QPen(QColor(68, 123, 231), 8.0, style=Qt.SolidLine, cap=Qt.RoundCap, join=Qt.RoundJoin))
        painter.drawRect(self.rect())


    def itemChange(self, change, value):
        if isinstance(value, QPointF):
            diffX = value.x()
            diffY = value.y()
            rect = self.rect()
            self.current_rect.setLeft(round(rect.left() + diffX))
            self.current_rect.setTop(round(rect.top() + diffY))
            self.current_rect.setWidth(rect.width())
            self.current_rect.setHeight(rect.height())
        return super().itemChange(change, value)
