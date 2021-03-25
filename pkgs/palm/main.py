import os
os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] = pow(2, 40).__str__()

import cv2
import numpy as np
import pandas as pd
from pathlib import Path
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi

from .dialog import warning_msg
from .utils.imutils import resize_image
from .item import PalmPositionCanvas, DatasetProducing

palm_radius = 20
pixel_size = 0.107541
size_limitation = 20000.


class palmGUI(QWidget):
    def __init__(self, parent=None):
        super(palmGUI, self).__init__(parent)
        loadUi('GUI/widget_palm.ui', self)

        # canvas initialization
        vc_geometry = self.view_canvas.geometry()
        self.view_canvas = PalmPositionCanvas(self, vc_geometry)
        
        # push buttons setting
        self.pb_openfile.clicked.connect(self.file_open)
        self.pb_loadcsv.clicked.connect(self.load_position)
        self.pb_save_csv.clicked.connect(self.save_position)
        self.pb_save_dataset.clicked.connect(self.dataset_producing)
        self.le_crop_size.setPlaceholderText('Crop Size')
        self.le_overlap_ratio.setPlaceholderText('Overlap Ratio')


    def file_open(self):
        self._im_path, _ = QFileDialog.getOpenFileName(self,
            caption='Open File', 
            directory='./data/palm',
            filter="Images (*.tif *.png *.jpg)")
    
        if not self._im_path: return  # cancel button pressed

        self._im_path = Path(self._im_path)
        self._im_dir = self._im_path.parent
        self._filename = self._im_dir.stem
        self.canvas_initial(self._im_path)


    def canvas_initial(self, im_path):
        self.org_im, self.im, self._factor, self._tfw = resize_image(im_path, pixel_size)

        self.view_canvas.setPhoto(self.im[..., ::-1].copy())
        self.view_canvas.set_factor(self._factor)
        self.view_canvas.set_add_point_mode(False)
        self.view_canvas.clean_all_pos_items()

        self.pb_save_dataset.setEnabled(False)
        self.pb_loadcsv.setEnabled(True)
        self.pb_save_csv.setEnabled(False)
        self.le_crop_size.setEnabled(False)
        self.le_overlap_ratio.setEnabled(False)
        self.info_display.setText('Image Loaded.')


    def load_position(self):
        pos_path, _ = QFileDialog.getOpenFileName(self,
            caption='Open File',
            filter="Excel (*.csv)")
        
        if not pos_path: return  # cancel button pressed

        self.view_canvas.initial_palm_pos(pos_path)
        self.pb_save_csv.setEnabled(True)
        self.info_display.setText('')


    def save_position(self):
        im_pos = np.rint(self.view_canvas._palm_pos/self._factor).astype('int')
        df = pd.DataFrame(im_pos)
        df.to_csv(os.path.join(self._im_dir, 'palm_img_pos.csv'), header=None, index=None)

        # Geographic position saving
        if self._tfw[:2] != (0, 1):
            im_pos = im_pos.astype('float')
            im_pos[:, 0] = self._tfw[0] + im_pos[:, 0] * pixel_size
            im_pos[:, 1] = self._tfw[3] - im_pos[:, 1] * pixel_size
            df = pd.DataFrame(im_pos)
            df.to_csv(os.path.join(self._im_dir, 'palm_gis_pos.csv'), header=None, index=None)

        self.info_display.setText("Save Done !")
        self.pb_save_dataset.setEnabled(True)
        self.le_crop_size.setEnabled(True)
        self.le_overlap_ratio.setEnabled(True)


    def dataset_producing(self):
        """
        Producing the Pascal VOC dataset     
        """
        size = self._check_split_size()
        ratio = self._check_overlap_ratio()
        if size is None or ratio is None: return

        self._prob_map_produced()
        ds = DatasetProducing(self.org_im, self.lb)
        ds.split(size, ratio)
        ds.save(filename=self._filename, save_dir=self._im_dir)
        self.info_display.setText("Dataset Completed !")


    def _prob_map_produced(self):
        """
        Probability map producing
        """
        self.lb = np.zeros(self.org_im.shape[:2], dtype='uint8')
        for pos in self.view_canvas._palm_pos:
            x, y = np.rint(pos / self._factor).astype('int')
            cv2.circle(self.lb, (x, y), palm_radius, (1,), -1, cv2.LINE_AA)


    def _check_split_size(self):
        """
        Checking the size format
        """
        crop_size = None
        try:
            crop_size = int(self.le_crop_size.text())
        except ValueError:
            if not self.le_crop_size.text():
                warning_msg('Crop size cell is empty.')
            else:
                warning_msg("Crop size must be integer.")
        return crop_size

    
    def _check_overlap_ratio(self):
        """
        Checking the overlap ratio format
        """
        ratio = None
        try:
            ratio = float(self.le_overlap_ratio.text())
            if not 0 <= ratio < 1:
                warning_msg("Overlap Ratio must in range [0,1).")
                ratio = None
        except ValueError:
            if not self.le_overlap_ratio.text():
                warning_msg('Overlap ratio cell is empty.')
            else:
                warning_msg("Overlap ratio must be float type.")
        return ratio