import cv2
import gdal
import numpy as np
import shutil
import random
from typing import Union
from tqdm import tqdm
from pathlib import Path
from skimage.util.shape import view_as_windows


class DatasetProducing(object):

    def __init__(self, raster: gdal.Dataset, 
                       pos: np.ndarray,
                       reso: float, 
                       n_class: int=None, 
                       seed: int=None, 
                       alpha: float=0.6):
        """ Initialization

        # Args:
            raster (gdal.Dataset): image
            n_class (int, optional): class number. Defaults to None.
            seed (int, optional): random seed. Defaults to None.
            alpha (float, optional): blending alpha value.
        """
        super().__init__()
        assert 0 <= alpha <= 1
        
        self.ds = raster
        self.pos = pos
        self.reso = reso
        self.n_class = n_class

        # image and label visualization
        np.random.seed(seed if seed is not None else np.random.randint(2**31))
        self.lb_color = np.random.randint(256, size=(self.n_class, 3))
        self.alpha = alpha

    def split(self, size: int, ratio: float, filter: tuple=None, windows: np.ndarray=None):
        """Splitting the images into blocks

        # Args:
            size (int): block size
            ratio (float): overlapping ratio
            filter (tuple, optional): coverage ratio lower/upper bound. (Defaults to None.)
        """
        height, width = self.ds.RasterYSize, self.ds.RasterXSize
        stride = int(size * (1 - ratio))

        assert size <= height and size <= width
        assert 0 <= ratio < 1

        self.im_tiles = np.empty((0, size, size, 3), dtype=np.uint8)
        self.lb_tiles = np.empty((0, size, size), dtype=np.uint8)

        if len(windows):
            for win in windows:
                coords = self._win_size_trim(win, width, height)
                im, lb = self._label_image_generate(coords)
                _im = view_as_windows(im, (size, size, 3), stride)
                self.im_tiles = np.concatenate((self.im_tiles, _im.reshape(-1, *(size, size, 3))))
                _lb = view_as_windows(lb, (size, size), stride)
                self.lb_tiles = np.concatenate((self.lb_tiles, _lb.reshape(-1, *(size, size))))
        else:
            im, lb = self._label_image_generate()
            self.im_tiles = view_as_windows(im, (size, size, 3), stride)
            self.im_tiles = self.im_tiles.reshape(-1, *(size, size, 3))
            self.lb_tiles = view_as_windows(lb, (size, size), stride)
            self.lb_tiles = self.lb_tiles.reshape(-1, *(size, size))

        if filter is not None:
            assert len(filter) == 2
            self._filter_by_coverage(filter)

    def save(self, split_ratio: float=0.8, filename: str='', save_dir: Union[str, Path]=''):
        assert isinstance(save_dir, (str, Path)) or save_dir is None
        assert 0.5 <= split_ratio <= 1, "Split Ratio must in rnage [0.5, 1]."

        self.save_dir = Path(save_dir) if save_dir else Path.cwd()
        self.save_dir = self.save_dir.joinpath('PascalVOC')
        if self.save_dir.exists(): shutil.rmtree(str(self.save_dir))

        self.save_dir.joinpath('JPEGImages').mkdir(parents=True)
        self.save_dir.joinpath('SegmentationClass').mkdir(parents=True)
        self.save_dir.joinpath('VisualImages').mkdir(parents=True)

        idx, fns = 0, []
        with tqdm(total=len(self.im_tiles)) as pbar:
            for im, lb in zip(self.im_tiles, self.lb_tiles):
                if np.max(im) == 0: continue
                vs = self._label_visualization(im, lb)
                fns.append(f'{filename}_{idx}')
                cv2.imwrite(str(self.save_dir.joinpath('JPEGImages', f'{fns[-1]}.png')), im)
                cv2.imwrite(str(self.save_dir.joinpath('SegmentationClass', f'{fns[-1]}.png')), lb)
                cv2.imwrite(str(self.save_dir.joinpath('VisualImages', f'{fns[-1]}.png')), vs)
                idx += 1
                pbar.update(1)

        self.save_train_val(fns, split_ratio)

    def save_train_val(self, fns: list, ratio: float):
        """ Splitting the training and validation
        data through image name by specified ratio

        # Args:
            fns (list): filenames
            ratio (float): train and validation split ratio
        """
        det_dir = self.save_dir.joinpath('ImageSets/Segmentation')
        det_dir.mkdir(parents=True)

        train_num = int(len(fns) * ratio)
        random.shuffle(fns)
        with open(str(det_dir.joinpath('train.txt')), 'w') as file:
            file.writelines('\n'.join(fns[:train_num]))
        with open(str(det_dir.joinpath('val.txt')), 'w') as file:
            file.writelines('\n'.join(fns[train_num:]))

    def _filter_by_coverage(self, filter: tuple):
        """ Filter the mask by coverage """
        l_b, u_b = filter
        assert 0 <= l_b < u_b <= 1

        def coverage_ratio(mask):
            if np.max(mask) == 0: return 0
            area = mask.shape[0] * mask.shape[1]
            return np.count_nonzero(mask)/area

        new_im_tiles = []
        new_lb_tiles = []

        for im, lb in zip(self.im_tiles, self.lb_tiles):
            if l_b <= coverage_ratio(lb) <= u_b:
                new_im_tiles.append(im)
                new_lb_tiles.append(lb)

        self.im_tiles = np.array(new_im_tiles).astype('uint8')
        self.lb_tiles = np.array(new_lb_tiles).astype('uint8')

    def _label_visualization(self, im, lb):
        vs = np.zeros_like(im)
        for lb_class in range(self.n_class):
            vs[lb == lb_class] = self.lb_color[lb_class]
        vs[lb == 0] = im[lb == 0]
        return (vs*self.alpha + im*(1-self.alpha)).astype('uint8')

    def _win_size_trim(self, win, width, height):
        x1, y1, x2, y2 = win
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(width, x2)
        y2 = min(height, y2)
        return x1, y1, x2 ,y2

    def _label_image_generate(self, coords: list=None):
        palm_radius = 1.5 # unit: meter

        if coords is None: 
            im = self.ds.ReadAsArray()[:3]
            im = np.moveaxis(im, 0, -1)[..., ::-1]
            lb = np.zeros((self.ds.RasterYSize, self.ds.RasterXSize), dtype='uint8')
            for x, y in self.pos:
                cv2.circle(lb, (x, y), 
                    int(palm_radius / self.reso), 
                    (1,), -1, cv2.LINE_AA)
        else:
            x1, y1, x2, y2 = list(map(int, coords))
            x_in_range = np.logical_and(self.pos[:,0] >= x1, self.pos[:,0] < x2)
            y_in_range = np.logical_and(self.pos[:,1] >= y1, self.pos[:,1] < y2)
            pos_in_win = self.pos[np.logical_and(x_in_range, y_in_range)]

            im = self.ds.ReadAsArray(x1, y1, x2-x1, y2-y1)[:3]
            im = np.moveaxis(im, 0, -1)[..., ::-1]
            lb = np.zeros((y2 - y1, x2 - x1), dtype='uint8')

            for x, y in pos_in_win:
                cv2.circle(lb, (x-x1, y-y1), 
                    int(palm_radius / self.reso), 
                    (1,), -1, cv2.LINE_AA)

        return im, lb


if __name__ == "__main__":
    im = cv2.imread('_1.tif', -1)
    mask = (cv2.imread('_1_mask.png', -1) / 255).astype('uint8')
    db = DatasetProducing(im, mask)
    db.split(800, 0.9)
    db.save(filename='_1')

