#from program_viewer import main
from PyQt5 import QtCore, QtWidgets
import sys
import os
from program_viewer import ApplicationWindow


if __name__ == "__main__":
    import time
    app = QtWidgets.QApplication(sys.argv)
    application = ApplicationWindow()
    application.show()
    sys.exit(app.exec_())
