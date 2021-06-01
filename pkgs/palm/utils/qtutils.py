import math
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


def dist_pts(a: QPointF, b: QPointF) -> float:
    """ Calculating distance between two QPointF. """
    return math.sqrt((a.x()-b.x())**2 + (a.y()-b.y())**2)


def qpointf_to_list(pt: QPointF, dtype=float):
    if dtype is int:
        return [round(pt.x()), round(pt.y())]
    elif dtype is float:
        return [pt.x(), pt.y()]
    else:
        raise TypeError("Unsupported dtype.")
