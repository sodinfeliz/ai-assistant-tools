import cv2
import numpy as np
import shutil
import random
from pathlib import Path
from skimage.util.shape import view_as_windows


class DatasetProducing(object):

    def __init__(self, im, lb, n_class: int=None, seed: int=None, alpha=0.6) -> None:
        """ Initialization

        # Args:
            im (np.ndarray or list): image
            lb (np.ndarray or list): label
            n_class (int, optional): class number. Defaults to None.
            seed (int, optional): random seed. Defaults to None.
            alpha (float, optional): blending alpha value.
        """
        super().__init__()
        assert 0 <= alpha <= 1

        self._check_im_and_lb(im, lb)
        self._check_n_class(n_class)
        self._visualization_mask(seed, alpha)


    def _check_im_and_lb(self, im, lb):
        assert isinstance(im, (list, np.ndarray)) and \
            isinstance(lb, (list, np.ndarray))
        im, lb = np.array(im), np.array(lb)

        assert im.shape[:2] == lb.shape[:2], "Image and Lbabel shapes are inconsistent."
        assert len(im.shape) == 3 and im.shape[2] in (3, 4), "Must be RGB or RGBA Image."
        if len(lb.shape) == 3: # milti-class
            lb = np.argmax(lb, axis=2)

        self.im = im[..., :3] # extracting RGB-channels
        self.lb = lb


    def _check_n_class(self, n_class: int):
        if n_class is not None:
            assert all(np.unique(self.lb) < n_class)
        else:
            n_class = np.max(self.lb)
        self.n_class = n_class

        
    def split(self, size: int, ratio: float, filter: tuple=None):
        """Splitting the images into blocks

        # Args:
            size (int): block size
            ratio (float): overlapping ratio
            filter (tuple, optional): coverage ratio lower/upper bound. (Defaults to None.)
        """
        assert all(sz >= size for sz in self.im.shape[:2])
        assert 0 <= ratio < 1

        stride = int(size * (1 - ratio))
        self.im_tiles = view_as_windows(self.im, (size, size, 3), stride)
        self.im_tiles = self.im_tiles.reshape(-1, *(size, size, 3))
        self.vs_tiles = view_as_windows(self.vs, (size, size, 3), stride)
        self.vs_tiles = self.vs_tiles.reshape(-1, *(size, size, 3))
        self.lb_tiles = view_as_windows(self.lb, (size, size), stride)
        self.lb_tiles = self.lb_tiles.reshape(-1, *(size, size))

        if filter is not None:
            assert len(filter) == 2
            self._filter_by_coverage(filter)


    def save(self, split_ratio=0.8, filename: str='', save_dir=None):
        assert isinstance(save_dir, (str, Path)) or save_dir is None
        assert 0.5 <= split_ratio <= 1, "Split Ratio must in rnage [0.5, 1]."

        self.save_dir = Path.cwd() if save_dir is None else Path(save_dir)
        self.save_dir = self.save_dir.joinpath('PascalVOC')
        if self.save_dir.exists(): shutil.rmtree(str(self.save_dir))

        self.save_dir.joinpath('JPEGImages').mkdir(parents=True)
        self.save_dir.joinpath('SegmentationClass').mkdir(parents=True)
        self.save_dir.joinpath('VisualImages').mkdir(parents=True)

        idx, fns = 0, []
        for im, vs, lb in zip(self.im_tiles, self.vs_tiles, self.lb_tiles):
            if np.max(im) == 0: continue

            fns.append(f'{filename}_{idx}')
            cv2.imwrite(str(self.save_dir.joinpath('JPEGImages', f'{fns[-1]}.png')), im)
            cv2.imwrite(str(self.save_dir.joinpath('SegmentationClass', f'{fns[-1]}.png')), lb)
            cv2.imwrite(str(self.save_dir.joinpath('VisualImages', f'{fns[-1]}.png')), vs)
            idx += 1

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
        def coverage_ratio(mask):
            if np.max(mask) == 0: return 0
            area = mask.shape[0] * mask.shape[1]
            return np.count_nonzero(mask)/area

        new_im_tiles = []
        new_vs_tiles = []
        new_lb_tiles = []
        l_b, u_b = filter

        for im, vs, lb in zip(self.im_tiles, self.vs_tiles, self.lb_tiles):
            r = coverage_ratio(lb)
            if l_b <= r <= u_b:
                new_im_tiles.append(im)
                new_vs_tiles.append(vs)
                new_lb_tiles.append(lb)

        self.im_tiles = np.array(new_im_tiles).astype('uint8')
        self.vs_tiles = np.array(new_vs_tiles).astype('uint8')
        self.lb_tiles = np.array(new_lb_tiles).astype('uint8')


    def _visualization_mask(self, seed, alpha):
        np.random.seed(seed if seed is not None else np.random.randint(2**31))
        label_color = np.random.randint(256, size=(self.n_class, 3))
        self.vs = np.zeros_like(self.im)
        for lb_class in range(self.n_class):
            self.vs[self.lb == lb_class] = label_color[lb_class]

        self.vs[self.lb == 0] = self.im[self.lb == 0]
        self.vs = (self.vs*alpha + self.im*(1-alpha)).astype('uint8')


if __name__ == "__main__":
    im = cv2.imread('_1.tif', -1)
    mask = (cv2.imread('_1_mask.png', -1) / 255).astype('uint8')
    db = DatasetProducing(im, mask)
    db.split(800, 0.9)
    db.save(filename='_1')

