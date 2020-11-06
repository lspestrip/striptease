#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from typing import List
from pathlib import Path

from PyQt5 import QtCore, QtWidgets, uic
from postmortem_viewer.ui import Ui_mainWindow
import striptease as st


class ApplicationWindow(QtWidgets.QMainWindow):
    """Main window class"""

    def __init__(self):
        "Initialize the user interface and scan the folder containing HDF5 files"
        super(ApplicationWindow, self).__init__()

        self.settings = QtCore.QSettings("Strip", "post-mortem-viewer")

        self.hdf5_files = []  # type: List[st.DataFile]

        ui = Ui_mainWindow()
        self.ui = ui
        ui.setupUi(self)

        ui.action_Set_data_directory.triggered.connect(self.query_data_path)
        ui.action_Quit.triggered.connect(self.close)

        ui.calendarWidget.selectionChanged.connect(self.refresh_view)

        self.set_data_path(self.settings.value("data_path", "."))

        self.board_check_boxes = {
            "I": ui.checkBox_I,
            "G": ui.checkBox_G,
            "B": ui.checkBox_B,
            "V": ui.checkBox_V,
            "R": ui.checkBox_R,
            "O": ui.checkBox_O,
            "Y": ui.checkBox_Y,
        }

    def query_data_path(self):
        "Ask the user to provide a new path for HDF5 files"

        if self.data_path:
            start_folder = self.data_path
        else:
            start_folder = ""

        new_folder = QtWidgets.QFileDialog.getExistingDirectory(
            parent=None, caption="Choose the data folder", directory=str(start_folder),
        )
        if new_folder:
            self.set_data_path(new_folder)
            self.refresh_view()

    def set_data_path(self, folder):
        "Refresh the list of HDF5 files"

        self.data_path = Path(folder)
        self.hdf5_files = st.scan_data_path(self.data_path)

        # Save the current folder in the settings file
        self.settings.setValue("data_path", str(self.data_path))

    def refresh_view(self):
        "Update the main window when a new date is selected on the calendar"

        current_date = self.ui.calendarWidget.selectedDate()
        # First element *must* be a datetime, second element a QDate!!
        match_fn = (
            lambda x, y: (x.year == y.year())
            and (x.month == y.month())
            and (x.day == y.day())
        )

        # Find the set of files that were acquired on the date
        # currently selected in the calendar widget
        daily_files = [x for x in self.hdf5_files if match_fn(x.datetime, current_date)]

        # Find which boards were acquired during the selected date
        boards = set()
        for cur_file in daily_files:
            boards = boards.union(cur_file.boards)

        # Refresh the board checkboxes
        for elem in self.board_check_boxes.keys():
            self.board_check_boxes[elem].setChecked(elem in boards)
