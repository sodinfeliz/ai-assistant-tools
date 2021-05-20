import math
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from scipy.spatial.distance import cdist

from .circle import PosCircleItem


func_mode = {
    'select': 0,
    'crop': 1
}


class PhotoViewer(QGraphicsView):
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

    def fitInView(self, scale=True):
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
                self.scale(factor, factor)
            self._zoom = 0

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
            factor = 1.25
            self._zoom += 1
            if self._zoom > 0:
                self.scale(factor, factor)
            else:
                self._zoom = 0
                self.fitInView()

    def zoom_out(self):
        if self.hasPhoto():
            factor = 0.8
            self._zoom -= 1
            if self._zoom > 0:
                self.scale(factor, factor)
            else:
                self._zoom = 0 
                self.fitInView() 

    def wheelEvent(self, event):
        numDegrees = event.angleDelta() / 8
        numSteps = (numDegrees / 15).y()
        
        if self.hasPhoto() and event.modifiers() == Qt.ControlModifier:
            if numSteps > 0:
                self.zoom_in()
            elif numSteps < 0:
                self.zoom_out()


class PalmPositionCanvas(PhotoViewer):

    add_item_signal = pyqtSignal(QPointF)
    delete_item_signal = pyqtSignal()

    def __init__(self, parent, geometry: QRect):
        super(PalmPositionCanvas, self).__init__(parent)
        self.setStyleSheet("background-color: #EDF3FF; border-radius: 7px;")
        self.setGeometry(geometry)
        self._mode = func_mode['select']
        self._crop_win = []
        self._factor = 1.
        self._add_point = False
        self._palm_pos = np.empty((0,2), dtype=int)
        self._palm_pos_items = []

    def mousePressEvent(self, mouseEvent):     
        if self.get_mode() == func_mode['crop']:
            # Shift + Right: Remove the crop window.
            # Press + Left : Create new crop window.
            if mouseEvent.modifiers() == Qt.ShiftModifier and mouseEvent.buttons() == Qt.RightButton:
                mousePos = self.mapToScene(mouseEvent.pos())
                cindex = self._closeast_crop_win(mousePos)
                if cindex is not None:
                    self._scene.removeItem(self._crop_win[cindex])
                    del self._crop_win[cindex]
                    self.delete_item_signal.emit()
            elif mouseEvent.buttons() == Qt.LeftButton and mouseEvent.modifiers() == Qt.NoModifier:
                self.add_item_signal.emit(self.mapToScene(mouseEvent.pos()))
        
        super().mousePressEvent(mouseEvent)

    def mouseDoubleClickEvent(self, mouseEvent):
        if self.get_mode() == func_mode['select'] and self._add_point:    
            pos = self.mapToScene(mouseEvent.pos())
            pos = self._qpointf_to_list(pos)
            dist = cdist([pos], self._palm_pos)
            
            if len(self._palm_pos) and dist.min() <= 30 * self._factor:
                index = dist.argmin()
                self._palm_pos = np.delete(self._palm_pos, index, axis=0)
                self._scene.removeItem(self._palm_pos_items[index])
                del self._palm_pos_items[index]
            else:
                self._add_new_pos(pos)

    def add_item_to_scene(self, it):
        self._scene.addItem(it)
        return it

    def set_factor(self, factor):
        self._factor = factor

    def set_mode(self, mode):
        self._mode = mode
        if mode == func_mode['select']:
            self._add_point = True
        elif mode == func_mode['crop']:
            self._add_point = False

    def get_mode(self) -> int:
        """Return the mode value
        0: Select Mode
        1: Crop Mode
        """
        return self._mode

    ###############################
    #  Position Items related
    ###############################

    def clean_all_pos_items(self):
        for it in self._palm_pos_items:
            self._scene.removeItem(it)
        self._palm_pos = np.empty((0,2), dtype=int)
        self._palm_pos_items = []

    def palm_pos_data_loading(self, pos, mode='insert'):
        assert mode in ['insert', 'override']
        if mode == 'override':
            self.clean_all_pos_items()
            self._palm_pos = pos
            self._palm_pos = np.rint(self._palm_pos*self._factor).astype(int)
            for x, y in self._palm_pos:
                self._palm_pos_items.append(self.add_item_to_scene(PosCircleItem(x, y, 'red')))
        elif mode == 'insert':
            pos = np.rint(pos*self._factor).astype(int)
            self._palm_pos = np.vstack((self._palm_pos, pos))
            for x, y in pos:
                self._palm_pos_items.append(self.add_item_to_scene(PosCircleItem(x, y, 'red'))) 

        self._add_point = True

    def set_add_point(self, mode):
        self._add_point = mode

    def get_palm_pos_list(self):
        return np.rint(self._palm_pos/self._factor).astype(int)

    def _add_new_pos(self, pos):
        circle = PosCircleItem(*pos, 'red')
        self._palm_pos = np.vstack((self._palm_pos, pos))
        self._palm_pos_items.append(self.add_item_to_scene(circle))
        self.add_item_signal.emit(QPointF(*pos))

    ###############################
    #  Crop Windows related
    ###############################

    def add_crop_win_to_scene(self, it):
        self.add_item_to_scene(it)
        self._crop_win.append(it)

    def delete_crop_win_from_scene(self, it):
        self._scene.removeItem(it)

    def delete_all_crop_win(self):
        """ Removing all '_crop_win' objects from scene """
        for it in self._crop_win:
            self.delete_crop_win_from_scene(it)
        self._crop_win = []
        self.delete_item_signal.emit()

    def get_all_crop_win(self):
        windows = []
        for rects in self._crop_win:
            windows.append(list(map(int, rects.originRect().getCoords())))
        return np.array(windows)

    def _closeast_crop_win(self, pos: QPointF) -> int:
        """ Return the most close `crop_win` to `pos` """
        def dist_pts(a: QPointF, b: QPointF) -> float:
            return math.sqrt((a.x()-b.x())**2 + (a.y()-b.y())**2)

        cdist = np.inf # candidate distance
        cindex = None  # candidate index

        for idx, it in enumerate(self._crop_win):
            rect = it.originRect()
            if not rect.contains(pos): continue
            cx = rect.x() + rect.width() // 2
            cy = rect.y() + rect.height() // 2
            dist = dist_pts(pos, QPointF(cx, cy))
            if dist < cdist:
                cdist, cindex = dist, idx

        return cindex

    ###############################
    #  Others
    ###############################

    def _qpointf_to_list(self, pt: QPointF, dtype=float):
        if dtype is int:
            return [pt.x(), pt.y()]
        elif dtype is float:
            return [round(pt.x()), round(pt.y())]
        else:
            raise TypeError("Unsupported dtype.")
