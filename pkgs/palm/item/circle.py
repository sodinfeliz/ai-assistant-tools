import math
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from typing import Tuple

from ..utils.qtutils import dist_pts


class PosCircleItem(QGraphicsEllipseItem):
    
    defaultCircleSize = 25
    defaultCircleColor = [255, 0, 0]

    changeable = True

    def __init__(self, pos: QPoint):
        assert isinstance(pos, (QPointF, QPoint))
        super(PosCircleItem, self).__init__(
            pos.x() - self.__class__.defaultCircleSize//2,
            pos.y() - self.__class__.defaultCircleSize//2,
            self.__class__.defaultCircleSize,
            self.__class__.defaultCircleSize
        )
        self.dragging = False
        self.scaling = False

    def mousePressEvent(self, mouseEvent: 'QGraphicsSceneMouseEvent') -> None:
        self.mouse_from = mouseEvent.pos()
        if mouseEvent.modifiers() == Qt.ShiftModifier and mouseEvent.buttons() == Qt.LeftButton:
            self.dragging = True
        elif mouseEvent.modifiers() == Qt.ControlModifier and mouseEvent.buttons() == Qt.LeftButton:
            self.init_center = self.rect().center()
            self.init_radius = self.radius
            self.scaling = True
        else:
            return super().mousePressEvent(mouseEvent)

    def mouseMoveEvent(self, mouseEvent: 'QGraphicsSceneMouseEvent') -> None:
        if self.dragging:
            shift = mouseEvent.pos() - self.mouse_from
            self.moveBy(shift.x(), shift.y())
        elif self.scaling:
            start_dist = dist_pts(self.init_center, self.mouse_from)
            finish_dist = dist_pts(self.init_center, mouseEvent.pos())
            shift = finish_dist - start_dist
            self.setRect(
                self.init_center.x() - (self.init_radius + shift),
                self.init_center.y() - (self.init_radius + shift),
                2 * abs(int(self.init_radius + shift)),
                2 * abs(int(self.init_radius + shift))
            )
        else:
            return super().mouseMoveEvent(mouseEvent)

    def mouseReleaseEvent(self, mouseEvent: 'QGraphicsSceneMouseEvent') -> None:
        self.dragging = False
        self.scaling = False
        return super().mouseReleaseEvent(mouseEvent)

    def sceneEvent(self, event: QEvent) -> bool:
        if not self.__class__.changeable: return True
        if event.type() == QEvent.GraphicsSceneMousePress:
            self.mousePressEvent(event)
        elif event.type() == QEvent.GraphicsSceneMouseMove:
            self.mouseMoveEvent(event)
        elif event.type() == QEvent.GraphicsSceneMouseRelease:
            self.mouseReleaseEvent(event)
        return True
    
    def paint(self, painter: QPainter, option, widget=None):
        painter.setBrush(QBrush(QColor(*self.defaultCircleColor, 45), style = Qt.SolidPattern))
        painter.setPen(QPen(QColor(*self.defaultCircleColor, 200), 3, style=Qt.SolidLine))
        painter.drawEllipse(self.rect())

    @classmethod
    def set_changeable(cls, mode: bool):
        cls.changeable = mode

    @property
    def radius(self) -> int:
        return int(self.rect().width() // 2)
