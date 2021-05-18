import sys
import signal
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from pkgs.palm.main import palmGUI

app = None


def signal_handler(signum, stack):
    sys.exit(app.exec_())


def signal_setting(func):
    signal.signal(signal.SIGTERM, func)
    signal.signal(signal.SIGINT, func)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setOverrideCursor(Qt.ArrowCursor)
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    QFontDatabase.addApplicationFont("GUI/Merriweather-Regular.ttf")
    widget = palmGUI()
    sys.exit(app.exec_())
