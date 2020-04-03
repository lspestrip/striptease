# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'main_window.ui'
#
# Created by: PyQt5 UI code generator 5.12.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_main_window(object):
    def setupUi(self, main_window):
        main_window.setObjectName("main_window")
        main_window.resize(775, 725)
        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap("../images/turnon_icon.svg"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        main_window.setWindowIcon(icon)
        self.centralwidget = QtWidgets.QWidget(main_window)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.groupBox = QtWidgets.QGroupBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout_3.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.formLayout.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)
        self.formLayout.setObjectName("formLayout")
        self.board_label = QtWidgets.QLabel(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.board_label.sizePolicy().hasHeightForWidth())
        self.board_label.setSizePolicy(sizePolicy)
        self.board_label.setObjectName("board_label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.board_label)
        self.list_boards = QtWidgets.QComboBox(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.list_boards.sizePolicy().hasHeightForWidth())
        self.list_boards.setSizePolicy(sizePolicy)
        self.list_boards.setObjectName("list_boards")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.list_boards)
        self.channel_label = QtWidgets.QLabel(self.groupBox)
        self.channel_label.setObjectName("channel_label")
        self.formLayout.setWidget(
            1, QtWidgets.QFormLayout.LabelRole, self.channel_label
        )
        self.list_channels = QtWidgets.QComboBox(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.list_channels.sizePolicy().hasHeightForWidth()
        )
        self.list_channels.setSizePolicy(sizePolicy)
        self.list_channels.setObjectName("list_channels")
        self.formLayout.setWidget(
            1, QtWidgets.QFormLayout.FieldRole, self.list_channels
        )
        self.delay_label = QtWidgets.QLabel(self.groupBox)
        self.delay_label.setObjectName("delay_label")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.delay_label)
        self.delay_spinbox = QtWidgets.QDoubleSpinBox(self.groupBox)
        self.delay_spinbox.setDecimals(1)
        self.delay_spinbox.setMaximum(60.0)
        self.delay_spinbox.setSingleStep(0.5)
        self.delay_spinbox.setProperty("value", 0.5)
        self.delay_spinbox.setObjectName("delay_spinbox")
        self.formLayout.setWidget(
            2, QtWidgets.QFormLayout.FieldRole, self.delay_spinbox
        )
        self.verticalLayout_3.addLayout(self.formLayout)
        self.verticalLayout_5.addWidget(self.groupBox)
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.mock_run = QtWidgets.QCheckBox(self.centralwidget)
        self.mock_run.setObjectName("mock_run")
        self.horizontalLayout_6.addWidget(self.mock_run)
        spacerItem = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_6.addItem(spacerItem)
        self.start_button = QtWidgets.QPushButton(self.centralwidget)
        self.start_button.setDefault(True)
        self.start_button.setObjectName("start_button")
        self.horizontalLayout_6.addWidget(self.start_button)
        self.stop_button = QtWidgets.QPushButton(self.centralwidget)
        self.stop_button.setEnabled(False)
        self.stop_button.setObjectName("stop_button")
        self.horizontalLayout_6.addWidget(self.stop_button)
        self.pause_button = QtWidgets.QPushButton(self.centralwidget)
        self.pause_button.setEnabled(False)
        self.pause_button.setObjectName("pause_button")
        self.horizontalLayout_6.addWidget(self.pause_button)
        self.verticalLayout_5.addLayout(self.horizontalLayout_6)
        self.splitter = QtWidgets.QSplitter(self.centralwidget)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.layoutWidget = QtWidgets.QWidget(self.splitter)
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.log_label = QtWidgets.QLabel(self.layoutWidget)
        self.log_label.setObjectName("log_label")
        self.verticalLayout.addWidget(self.log_label)
        self.log_widget = QtWidgets.QTableWidget(self.layoutWidget)
        self.log_widget.setAlternatingRowColors(True)
        self.log_widget.setColumnCount(2)
        self.log_widget.setObjectName("log_widget")
        self.log_widget.setRowCount(0)
        self.verticalLayout.addWidget(self.log_widget)
        self.layoutWidget1 = QtWidgets.QWidget(self.splitter)
        self.layoutWidget1.setObjectName("layoutWidget1")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.layoutWidget1)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.command_label = QtWidgets.QLabel(self.layoutWidget1)
        self.command_label.setObjectName("command_label")
        self.verticalLayout_2.addWidget(self.command_label)
        self.commands_widget = QtWidgets.QTextBrowser(self.layoutWidget1)
        self.commands_widget.setObjectName("commands_widget")
        self.verticalLayout_2.addWidget(self.commands_widget)
        self.verticalLayout_5.addWidget(self.splitter)
        self.groupBox_2 = QtWidgets.QGroupBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_2.sizePolicy().hasHeightForWidth())
        self.groupBox_2.setSizePolicy(sizePolicy)
        self.groupBox_2.setObjectName("groupBox_2")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.groupBox_2)
        self.verticalLayout_4.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.log_message_edit = QtWidgets.QLineEdit(self.groupBox_2)
        self.log_message_edit.setObjectName("log_message_edit")
        self.verticalLayout_4.addWidget(self.log_message_edit)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem1 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout.addItem(spacerItem1)
        self.new_log_button = QtWidgets.QPushButton(self.groupBox_2)
        self.new_log_button.setObjectName("new_log_button")
        self.horizontalLayout.addWidget(self.new_log_button)
        self.verticalLayout_4.addLayout(self.horizontalLayout)
        self.verticalLayout_5.addWidget(self.groupBox_2)
        main_window.setCentralWidget(self.centralwidget)
        self.menu = QtWidgets.QMenuBar(main_window)
        self.menu.setGeometry(QtCore.QRect(0, 0, 775, 22))
        self.menu.setObjectName("menu")
        self.menuFile = QtWidgets.QMenu(self.menu)
        self.menuFile.setObjectName("menuFile")
        main_window.setMenuBar(self.menu)
        self.statusbar = QtWidgets.QStatusBar(main_window)
        self.statusbar.setObjectName("statusbar")
        main_window.setStatusBar(self.statusbar)
        self.actionload_board_file = QtWidgets.QAction(main_window)
        self.actionload_board_file.setObjectName("actionload_board_file")
        self.actionload_pol_calibration = QtWidgets.QAction(main_window)
        self.actionload_pol_calibration.setObjectName("actionload_pol_calibration")
        self.action_exit = QtWidgets.QAction(main_window)
        self.action_exit.setObjectName("action_exit")
        self.menuFile.addAction(self.actionload_board_file)
        self.menuFile.addAction(self.actionload_pol_calibration)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.action_exit)
        self.menu.addAction(self.menuFile.menuAction())
        self.board_label.setBuddy(self.list_boards)
        self.channel_label.setBuddy(self.list_channels)
        self.delay_label.setBuddy(self.delay_spinbox)

        self.retranslateUi(main_window)
        QtCore.QMetaObject.connectSlotsByName(main_window)
        main_window.setTabOrder(self.list_boards, self.list_channels)
        main_window.setTabOrder(self.list_channels, self.delay_spinbox)
        main_window.setTabOrder(self.delay_spinbox, self.mock_run)
        main_window.setTabOrder(self.mock_run, self.start_button)
        main_window.setTabOrder(self.start_button, self.stop_button)
        main_window.setTabOrder(self.stop_button, self.pause_button)
        main_window.setTabOrder(self.pause_button, self.log_widget)
        main_window.setTabOrder(self.log_widget, self.commands_widget)
        main_window.setTabOrder(self.commands_widget, self.log_message_edit)
        main_window.setTabOrder(self.log_message_edit, self.new_log_button)

    def retranslateUi(self, main_window):
        _translate = QtCore.QCoreApplication.translate
        main_window.setWindowTitle(
            _translate("main_window", "Turn on Strip polarimeters")
        )
        self.groupBox.setTitle(_translate("main_window", "Options"))
        self.board_label.setText(_translate("main_window", "&Board"))
        self.list_boards.setToolTip(
            _translate(
                "main_window",
                "<html><head/><body><p>Name of the board to turn on</p></body></html>",
            )
        )
        self.channel_label.setText(_translate("main_window", "&Channel"))
        self.delay_label.setText(
            _translate("main_window", "&Delay between commands (sec)")
        )
        self.mock_run.setStatusTip(
            _translate(
                "main_window", "If checked, no command will be sent to the webserver"
            )
        )
        self.mock_run.setText(_translate("main_window", "Dry run"))
        self.start_button.setToolTip(
            _translate(
                "main_window",
                "<html><head/><body><p>Start the turn-on procedure</p></body></html>",
            )
        )
        self.start_button.setText(_translate("main_window", "&Start"))
        self.stop_button.setText(_translate("main_window", "S&top"))
        self.pause_button.setText(_translate("main_window", "&Pause"))
        self.log_label.setText(_translate("main_window", "Log messages"))
        self.command_label.setText(_translate("main_window", "Commands"))
        self.groupBox_2.setTitle(_translate("main_window", "Create log message"))
        self.new_log_button.setText(_translate("main_window", "Cr&eate"))
        self.menuFile.setTitle(_translate("main_window", "&File"))
        self.actionload_board_file.setText(
            _translate("main_window", "Load board file…")
        )
        self.actionload_pol_calibration.setText(
            _translate("main_window", "Load &pol calibration…")
        )
        self.action_exit.setText(_translate("main_window", "&Exit"))
        self.action_exit.setShortcut(_translate("main_window", "Ctrl+Q"))
