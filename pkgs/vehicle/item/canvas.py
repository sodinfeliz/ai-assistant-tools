import cv2
import numpy as np
import threading
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


    def setPhoto(self, back_im=None):
        self.back_im_path = back_im
        self.back_im = cv2.imread(back_im)
        pixmap = QPixmap(back_im)
        self._zoom = 0
        if pixmap and not pixmap.isNull():
            self._empty = False
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self._photo.setPixmap(pixmap)
            print(self._photo.pixmap().rect())
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


class LabelCanvas(PhotoViewer):

    add_item_signal = pyqtSignal(QPointF)
    delete_item_signal = pyqtSignal(QPointF)

    def __init__(self, parent, geometry: QRect):
        super(LabelCanvas, self).__init__(parent)
        assert isinstance(geometry, QRect), "Parameter geometry must be QRect type."
        self.setStyleSheet("background-color: #EDF3FF;  border-radius: 7px;")
        self.setGeometry(geometry)
        self.all_items = []
        self.in_items_range = False


    def mousePressEvent(self, mouseEvent):
        if mouseEvent.buttons() == Qt.RightButton and mouseEvent.modifiers() == Qt.ShiftModifier:
            self.delete_item_signal.emit(self.mapToScene(mouseEvent.pos()))
        elif not self.in_items_range and mouseEvent.buttons() == Qt.LeftButton and mouseEvent.modifiers() == Qt.NoModifier:
            self.add_item_signal.emit(self.mapToScene(mouseEvent.pos()))
        super().mousePressEvent(mouseEvent)

    
    def mouseMoveEvent(self, mouseEvent):
        for it in self.all_items:
            if it.rect().contains(self.mapToScene(mouseEvent.pos())):
                self.in_items_range = True
                break
            else:
                self.in_items_range = False
        super().mouseMoveEvent(mouseEvent)


    def add_item_to_scene(self, it):
        self.all_items.append(it)
        self._scene.addItem(it)
        self._scene.addItem(it.lback)
        self._scene.addItem(it.label)


    def delete_item_on_scene(self, it):
        index = self.all_items.index(it)
        del self.all_items[index]
        self._scene.removeItem(it)
        self._scene.removeItem(it.lback)
        self._scene.removeItem(it.label)


    def clear_items(self):
        for it in self.all_items:
            self._scene.removeItem(it)
            self._scene.removeItem(it.lback)
            self._scene.removeItem(it.label)
        self.all_items = []
        

#################################################
#################################################


class CropCanvas(PhotoViewer):
    def __init__(self, parent, geometry: QRect):
        super(CropCanvas, self).__init__(parent)
        assert isinstance(geometry, QRect), "Parameter geometry must be QRect type."
        self.setStyleSheet("background-color: #EDF3FF; border-radius: 7px;")
        self.setGeometry(geometry)
        self._grabbed = False
        self.crop_win = []


    def mousePressEvent(self, mouseEvent):
        if mouseEvent.modifiers() == Qt.ShiftModifier and mouseEvent.buttons() == Qt.RightButton:
            mousePos = self.mapToScene(mouseEvent.pos())
            for idx, it in enumerate(self.crop_win):
                if it.current_rect.contains(mousePos):
                    self._scene.removeItem(it)
                    del self.crop_win[idx]
                    self.focusBackImage()
                    break
        super().mousePressEvent(mouseEvent)


    def mouseReleaseEvent(self, mouseEvent):
        if self.grabbed:
            self.focusBackImage()
            self.grabbed = False
        super().mouseReleaseEvent(mouseEvent)


    def mouseMoveEvent(self, mouseEvent):
        self.grabbed = True if self._scene.mouseGrabberItem() else False
        if mouseEvent.modifiers() == Qt.ControlModifier or self._scene.mouseGrabberItem():
            super().mouseMoveEvent(mouseEvent)


    def add_item_to_scene(self, it):
        self.crop_win.append(it)
        self._scene.addItem(it)
        self.focusBackImage()


    def clear_all_items(self):
        for it in self.crop_win:
            self._scene.removeItem(it)
        self.crop_win = []


    def all_crop_bboxes(self):
        bboxes = []
        for it in self.crop_win:
            x, y, w, h = list(map(int, it.current_rect.getRect()))
            bboxes.append([x, y, x + w, y + h])
        return bboxes


    def focusBackImage(self):
        height, width, channel = self.back_im.shape

        crop_region = np.zeros((self.back_im.shape[0], self.back_im.shape[1]), dtype='uint8')
        for it in self.crop_win:
            xmin, ymin, w, h = list(map(int, it.current_rect.getRect()))
            crop_region[max(0, ymin): ymin + h, max(0, xmin): xmin + w] = 1

        mask = self.back_im.copy()
        for ch in range(channel):
            mask[..., ch] *= crop_region

        mRatio = 0.65
        dst = cv2.addWeighted(self.back_im, 1 - mRatio, mask, mRatio, 0)
        qDst = QImage(dst, width, height, QImage.Format_RGB888)
        self._photo.setPixmap(QPixmap.fromImage(qDst))

