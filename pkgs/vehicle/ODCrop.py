import cv2
import shutil
import numpy as np
import xml.etree.ElementTree as ET
from pascal_voc_writer import Writer
from glob import glob
from pathlib import Path


def _dir_create(path, delete=False):
    path = Path(path)
    if path.exists(): 
        shutil.rmtree(str(path))
    path.mkdir(parents=True)


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


def subbbox_extract(img, objects, bbox=None):
    if bbox is None:
        bbox = [0, 0, img.shape[1], img.shape[0]]
        
    im_orgn = img[bbox[1]:bbox[3], bbox[0]:bbox[2]].copy()
    result = im_orgn.copy()
    result_objects = []
    
    for obj in objects:
        xmin, ymin, xmax, ymax = obj['bbox']
        if xmin > bbox[2] or xmax < bbox[0] or ymin > bbox[3] or ymax < bbox[1]: continue

        xmin, ymin = max(xmin, bbox[0]) - bbox[0], max(ymin, bbox[1]) - bbox[1]
        xmax, ymax = min(xmax, bbox[2]) - bbox[0], min(ymax, bbox[3]) - bbox[1]

        # filtering the tiny rectangle
        if xmax - xmin <= 10 or ymax - ymin <= 10: continue
            
        cv2.rectangle(result, (xmin, ymin), (xmax, ymax), (0, 0, 255), 2)
        temp_obj = obj.copy()
        temp_obj['bbox'] = [xmin+1, ymin+1, xmax+1, ymax+1]
        result_objects.append(temp_obj)
        
    return im_orgn, result, result_objects


def train_test_split(all_fn, dir, ratio):
    assert 0 < ratio  < 1
    train_num = int(len(all_fn) * (1 - ratio))
    
    train_fn = np.random.choice(all_fn, train_num, replace=False)
    train_fn.sort()
    test_fn = np.setdiff1d(all_fn, train_fn)
    test_fn.sort()

    with open(str(Path(dir).joinpath('trainval.txt')), 'w') as f:
        f.writelines('\n'.join(all_fn))
    with open(str(Path(dir).joinpath('train.txt')), 'w') as f:
        f.writelines('\n'.join(train_fn))
    with open(str(Path(dir).joinpath('val.txt')), 'w') as f:
        f.writelines('\n'.join(test_fn))


class ODCropData:

    def __init__(self, data_path, bboxes, angles=None):
        self.data_path = Path(data_path)
        self.filename = self.data_path.stem
        self.im_path = self.data_path.joinpath('images')
        self.bnb_path = self.data_path.joinpath('bnboxes')
        self.out_im = self.data_path.joinpath('PascalVOC/JPEGImages')
        self.out_bb = self.data_path.joinpath('PascalVOC/Annotations')
        self.out_vs = self.data_path.joinpath('PascalVOC/VisualImages')
        _dir_create(self.out_im, delete=True)
        _dir_create(self.out_bb, delete=True)
        _dir_create(self.out_vs, delete=True)
        self.extract_bboxes = bboxes
        self.angles = [0] if angles is None else angles
        self.all_filename = []


    def extract(self, path):
        path = Path(path)
        im = cv2.imread(str(path))
        objects = parse_rec(self.bnb_path.joinpath(f'{path.stem}.xml'))
        scale_lower = 1 if len(self.angles) == 1 else 0.8

        for bbid, ebbox in enumerate(self.extract_bboxes):
            center = self._compute_center_by_bbox(ebbox)

            for aid, angle in enumerate(self.angles):
                scale = np.random.uniform(scale_lower, 1.0)
                M = cv2.getRotationMatrix2D(center, angle, scale)
                rotated_im = cv2.warpAffine(im, M, (im.shape[1], im.shape[0]))
                rotated_ob = self._affine_objects(M, objects)

                sub_im_fn = f'{path.stem}_{bbid}_{aid}'
                sub_im_path = self.out_im.joinpath(f'{sub_im_fn}.jpg')
                sub_im_orgn, sub_im_visual, sub_objects = subbbox_extract(rotated_im, rotated_ob, ebbox)
                self.all_filename.append(sub_im_fn)

                cv2.imwrite(str(sub_im_path), sub_im_orgn)
                cv2.imwrite(str(self.out_vs.joinpath(f'{sub_im_fn}.jpg')), sub_im_visual)

                writer = Writer(str(sub_im_path), sub_im_orgn.shape[1], sub_im_orgn.shape[0])
                for obj in sub_objects:
                    writer.addObject(obj['name'], *obj['bbox'])
                writer.save(str(self.out_bb.joinpath(f'{sub_im_fn}.xml')))


    def split(self, ratio=0.05):
        if self.filename:
            out_db = self.data_path.joinpath('PascalVOC/ImageSets/Main')
            _dir_create(out_db, delete=True)
            train_test_split(self.all_filename, out_db, ratio=ratio)
            return True
        return False


    def extract_all(self):
    
        paths = glob(str(self.im_path.joinpath('*.png')))
        for path in paths:
            path = Path(path)
            im = cv2.imread(str(path))
            objects = parse_rec(self.bnb_path.joinpath(f'{path.stem}.xml'))

            for bbid, ebbox in enumerate(self.extract_bboxes):
                center = self._compute_center_by_bbox(ebbox)

                for aid, angle in enumerate(self.angles):
                    scale = np.random.uniform(0.8, 1.0)
                    M = cv2.getRotationMatrix2D(center, angle, scale)
                    rotated_im = cv2.warpAffine(im, M, (im.shape[1], im.shape[0]))
                    rotated_ob = self._affine_objects(M, objects)

                    sub_im_fn = f'{path.stem}_{bbid}_{aid}'
                    sub_im_path = self.out_im.joinpath(f'{sub_im_fn}.jpg')
                    sub_im_orgn, sub_im_visual, sub_objects = subbbox_extract(rotated_im, rotated_ob, ebbox)
                    self.all_filename.append(sub_im_fn)

                    cv2.imwrite(str(sub_im_path), sub_im_orgn)
                    cv2.imwrite(str(self.out_vs.joinpath(f'{sub_im_fn}.jpg')), sub_im_visual)

                    writer = Writer(str(sub_im_path), sub_im_orgn.shape[1], sub_im_orgn.shape[0])
                    for obj in sub_objects:
                        writer.addObject(obj['name'], *obj['bbox'])
                    writer.save(str(self.out_bb.joinpath(f'{sub_im_fn}.xml')))

        out_db = self.data_path.joinpath('PascalVOC/ImageSets/Main')
        _dir_create(out_db, delete=True)
        train_test_split(self.all_filename, out_db, ratio=0.05)


    def _compute_center_by_bbox(self, bbox):
        return (int((bbox[0] + bbox[2])/2), int((bbox[1] + bbox[3])/2))


    def _affine_objects(self, M, objects):
        aObjects = []

        for obj in objects:
            xmin, ymin, xmax, ymax = obj['bbox']
            coords = np.array([[xmin, ymin], [xmin, ymax], [xmax, ymin], [xmax, ymax]])   
            for i, coord in enumerate(coords):
                coords[i] = np.matmul(M, np.hstack((coord, [1])))

            temp_obj = obj.copy()
            temp_obj['bbox'] = [min(coords[:, 0]), min(coords[:, 1]), max(coords[:, 0]), max(coords[:, 1])]
            aObjects.append(temp_obj)

        return aObjects


if __name__ == '__main__':
    filename = 'C05-04'
    ODCropData(filename)
