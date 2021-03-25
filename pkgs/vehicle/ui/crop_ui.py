import os
os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] = pow(2, 40).__str__()

import numpy as np
import threading
from glob import glob
from pathlib import Path
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi

from ..dialog.error import warning_msg
from ..ODCrop import ODCropData
from ..item import RectItem, CropCanvas


angles = {
    0: [0],
    1: [0, 90],
    2: [0, 60, -60],
    3: [0, 45, 90, -45]
}


class cropUI(QWidget):    
    def __init__(self, parent=None):
        super(cropUI, self).__init__(parent)
        loadUi('GUI/widget_crop.ui', self)

        self._back_im_path = ''
        self._data_path = ''
        self._filename = ''
        self._crop_width = None
        self._crop_height = None

        geometry = self.canvas.geometry()
        self.canvas = CropCanvas(self, geometry)
        self.canvas.setViewportUpdateMode(0)
        self.canvas.clear_all_items()

        self.lineEdit_info.setReadOnly(True)
        self.lineEdit_width.setPlaceholderText('width')
        self.lineEdit_height.setPlaceholderText('height')
        self.lineEdit_info.setText('Wait For Extracting !')

        self.pb_openfile.clicked.connect(self.file_open)
        self.pb_save.clicked.connect(self.dataset_producing)
        self.pb_repeat.clicked.connect(self.load_im_to_scene)
        self.pb_save.setEnabled(False)

        self.cb_angle.addItem('1 Angle: 0')
        self.cb_angle.addItem('2 Angles: 0, 90')
        self.cb_angle.addItem('3 Angles: 0, 60, 120')
        self.cb_angle.addItem('4 Angles: 0, 45, 90, 135')
        self.cb_angle.setEnabled(False)


    def file_open(self):
        """
        Open the file manager to open the directory
        """
        self._data_path = Path(QFileDialog.getExistingDirectory(self, 'Open File'))
        self._filename = self._data_path.stem
        
        dir_check = ['images', 'bnboxes']
        if self._data_path and np.setdiff1d(dir_check, os.listdir(self._data_path)).size == 0:
            self._im_path = self._data_path.joinpath('images')
            self._back_im_path = str(sorted(self._im_path.glob('*.png'))[0])
            self.load_im_to_scene()
        else:
            warning_msg('Invalid directory !')


    def load_im_to_scene(self):
        if self._back_im_path:
            self.canvas.setPhoto(self._back_im_path)
            self.canvas.clear_all_items()
            self.pb_save.setEnabled(False)
            self.cb_angle.setEnabled(False)
            self.cb_angle.setCurrentIndex(0)
            self.lineEdit_info.setText(
                f'File: {self._filename}  Size: ({self.canvas.back_im.shape[1]}, {self.canvas.back_im.shape[0]})'
            )


    def dataset_producing(self):
        # retrieving all the crop bounding boxes in the current scene
        crop_boxes = self.canvas.all_crop_bboxes()

        for (xmin, ymin, xmax, ymax) in crop_boxes:
            if xmin < 0 or ymin < 0 or \
               xmax >= self.canvas.back_im.shape[1] or \
               ymax >= self.canvas.back_im.shape[0]:
                warning_msg('Bounding Box exceeds the image border.')
                return    

        progress_thread = threading.Thread(target=self.extract_process)
        progress_thread.start()


    def extract_process(self):
        self.pb_save.setEnabled(False)
        self.cb_angle.setEnabled(False)
        self.lineEdit_width.setEnabled(False)
        self.lineEdit_height.setEnabled(False)

        data = ODCropData(
            self._data_path,
            bboxes=self.canvas.all_crop_bboxes(),
            angles=angles[self.cb_angle.currentIndex()]
        )

        self.lineEdit_info.setText('')
        self.progressBar_extract.setTextVisible(True)
        paths = glob(str(data.im_path.joinpath('*.png')))
        for i, path in enumerate(paths):
            data.extract(path)
            self.progressBar_extract.setValue(int(round((i+1)/len(paths)*100)))
        data.split()
        self.progressBar_extract.setValue(0)
        self.progressBar_extract.setTextVisible(False)
        self.lineEdit_info.setText('Completed !')

        self.pb_save.setEnabled(True)
        self.cb_angle.setEnabled(True)
        self.lineEdit_width.setEnabled(True)
        self.lineEdit_height.setEnabled(True)


    def mouseDoubleClickEvent(self, event):
        add_rect = self._check_width_height()
        if add_rect and event.buttons() == Qt.LeftButton and self._data_path: 
            widget_x, widget_y = self.canvas.pos().x(), self.canvas.pos().y()
            pos = self.canvas.mapToScene(event.x() - widget_x, event.y() - widget_y)

            x, y = round(pos.x()) - self._crop_width/2, round(pos.y()) - self._crop_height/2
            self.canvas.add_item_to_scene(RectItem(x, y, self._crop_width, self._crop_height))
            self.pb_save.setEnabled(True)

            if self._crop_width == self._crop_height:
                self.cb_angle.setEnabled(True)
            else:
                self.cb_angle.setCurrentIndex(0)  # only 1-anlge when all squares
                self.cb_angle.setEnabled(False)


    def _check_width_height(self):
        if not self.lineEdit_width.text().isdigit() or not self.lineEdit_height.text().isdigit():
            warning_msg("Invalid format in \'Width\' or \'Height\' cell.")
            return False

        reasign = False
        if self._crop_width is None:
            reasign = True
        elif self._crop_width != int(self.lineEdit_width.text()) or \
             self._crop_height != int(self.lineEdit_height.text()):
            reasign = True
            self.canvas.clear_all_items()
        if reasign:
            self._crop_width = int(self.lineEdit_width.text())
            self._crop_height = int(self.lineEdit_height.text())

        return True
