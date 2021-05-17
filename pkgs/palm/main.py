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
from scipy import spatial

from .dialog import warning_msg, critical_msg
from .utils.imutils import resize_image
from .item import PalmPositionCanvas, RectItemHandle, DatasetProducing
from .style.stylesheet import connect_to_stylesheet

palm_radius = 1.5 # unit: meter
#pixel_size = 0.107541
pixel_size = 0.05
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
        self.pb_clear_crop.clicked.connect(self.clean_canvas_by_click)
        self.pb_select_mode.clicked.connect(lambda: self.mode_switch('select'))
        self.pb_crop_mode.clicked.connect(lambda: self.mode_switch('crop'))
        self.le_crop_size.setPlaceholderText('Crop Size')
        self.le_overlap_ratio.setPlaceholderText('Overlap Ratio')

        self.le_crop_size.editingFinished.connect(self.crop_and_split_size_check)


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
        self.org_im, self.org_im_shape, self.im, self._factor, self._tfw = resize_image(im_path, pixel_size)

        self.view_canvas.setPhoto(self.im[..., ::-1].copy())
        self.view_canvas.set_factor(self._factor)
        self.view_canvas.set_add_point_mode(False)
        self.view_canvas.clean_all_pos_items()
        self.view_canvas.delete_all_crop_win()
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
        if self.view_canvas.get_mode() != func_mode[mode]:
            if mode == 'select':
                self.pb_select_mode.setStyleSheet(connect_to_stylesheet('button_selected', ssdir))
                self.pb_crop_mode.setStyleSheet(connect_to_stylesheet('button_unselected', ssdir))
            else:
                self.pb_select_mode.setStyleSheet(connect_to_stylesheet('button_unselected', ssdir))
                self.pb_crop_mode.setStyleSheet(connect_to_stylesheet('button_selected', ssdir))
            self.view_canvas.set_mode(func_mode[mode])


    def add_signal_handler(self, mousePos):
        if self.view_canvas.get_mode() == func_mode['select']:
            self.info_display.setText("")
        elif self.view_canvas.get_mode() == func_mode['crop']:
            x, y = mousePos.x(), mousePos.y()
            item = RectItemHandle(x, y, 1, 1, handleSize=100)
            self.view_canvas.add_crop_win_to_scene(item)
            item.item_delete_signal.signal.connect(self.delete_crop_win_by_signal)


    def clean_canvas_by_click(self):
        if self.view_canvas.get_mode() == func_mode['select']:
            self.view_canvas.clean_all_pos_items()
            self.pb_save_csv.setEnabled(False)
        elif self.view_canvas.get_mode() == func_mode['crop']:
            self.view_canvas.delete_all_crop_win()


    #############################
    ##  Position Data Related  
    #############################

    def load_position(self):
        pos_path, _ = QFileDialog.getOpenFileName(self,
            caption='Open File',
            filter="Excel (*.csv)")
        if not pos_path: return  # cancel button pressed

        palm_pos = np.array(pd.read_csv(pos_path))

        # convert the geopos into image positions
        if isinstance(palm_pos[0,0], float):
            pos_new = []
            for x, y in palm_pos:
                x = int((x-self._tfw[0])/pixel_size)
                y = int((self._tfw[3]-y)/pixel_size)
                pos_new.append([x,y])
            palm_pos = np.array(pos_new)

        # exclude the positions outside the image
        #mode = 'gis' if isinstance(palm_pos[0,0], float) else 'img'
        palm_pos = self.pos_filter(palm_pos)

        # Merge Dialog Window - select OK will merge the positions
        # that already in canvas with the new palm pos.
        pos_in_canvas = self.view_canvas.get_palm_pos_list()
        mode = 'override'
        if len(pos_in_canvas):
            merge_msg_box = QMessageBox()
            merge_msg_box.setIcon(QMessageBox.Information)
            merge_msg_box.setText(
                "There're already position loaded, \n" +
                "do you wanna merge the existing data \n" +
                "with the new loaded one? (Select 'No' \n" +
                "will override the existing data)")
            merge_msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.No)
            merge_msg_box.setDefaultButton(QMessageBox.Ok)
            ret = merge_msg_box.exec_() # 1024: Ok, 65536: No
            
            if ret == 1024:
                CLOSE_DISTANCE = 2 # unit: meter
                mode = 'insert'
                tree = spatial.cKDTree(pos_in_canvas)
                pos_new = []
                for x, y in palm_pos:
                    indices = tree.query_ball_point([[x,y]], r=int(CLOSE_DISTANCE/pixel_size))
                    if not indices:
                        pos_new.append([x, y])
                palm_pos = np.array(pos_new)

        self.view_canvas.palm_pos_data_loading(palm_pos, mode=mode)
        self.pb_save_csv.setEnabled(True)
        self.info_display.setText('Position data loaded.')


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


    def pos_filter(self, pos):
        pos_new = []
        h, w = self.org_im_shape
        for x, y in pos:
            if 0 <= x < w and 0 <= y < h:
                pos_new.append([x, y])

        return np.array(pos_new)
            

    #############################
    ##  Crop Mode Related 
    #############################

    def crop_and_split_size_check(self):
        crop_win_adjust = False
        try:
            crop_size = int(self.le_crop_size.text())
            RectItemHandle.set_min_size(crop_size*self._factor)
            for rect in self.view_canvas._crop_win:
                win = list(map(int, rect.originRect().getCoords()))
                x1, y1, x2, y2 = (np.array(win) / self._factor).astype('int')
                width, height = x2-x1, y2-y1
                if width < crop_size or height < crop_size:
                    crop_win_adjust = True
                    rect.switch_color('selected')
                else:
                    rect.switch_color('default')
        except Exception:
            warning_msg("Crop size must be integer.")
        return crop_win_adjust


    def delete_crop_win_by_signal(self, it):
        del self.view_canvas._crop_win[-1]
        self.view_canvas.delete_crop_win_from_scene(it)


    #############################
    ##  Dataset Related 
    #############################

    def dataset_producing(self):
        """
        Producing the Pascal VOC dataset     
        """
        self.info_display.setText('Waiting ...')
        windows = self.view_canvas.get_all_crop_win()
        windows = (windows/self._factor).astype(int)

        size = self.check_split_size()
        ratio = self.check_overlap_ratio()
        if size is None or ratio is None: return

        self.prob_map_produce()
        ds = DatasetProducing(self.org_im, self.lb, alpha=.6)
        ds.split(size, ratio, windows=windows)
        ds.save(filename=self._filename, save_dir=self._im_dir)
        self.info_display.setText("Dataset Completed !")


    def prob_map_produce(self):
        """
        Probability map producing
        """
        self.lb = np.zeros(self.org_im.shape[:2], dtype='uint8')
        for pos in self.view_canvas._palm_pos:
            x, y = np.rint(pos / self._factor).astype('int')
            cv2.circle(self.lb, (x, y), int(palm_radius/pixel_size), (1,), -1, cv2.LINE_AA)


    def check_split_size(self):
        """
        Checking the size format and crop
        window size must greater than split size if exists.
        """
        crop_size = None
        try:
            crop_size = int(self.le_crop_size.text())
            if self.crop_and_split_size_check():
                warning_msg('Crop window size must greater than split size.')
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
