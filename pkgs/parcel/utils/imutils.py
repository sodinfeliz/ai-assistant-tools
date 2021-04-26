import cv2
import numpy as np
from pathlib import Path
from skimage.util.shape import view_as_windows

try:
    from osgeo import gdal
except ImportError:
    import gdal


def resize_image(im_path: Path, pixel_size):
    tfw = gdal.Open(str(im_path)).GetGeoTransform()
    im = cv2.imread(str(im_path), -1)
    im_shape = np.array(im.shape[:2])

    # resize the image into resolution `pixel_size`
    im_factor = round(tfw[1]/pixel_size, 4) if tfw[:2] != (0, 1) else 1
    if round(im_factor, 4) != 1:
        im = cv2.resize(im, (int(im_shape[1] * im_factor),
                             int(im_shape[0] * im_factor)))
        im_shape = np.array(im.shape[:2])

    return im, im_shape, im_factor, tfw


def crop_im_into_tiles(img, windows, wsize, overlap, factor):
    if len(img.shape) == 2:
        tsize = (wsize,)*2
    else:
        tsize = (wsize, wsize, img.shape[-1])

    tiles = []
    stride = int(wsize * (1-overlap))
    for window in windows:
        x1, y1, x2, y2 = (np.array(window) / factor).astype('int')
        tpim = img[y1: y2, x1: x2]
        try:
            tile = view_as_windows(tpim, tsize, stride).reshape(-1, *tsize)
            tiles.extend(tile)
        except:
            continue
    return tiles


def random_90_rotation(images, seed=53):
    np.random.seed(seed)
    rot = {0: cv2.ROTATE_90_CLOCKWISE, 1: cv2.ROTATE_90_COUNTERCLOCKWISE}
    result = images.copy()
    for im in images:
        rotim = cv2.rotate(im, rot[round(np.random.rand())])
        result.append(rotim)
    return result

