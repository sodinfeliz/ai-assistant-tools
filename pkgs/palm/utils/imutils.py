import cv2
import numpy as np
from numpy.core.fromnumeric import size

try:
    from osgeo import gdal
except ImportError:
    import gdal


def resize_image(im_path, pixel_size):
    tfw = gdal.Open(str(im_path)).GetGeoTransform()
    org_im = cv2.imread(str(im_path), -1)[..., :3]
    im_shape = np.array(org_im.shape[:2])

    # resize the image into resolution `pixel_size`
    im_factor = tfw[1] / pixel_size if tfw[:2] != (0, 1) else 1
    if round(im_factor, 4) != 1:
        org_im = cv2.resize(org_im, (int(im_shape[1] * im_factor),
                                     int(im_shape[0] * im_factor)))
        im_shape = np.array(org_im.shape[:2])

    # resize by the size limitation
    size_limit = 16000
    max_len = max(org_im.shape[:2])
    im_factor = size_limit / max_len if max_len > size_limit else 1
    im = cv2.resize(org_im, (int(im_shape[1] * im_factor),
                             int(im_shape[0] * im_factor)))

    return org_im, im, im_factor, tfw