import math
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from shapely.geometry.polygon import Polygon


class PolyItemHandle(QGraphicsPolygonItem):

    selectedColor = (196, 51, 51)

    def __init__(self, poly: Polygon, tfw: tuple, factor: float, color: tuple, handleSize: int=20):
        """ initialize the handle polygon item

        # Args:
            poly (shapely.Polygon): shapely polygon instance
            tfw (tuple): geographic information
            factor (float): resize factor
            color (tuple): polygon painting color
        """
        super().__init__()

        # handle
        self.handles = []
        self.handleSize = handleSize
        self.handleSpace = -1 * (handleSize // 2)
        self.handleSelected = None
        self.mousePressPos = None

        self.changable = False
        self.orn_color = color
        self.color = color
        self.orn_poly = poly
        self.gis_coords = list(poly.exterior.coords)
        
        self.qt_polygon = self._coords_setting(tfw, factor)
        self.setPolygon(self.qt_polygon)

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        #self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.updateHandlesPos()


    def _coords_setting(self, tfw, factor):
        """ Converting the geographic coordinates to
        the image coordinates then set the polygon items

        # Args:
            tfw (tuple): geographic information
            factor (int): resize factor
        """
        qt_polygon = QPolygonF()
        self.img_coords = []
        for px, py in self.gis_coords:
            px = int((px - tfw[0]) / tfw[1] * factor) 
            py = int((py - tfw[3]) / tfw[5] * factor)
            qt_polygon.append(QPointF(px, py))
            self.img_coords.append((px, py))
        return qt_polygon


    def handleAt(self, point):
        """
        Returns the resize handle below the given point.
        """
        index, candidate, min_dis = None, None, None
        for i, handle in enumerate(self.handles):
            if handle.contains(point):
                d = point - handle.center()
                l = math.sqrt(d.x()**2 + d.y()**2)
                if candidate is None or l < min_dis:
                    candidate = handle
                    index = i
                    min_dis = l

        if candidate is not None:
            return (index, candidate)
        return None
        

    def updateHandlesPos(self):
        s = self.handleSize
        o = self.handleSize + self.handleSpace
        self.handles = []
        for px, py in self.img_coords:
            self.handles.append(QRectF(px-o, py-o, s, s))


    def hoverMoveEvent(self, moveEvent):
        """
        Executed when the mouse moves over the shape (NOT PRESSED).
        """
        self.color = self.selectedColor
        super().hoverMoveEvent(moveEvent)


    def hoverLeaveEvent(self, moveEvent):
        """
        Executed when the mouse leaves the shape (NOT PRESSED).
        """
        self.color = self.orn_color
        super().hoverLeaveEvent(moveEvent)


    def mousePressEvent(self, mouseEvent):
        """ 
        Executed when the mouse is pressed on the item.
        """
        if mouseEvent.modifiers() == Qt.ShiftModifier:
            self.handleSelected = self.handleAt(mouseEvent.pos())
            self.mousePressPos = mouseEvent.pos()
        #super().mousePressEvent(mouseEvent)


    def mouseMoveEvent(self, mouseEvent):
        """
        Executed when the mouse is being moved over the item while being pressed.
        """
        if mouseEvent.modifiers() == Qt.ShiftModifier and self.changable:
            self.interactiveResize(mouseEvent.pos())
        self.setActive(False)


    def mouseReleaseEvent(self, mouseEvent):
        """
        Executed when the mouse is released from the item.
        """
        self.handleSelected = None
        self.mousePressPos = None
        self.update()
        super().mouseReleaseEvent(mouseEvent)


    def interactiveResize(self, mousePos):
        self.prepareGeometryChange()
        if self.handleSelected is not None:
            index, _ = self.handleSelected 
            fromX, fromY = self.img_coords[index]
            toX = fromX + mousePos.x() - self.mousePressPos.x()
            toY = fromY + mousePos.y() - self.mousePressPos.y()
            self.mousePressPos = mousePos
            self.img_coords[index] = [toX, toY]
            self.qt_polygon[index] = QPointF(toX, toY)
            self.setPolygon(self.qt_polygon)

        self.updateHandlesPos()


    def paint(self, painter, option, widget=None):
        """
        Paint the node in the graphic view.
        """
        # drawing the bounding box rect
        # (1, 254, 129)
        painter.setBrush(QBrush(QColor(*self.color, 120), style = Qt.SolidPattern))
        painter.setPen(QPen(QColor(*self.color), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawConvexPolygon(self.qt_polygon)

        # drawing the circle handles
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(*self.color, 255)))
        painter.setPen(QPen(QColor(*self.color, 255), 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        
        for index, handle in enumerate(self.handles):
            if self.handleSelected is None or index == self.handleSelected[0]:
                r = 1  # drawed circle radius
                cp = handle.center()
                painter.drawEllipse(QRectF(cp.x()-r, cp.y()-r, 2*r, 2*r))
