from PyQt5.QtGui import *
from PyQt5.QtWidgets import QMessageBox


def replace_shpfile_msgbox():
    msg_box = QMessageBox()
    msg_box.setWindowIcon(QIcon('GUIImg/python.png'))
    msg_box.setWindowTitle('')
    msg_box.setIcon(QMessageBox.NoIcon)
    msg_box.setText("Replace the Origin Shapefiles ?")
    #msg_box.setInformativeText("Do you want to save your changes?");
    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
    msg_box.setDefaultButton(QMessageBox.Cancel)
    ret = msg_box.exec()
    return ret

