# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'window.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets
from widgets.plot import MyStaticMplCanvas,MyDynamicMplCanvas

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setMaximumSize(QtCore.QSize(16777215, 12))
        self.label.setObjectName("label")
        self.gridLayout_2.addWidget(self.label, 0, 1, 1, 1)
        self.plot_dx = MyStaticMplCanvas(self.centralwidget, width=5, height=4, dpi=100)
        self.plot_dx.setObjectName("plot_dx")
        self.gridLayout_2.addWidget(self.plot_dx, 1, 1, 1, 1)
        #self.plot_sx = MyDynamicMplCanvas(self.centralwidget, width=5, height=4, dpi=100)
        #self.plot_sx.setObjectName("plot_sx")
        #elf.gridLayout_2.addWidget(self.plot_sx, 1, 0, 1, 1)
        self.combo_sx = QtWidgets.QComboBox(self.centralwidget)
        self.combo_sx.setObjectName("combo_sx")
        self.gridLayout_2.addWidget(self.combo_sx, 2, 0, 1, 1)
        self.combo_dx = QtWidgets.QComboBox(self.centralwidget)
        self.combo_dx.setObjectName("combo_dx")
        self.gridLayout_2.addWidget(self.combo_dx, 2, 1, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 13))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label.setText(_translate("MainWindow", "TextLabel"))
