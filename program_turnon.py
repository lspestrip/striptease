#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from collections import namedtuple
import logging as log
import os.path
import time
import sys

from config import Config
from striptease import StripConnection, StripTag

from widgets.plot.pol import PolMplCanvas
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QIcon
from program_turnon import SetupBoard
from program_turnon.ui.main_window import Ui_main_window
from striptease.biases import InstrumentBiases


class WorkerSignals(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(str)
    result = QtCore.pyqtSignal(object)
    command = QtCore.pyqtSignal(tuple)  # (index, url, dictionary)
    log = QtCore.pyqtSignal(str)
    pause = QtCore.pyqtSignal()
    resume = QtCore.pyqtSignal()
    stop = QtCore.pyqtSignal()


class Worker(QtCore.QRunnable):
    """This class implements the background thread that sends the commands
    necessary to run the turn-on procedure to the web server.

    """

    def __init__(
        self, conn, conf, board_setup, polarimeter, delay_sec=0.5, mock_run=False
    ):
        super(Worker, self).__init__()
        self.conn = conn
        self.conf = conf
        self.board_setup = board_setup
        self.paused = False
        self.must_stop = False
        self.polarimeter = polarimeter
        self.delay_sec = delay_sec
        self.mock_run = mock_run

        self.signals = WorkerSignals()
        self.signals.pause.connect(self.on_pause)
        self.signals.resume.connect(self.on_resume)
        self.signals.stop.connect(self.on_stop)

        self.biases = InstrumentBiases()
        self.command_idx = 0
        self.lock_count = 0

    def post_command(self, url, cmd):
        while self.lock_count > 0:
            time.sleep(0.1)

        self.lock_count += 1

        if self.must_stop:
            self.signals.finished.emit()
            self.must_stop = False
            self.paused = False
            self.lock_count -= 1
            return False
        self.check_pause()

        if 'level' not in cmd:
            # Only do this if the command is not a log command
            self.signals.command.emit((self.command_idx, url, cmd))
            self.command_idx += 1
            time.sleep(self.delay_sec)

        if not self.mock_run:
            result = self.conn.post(url, cmd)

            if result["status"] != "OK":
                self.signals.error.emit(f"Error executing {cmd}: {result}")
            self.lock_count -= 1
            return False

        self.lock_count -= 1
        return True

    def tag_start(self, name, comment=""):
        # Making this command share the same name and parameters as
        # StripConnection allows us to use StripTag on a Worker class
        # instead of a StripConnection object!
        self.signals.log.emit(f'Starting tag "{name}"')
        if not self.mock_run:
            self.conn.tag_start(name, comment)

    def tag_stop(self, name, comment=""):
        # See the comment for tag_stop
        self.signals.log.emit(f'Closing tag "{name}"')
        if not self.mock_run:
            self.conn.tag_stop(name, comment)

    def on_stop(self):
        self.signals.log.emit("Going to stop the job…")
        self.paused = False
        self.must_stop = True

    def on_pause(self):
        self.signals.log.emit("Going to pause the job…")
        self.paused = True

    def on_resume(self):
        self.paused = False
        self.signals.log.emit("Going to resume the job…")

    def check_pause(self):
        message_printed = False
        while self.paused:
            if not message_printed:
                self.signals.log.emit("Paused…")
                message_printed = True
            time.sleep(0.5)

    @QtCore.pyqtSlot()
    def run(self):
        self.board_setup.post_command = lambda url, cmd: self.post_command(url, cmd)

        self.paused = False
        self.must_stop = False

        # 1
        with StripTag(
            conn=self,
            name="BOARD_TURN_ON",
            comment=f"Turning on board for {self.polarimeter}",
            dry_run=True,
        ):
            self.signals.log.emit("Going to set up the board…")
            self.board_setup.board_setup()
            self.signals.log.emit("Board has been set up")

        # 2
        with StripTag(
            conn=self,
            name="ELECTRONICS_ENABLE",
            comment=f"Enabling electronics for {self.polarimeter}",
        ):
            self.signals.log.emit(f"Enabling electronics for {self.polarimeter}…")
            self.board_setup.enable_electronics(
                polarimeter=self.polarimeter, delay_sec=self.delay_sec
            )
            self.signals.log.emit("The electronics has been enabled")

        # 3
        for idx in (0, 1, 2, 3):
            with StripTag(
                conn=self,
                name="DETECTOR_TURN_ON",
                comment=f"Turning on detector {idx} in {self.polarimeter}",
            ):
                self.board_setup.turn_on_detector(self.polarimeter, idx)

        # 4
        biases = self.biases.get_biases(module_name=self.polarimeter)
        for (index, vpin, ipin) in zip(
            range(4),
            [biases.vpin0, biases.vpin1, biases.vpin2, biases.vpin3],
            [biases.ipin0, biases.ipin1, biases.ipin2, biases.ipin3],
        ):
            try:
                with StripTag(
                    conn=self,
                    name="PHSW_BIAS",
                    comment=f"Setting biases for PH/SW {index} in {self.polarimeter}",
                ):
                    self.board_setup.set_phsw_bias(self.polarimeter, index, vpin, ipin)
            except:
                log.warning(f"Unable to set bias for detector #{index}")

        # 5
        for idx in (0, 1, 2, 3):
            with StripTag(
                conn=self,
                name="PHSW_STATUS",
                comment=f"Setting status for PH/SW {index} in {self.polarimeter}",
            ):
                self.board_setup.set_phsw_status(self.polarimeter, idx, status=7)

        self.signals.finished.emit()


CommandEntry = namedtuple("CommandEntry", ["idx", "url", "command"])

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_main_window()
        self.ui.setupUi(self)

        self.command_history = []

        # We connect to the server immediately before showing the main window
        log.info("Trying to connect to the server…")
        self.conn = StripConnection()
        try:
            if self.conn.has_login():
                self.conn.login()
            else:
                dialog = LoginWidget()
                dialog.exec_()
                self.conn.login(dialog.user, dialog.password)
        except Exception as e:
            log.error(f"Unable to connect to the server: {e}")
            sys.exit(1)
        log.info("Connection has been established")

        # We need to load the configuration from the server, as it
        # includes vital information about the board
        # configuration. This information is needed to properly
        # initialize the hardware
        log.info("Initializing the configuration…")
        self.conf = Config()
        self.conf.load(self.conn)
        log.info("The configuration has been retrieved from the server")

        self.sb = None

        # We initialize the window's widgets only once we have the
        # board configuration available in `self.conf`, as the latter
        # is used to properly initialize some widgets (e.g., items in
        # combo boxes)
        self.init_controls()
        self.connect_actions()

        self.threadpool = QtCore.QThreadPool()
        log.info(f"Using {self.threadpool.maxThreadCount()} threads")
        self.worker = None
        self.job_running = False
        self.paused = False

    def init_controls(self):
        self.setWindowIcon(QIcon(os.path.join("program_turnon", "ui", "turnon_icon.svg")))

        # Set the contents of the combo box listing the available boards
        for cur_board in self.conf.boards:
            self.ui.list_boards.addItem(cur_board["name"])

        # To set the contents of the combo box listing the polarimeters,
        # we trigger a "changed" event on the combo, as the polarimeter list
        # depends on the board that is currently selected in
        # `self.ui.list_boards`
        self.ui.list_boards.setCurrentIndex(0)
        self.on_board_changed()

        self.ui.log_widget.setHorizontalHeaderLabels(["Time", "Message"])

    def connect_actions(self):
        self.ui.start_button.pressed.connect(self.on_start_job)
        self.ui.stop_button.pressed.connect(self.on_stop_job)
        self.ui.pause_button.pressed.connect(self.on_pause_job)
        self.ui.action_exit.triggered.connect(self.on_exit)
        self.ui.list_boards.currentIndexChanged.connect(self.on_board_changed)
        self.ui.new_log_button.pressed.connect(self.on_new_log_message)

    def update_command_history(self):
        self.ui.commands_widget.clear()
        self.command_history = sorted(self.command_history, key=lambda x: x.idx)

        s = ""
        for cmd in self.command_history:
            s += f"#{cmd.idx}: {cmd.command}\n"

        self.ui.commands_widget.setPlainText(s)

    def log_message(self, message):
        log.info(message)

        if self.sb and self.sb.post_command:
            self.sb.log(message)

        currow = self.ui.log_widget.rowCount()
        self.ui.log_widget.setRowCount(currow + 1)
        self.ui.log_widget.setItem(
            currow, 0, QtWidgets.QTableWidgetItem(time.strftime("%Y-%m-%d %H:%M:%S"))
        )
        self.ui.log_widget.setItem(currow, 1, QtWidgets.QTableWidgetItem(message))
        self.ui.log_widget.resizeColumnsToContents()

    def update_job_buttons(self):
        if self.job_running:
            self.ui.start_button.setEnabled(False)
            self.ui.stop_button.setEnabled(True)
            self.ui.pause_button.setEnabled(True)
        else:
            self.ui.start_button.setEnabled(True)
            self.ui.stop_button.setEnabled(False)
            self.ui.pause_button.setEnabled(False)

    def on_start_job(self):
        if self.job_running:
            return

        self.ui.log_widget.clear()
        self.ui.log_widget.setRowCount(0)
        self.ui.commands_widget.clear()

        self.worker = Worker(
            conn=self.conn,
            conf=self.conf,
            board_setup=self.sb,
            polarimeter=self.ui.list_channels.currentText(),
            delay_sec=self.ui.delay_spinbox.value(),
            mock_run=self.ui.mock_run.isChecked(),
        )
        self.worker.signals.log.connect(self.worker_on_log)
        self.worker.signals.command.connect(self.worker_on_command)
        self.worker.signals.finished.connect(self.worker_on_finished)
        self.threadpool.start(self.worker)
        self.job_running = True

        self.update_job_buttons()

    def on_pause_job(self):
        if not self.job_running:
            return

        if self.paused:
            self.worker.signals.resume.emit()
            self.ui.pause_button.setText("&Pause")
        else:
            self.worker.signals.pause.emit()
            self.ui.pause_button.setText("&Resume")

        self.paused = not self.paused
        self.update_job_buttons()

    def on_stop_job(self):
        if not self.job_running:
            return

        self.worker.signals.stop.emit()
        self.job_running = False
        self.update_job_buttons()

    def worker_on_log(self, message):
        assert self.worker
        self.log_message(message)

    def worker_on_command(self, url_command):
        log.info(f"In worker_on_command: {url_command}")
        cmd_idx, url, command = url_command

        self.command_history.append(
            CommandEntry(idx=cmd_idx, url=url, command=command)
        )

        self.update_command_history()

    def worker_on_finished(self):
        time.sleep(1)
        self.log_message("Job has completed, the board has been turned on")
        self.job_running = False
        self.update_job_buttons()

    def on_board_changed(self):
        # Every time the user changes the board in the combo box, the list
        # of polarimeters commanded by that board needs to be changed.
        self.ui.list_channels.clear()
        board_name = self.ui.list_boards.itemText(self.ui.list_boards.currentIndex())
        self.sb = SetupBoard(config=self.conf, board_name=board_name, post_command=None)
        for (pol, _) in self.sb.pols:
            self.ui.list_channels.addItem(pol)

    def on_new_log_message(self):
        self.log_message(self.ui.log_message_edit.text())

    def on_exit(self):
        self.close()


if __name__ == "__main__":
    import sys

    log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    app = QtWidgets.QApplication(sys.argv)
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec_())
