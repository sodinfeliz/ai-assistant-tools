import cv2
import numpy as np
from typing import Tuple

try:
    from osgeo import gdal
    from osgeo import gdalconst
except ImportError:
    import gdal
    import gdalconst


def load_image(im_path: str, pixel_size: float) -> Tuple[gdal.Dataset, np.ndarray, float, tuple]:
    raster = gdal.Open(str(im_path))
    trans = raster.GetGeoTransform()
    raster = _pixel_sz_trans(raster, pixel_size)

    org_im = raster.ReadAsArray()[:3]
    org_im = np.moveaxis(org_im, 0, -1)[..., ::-1]
    im_shape = (raster.RasterYSize, raster.RasterXSize)

    # resize by the size limitation
    size_limit = 16000
    max_len = max(org_im.shape[:2])
    im_factor = size_limit / max_len if max_len > size_limit else 1
    im = cv2.resize(org_im, (int(im_shape[1] * im_factor),
                             int(im_shape[0] * im_factor)))

    return raster, im, im_factor, trans


def _pixel_sz_trans(ds: gdal.Dataset, ps: float) -> gdal.Dataset:
    """ Resize the image by pixel size. """

    ds_trans = ds.GetGeoTransform()
    factor = ds_trans[1] / ps

    if list(ds_trans)[:2] == [0.0, 1.0] or round(factor, 2) == 1: 
        return ds

    ds_proj = ds.GetProjection()
    ds_dtype = ds.GetRasterBand(1).DataType
    width, height = ds.RasterXSize, ds.RasterYSize
    
    ts_trans = list(ds_trans)
    ts_trans[1] = ps
    ts_trans[5] = -ps

    mem_drv = gdal.GetDriverByName('MEM')
    dst_ds = mem_drv.Create('', 
        int(width * factor), 
        int(height * factor), 
        ds.RasterCount, ds_dtype)
    dst_ds.SetProjection(ds_proj)
    dst_ds.SetGeoTransform(ts_trans)
    gdal.ReprojectImage(ds, dst_ds, ds_proj, ds_proj, gdalconst.GRA_CubicSpline)

    return dst_ds
