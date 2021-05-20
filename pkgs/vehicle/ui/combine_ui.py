import os
os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] = pow(2, 40).__str__()

import cv2
import numpy as np
import xml.etree.ElementTree as ET
import threading
from glob import glob
from pascal_voc_writer import Writer
from pathlib import Path
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi

from ..dialog.error import warning_msg
from ..item import LabelCanvas, CropCanvas, RectItem, RectItemHandle
from ..ODCrop import ODCropData
from ..style.pbutton import push_button_setting
from ..style.stylesheet import connect_to_stylesheet


classes = {'vehicle', 'bus', 'truck'}
widget_index = {'bnbox': 0, 'crop': 1}

angles = {
    0: [0],
    1: [0, 90],
    2: [0, 60, -60],
    3: [0, 45, 90, -45]
}


def coords_correlated(coords, w, h):
    """ Cutting off the exceeding bounding box

    ex. width = 10000 and height = 10000 
    coords = [-10, -10, 90, 90] -> [0, 0, 90, 90]
    coords = [9700, 9700, 11200, 10800] -> [9700, 9700, 10000, 10000]

    # Arguments:
        coords: list, (xmin, ymin, xmax, ymax)
        w     : int, width
        h     : int, height

    # Arguments:
        correlated coordinates
    """
    if coords[0] >= w or coords[1] >= h or coords[2] < 0 or coords[3] < 0:
        return []

    coords[0] = max(0, coords[0])
    coords[1] = max(0, coords[1])
    coords[2] = min(w, coords[2])
    coords[3] = min(h, coords[3])

    if coords[2] - coords[0] == 0 or coords[3] - coords[1] == 0:
        return []
    else:
        return coords


def parse_rec(filename):
    """ Parse a PASCAL VOC xml file """
    tree = ET.parse(filename)
    objects = []
    for obj in tree.findall('object'):
        obj_struct = {}
        obj_struct['name'] = obj.find('name').text
        obj_struct['pose'] = obj.find('pose').text
        obj_struct['truncated'] = int(obj.find('truncated').text)
        obj_struct['difficult'] = int(obj.find('difficult').text)
        bbox = obj.find('bndbox')
        obj_struct['bbox'] = [int(bbox.find('xmin').text),
                              int(bbox.find('ymin').text),
                              int(bbox.find('xmax').text),
                              int(bbox.find('ymax').text)]
        objects.append(obj_struct)
    return objects


class carUI(QWidget):

    def __init__(self, parent=None):
        super(carUI, self).__init__(parent)
        loadUi('GUI/vehicle/widget_vehicle.ui', self)

        self._mode = 'bnbox' # start the bnbox page at first
        self._data_path = None
        self._filename = ''

        self.pb_openfile.clicked.connect(self.file_open)
        self.pb_repeat.clicked.connect(self.reload_im_to_scene)
        self.pb_repeat.setShortcut('F2')
        self.pb_leave.clicked.connect(self.close)
        self.pb_bnbox_mode.clicked.connect(lambda: self._top_widget_switch(mode='bnbox'))
        self.pb_crop_mode.clicked.connect(lambda: self._top_widget_switch(mode='crop'))
        self._canvas_widget_initial()
        self._top_widget_initial()

    def _canvas_widget_initial(self):
        self.sw_canvas = QStackedWidget(self)
        self.sw_canvas.setGeometry(63, 51, 1143, 850)

        self.canvas_bnbox = LabelCanvas(self, QRect(0, 0, 1143, 850))
        self.canvas_bnbox.setViewportUpdateMode(0)
        self.canvas_bnbox.clear_items()
        self.canvas_bnbox.add_item_signal.connect(self.add_item_by_drag)
        self.canvas_bnbox.delete_item_signal.connect(self.delete_item_by_click)

        self.canvas_crop = CropCanvas(self, QRect(63, 51, 1143, 850))
        self.canvas_crop.setViewportUpdateMode(0)
        self.canvas_crop.clear_all_items()

        self.sw_canvas.addWidget(self.canvas_bnbox)
        self.sw_canvas.addWidget(self.canvas_crop)
        self.sw_canvas.setCurrentWidget(self.canvas_bnbox)

    def _top_widget_switch(self, mode):
        if self._mode != mode:
            self._mode = mode
            self.sw_top_widget.setCurrentIndex(widget_index[self._mode])
            if mode == 'bnbox':
                self.sw_canvas.setCurrentWidget(self.canvas_bnbox)
                self.pb_bnbox_mode.setStyleSheet(connect_to_stylesheet('button_selected', dir='GUI/vehicle'))
                self.pb_crop_mode.setStyleSheet(connect_to_stylesheet('button_unselected', dir='GUI/vehicle'))
                self.pb_segment_mode.setStyleSheet(connect_to_stylesheet('button_unselected', dir='GUI/vehicle'))
                self.pb_save.clicked.connect(self.save_data)
                self.pb_save.setShortcut('Ctrl+S')
            elif mode == 'crop':
                self.sw_canvas.setCurrentWidget(self.canvas_crop)
                self.pb_bnbox_mode.setStyleSheet(connect_to_stylesheet('button_unselected', dir='GUI/vehicle'))
                self.pb_crop_mode.setStyleSheet(connect_to_stylesheet('button_selected', dir='GUI/vehicle'))
                self.pb_segment_mode.setStyleSheet(connect_to_stylesheet('button_unselected', dir='GUI/vehicle'))
                self.pb_save.clicked.connect(self.dataset_producing)
                self.pb_save.setEnabled(False)

    def _top_widget_initial(self):
        self.sw_top_widget.setCurrentIndex(widget_index[self._mode])
            
        if self._mode == 'bnbox':
            self.sw_canvas.setCurrentWidget(self.canvas_bnbox)
            self.pb_save.clicked.connect(self.save_data)
            self.pb_save.setShortcut('Ctrl+S')

        elif self._mode == 'crop':
            self.sw_canvas.setCurrentWidget(self.canvas_crop)
            self.pb_save.clicked.connect(self.dataset_producing)
            self.pb_save.setEnabled(False)

        # bnbox widhet initialization
        self.le_new_class.returnPressed.connect(self.add_new_class)
        self.le_current_frame.setText('- ')
        self.le_total_frame.setText('/ -')

        for c in classes: self.cb_label.addItem(c)
        self.cb_label.setInsertPolicy(3)
        self.cb_label.setCurrentIndex(-1)

        self.pb_add_class.clicked.connect(self.add_new_class)
        self.pb_prev_frame.clicked.connect(self.prev_frame)
        self.pb_next_frame.clicked.connect(self.next_frame)
        
        QShortcut(Qt.Key_Left, self, self.prev_frame)
        QShortcut(Qt.Key_Right, self, self.next_frame)

        # crop widhet initialization
        self._back_im_path = ''
        self._crop_width = None
        self._crop_height = None

        self.le_crop_info.setReadOnly(True)
        self.le_width.setPlaceholderText('width')
        self.le_height.setPlaceholderText('height')
        self.le_crop_info.setText('Wait For Extracting !')  

        self.cb_angle.addItem('1 Angle: 0')
        self.cb_angle.addItem('2 Angles: 0, 90')
        self.cb_angle.addItem('3 Angles: 0, 60, 120')
        self.cb_angle.addItem('4 Angles: 0, 45, 90, 135')
        self.cb_angle.setEnabled(False)

    def file_open(self):
        """
        Open the file manager to open the directory
        """
        dir_name = {
            'default': ['images', 'bnboxes', 'png'],
            'PascalVOC': ['JPEGImages', 'Annotations', 'jpg']
        }

        self._data_path = Path(QFileDialog.getExistingDirectory(self, 'Open File', directory='./data/vehicle'))
        self._filename = self._data_path.stem
        dir_check = dir_name['PascalVOC'] if self._filename == 'PascalVOC' else dir_name['default']
        
        if self._data_path and np.setdiff1d(dir_check[:2], os.listdir(self._data_path)).size == 0:
            self._im_dir = self._data_path.joinpath(dir_check[0])

            # crop mode only read first image in image directory
            # bnbox read all images and bnboxes data 
            if self._mode == 'bnbox':    
                self._im_path = glob(str(self._im_dir.joinpath(f'*.{dir_check[2]}')))
                self._bnb_dir = self._data_path.joinpath(dir_check[1])
                self._bnb_path = glob(str(self._bnb_dir.joinpath('*.xml')))
                self.thread_load_im_to_scene()
            elif self._mode == 'crop':
                self._back_im_path = str(sorted(self._im_dir.glob('*.png'))[0])
                self.load_im_to_scene()
        else:
            warning_msg('Invalid directory !')

    def thread_load_im_to_scene(self):
        loading_thread = threading.Thread(target=self.load_im_to_scene)
        loading_thread.start()
        loading_thread.join()

    def reload_im_to_scene(self):
        if self._mode == 'bnbox' and self.canvas_bnbox.hasPhoto():
            self.load_im_to_scene()
        elif self._mode == 'crop' and self.canvas_crop.hasPhoto():
            self.load_im_to_scene()

    def load_im_to_scene(self):
        
        if self._mode == 'bnbox':
            self.pb_add_class.setEnabled(False)
            self.le_new_class.setEnabled(False)
            self.pb_openfile.setEnabled(False)
            self.pb_save.setEnabled(False)
            self.pb_prev_frame.setEnabled(False)
            self.pb_next_frame.setEnabled(False)

            if self._im_path:
                self.le_total_frame.setText(f'/ {len(self._im_path) - 1}')
                self.le_current_frame.setText('0')
                self.saved = [0] * len(self._im_path)

                # image corresponding bnboxes loading
                self._all_bnboxes = []
                for path in self._bnb_path:
                    objects = parse_rec(path)
                    bnboxes = []
                    for obj in objects:
                        x1, y1, x2, y2 = obj['bbox']
                        item = RectItemHandle(x1, y1, x2-x1, y2-y1)
                        item.setLabel(obj['name'])
                        bnboxes.append(item)
                        item.item_changed_signal.signal.connect(self.item_changed)

                        if obj['name'] not in classes:
                            classes.add(obj['name'])

                    self._all_bnboxes.append(bnboxes)

                self.canvas_bnbox.setPhoto(self._im_path[0])
                self.canvas_bnbox.clear_items()
                self.load_bndox_to_scene(index=0)

            self.pb_add_class.setEnabled(True)
            self.pb_next_frame.setEnabled(True)
            self.le_new_class.setEnabled(True)
            self.pb_openfile.setEnabled(True)
            self.cb_label.setEnabled(True)
            self.cb_label.setCurrentIndex(0)

        elif self._mode == 'crop' and self._back_im_path:
            print(self._back_im_path)
            self.canvas_crop.setPhoto(self._back_im_path)
            self.canvas_crop.clear_all_items()
            self.pb_save.setEnabled(False)
            self.cb_angle.setEnabled(False)
            self.cb_angle.setCurrentIndex(0)
            self.le_crop_info.setText(
                f'File: {self._filename}  Size: ({self.canvas_crop.back_im.shape[1]}, {self.canvas_crop.back_im.shape[0]})'
            )

    def load_bndox_to_scene(self, index=0):
        for it in self._all_bnboxes[index]:
            self.canvas_bnbox.add_item_to_scene(it)

    def add_item_by_drag(self, pos):
        if self._mode == 'bnbox' and self.canvas_bnbox.hasPhoto():
            x, y = pos.x(), pos.y()
            item = RectItemHandle(x, y, 1, 1)
            item.setLabel(self.cb_label.currentText())

            index = int(self.le_current_frame.text())
            self._all_bnboxes[index].append(item)
            self.canvas_bnbox.add_item_to_scene(item)
            item.item_changed_signal.signal.connect(self.item_changed)
            item.item_delete_signal.signal.connect(self.delete_item_by_signal)

    def add_new_class(self):
        new_class = self.le_new_class.text().lower()
        if not new_class:
            return
        if new_class in classes:
            warning_msg('Class already exists.')
        else:
            classes.add(new_class)
            self.cb_label.addItem(new_class)
            self.cb_label.setCurrentIndex(self.cb_label.count()-1)

    def delete_item_by_click(self, pos):
        index = int(self.le_current_frame.text())
        for i, it in enumerate(self._all_bnboxes[index]):
            if it.rect().contains(pos):
                del self._all_bnboxes[index][i]
                self.canvas_bnbox.delete_item_on_scene(it)
                self.item_changed()
                break

    def delete_item_by_signal(self, it):
        del self._all_bnboxes[int(self.le_current_frame.text())][-1]
        self.canvas_bnbox.delete_item_on_scene(it)

    def item_changed(self):
        index =  int(self.le_current_frame.text())
        self.saved[index] = 1
        self.le_current_frame.setText(f'{index}')
        self.pb_save.setEnabled(True)

    def prev_frame(self):
        if self._mode == 'bnbox':
            index = int(self.le_current_frame.text()) - 1
            if index < 0: return

            self.canvas_bnbox.clear_items()
            self.pb_next_frame.setEnabled(True)
            self.le_current_frame.setText(f'{index}')
            self.canvas_bnbox._photo.setPixmap(QPixmap(self._im_path[index]))
            if index == 0:
                self.pb_prev_frame.setEnabled(False)
            self.load_bndox_to_scene(index=index)

    def next_frame(self):
        index = int(self.le_current_frame.text()) + 1
        if index >= len(self._im_path): return

        self.canvas_bnbox.clear_items()
        self.pb_prev_frame.setEnabled(True)
        self.le_current_frame.setText(f'{index}')
        self.canvas_bnbox._photo.setPixmap(QPixmap(self._im_path[index]))
        if index == len(self._im_path) - 1:
            self.pb_next_frame.setEnabled(False)
        self.load_bndox_to_scene(index=index)

    def save_data(self):
        for i, s in enumerate(self.saved):
            if s:
                h, w = cv2.imread(self._im_path[i]).shape[:2]
                writer = Writer(self._im_path[i], w, h)
                for it in self._all_bnboxes[i]:
                    label = it.label.toPlainText()
                    coords = list(map(round, it.originRect().getCoords()))
                    coords = coords_correlated(coords, w, h)
                    if coords:
                        writer.addObject(label, *coords)
                    else:
                        continue
                writer.save(self._bnb_path[i])

        self.saved = [0] * len(self._im_path)
        self.le_current_frame.setText(self.le_current_frame.text())
        self.pb_save.setEnabled(False)        

    def mouseDoubleClickEvent(self, event):
        if self._mode == 'crop': 
            add_rect = self._check_width_height()
            if add_rect and event.buttons() == Qt.LeftButton and self._data_path: 
                widget_x, widget_y = self.canvas_crop.pos().x(), self.canvas_crop.pos().y()
                pos = self.canvas_crop.mapToScene(event.x() - widget_x, event.y() - widget_y)

                x, y = round(pos.x()) - self._crop_width/2, round(pos.y()) - self._crop_height/2    
                self.canvas_crop.add_item_to_scene(RectItem(x, y, self._crop_width, self._crop_height))
                self.pb_save.setEnabled(True)

                if self._crop_width == self._crop_height:
                    self.cb_angle.setEnabled(True)
                else:
                    self.cb_angle.setCurrentIndex(0)  # only 1-anlge when all squares
                    self.cb_angle.setEnabled(False)
        else:
            super().mouseDoubleClickEvent(event)

    def _check_width_height(self):
        if not self.le_width.text().isdigit() or not self.le_height.text().isdigit():
            warning_msg("Invalid format in \'Width\' or \'Height\' cell.")
            return False

        reasign = False
        if self._crop_width is None:
            reasign = True
        elif self._crop_width != int(self.le_width.text()) or \
             self._crop_height != int(self.le_height.text()):
            reasign = True
            self.canvas_crop.clear_all_items()
        if reasign:
            self._crop_width = int(self.le_width.text())
            self._crop_height = int(self.le_height.text())

        return True

    def dataset_producing(self):
        # retrieving all the crop bounding boxes in the current scene
        crop_boxes = self.canvas_crop.all_crop_bboxes()

        for (xmin, ymin, xmax, ymax) in crop_boxes:
            if xmin < 0 or ymin < 0 or \
               xmax >= self.canvas_crop.back_im.shape[1] or \
               ymax >= self.canvas_crop.back_im.shape[0]:
                warning_msg('Bounding Box exceeds the image border.')
                return    

        progress_thread = threading.Thread(target=self.extract_process)
        progress_thread.start()

    def extract_process(self):
        self.pb_save.setEnabled(False)
        self.cb_angle.setEnabled(False)
        self.le_width.setEnabled(False)
        self.le_height.setEnabled(False)

        data = ODCropData(
            self._data_path,
            bboxes=self.canvas_crop.all_crop_bboxes(),
            angles=angles[self.cb_angle.currentIndex()]
        )

        self.le_crop_info.setText('')
        self.bar_extract.setTextVisible(True)
        paths = glob(str(data.im_path.joinpath('*.png')))
        for i, path in enumerate(paths):
            data.extract(path)
            self.bar_extract.setValue(int(round((i+1)/len(paths)*100)))
        data.split()
        self.bar_extract.setValue(0)
        self.bar_extract.setTextVisible(False)
        self.le_crop_info.setText('Completed !')

        self.pb_save.setEnabled(True)
        self.cb_angle.setEnabled(True)
        self.le_width.setEnabled(True)
        self.le_height.setEnabled(True)
