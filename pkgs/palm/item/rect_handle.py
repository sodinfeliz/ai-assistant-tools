from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class ChangeSignal(QObject):
    signal = pyqtSignal()
    def emit_signal(self):
        self.signal.emit()


class DeleteSignal(QObject):
    signal = pyqtSignal(QGraphicsRectItem)
    def emit_signal(self, obj):
        self.signal.emit(obj)


class RectItemHandle(QGraphicsRectItem):

    defaultEdgeWidth = 30
    defaultColor = (15, 71, 180)
    selectedColor = (224, 24, 24)
    minSize = None

    handleTopLeft = 1
    handleTopRight = 2
    handleBottomLeft = 3
    handleBottomRight = 4

    handleCursors = {
        handleTopLeft: Qt.SizeFDiagCursor,
        handleTopRight: Qt.SizeBDiagCursor,
        handleBottomLeft: Qt.SizeBDiagCursor,
        handleBottomRight: Qt.SizeFDiagCursor,
    }

    def __init__(self, x, y, width, height, handleSize=10, zfactor=1):
        """
        Initialize the shape.
        """
        super(RectItemHandle, self).__init__(x, y, width, height)
        
        assert handleSize > 0
        self.handleSize = handleSize
        self.handleSpace = -1 * (handleSize // 2)

        o = self.handleSize + self.handleSpace
        self.setRect(self.rect().adjusted(-o, -o, o, o))

        self.handles = {}
        self.handleSelected = None
        self.mousePressPos = None
        self.mousePressRect = None
        self.creating = False
        self.item_changed_signal = ChangeSignal()
        self.item_delete_signal = DeleteSignal()
        self.color = self.defaultColor

        self.set_edge_width(zfactor)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.updateHandlesPos()

    def handleAt(self, point: QPoint):
        """
        Returns the resize handle below the given point.
        """
        for k, v, in self.handles.items():
            if v.contains(point):
                return k
        return None

    def mousePressEvent(self, mouseEvent):
        """
        Executed when the mouse is pressed on the item.
        """
        self.set_creating()
        if mouseEvent.modifiers() == Qt.ShiftModifier or self.creating:
            self.handleSelected = self.handleAt(mouseEvent.pos())
            self.mousePressPos = mouseEvent.pos()
            self.mousePressRect = self.rect()
        elif mouseEvent.modifiers() == Qt.ControlModifier:
            return super().mousePressEvent(mouseEvent)

    def mouseMoveEvent(self, mouseEvent):
        """
        Executed when the mouse is being moved over the item while being pressed.
        """
        if mouseEvent.modifiers() == Qt.ShiftModifier or self.creating:
            self.interactiveResize(mouseEvent.pos())
        elif mouseEvent.modifiers() == Qt.ControlModifier:
            return super().mouseMoveEvent(mouseEvent)

    def mouseReleaseEvent(self, mouseEvent):
        """
        Executed when the mouse is released from the item.
        """
        o = self.handleSize + self.handleSpace
        x1, y1, x2, y2 = self.originRect().getCoords()
        
        if x2-x1 == 1 and y2-y1 == 1 and self.creating:
            self.item_delete_signal.emit_signal(self)
        else:
            if x1 > x2:
                x1, x2 = x2, x1
            if y1 > y2:
                y1, y2 = y2, y1
            self.setRect(x1-o, y1-o, x2-x1+2*o, y2-y1+2*o)
            self.updateHandlesPos()
            self.handleSelected = None
            self.mousePressPos = None
            self.mousePressRect = None
            self.update()

        self.creating = False
        super().mouseReleaseEvent(mouseEvent)

    def originRect(self):
        """
        Returns the bounding rect of the shape (including the resize handles).
        """
        o = self.handleSize + self.handleSpace
        return self.rect().adjusted(o, o, -o, -o)

    def updateHandlesPos(self):
        """
        Update current resize handles according to the shape size and position.
        """
        s = self.handleSize
        b = self.rect()
        self.handles[self.handleTopLeft] = QRectF(b.left(), b.top(), s, s)
        self.handles[self.handleTopRight] = QRectF(b.right() - s, b.top(), s, s)
        self.handles[self.handleBottomLeft] = QRectF(b.left(), b.bottom() - s, s, s)
        self.handles[self.handleBottomRight] = QRectF(b.right() - s, b.bottom() - s, s, s)

    def interactiveResize(self, mousePos):
        """
        Perform shape interactive resize.
        """
        offset = self.handleSize + self.handleSpace
        boundingRect = self.rect()

        self.prepareGeometryChange()

        if self.handleSelected == self.handleTopLeft:

            fromX = self.mousePressRect.left()
            fromY = self.mousePressRect.top()
            toX = fromX + mousePos.x() - self.mousePressPos.x()
            toY = fromY + mousePos.y() - self.mousePressPos.y()
            boundingRect.setLeft(toX)
            boundingRect.setTop(toY)
            self.setRect(boundingRect)

        elif self.handleSelected == self.handleTopRight:

            fromX = self.mousePressRect.right()
            fromY = self.mousePressRect.top()
            toX = fromX + mousePos.x() - self.mousePressPos.x()
            toY = fromY + mousePos.y() - self.mousePressPos.y()
            boundingRect.setRight(toX)
            boundingRect.setTop(toY)
            self.setRect(boundingRect)

        elif self.handleSelected == self.handleBottomLeft:

            fromX = self.mousePressRect.left()
            fromY = self.mousePressRect.bottom()
            toX = fromX + mousePos.x() - self.mousePressPos.x()
            toY = fromY + mousePos.y() - self.mousePressPos.y()
            boundingRect.setLeft(toX)
            boundingRect.setBottom(toY)
            self.setRect(boundingRect)

        elif self.handleSelected == self.handleBottomRight:

            fromX = self.mousePressRect.right()
            fromY = self.mousePressRect.bottom()
            toX = fromX + mousePos.x() - self.mousePressPos.x()
            toY = fromY + mousePos.y() - self.mousePressPos.y()
            boundingRect.setRight(toX)
            boundingRect.setBottom(toY)
            self.setRect(boundingRect)

        else:
            fromL = self.mousePressRect.left()
            fromT = self.mousePressRect.top()
            fromR = self.mousePressRect.right()
            fromB = self.mousePressRect.bottom()
            toL = fromL + mousePos.x() - self.mousePressPos.x()
            toT = fromT + mousePos.y() - self.mousePressPos.y()
            toR = fromR + mousePos.x() - self.mousePressPos.x()
            toB = fromB + mousePos.y() - self.mousePressPos.y()
            boundingRect.setLeft(toL)
            boundingRect.setTop(toT)
            boundingRect.setRight(toR)
            boundingRect.setBottom(toB)
            self.setRect(boundingRect)

        if self.__class__.minSize is not None:
            if abs(boundingRect.width()) < self.__class__.minSize or \
               abs(boundingRect.height()) < self.__class__.minSize:
                self.switch_color('selected')
            else:
                self.switch_color('default')

        self.updateHandlesPos()
        self.item_changed_signal.emit_signal()

    def shape(self):
        """
        Returns the shape of this item as a QPainterPath in local coordinates.
        """
        path = QPainterPath()
        path.addRect(self.rect())
        return path

    def width(self):
        return self.originRect().width()

    def height(self):
        return self.originRect().height()

    def paint(self, painter, option, widget=None):
        """
        Paint the node in the graphic view.
        """
        painter.setBrush(QBrush(QColor(*self.color, 50)))
        painter.setPen(QPen(QColor(*self.color, 200), self.edge_width, style=Qt.SolidLine, cap=Qt.RoundCap, join=Qt.RoundJoin))
        painter.drawRect(self.originRect())

    def set_creating(self):
        if self.originRect().width() == 1 and self.originRect().height() == 1:
            self.creating = True
        else:
            self.creating = False

    def set_edge_width(self, zfactor):
        new_width = self.__class__.defaultEdgeWidth / (1.2**zfactor)
        self.edge_width = 1 if new_width < 1 else int(new_width)

    def switch_color(self, mode):
        if mode == 'default':
            self.color = self.defaultColor
        elif mode == 'selected':
            self.color = self.selectedColor
        self.update()

    @classmethod
    def set_min_size(cls, sz):
        cls.minSize = sz 
