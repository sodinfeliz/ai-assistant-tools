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

    def __init__(self, x, y, width, height, handleSize=10):
        """
        Initialize the shape.
        """
        super().__init__(x, y, width, height)
        
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

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.updateHandlesPos()


    def handleAt(self, point):
        """
        Returns the resize handle below the given point.
        """
        for k, v, in self.handles.items():
            if v.contains(point):
                return k
        return None


    def hoverEnterEvent(self, moveEvent):
        super().hoverEnterEvent(moveEvent)


    def hoverMoveEvent(self, moveEvent):
        """
        Executed when the mouse moves over the shape (NOT PRESSED).
        """
        if self.isSelected():
            handle = self.handleAt(moveEvent.pos())
            cursor = Qt.ArrowCursor if handle is None else self.handleCursors[handle]
            self.setCursor(cursor)
        super().hoverMoveEvent(moveEvent)


    def hoverLeaveEvent(self, moveEvent):
        """
        Executed when the mouse leaves the shape (NOT PRESSED).
        """
        self.setCursor(Qt.ArrowCursor)
        super().hoverLeaveEvent(moveEvent)


    def mousePressEvent(self, mouseEvent):
        """
        Executed when the mouse is pressed on the item.
        """
        self.is_creating()
        if mouseEvent.modifiers() == Qt.ShiftModifier or self.creating:
            self.handleSelected = self.handleAt(mouseEvent.pos())
            self.mousePressPos = mouseEvent.pos()
            self.mousePressRect = self.rect()
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
            self.creating = False
            self.update()
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

        self.updateHandlesPos()
        self.item_changed_signal.emit_signal()


    def shape(self):
        """
        Returns the shape of this item as a QPainterPath in local coordinates.
        """
        path = QPainterPath()
        path.addRect(self.rect())
        return path


    def paint(self, painter, option, widget=None):
        """
        Paint the node in the graphic view.
        """
        # drawing the bounding box rect
        # (1, 254, 129)
        eSize = self.handleSize // 4

        painter.setBrush(QBrush(QColor(15, 71, 180, 50)))
        painter.setPen(QPen(QColor(15, 71, 180, 200), eSize, style=Qt.SolidLine, cap=Qt.RoundCap, join=Qt.RoundJoin))
        painter.drawRect(self.originRect())

        # drawing the circle handles
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(255, 255, 255, 0)))
        painter.setPen(QPen(QColor(255, 255, 255, 0), eSize, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        for handle, rect in self.handles.items():
            if self.handleSelected is None or handle == self.handleSelected:
                o = self.handleSize / 2 - 2  # adjusting the visual size to 2px
                painter.drawEllipse(rect.adjusted(o, o, -o, -o))


    def is_creating(self):
        if self.originRect().width() == 1 and self.originRect().height() == 1:
            self.creating = True

