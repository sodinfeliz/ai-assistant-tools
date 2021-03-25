

import json
import gdal
import ogr
from pathlib import Path
from shapely.geometry.polygon import Polygon


def shppoly_extract(path, filter: Polygon=None):
    """  loading shapefile then parsing, converting
    it into shapely.geometry.polygon.Polygon

    # Args:
        path (str): shapeile (.shp) path
        filter (Polygon, optional): Filtering Region. Defaults to None.

    # Returns:
        list of Polygon
    """
    file = ogr.Open(str(path))
    shape = file.GetLayer(0)
    polys = []
    
    for i in range(len(shape)):
        feature = shape.GetFeature(i)
        first = json.loads(feature.ExportToJson())
        if first['geometry'] is None: continue
            
        poly_type = first['geometry']['type']
        if poly_type not in ('MultiPolygon', 'Polygon'): continue
        
        coords = first['geometry']['coordinates'] 
        if poly_type == 'Polygon': coords = [coords]        
        for coord in coords:
            poly = Polygon(coord[0])
            if filter and not filter.contains(poly): continue
            polys.append(poly)
            
    return polys


def rgnshp_generate(ipath, tfw=None):
    """ Generating the corresponding
    geographic region of ipath only
    .tif extension accepted

    # Args:
        ipath (str, Path): image path
        tfw (tuple, optional): Geographicc information. Defaults to None.

    # Returns:
        shapely.Polygon instantiation
    """
    ds = gdal.Open(str(ipath))
    if tfw is None: 
        assert  Path(ipath).suffix == '.tif'
        tfw = ds.GetGeoTransform()

    lt = (tfw[0], tfw[3]) # left top cood
    rb = (tfw[0]+tfw[1]*ds.RasterXSize, tfw[3]+tfw[5]*ds.RasterYSize) # right bottom coord
    return Polygon([lt, (rb[0], lt[1]), rb, (lt[0], rb[1])])


