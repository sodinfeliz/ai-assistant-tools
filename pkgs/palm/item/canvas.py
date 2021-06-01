import math
from typing import cast
import numpy as np
from decouple import config
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from scipy.spatial.distance import cdist

from .circle import PosCircleItem
from .rect_handle import RectItemHandle
from ..utils.qtutils import dist_pts, qpointf_to_list


func_mode = {
    'select': 0,
    'crop': 1
}


class PhotoViewer(QGraphicsView):

    zoom_factor = 1.25
    zoom_signal = pyqtSignal()

    def __init__(self, parent=None):
        super(PhotoViewer, self).__init__(parent)
        self._zoom = 0
        self._empty = True
        self._grabbed = False
        self._scene = QGraphicsScene(self)
        self._photo = QGraphicsPixmapItem()
        self._scene.addItem(self._photo)
        
        self.setScene(self._scene)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)

    def hasPhoto(self):
        return not self._empty

    def fitInView(self):
        rect = QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasPhoto():
                unity = self.transform().mapRect(QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.geometry()
                viewrect.setRect(0, 0, viewrect.width(), viewrect.height())
                scenerect = self.transform().mapRect(rect)
                factor = max(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                factor *= self.__class__.zoom_factor**self._zoom
                self.scale(factor, factor)

    def setPhoto(self, back_im: np.ndarray=None):
        height, width, chnum = back_im.shape
        bytesPerLine = width * chnum
        imgFormat = QImage.Format_ARGB32 if chnum == 4 else QImage.Format_RGB888
        qImg = QImage(back_im.data, width, height, bytesPerLine, imgFormat)
        pixmap = QPixmap(qImg)

        self._zoom = 0
        if pixmap and not pixmap.isNull():
            self._empty = False
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self._photo.setPixmap(pixmap)
        else:
            self._empty = True
            self.setDragMode(QGraphicsView.NoDrag)
            self._photo.setPixmap(QPixmap())
        self.fitInView()

    def zoom_in(self):
        if self.hasPhoto():
            factor = self.__class__.zoom_factor
            self._zoom += 1
            self.scale(factor, factor)

    def zoom_out(self):
        if self.hasPhoto():
            factor = 1 / self.__class__.zoom_factor
            self._zoom -= 1
            if self._zoom > 0:
                self.scale(factor, factor)
            else:
                self._zoom = 0 
                self.fitInView()

    def get_zoom_factor(self):
        return self._zoom

    def wheelEvent(self, event):
        numDegrees = event.angleDelta() / 8
        numSteps = (numDegrees / 15).y()
        
        if self.hasPhoto():
            if numSteps > 0:
                self.zoom_in()
                self.zoom_signal.emit()
            elif numSteps < 0 and self._zoom != 0:
                self.zoom_out()
                self.zoom_signal.emit()
            

class PalmPositionCanvas(PhotoViewer):

    add_win_signal = pyqtSignal(QPointF)
    add_pos_signal = pyqtSignal()

    def __init__(self, parent, geometry: QRect):
        super(PalmPositionCanvas, self).__init__(parent)
        self.setStyleSheet("background-color: #EDF3FF; border-radius: 7px; border: None;")
        self.setGeometry(geometry)

        self.pos_group = self._scene.createItemGroup(list())
        self.win_group = self._scene.createItemGroup(list())

        self._mode = func_mode['select']
        self._factor = 1.
        self._pixel_size = 1.
        self._add_point = False

    def mousePressEvent(self, mouseEvent: QMouseEvent):
        # view_rect = self.geometry()
        # lt_pt = self.mapToScene(0, 0)
        # print(f'Left Top: {lt_pt.x()}')
        # print(f'Right Bottom: {self.mapToScene(view_rect.width(), view_rect.height())}')

        if self.get_mode() == func_mode['crop']:
            # Shift + Right: Remove the crop window.
            # Press + Left : Create new crop window.
            mouse_pos = self.mapToScene(mouseEvent.pos())
            if mouseEvent.modifiers() == Qt.ShiftModifier and mouseEvent.buttons() == Qt.RightButton:
                self._delete_closeast_crop_win(mouse_pos)
            elif mouseEvent.buttons() == Qt.LeftButton and mouseEvent.modifiers() == Qt.NoModifier:
                self.add_win_signal.emit(mouse_pos)
        
        super().mousePressEvent(mouseEvent)

    def mouseDoubleClickEvent(self, mouseEvent: QMouseEvent):
        if self.get_mode() == func_mode['select'] and self._add_point:    
            self._add_remove_pos_in_canvas(mouseEvent.pos())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self.mouse_pos = event.pos() # tracking for key press event
        return super().mouseMoveEvent(event)

    def keyPressEvent(self, keyEvent: QKeyEvent) -> None:
        if self.get_mode() == func_mode['select'] and \
           self._add_point and keyEvent.key() == Qt.Key_Space:
            self._add_remove_pos_in_canvas(self.mouse_pos)

    def add_item_to_scene(self, it: QGraphicsItem):
        self._scene.addItem(it)

    def remove_item_from_scene(self, it: QGraphicsItem):
        self._scene.removeItem(it)

    def set_factor(self, factor: float):
        self._factor = factor

    def set_pixel_size(self, pixel_size: float):
        self._pixel_size = pixel_size

    def set_mode(self, mode: str):
        self._mode = mode
        if mode == func_mode['select']:
            self._add_point = True
            PosCircleItem.set_changeable(True)
        elif mode == func_mode['crop']:
            self._add_point = False
            PosCircleItem.set_changeable(False)

    def get_mode(self) -> int:
        """Return the mode value
        0: Select Mode
        1: Crop Mode
        """
        return self._mode

    ###############################
    #  Position Items related
    ###############################

    def clean_pos_items(self):
        self._scene.removeItem(self.pos_group)
        self.pos_group = self._scene.createItemGroup(list())

    def palm_pos_data_loading(self, positions: np.ndarray, mode: str='insert'):
        assert mode in ['insert', 'override']
        if mode == 'override': self.clean_pos_items()

        for pos in positions:
            x, y = (pos*self._factor).astype(int)
            self.pos_group.addToGroup(PosCircleItem(QPoint(x, y)))

        self._add_point = True

    def set_add_point(self, mode: bool):
        self._add_point = mode

    def get_palm_pos_data(self) -> np.ndarray:
        return np.array([qpointf_to_list(it.rect().center()) for it in self.pos_group.childItems()])

    def get_palm_radius_data(self) -> np.ndarray:
        return np.array([it.radius for it in self.pos_group.childItems()])

    def _add_remove_pos_in_canvas(self, mouse_pos: QPoint):
        pos = self.mapToScene(mouse_pos)
        self.add_pos_signal.emit()

        dc, ic = np.Inf, None
        for it in self.pos_group.childItems():
            dist = dist_pts(it.rect().center(), pos)
            if dist < dc: dc, ic = dist, it
        
        if dc <= config('CLOSE_DIST_IN_CANVAS', cast=float) / self._pixel_size * self._factor:
            self._scene.removeItem(ic)
        else:
            circle = PosCircleItem(pos)
            self.pos_group.addToGroup(circle)
            
    @property
    def no_pts(self) -> bool:
        return len(self.pos_group.childItems()) == 0

    ###############################
    #  Crop Windows related
    ###############################

    def add_crop_win_to_scene(self, it: RectItemHandle):
        it.item_delete_signal.signal.connect(self.remove_item_from_scene)
        self.win_group.addToGroup(it)

    def clean_win_items(self):
        """ Removing all 'RectItemHandle' objects from scene """
        self._scene.removeItem(self.win_group)
        self.win_group = self._scene.createItemGroup(list())

    def get_all_crop_win(self) -> np.ndarray:
        """ Return all `crop_win` coordinates. """
        windows = []
        for rects in self.win_group.childItems():
            windows.append(list(map(int, rects.originRect().getCoords())))
        return np.array(windows)

    def _delete_closeast_crop_win(self, pos: QPointF):
        """ Return the most close `crop_win` to `pos` """
        cdist = np.inf # candidate distance
        citem = None  # candidate index

        for it in self.win_group.childItems():
            rect = it.originRect()
            if not rect.contains(pos): continue
            cx = rect.x() + rect.width() // 2
            cy = rect.y() + rect.height() // 2
            dist = dist_pts(pos, QPointF(cx, cy))
            if dist < cdist:
                cdist, citem = dist, it

        if citem is not None: self._scene.removeItem(citem)
