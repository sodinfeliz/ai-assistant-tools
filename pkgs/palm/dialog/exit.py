from PyQt5.QtGui import *
from PyQt5.QtWidgets import QMessageBox


def exit_dialog():
    msg_box = QMessageBox()
    msg_box.setWindowIcon(QIcon('GUIImg/python.png'))
    msg_box.setWindowTitle('Exit the Process')
    msg_box.setIcon(QMessageBox.NoIcon)
    msg_box.setText("Save the changes ?")
    #msg_box.setInformativeText("Do you want to save your changes?");
    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg_box.setDefaultButton(QMessageBox.Yes)
    ret = msg_box.exec()
    return ret

