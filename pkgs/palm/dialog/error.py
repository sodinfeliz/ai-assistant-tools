from PyQt5.QtWidgets import QMessageBox


def warning_msg(msg=''):
    file_empty = QMessageBox()
    file_empty.setIcon(QMessageBox.Warning)
    file_empty.setText(msg)
    file_empty.setWindowTitle('Warning Message')
    file_empty.setStandardButtons(QMessageBox.Ok)
    file_empty = file_empty.exec()


def critical_msg(msg=''):
    file_empty = QMessageBox()
    file_empty.setIcon(QMessageBox.Warning)
    file_empty.setText(msg)
    file_empty.setWindowTitle('Critical Message')
    file_empty.setStandardButtons(QMessageBox.Ok)
    file_empty = file_empty.exec()
