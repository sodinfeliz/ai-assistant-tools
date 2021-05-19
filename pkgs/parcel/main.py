import os
os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] = pow(2, 40).__str__()

import shutil
import re
import cv2
import numpy as np
import random
from pathlib import Path
from PIL import Image, ImageDraw
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi

from .dialog import warning_msg, replace_shpfile_msgbox
from .item import ParcelCanvas, PolyItemHandle, RectItemHandle, LabelFrame, LineHandleItem
from .utils.visualization import color_generate 
from .utils.shputil import shppoly_extract, rgnshp_generate
from .utils.imutils import resize_image, crop_im_into_tiles
from .style.stylesheet import connect_to_stylesheet


pixel_size = 0.25  # default resolution
func_mode = {
    'crop': 0,
    'poly': 1,
    'cut': 2
}


class SaveWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, im, windows: list, wsize: int,
                 ratio: float, dir_root: Path,
                 dir_name: str, parent=None) -> None:
        super().__init__(parent=parent)

        self._dir = dir_root.joinpath(dir_name)
        shutil.rmtree(str(self._dir), ignore_errors=True)
        self._dir.mkdir(parents=True)

        self.im = im
        self.windows = windows
        self.wsize = wsize
        self.ratio = ratio

    def run(self):
        pass


class parcelGUI(QDialog):
    def __init__(self, parent=None):
        super(parcelGUI, self).__init__(parent)
        loadUi('GUI/parcel/dialog_parcel.ui', self)

        # canvas initialization
        self.view_canvas = ParcelCanvas(self, QRect(0, 0, 10, 10))
        self.view_canvas.setViewportUpdateMode(0)
        self.gl_canvas.addWidget(self.view_canvas)
        
        # widgets setting
        self.pb_open_image.clicked.connect(self.image_open)
        self.pb_open_shape.clicked.connect(self.shapefile_open)
        self.pb_open_shape.setEnabled(False)
        self.pb_clear_crop.clicked.connect(self.view_canvas.delete_all_crop_win)
        self.pb_save.clicked.connect(self.data_save)
        self.pb_initial.clicked.connect(self._re_initialization)
        self.pb_leave.clicked.connect(self.close)

        self.pb_crop_mode.clicked.connect(lambda: self.mode_switch('crop'))
        self.pb_poly_mode.clicked.connect(lambda: self.mode_switch('poly'))
        self.pb_cut_mode.clicked.connect(lambda: self.mode_switch('cut'))
        self.hs_split_ratio.valueChanged.connect(lambda: self._ratio_changed('split'))
        self.hs_overlap_ratio.valueChanged.connect(lambda: self._ratio_changed('overlap'))

        # initializaion
        self._top_widget_initialization()
        #self.show_label_window()


    def mode_switch(self, mode):
        """ Mode switching and changing
         the functional push buttons' stylesheet 

        # Args:
            mode (str): must be either 'crop', 'poly' or 'cut'
        """
        assert mode in func_mode, f"Undefined mode: {mode}."
        ssdir = 'GUI/parcel'
        if self.view_canvas.mode != func_mode[mode]:
            if mode == 'crop':
                self.pb_crop_mode.setStyleSheet(connect_to_stylesheet('button_selected', ssdir))
                self.pb_poly_mode.setStyleSheet(connect_to_stylesheet('button_unselected', ssdir))
                self.pb_cut_mode.setStyleSheet(connect_to_stylesheet('button_unselected', ssdir))
            elif mode == 'poly':
                self.pb_crop_mode.setStyleSheet(connect_to_stylesheet('button_unselected', ssdir))
                self.pb_poly_mode.setStyleSheet(connect_to_stylesheet('button_selected', ssdir))
                self.pb_cut_mode.setStyleSheet(connect_to_stylesheet('button_unselected', ssdir))
            else:
                self.pb_crop_mode.setStyleSheet(connect_to_stylesheet('button_unselected', ssdir))
                self.pb_poly_mode.setStyleSheet(connect_to_stylesheet('button_unselected', ssdir))
                self.pb_cut_mode.setStyleSheet(connect_to_stylesheet('button_selected', ssdir))
            self.view_canvas.mode = func_mode[mode]
            self.set_poly_changable()


    def show_label_window(self):
        *_, w, h = self.frame_main.frameGeometry().getRect()
        cp = QDesktopWidget().availableGeometry().center()
        self.frame_label = LabelFrame()
        self.frame_label.move(QPoint(cp.x()+w//2, cp.y()-h//2))
        self.frame_label.show()    


    def image_open(self):
        self._im_path, _ = QFileDialog.getOpenFileName(self,
            caption='Open File',
            directory='./data/parcel',
            filter="TiffImages (*.tif)")

        if not self._im_path: return  # cancel button pressed
        if self.view_canvas.hasPhoto():
            self._re_initialization()

        self._im_path = Path(self._im_path)
        self._im_dir = self._im_path.parent
        self._filename = self._im_path.stem
        self.canvas_initial(Path(self._im_path))
        self.pb_open_shape.setEnabled(True)
        

    def canvas_initial(self, im_path):
        self.back_im, self._im_shape, self._factor, self._tfw = resize_image(im_path, pixel_size)

        self._check_im_size()

        self.view_canvas.setPhoto(self._back_im)
        self.view_canvas.set_factor(self._factor)
        self.view_canvas.add_item_signal.connect(self.add_item_by_drag)
        self.view_canvas.delete_item_signal.connect(self.delete_item_by_click)
        
        self.pb_save.setEnabled(False)
        self.le_crop_info.setText('Image Loaded.')


    def shapefile_open(self):
        self._shp_path = QFileDialog.getExistingDirectory(self,
            caption='Open File',
            directory=str(self._im_dir))

        if not self._shp_path: return  # cancel button pressed

        self._shpfile_replace_check()
        self.view_canvas.delete_all_crop_win()

        new_shapepaths = self._shpfile_path_name_grab()
        self.shapepaths.extend(new_shapepaths)

        self.class_num = len(self.shapepaths)
        self.colors = color_generate(self.class_num, seed=3)
        if self.rgnshape is None:
            self.rgnshape = rgnshp_generate(self._im_path, self._tfw)

        # extracting the polygons from shapefile and
        # converting all shapely polygon into QtItem
        for path, color in zip(new_shapepaths, self.colors[-len(new_shapepaths):]):
            polys = []
            poly_per_class = shppoly_extract(path, self.rgnshape)
            for poly in poly_per_class:
                poly = PolyItemHandle(poly, self._tfw, self._factor, color)
                self.view_canvas.add_item_to_scene(poly)
                polys.append(poly)
            self.polyitems.append(polys)

        self._ratio_changed('split')
        self._ratio_changed('overlap')
        self.le_wsize.setEnabled(True)
        self.le_crop_info.setText('Shapefile Polygons Loaded.')
        self.hs_split_ratio.setEnabled(True)
        self.hs_overlap_ratio.setEnabled(True)


    def add_item_by_drag(self, mousePos):
        if self.view_canvas.mode == func_mode['crop'] and self.view_canvas.hasPhoto() and self.polyitems:
            x, y = mousePos.x(), mousePos.y()
            item = RectItemHandle(x, y, 1, 1, handleSize=100)
            self.view_canvas.add_crop_win_to_scene(item)
            item.item_delete_signal.signal.connect(self.delete_item_by_signal)
            self.pb_save.setEnabled(True)
        elif self.view_canvas.mode == func_mode['cut'] and self.view_canvas.hasPhoto() and self.polyitems:
            item = LineHandleItem(mousePos, mousePos)
            self.view_canvas.add_item_to_scene(item)
            item.item_delete_signal.signal.connect(self.delete_item_by_signal)


    def delete_item_by_click(self):
        """ ======= CROP MODE =======
        Setting 'pb_save' disabled 
        if none of cropped windows exists
        """
        if self.view_canvas.mode == func_mode['crop'] and len(self.view_canvas.crop_win) == 0:
            self.pb_save.setEnabled(False)
            self.le_crop_info.setText('')


    def delete_item_by_signal(self, it):
        if self.view_canvas.mode == func_mode['crop']:
            del self.view_canvas.crop_win[-1]
            self.view_canvas.delete_item_from_scene(it)
            self.le_crop_info.setText('')
        elif self.view_canvas.mode == func_mode['cut']:
            self.view_canvas.delete_item_from_scene(it)

    
    def data_save(self):
        """ ======= CROP MODE =======
        Rasterize all the polygons then
        splitting, saving tiles into local directories
        """
        self.pb_save.setEnabled(False)
        if self.view_canvas.mode == func_mode['crop']:
            wsize = self._check_wsize()
            ratio = float(self.le_overlap_ratio.text())
            if wsize is None: return
            
            det_dir = self._im_dir.joinpath('PascalVOC')
            mask, visual = self._poly_mask_generating()
            windows = self.view_canvas.get_all_crop_win()

            self._save_to_local(
                [self.back_im, mask, visual],
                windows, wsize, ratio, det_dir,
                ['JPEGImages', 'SegmentationClass', 'VisualImages'])

            self._train_val_split(det_dir, 'ImageSets/Segmentation', 'JPEGImages')
            self.le_crop_info.setText('Dataset Producing Completed.')


    def set_poly_changable(self):
        mode = True if self.view_canvas.mode == 1 else False
        for polys in self.polyitems:
            for poly in polys:
                poly.changable = mode


    def _check_im_size(self):
        h, w, c = self.back_im.shape
        memGB = h*w*c / (1024**3)
        memLimit = 2  # 2GB
        if memGB > memLimit:
            self._factor = memLimit / memGB
            self._back_im = cv2.resize(
                self.back_im,
                (int(w * self._factor), int(h * self._factor)))
        else:
            self._back_im = self.back_im


    def _top_widget_initialization(self):
        """ QStackedWidget 'sw_top_widget' initialization """
        self.shapepaths = []
        self.classname = []
        self.polyitems = []
        self.rgnshape = None


    def _re_initialization(self):
        if self.view_canvas.mode == func_mode['crop']:
            self._clear_all_polygon_items()
            self.view_canvas.canvas_clean()
            self.shapepaths = []
            self.classname = []
            self.polyitems = []
            self.rgnshape = None
            self.pb_open_shape.setEnabled(False)
            self.hs_split_ratio.setValue(16)
            self.hs_overlap_ratio.setValue(16)
            self.hs_split_ratio.setEnabled(False)
            self.hs_overlap_ratio.setEnabled(False)
            self.le_wsize.setText('')


    def _save_to_local(self, ims: list, windows: list,
                       wsize: int, ratio: float,
                       dir_root: Path, dir_names: str):
        """ ======= CROP MODE =======
        Splitting the 'im' into tiles with
        window(crop) size and overlap ratio
        then saving them to the local directory

        # Arguments:
            im (list of numpy.ndarray): images to be splitted
            windows (list of tuple): cropped regions
            wsize (int): croppin windown size
            ratio (float): tiles overlapped ratio
            dir_root (Path): [description]
            dir_name (str): [description]
        """
        assert isinstance(dir_root, Path)
        assert 0 <= ratio < 1

        for im, dir_name in zip(ims, dir_names):
            _dir = dir_root.joinpath(dir_name)
            shutil.rmtree(str(_dir), ignore_errors=True)
            _dir.mkdir(parents=True)

            tiles = crop_im_into_tiles(im, windows, wsize, ratio, self._factor)
            for i, tile in enumerate(tiles):
                cv2.imwrite(str(_dir.joinpath(f'{self._filename}_{i}.png')), tile)


    def _train_val_split(self, dir_root: Path, dir_name: str, im_dir: str):
        """ Splitting the training and validation
        data through image name by specified ratio

        # Args:
            dir_root (Path): [description]
            dir_name (str): [description]
            im_dir (str): [description]
        """
        assert isinstance(dir_root, Path)
        det_dir = dir_root.joinpath(dir_name)
        src_dir = dir_root.joinpath(im_dir)
        det_dir.mkdir(parents=True, exist_ok=True)

        imnames = np.array([path.stem for path in src_dir.glob('*.png')])
        train_num = int(len(imnames) * float(self.le_split_ratio.text()))
        random.shuffle(imnames)

        with open(str(det_dir.joinpath('train.txt')), 'w') as file:
            file.writelines('\n'.join(imnames[:train_num]))
        with open(str(det_dir.joinpath('val.txt')), 'w') as file:
            file.writelines('\n'.join(imnames[train_num:]))


    def _poly_mask_generating(self):
        """ ======= CROP MODE =======
        Rasterizing the polygons into
        mask (binary label) and visual (blend 
        image between the origin image and class label)

        # Returns:
            (mask, visual)
        """
        def coord_transform(coords):
            trans = []
            for px, py in coords:
                px = int(px/self._factor)
                py = int(py/self._factor)
                trans.append((px, py))
            return trans

        mask = Image.new('L', tuple(self._im_shape[::-1]), color=0)
        visual = Image.fromarray(self.back_im)
        for i, (items, color) in enumerate(zip(self.polyitems, self.colors)):
            for it in items:
                ImageDraw.Draw(mask).polygon(coord_transform(it.img_coords), outline=1, fill=i+1)
                ImageDraw.Draw(visual).polygon(coord_transform(it.img_coords), outline=1, fill=tuple(color[::-1]))

        visual = Image.blend(Image.fromarray(self.back_im), visual, 0.6)
        return np.array(mask), np.array(visual)


    def _check_wsize(self):
        """ ======= CROP MODE =======
        Checking the validity of Window size
        and overlap ratio QLineEdit

        Returns:
            None if not fitting the format
            (wsize, ratio) otherwise
        """
        wsize = self.le_wsize.text()
        if not re.findall('^[1-9][0-9]*$', wsize) or any([s < int(wsize) for s in self._im_shape]):
            warning_msg('Window size format invalid.')
            return None
        return int(wsize)


    def _clear_all_polygon_items(self):
        """ ======= CROP MODE =======
        Removing all polygon items from scene
        """
        for polys in self.polyitems:
            for it in polys:
                self.view_canvas.delete_item_from_scene(it)
        self.polyitems = []


    def _shpfile_replace_check(self):
        """ ======= CROP MODE =======
        shapefile re-open Dialog
            OK - empty the origin polygon items
            Cancel - added the another shapefile
        """
        if not self.polyitems: return False# first loaded
        if replace_shpfile_msgbox() == 16384:  # 16384: OK
            self._clear_all_polygon_items()
            self.shapepaths = []
            self.classname = []
            self.polyitems = []
            return True
        return False

    
    def _shpfile_path_name_grab(self):
        """ ======= CROP MODE =======
        Grabbing all the shapefile paths
        and adding the new classname to 'self.classname'
        according to the rules below:
        1. file unorganized mode:
            - read .shp directly in self._shp_path
            - treating filename as classname
        2. file organized mode:
            - read all sub-directories under self._shp_path
            - treating the directory name as classname
        Returns:
            list of new shapefile paths
        """
        self._shp_path = Path(self._shp_path)
        _exam = list(self._shp_path.glob('*.shp'))
        if _exam:
            self.classname.extend([p.stem for p in _exam])
            return _exam
        else:
            subdir = list(self._shp_path.glob('*/*.shp'))
            self.classname.extend([p.parent.stem for p in subdir])
            return subdir


    def _ratio_changed(self, mode):
        if mode == 'split':
            ratio = self.hs_split_ratio.value() / 20.
            self.le_split_ratio.setText(f'{ratio:.2f}')
        elif mode == 'overlap':
            ratio = self.hs_overlap_ratio.value() / 20.
            self.le_overlap_ratio.setText(f'{ratio:.2f}')
        



