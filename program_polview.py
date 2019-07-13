from PyQt5 import QtCore, QtWidgets
import sys
import os
from program_polview import ApplicationWindow
import asyncio
from threading import Thread

if __name__ == "__main__":
    import time
    app = QtWidgets.QApplication(sys.argv)
    application = ApplicationWindow()
    application.show()
    ec = app.exec_()
    print("Closing application")
    application.stop()
    sys.exit(ec)
