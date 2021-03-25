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
from ..item import LabelCanvas, RectItemHandle
from ..style.pbutton import push_button_setting


classes = {'vehicle', 'bus', 'truck'}


def coords_correlated(coords, w, h):
    """
    # Arguments:
        coords: (xmin, ymin, xmax, ymax)
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


class bnboxUI(QWidget):    
    def __init__(self, parent=None):
        super(bnboxUI, self).__init__(parent)
        loadUi('GUI/widget_bnbox.ui', self)

        self._data_path = None
        self._push_button_setup()

        geometry = self.canvas.geometry()
        self.canvas = LabelCanvas(self, geometry)
        self.canvas.setViewportUpdateMode(0)
        self.canvas.clear_items()

        self.le_new_class.returnPressed.connect(self.add_new_class)
        self.le_current_frame.setText('- ')
        self.le_total_frame.setText('/ -')
        self.canvas.add_item_signal.connect(self.add_item_by_drag)
        self.canvas.delete_item_signal.connect(self.delete_item_by_click)

        for c in classes: self.cb_label.addItem(c)
        self.cb_label.setInsertPolicy(3)
        self.cb_label.setCurrentIndex(-1)

        QShortcut(Qt.Key_Left, self, self.prev_frame)
        QShortcut(Qt.Key_Right, self, self.next_frame)


    def _icon_setting(self):
        '''
        self.pb_return.setIcon(QIcon('./GUIImg/pb-home.png'))
        self.pb_repeat.setIcon(QIcon('./GUIImg/pb-repeat.png'))
        self.pb_openfile.setIcon(QIcon('./GUIImg/pb-computer-folder.png'))
        self.pb_save.setIcon(QIcon('./GUIImg/pb-save.png'))
        self.pb_prev_frame.setIcon(QIcon('./GUIImg/pb-arrow-left.png'))
        self.pb_next_frame.setIcon(QIcon('./GUIImg/pb-arrow-right.png'))
        '''

    def add_item_by_drag(self, pos):
        if self.canvas.hasPhoto():
            x, y = pos.x(), pos.y()
            item = RectItemHandle(x, y, 1, 1)
            item.setLabel(self.cb_label.currentText())

            index = int(self.le_current_frame.text())
            self._all_bnboxes[index].append(item)
            self.canvas.add_item_to_scene(item)
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
                self.canvas.delete_item_on_scene(it)
                self.item_changed()
                break


    def delete_item_by_signal(self, it):
        del self._all_bnboxes[int(self.le_current_frame.text())][-1]
        self.canvas.delete_item_on_scene(it)


    def file_open(self, ignore=False):
        """
        Open the file manager to open the directory
        """
        dir_name = {
            'origin': ['images', 'bnboxes', 'png'],
            'PascalVOC': ['JPEGImages', 'Annotations', 'jpg']
        }

        if self._data_path is None or self.canvas.hasPhoto():
            self._data_path = Path(QFileDialog.getExistingDirectory(self, 'Open File'))
            self._filename = self._data_path.stem
            dir_check = dir_name['PascalVOC'] if self._filename == 'PascalVOC' else dir_name['origin']
        else:
            self._filename = self._data_path.stem
            self._data_path = self._data_path.joinpath('PascalVOC')
            dir_check = dir_name['PascalVOC']
        
        if self._data_path and np.setdiff1d(dir_check[:2], os.listdir(self._data_path)).size == 0:
            self._im_dir = self._data_path.joinpath(dir_check[0])
            self._im_path = glob(str(self._im_dir.joinpath(f'*.{dir_check[2]}')))
            self._bnb_dir = self._data_path.joinpath(dir_check[1])
            self._bnb_path = glob(str(self._bnb_dir.joinpath('*.xml')))
            self.thread_load_im_to_scene()         
        elif not ignore:
            warning_msg('Invalid directory !')


    def thread_load_im_to_scene(self):
        loading_thread = threading.Thread(target=self.load_im_to_scene)
        loading_thread.start()
        loading_thread.join()


    def reload_im_to_scene(self):
        if self.canvas.hasPhoto():
            self.load_im_to_scene()


    def load_im_to_scene(self):
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

            self.canvas.setPhoto(self._im_path[0])
            self.canvas.clear_items()
            self.load_bndox_to_scene(index=0)

        self.pb_add_class.setEnabled(True)
        self.pb_next_frame.setEnabled(True)
        self.le_new_class.setEnabled(True)
        self.pb_openfile.setEnabled(True)
        self.cb_label.setEnabled(True)
        self.cb_label.setCurrentIndex(0)
        

    def load_bndox_to_scene(self, index=0):
        for it in self._all_bnboxes[index]:
            self.canvas.add_item_to_scene(it)


    def item_changed(self):
        index =  int(self.le_current_frame.text())
        self.saved[index] = 1
        self.le_current_frame.setText(f'{index}')
        self.pb_save.setEnabled(True)


    def prev_frame(self):
        index = int(self.le_current_frame.text()) - 1
        if index < 0: return

        self.canvas.clear_items()
        self.pb_next_frame.setEnabled(True)
        self.le_current_frame.setText(f'{index}')
        self.canvas._photo.setPixmap(QPixmap(self._im_path[index]))
        if index == 0:
            self.pb_prev_frame.setEnabled(False)
        self.load_bndox_to_scene(index=index)
        

    def next_frame(self):
        index = int(self.le_current_frame.text()) + 1
        if index >= len(self._im_path): return

        self.canvas.clear_items()
        self.pb_prev_frame.setEnabled(True)
        self.le_current_frame.setText(f'{index}')
        self.canvas._photo.setPixmap(QPixmap(self._im_path[index]))
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


    def _push_button_setup(self):
        self.pb_openfile.clicked.connect(self.file_open)
        self.pb_return.setShortcut('Home')
        self.pb_repeat.clicked.connect(self.reload_im_to_scene)
        self.pb_repeat.setShortcut('F2')
        self.pb_save.clicked.connect(self.save_data)
        self.pb_save.setShortcut('Ctrl+S')
        self.pb_add_class.clicked.connect(self.add_new_class)
        self.pb_prev_frame.clicked.connect(self.prev_frame)
        self.pb_next_frame.clicked.connect(self.next_frame)


