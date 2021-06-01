import os
os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] = pow(2, 40).__str__()

import cv2
import numpy as np
import pandas as pd
from decouple import config
from pathlib import Path
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi
from scipy import spatial
from screeninfo import get_monitors

from .dialog import warning_msg, critical_msg
from .utils.imutils import load_image
from .item import PalmPositionCanvas, RectItemHandle, DatasetProducing
from .style.stylesheet import connect_to_stylesheet


palm_radius = 1.5 # unit: meter
#pixel_size = 0.107541
pixel_size = 0.05
size_limitation = 20000.
func_mode = {'select': 0, 'crop': 1}


class palmGUI(QDialog):

    def __init__(self, parent=None):
        super(palmGUI, self).__init__(parent)
        loadUi('GUI/dialog_palm.ui', self)
        self.setWindowIcon(QIcon('GUIImg/palm-tree.png'))
        self.full_screen = False
        self.org_screen_sz = None
        self.pos_saved = False

        # canvas initialization
        self.view_canvas = PalmPositionCanvas(self, QRect(0, 0, 10, 10))
        self.view_canvas.setViewportUpdateMode(0)
        self.gl_canvas.addWidget(self.view_canvas)
        
        # push buttons setting
        self.pb_openfile.clicked.connect(self.image_open)
        self.pb_loadcsv.clicked.connect(self.load_position)
        self.pb_leave.clicked.connect(self.close)
        self.pb_save_csv.clicked.connect(self.save_position)
        self.pb_save_dataset.clicked.connect(self.dataset_producing)
        self.pb_clean.clicked.connect(self.clean_canvas_by_click)
        self.pb_select_mode.clicked.connect(lambda: self.mode_switch('select'))
        self.pb_crop_mode.clicked.connect(lambda: self.mode_switch('crop'))
        self.le_crop_size.setPlaceholderText('Crop Size')
        self.le_overlap_ratio.setPlaceholderText('Overlap Ratio')
        self.le_crop_size.editingFinished.connect(self.crop_and_split_size_check)

        # Shortcut setting
        QShortcut(Qt.CTRL+Qt.Key_S, self, self.save_position)
        QShortcut(Qt.Key_Escape, self, self.close)

    def mousePressEvent(self, mouseEvent: QMouseEvent) -> None:
        self.mouse_from = mouseEvent.globalPos()
        self.frame_from_x = self.x()
        self.frame_from_y = self.y()

    def mouseMoveEvent(self, mouseEvent: QMouseEvent) -> None:
        if not self.full_screen:
            move = mouseEvent.globalPos() - self.mouse_from
            self.setGeometry(QRect(
                self.frame_from_x + move.x(),
                self.frame_from_y + move.y(),
                self.width(), self.height()
            ))

    def mouseDoubleClickEvent(self, mouseEvent: QMouseEvent) -> None:
        if self.full_screen:
            self.setGeometry(self.org_screen_sz)
            self.setSizeGripEnabled(True)
            self.full_screen = False
        else:
            self.org_screen_sz = self.geometry()
            self.setSizeGripEnabled(False)
            x, y, _, _ = self.org_screen_sz.getCoords()
            for m in get_monitors():
                if m.x <= x < m.x + m.width and m.y <= y < m.y + m.height:
                    self.setGeometry(QRect(m.x, m.y, m.width, m.height))
                    break
            self.full_screen = True
            
    def resizeEvent(self, a0: QResizeEvent) -> None:
        if self.view_canvas.hasPhoto():
            self.view_canvas.fitInView()
            self.full_screen = False
        return super().resizeEvent(a0)

    def image_open(self):
        self._im_path, _ = QFileDialog.getOpenFileName(self,
            caption='Open File', 
            directory='data/palm/',
            filter="Images (*.tif *.png *.jpg)")
    
        if not self._im_path: return  # cancel button pressed

        self._im_path = Path(self._im_path)
        self._filename = self._im_path.stem
        self._im_dir = self._im_path.parent
        self._im_dir.mkdir(parents=True, exist_ok=True)
        self.canvas_initial(self._im_path)

    def canvas_initial(self, im_path: Path):
        self.raster, scaled_im, self._factor, self._trans = load_image(im_path, pixel_size)

        self.view_canvas.clean_pos_items()
        self.view_canvas.clean_win_items()
        self.view_canvas.setPhoto(scaled_im[..., ::-1].copy())
        self.view_canvas.set_factor(self._factor)
        self.view_canvas.set_add_point(True)
        self.view_canvas.set_pixel_size(pixel_size)
        self.view_canvas.add_win_signal.connect(self.add_win_handler)
        self.view_canvas.add_pos_signal.connect(self.add_pos_handler)
        self.view_canvas.zoom_signal.connect(self.update_win_edge_when_zoom)

        self.pb_save_dataset.setEnabled(False)
        self.pb_loadcsv.setEnabled(True)
        self.pb_save_csv.setEnabled(True)
        self.le_crop_size.setEnabled(False)
        self.le_overlap_ratio.setEnabled(False)
        self.info_display.setText('Image Loaded.')
    
    def mode_switch(self, mode: str):
        """ Mode switching and changing
         the functional push buttons' stylesheet 

        # Args:
            mode (str): must be either 'select' or 'crop'
        """
        assert mode in func_mode, f"Undefined mode: {mode}."

        sstyle = connect_to_stylesheet('button_selected', 'GUI/palm/')
        ustyle = connect_to_stylesheet('button_unselected', 'GUI/palm')

        if self.view_canvas.get_mode() != func_mode[mode]:
            if mode == 'select':
                self.pb_select_mode.setStyleSheet(sstyle)
                self.pb_crop_mode.setStyleSheet(ustyle)
            else:
                self.pb_select_mode.setStyleSheet(ustyle)
                self.pb_crop_mode.setStyleSheet(sstyle)
            self.view_canvas.set_mode(func_mode[mode])

    def clean_canvas_by_click(self):
        if self.view_canvas.get_mode() == func_mode['select']:
            if not self.pos_saved:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText(
                    "Palm position data haven't saved yet. \n" +
                    "Do you wanna save data before cleaning?")
                msg_box.setStandardButtons(
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                msg_box.setDefaultButton(QMessageBox.Yes)
                ret = msg_box.exec()
                if ret == QMessageBox.Yes:
                    self.save_position()
                    self.view_canvas.clean_pos_items()
                elif ret == QMessageBox.No:
                    self.view_canvas.clean_pos_items()
                elif ret == QMessageBox.Cancel:
                    return
            else:
                self.view_canvas.clean_pos_items()
        elif self.view_canvas.get_mode() == func_mode['crop']:
            self.view_canvas.clean_win_items()

    def clean_info_display(self):
        self.info_display.setText("")

    # ================================
    #   Palm Position Related  
    # ================================

    def add_pos_handler(self):
        self.pos_saved = False
        self.clean_info_display()

    def load_position(self):
        """ Loading position data file (`.csv`). """
        pos_path, _ = QFileDialog.getOpenFileName(self,
            caption='Open File',
            directory=str(self._im_dir),
            filter="Excel (*.csv)")
        if not pos_path: return  # cancel button pressed

        palm_pos = np.array(pd.read_csv(pos_path, header=None))
        if isinstance(palm_pos[0,0], float):
            palm_pos[:, 0] = (palm_pos[:, 0] - self._trans[0]) // pixel_size
            palm_pos[:, 1] = (self._trans[3] - palm_pos[:, 1]) // pixel_size
        palm_pos = self.pos_filter(palm_pos)

        # Merge Dialog Window - select OK will merge the positions
        # that already in canvas with the new palm pos.
        mode = 'override'
        if not self.view_canvas.no_pts:
            merge_msg_box = QMessageBox()
            merge_msg_box.setIcon(QMessageBox.Information)
            merge_msg_box.setText(
                "There're already position in canvas, \n" +
                "do you wanna merge the existing data \n" +
                "with the new loaded one? (Select 'No' \n" +
                "will override the existing data)")
            merge_msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.No)
            merge_msg_box.setDefaultButton(QMessageBox.Ok)
            ret = merge_msg_box.exec()
            
            if ret == QMessageBox.Ok:
                CLOSE_DISTANCE = 2 # unit: meter
                mode = 'insert'
                pos_current = (self.view_canvas.get_palm_pos_data() / self._factor).astype(int)
                tree = spatial.cKDTree(pos_current)
                pos_new = []
                for x, y in palm_pos:
                    indices = tree.query_ball_point([[x,y]], r=int(CLOSE_DISTANCE/pixel_size))
                    if not indices:
                        pos_new.append([x, y])
                palm_pos = np.array(pos_new)

        self.pos_saved = True
        self.view_canvas.palm_pos_data_loading(palm_pos, mode=mode)
        self.info_display.setText('Position data loaded.')
        self.pb_save_dataset.setEnabled(True)
        self.le_crop_size.setEnabled(True)
        self.le_overlap_ratio.setEnabled(True)

    def save_position(self):
        """
        Saving the positions to csv files.
        Gis position file named `palm_gis_pos.csv`
        Image position file named `palm_img_pos.csv`.
        """
        if not self.view_canvas.hasPhoto(): return
        if self.view_canvas.no_pts:
            warning_msg('Save failed since no point in canvas.')
            return

        im_pos = self.view_canvas.get_palm_pos_data()
        im_pos = np.rint(im_pos / self._factor).astype('int')
        df = pd.DataFrame(im_pos)
        try:
            df.to_csv(self._im_dir.joinpath('palm_img_pos.csv'), header=None, index=None)
        except PermissionError as err:
            critical_msg(str(err))
            return

        # Geographic position saving
        if self._trans[:2] != (0, 1):
            im_pos = im_pos.astype('float')
            im_pos[:, 0] = self._trans[0] + im_pos[:, 0] * pixel_size
            im_pos[:, 1] = self._trans[3] - im_pos[:, 1] * pixel_size
            df = pd.DataFrame(im_pos)
            try:
                df.to_csv(self._im_dir.joinpath('palm_gis_pos.csv'), header=None, index=None)
            except PermissionError as err:
                critical_msg(str(err))
                return

        self.info_display.setText("Save Done !")
        self.pb_save_dataset.setEnabled(True)
        self.le_crop_size.setEnabled(True)
        self.le_overlap_ratio.setEnabled(True)

    def pos_filter(self, pos: np.ndarray) -> np.ndarray:
        """ 
        Eliminating the position that fall outside the image.
        """
        pos_new = []
        h, w = self.raster.RasterYSize, self.raster.RasterXSize
        for x, y in pos:
            if 0 <= x < w and 0 <= y < h:
                pos_new.append([x, y])

        return np.array(pos_new)
            
    # ================================
    #   Crop Windows Related 
    # ================================

    def add_win_handler(self, mousePos: QPoint):
        x, y = mousePos.x(), mousePos.y()
        item = RectItemHandle(
            x, y, 1, 1, 
            handleSize=100, 
            zfactor=self.view_canvas.get_zoom_factor()
        )
        item.mouse_release_signal.signal.connect(self.win_size_filter)
        item.shape_changed_signal.signal.connect(self.win_shape_display)
        self.view_canvas.add_crop_win_to_scene(item)

    def crop_and_split_size_check(self) -> bool:
        crop_win_adjust = False
        try:
            crop_size = int(self.le_crop_size.text())
            RectItemHandle.set_min_size(crop_size*self._factor)
            for rect in self.view_canvas.win_group.childItems():
                win = list(map(int, rect.originRect().getCoords()))
                x1, y1, x2, y2 = np.array(win).astype('int')
                width, height = x2-x1, y2-y1
                if width < crop_size or height < crop_size:
                    crop_win_adjust = True
                    rect.switch_color('selected')
                else:
                    rect.switch_color('default')
        except Exception:
            warning_msg("Crop size must be integer.")
        return crop_win_adjust

    def update_win_edge_when_zoom(self):
        for it in self.view_canvas.win_group.childItems():
            it.set_edge_width(self.view_canvas.get_zoom_factor())
            it.update()

    def win_shape_display(self, rect: QRectF):
        w = abs(int(rect.width() / self._factor))
        h = abs(int(rect.height() / self._factor))
        self.info_display.setText(f"({w}, {h})")

    def win_size_filter(self):
        self.check_win_size()
        self.clean_info_display()

    # ================================
    #   Dataset Related 
    # ================================

    def dataset_producing(self):
        """
        Producing the Pascal VOC dataset     
        """
        self.info_display.setText('Waiting ...')
        self.check_win_size()
        windows = self.view_canvas.get_all_crop_win()
        windows = (windows / self._factor).astype(int)

        size = self.check_split_size()
        ratio = self.check_overlap_ratio()
        if size is None or ratio is None: return

        pos = self.view_canvas.get_palm_pos_data()
        pos = (pos / self._factor).astype('int')

        ds = DatasetProducing(
            raster=self.raster,
            pos=pos, reso=pixel_size, 
            n_class=1, alpha=.6)

        ds.split(size, ratio, windows=windows)
        ds.save(filename=self._filename, save_dir=self._im_dir)
        self.info_display.setText("Dataset Completed !")

    def check_win_size(self):
        """ Delete the trivial crop windows. """
        MINIMUM_WIN_SIZE = 10
        for item in self.view_canvas.win_group.childItems():
            x1, y1, x2, y2 = list(map(int, item.originRect().getCoords()))
            w, h = self.raster.RasterXSize, self.raster.RasterYSize
            x1, y1 = max(x1, 0), max(y1, 0)
            x2, y2 = min(x2, w), min(y2, h)
            if x2 - x1 < MINIMUM_WIN_SIZE or y2 - y1 < MINIMUM_WIN_SIZE:
                self.view_canvas.remove_item_from_scene(item)

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
                return None
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
