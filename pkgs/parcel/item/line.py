import math
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class DeleteSignal(QObject):
    signal = pyqtSignal(QGraphicsLineItem)
    def emit_signal(self, obj):
        self.signal.emit(obj)


class LineHandleItem(QGraphicsLineItem):

    color = (196, 51, 51)

    def __init__(self, p1: QPointF, p2: QPointF, handleSize: int=20):
        assert isinstance(p1, QPointF) and isinstance(p2, QPointF)
        super().__init__()
        self._line = QLineF(p1, p2)
        self.points = [p1, p2]
        self.setLine(self._line)

        # handle
        self.handle1 = None
        self.handle2 = None
        self.handleSize = handleSize
        self.handleSpace = -1 * (handleSize // 2)
        self.handleSelected = None
        self.creating = False
        self.mousePressPos = None
        self.item_delete_signal = DeleteSignal()
        self._opacity = 0

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.updateHandlesPos()


    def updateHandlesPos(self):
        s = self.handleSize
        o = self.handleSize + self.handleSpace
        self.handles = dict()
        self.handles[1] = QRectF(self.points[0].x()-o, self.points[0].y()-o, s, s)
        self.handles[2] = QRectF(self.points[1].x()-o, self.points[1].y()-o, s, s)


    def handleAt(self, point):
        if self.handles[1].contains(point):
            return 1
        elif self.handles[2].contains(point):
            return 2
        return None


    def mousePressEvent(self, mouseEvent):
        """ 
        Executed when the mouse is pressed on the item.
        """
        self.is_creating()
        if mouseEvent.modifiers() == Qt.ShiftModifier or self.creating:
            self.handleSelected = self.handleAt(mouseEvent.pos())
            self.mousePressPos = mouseEvent.pos()
        super().mousePressEvent(mouseEvent)


    def mouseMoveEvent(self, mouseEvent):
        """
        Executed when the mouse is being moved over the item while being pressed.
        """
        if mouseEvent.modifiers() == Qt.ShiftModifier or self.creating:
            self.interactiveResize(mouseEvent.pos())


    def mouseReleaseEvent(self, mouseEvent):
        """
        Executed when the mouse is released from the item.
        """
        
        if self._width() == 0 and self._height() == 0 and self.creating:
            self.item_delete_signal.emit_signal(self)
        else:
            self.handleSelected = None
            self.mousePressPos = None
            self.creating = False
            self.update()
        super().mouseReleaseEvent(mouseEvent)


    def interactiveResize(self, mousePos):
        if self.handleSelected is not None:
            cp = self.handles[self.handleSelected].center()
            toX = cp.x() + mousePos.x() - self.mousePressPos.x()
            toY = cp.y() + mousePos.y() - self.mousePressPos.y()
            self.mousePressPos = mousePos
            self.points[self.handleSelected-1] = QPointF(toX, toY)
            self._line = QLineF(*self.points)
            self.setLine(self._line)
            self._opacity = 255
        self.updateHandlesPos()


    def center(self):
        cx = (self.points[0].x() + self.points[1].x()) / 2
        cy = (self.points[0].y() + self.points[1].y()) / 2
        return QPointF(cx, cy)


    def paint(self, painter, option, widget=None):
        """
        Paint the node in the graphic view.
        """
        # drawing the bounding box rect
        # (1, 254, 129)
        painter.setPen(QPen(QColor(*self.color, self._opacity), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawLine(self._line)

        # drawing the circle handles
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(*self.color, self._opacity), 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        
        for _, rect in self.handles.items():
            r = 1  # drawed circle radius
            cp = rect.center()
            painter.drawEllipse(QRectF(cp.x()-r, cp.y()-r, 2*r, 2*r))


    def is_creating(self):
        if self._width() == 0 and self._height() == 0:
            self.creating = True



    def _width(self):
        return abs(self.points[0].x() - self.points[1].x())


    def _height(self):
        return abs(self.points[0].y() - self.points[1].y())