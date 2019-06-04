from widgets.plot.pol import PolMplCanvas
from PyQt5 import QtCore, QtGui, QtWidgets
from program_turnon.ui.main_window import Ui_MainWindow

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
