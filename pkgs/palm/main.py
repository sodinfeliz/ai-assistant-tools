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
from .item import PalmPositionCanvas, RectItemHandle, DatasetProducing
from .style.stylesheet import connect_to_stylesheet

palm_radius = 20
pixel_size = 0.107541
size_limitation = 20000.
func_mode = {'select': 0, 'crop': 1}


class palmGUI(QWidget):
    def __init__(self, parent=None):
        super(palmGUI, self).__init__(parent)
        loadUi('GUI/widget_palm.ui', self)

        # canvas initialization
        vc_geometry = self.view_canvas.geometry()
        self.view_canvas = PalmPositionCanvas(self, vc_geometry)
        self.view_canvas.setViewportUpdateMode(0)
        
        # push buttons setting
        self.pb_openfile.clicked.connect(self.file_open)
        self.pb_loadcsv.clicked.connect(self.load_position)
        self.pb_save_csv.clicked.connect(self.save_position)
        self.pb_save_dataset.clicked.connect(self.dataset_producing)
        self.pb_clear_crop.clicked.connect(self.view_canvas.delete_all_crop_win)
        self.pb_select_mode.clicked.connect(lambda: self.mode_switch('select'))
        self.pb_crop_mode.clicked.connect(lambda: self.mode_switch('crop'))
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
        self.view_canvas.add_item_signal.connect(self.add_signal_handler)

        self.pb_save_dataset.setEnabled(False)
        self.pb_loadcsv.setEnabled(True)
        self.pb_save_csv.setEnabled(False)
        self.le_crop_size.setEnabled(False)
        self.le_overlap_ratio.setEnabled(False)
        self.info_display.setText('Image Loaded.')

    
    def mode_switch(self, mode):
        """ Mode switching and changing
         the functional push buttons' stylesheet 

        # Args:
            mode (str): must be either 'select' or 'crop'
        """
        assert mode in func_mode, f"Undefined mode: {mode}."
        ssdir = 'GUI/stylesheet/palm' # stylesheet directory
        if self.view_canvas._mode != func_mode[mode]:
            if mode == 'select':
                self.pb_select_mode.setStyleSheet(connect_to_stylesheet('button_selected', ssdir))
                self.pb_crop_mode.setStyleSheet(connect_to_stylesheet('button_unselected', ssdir))
            else:
                self.pb_select_mode.setStyleSheet(connect_to_stylesheet('button_unselected', ssdir))
                self.pb_crop_mode.setStyleSheet(connect_to_stylesheet('button_selected', ssdir))
            self.view_canvas.set_mode(func_mode[mode])


    def add_signal_handler(self, mousePos):
        if self.view_canvas._mode == func_mode['select']:
            self.info_display.setText("")
        elif self.view_canvas._mode == func_mode['crop']:
            x, y = mousePos.x(), mousePos.y()
            item = RectItemHandle(x, y, 1, 1, handleSize=100)
            self.view_canvas.add_crop_win_to_scene(item)
            item.item_delete_signal.signal.connect(self.delete_crop_win_by_signal)


    ###########################
    ##  Select Mode Related  ##
    ###########################

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


    #########################
    ##  Crop Mode Related  ##
    #########################

    def delete_crop_win_by_signal(self, it):
        if self.view_canvas._mode == func_mode['crop']:
            del self.view_canvas._crop_win[-1]
            self.view_canvas.delete_crop_win_from_scene(it)


    #######################
    ##  Dataset Related  ##
    #######################

    def dataset_producing(self):
        """
        Producing the Pascal VOC dataset     
        """
        size = self.check_split_size()
        ratio = self.check_overlap_ratio()
        if size is None or ratio is None: return

        self.prob_map_produced()
        ds = DatasetProducing(self.org_im, self.lb)
        ds.split(size, ratio)
        ds.save(filename=self._filename, save_dir=self._im_dir)
        self.info_display.setText("Dataset Completed !")


    def prob_map_produced(self):
        """
        Probability map producing
        """
        self.lb = np.zeros(self.org_im.shape[:2], dtype='uint8')
        for pos in self.view_canvas._palm_pos:
            x, y = np.rint(pos / self._factor).astype('int')
            cv2.circle(self.lb, (x, y), palm_radius, (1,), -1, cv2.LINE_AA)


    def check_split_size(self):
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

    
    def check_overlap_ratio(self):
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
