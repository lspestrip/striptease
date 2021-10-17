# program_viewer.py --- standard main for Qt5 application
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it
from PyQt5 import QtWidgets
import sys
from program_viewer import ApplicationWindow

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    application = ApplicationWindow()
    application.show()
    ec = app.exec_()
    print("Closing application")
    application.stop()
    sys.exit(ec)
