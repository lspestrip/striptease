#from program_viewer import main
from PyQt5 import QtCore, QtWidgets
import sys
import os
from program_viewer.ui.main_window import Ui_MainWindow

progname = os.path.basename(sys.argv[0])
qApp = QtWidgets.QApplication(sys.argv)

#aw = ApplicationWindow()
#aw.setWindowTitle("%s" % progname)
#aw.show()
#sys.exit(qApp.exec_())



class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(ApplicationWindow, self).__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)


def main():
    app = QtWidgets.QApplication(sys.argv)
    application = ApplicationWindow()
    application.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
