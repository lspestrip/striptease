# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created by: PyQt5 UI code generator 5.12.3
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtWidgets


class Ui_mainWindow(object):
    def setupUi(self, mainWindow):
        mainWindow.setObjectName("mainWindow")
        mainWindow.resize(800, 721)
        self.centralwidget = QtWidgets.QWidget(mainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.calendarWidget = QtWidgets.QCalendarWidget(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.calendarWidget.sizePolicy().hasHeightForWidth()
        )
        self.calendarWidget.setSizePolicy(sizePolicy)
        self.calendarWidget.setMinimumDate(QtCore.QDate(2019, 1, 1))
        self.calendarWidget.setMaximumDate(QtCore.QDate(2021, 12, 31))
        self.calendarWidget.setGridVisible(False)
        self.calendarWidget.setHorizontalHeaderFormat(
            QtWidgets.QCalendarWidget.ShortDayNames
        )
        self.calendarWidget.setVerticalHeaderFormat(
            QtWidgets.QCalendarWidget.NoVerticalHeader
        )
        self.calendarWidget.setNavigationBarVisible(True)
        self.calendarWidget.setDateEditEnabled(True)
        self.calendarWidget.setObjectName("calendarWidget")
        self.verticalLayout_2.addWidget(self.calendarWidget)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.checkBox_I = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_I.setEnabled(False)
        self.checkBox_I.setObjectName("checkBox_I")
        self.verticalLayout.addWidget(self.checkBox_I)
        self.checkBox_G = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_G.setEnabled(False)
        self.checkBox_G.setObjectName("checkBox_G")
        self.verticalLayout.addWidget(self.checkBox_G)
        self.checkBox_B = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_B.setEnabled(False)
        self.checkBox_B.setObjectName("checkBox_B")
        self.verticalLayout.addWidget(self.checkBox_B)
        self.checkBox_V = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_V.setEnabled(False)
        self.checkBox_V.setCheckable(True)
        self.checkBox_V.setChecked(False)
        self.checkBox_V.setObjectName("checkBox_V")
        self.verticalLayout.addWidget(self.checkBox_V)
        self.checkBox_R = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_R.setEnabled(False)
        self.checkBox_R.setObjectName("checkBox_R")
        self.verticalLayout.addWidget(self.checkBox_R)
        self.checkBox_O = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_O.setEnabled(False)
        self.checkBox_O.setObjectName("checkBox_O")
        self.verticalLayout.addWidget(self.checkBox_O)
        self.checkBox_Y = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_Y.setEnabled(False)
        self.checkBox_Y.setObjectName("checkBox_Y")
        self.verticalLayout.addWidget(self.checkBox_Y)
        spacerItem = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.verticalLayout.addItem(spacerItem)
        self.horizontalLayout.addLayout(self.verticalLayout)
        self.graphicsView = QtWidgets.QGraphicsView(self.centralwidget)
        self.graphicsView.setObjectName("graphicsView")
        self.horizontalLayout.addWidget(self.graphicsView)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        mainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(mainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 30))
        self.menubar.setObjectName("menubar")
        self.menu_File = QtWidgets.QMenu(self.menubar)
        self.menu_File.setObjectName("menu_File")
        mainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(mainWindow)
        self.statusbar.setObjectName("statusbar")
        mainWindow.setStatusBar(self.statusbar)
        self.action_Set_data_directory = QtWidgets.QAction(mainWindow)
        self.action_Set_data_directory.setObjectName("action_Set_data_directory")
        self.action_Quit = QtWidgets.QAction(mainWindow)
        self.action_Quit.setObjectName("action_Quit")
        self.menu_File.addAction(self.action_Set_data_directory)
        self.menu_File.addSeparator()
        self.menu_File.addAction(self.action_Quit)
        self.menubar.addAction(self.menu_File.menuAction())

        self.retranslateUi(mainWindow)
        QtCore.QMetaObject.connectSlotsByName(mainWindow)
        mainWindow.setTabOrder(self.calendarWidget, self.checkBox_I)
        mainWindow.setTabOrder(self.checkBox_I, self.checkBox_G)
        mainWindow.setTabOrder(self.checkBox_G, self.checkBox_B)
        mainWindow.setTabOrder(self.checkBox_B, self.checkBox_V)
        mainWindow.setTabOrder(self.checkBox_V, self.checkBox_R)
        mainWindow.setTabOrder(self.checkBox_R, self.checkBox_O)
        mainWindow.setTabOrder(self.checkBox_O, self.checkBox_Y)
        mainWindow.setTabOrder(self.checkBox_Y, self.graphicsView)

    def retranslateUi(self, mainWindow):
        _translate = QtCore.QCoreApplication.translate
        mainWindow.setWindowTitle(_translate("mainWindow", "MainWindow"))
        self.checkBox_I.setText(_translate("mainWindow", "I module"))
        self.checkBox_G.setText(_translate("mainWindow", "G module"))
        self.checkBox_B.setText(_translate("mainWindow", "B module"))
        self.checkBox_V.setText(_translate("mainWindow", "V module"))
        self.checkBox_R.setText(_translate("mainWindow", "R module"))
        self.checkBox_O.setText(_translate("mainWindow", "O module"))
        self.checkBox_Y.setText(_translate("mainWindow", "Y module"))
        self.menu_File.setTitle(_translate("mainWindow", "&File"))
        self.action_Set_data_directory.setText(
            _translate("mainWindow", "&Set data directory…")
        )
        self.action_Quit.setText(_translate("mainWindow", "&Quit"))
