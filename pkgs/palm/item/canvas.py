import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


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
                #viewrect = self.viewport().rect()
                viewrect = self.geometry()
                viewrect.setRect(0, 0, viewrect.width(), viewrect.height())
                scenerect = self.transform().mapRect(rect)
                factor = max(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                self.scale(factor, factor)
            self._zoom = 0


    def setPhoto(self, back_im: np.ndarray=None):
        if back_im is None:
            pixmap = QPixmap(back_im)
        else:
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

#################################################
#################################################
from pandas import read_csv
from scipy.spatial.distance import cdist
from .circle import PosCircleItem


class PalmPositionCanvas(PhotoViewer):

    add_item_signal = pyqtSignal()

    def __init__(self, parent, geometry: QRect):
        super(PalmPositionCanvas, self).__init__(parent)
        self.setStyleSheet("background-color: #EDF3FF; border-radius: 7px;")
        self.setGeometry(geometry)
        self._factor = 1.
        self._add_point = False
        self._palm_pos = []
        self._palm_pos_items = []


    def mouseDoubleClickEvent(self, event):
        if self._add_point:    
            pos = self.mapToScene(event.pos().x(), event.pos().y())
            pos = [round(pos.x()), round(pos.y())]

            if len(self._palm_pos) == 0:
                self._palm_pos = np.vstack((self._palm_pos, pos))
                self._palm_pos_items.append(self.add_item_to_scene(PosCircleItem(pos[0], pos[1], 'red')))
                self.add_item_signal.emit()
            else:
                if cdist([pos], self._palm_pos).min() <= round(30*self._factor):
                    index = cdist([pos], self._palm_pos).argmin()
                    self._palm_pos = np.delete(self._palm_pos, index, axis=0)
                    self._scene.removeItem(self._palm_pos_items[index].item)
                    del self._palm_pos_items[index]
                else:
                    self._palm_pos = np.vstack((self._palm_pos, pos))
                    self._palm_pos_items.append(self.add_item_to_scene(PosCircleItem(pos[0], pos[1], 'red')))
                    self.add_item_signal.emit()


    def add_item_to_scene(self, it):
        self._scene.addItem(it.item)
        return it


    def clean_all_pos_items(self):
        for it in self._palm_pos_items:
            self._scene.removeItem(it.item)
        self._palm_pos_items = []


    def initial_palm_pos(self, path):
        try:
            self._palm_pos = np.array(read_csv(path))
        except:
            self._palm_pos = np.empty([0, 2], dtype='int')

        self._palm_pos = np.rint(self._palm_pos*self._factor).astype(self._palm_pos.dtype)
        self._add_point = True

        for x, y in self._palm_pos:
            self._palm_pos_items.append(self.add_item_to_scene(PosCircleItem(x, y, 'red')))


    def set_factor(self, factor):
        self._factor = factor


    def set_add_point_mode(self, switch):
        self._add_point = switch

