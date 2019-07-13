import logging as log
import time
import sys

from config import Config
from web.rest.base import Connection

from widgets.plot.pol import PolMplCanvas
from PyQt5 import QtCore, QtGui, QtWidgets
from program_turnon import SetupBoard
from program_turnon.ui.main_window import Ui_main_window
from striptease.biases import InstrumentBiases

class WorkerSignals(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(str)
    result = QtCore.pyqtSignal(object)
    command = QtCore.pyqtSignal(tuple)
    log = QtCore.pyqtSignal(str)
    pause = QtCore.pyqtSignal()
    resume = QtCore.pyqtSignal()
    stop = QtCore.pyqtSignal()


class Worker(QtCore.QRunnable):
    def __init__(self, conn, conf, board_setup, polarimeter, delay_sec=0.5):
        super(Worker, self).__init__()
        self.conn = conn
        self.conf = conf
        self.board_setup = board_setup
        self.paused = False
        self.must_stop = False
        self.polarimeter = polarimeter
        self.delay_sec = delay_sec

        self.signals = WorkerSignals()
        self.signals.pause.connect(self.on_pause)
        self.signals.resume.connect(self.on_resume)
        self.signals.stop.connect(self.on_stop)

        self.biases = InstrumentBiases()

    def post_command(self, url, cmd):
        if self.must_stop:
            self.signals.finished.emit()
            self.must_stop = False
            self.paused = False
            return False
        self.check_pause()

        log.info(f'Command : {cmd}')
        self.signals.command.emit((url, cmd))
        time.sleep(self.delay_sec)
        if False:
            result = self.conn.post(url, cmd)

            if result["status"] != "OK":
                self.signals.error.emit(f"Error executing {cmd}: {result}")
                return False

        return True

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
        self.signals.log.emit("Going to set up the board…")
        self.board_setup.board_setup()
        self.signals.log.emit("Board has been set up")

        # 2
        self.signals.log.emit(
            f"Enabling electronics for {self.polarimeter}…"
        )
        self.board_setup.enable_electronics(
            polarimeter=self.polarimeter, delay_sec=self.delay_sec
        )
        self.signals.log.emit("The electronics has been turned on")

        # 3
        for idx in (0, 1, 2, 3):
            self.board_setup.turn_on_detector(self.polarimeter, idx)

        # 4
        biases = self.biases.get_biases(module_name=self.polarimeter)
        for (index, vpin, ipin) in zip(
            range(4),
            [biases.vpin0, biases.vpin1, biases.vpin2, biases.vpin3],
            [biases.ipin0, biases.ipin1, biases.ipin2, biases.ipin3],
        ):
            self.board_setup.set_phsw_bias(self.polarimeter, index, vpin, ipin)

        # 5
        for idx in (0, 1, 2, 3):
            self.board_setup.set_phsw_status(self.polarimeter, idx, status=7)

        self.signals.finished.emit()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_main_window()
        self.ui.setupUi(self)

        # We connect to the server immediately before showing the main window
        log.info("Trying to connect to the server…")
        self.conn = Connection()
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

        # We need to load the configuration from the server, as it includes
        # vital information about the board configuration, which is needed
        # to properly initialize the hardware
        log.info("Initializing the configuration…")
        self.conf = Config()
        self.conf.load(self.conn)
        log.info("The configuration has been retrieved from the server")

        self.sb = None

        # We initialize the window's widgets only once we have the board
        # configuration available in `self.conf`
        self.init_controls()
        self.connect_actions()

        self.threadpool = QtCore.QThreadPool()
        log.info(f"Using {self.threadpool.maxThreadCount()} threads")
        self.worker = None
        self.paused = False

    def init_controls(self):
        # Set the contents of the combo box listing the available boards
        for cur_board in self.conf.boards:
            self.ui.list_boards.addItem(cur_board["name"])

        # To set the contents of the combo box listing the polarimeters,
        # we trigger a "changed" event on the combo, as the polarimeter list
        # depends on the board that is currently selected in
        # `self.ui.list_boards`
        self.ui.list_boards.setCurrentIndex(0)
        self.on_board_changed()

        self.ui.log_widget.setHorizontalHeaderLabels([
            "Time",
            "Message",
        ])

    def connect_actions(self):
        self.ui.start_button.pressed.connect(self.on_start_job)
        self.ui.stop_button.pressed.connect(self.on_stop_job)
        self.ui.pause_button.pressed.connect(self.on_pause_job)
        self.ui.action_exit.triggered.connect(self.on_exit)
        self.ui.list_boards.currentIndexChanged.connect(self.on_board_changed)

    def log_message(self, message):
        log.info(message)
        self.sb.log(message)

        currow = self.ui.log_widget.rowCount()
        self.ui.log_widget.setRowCount(currow + 1)
        self.ui.log_widget.setItem(currow, 0, QtWidgets.QTableWidgetItem(time.strftime("%Y-%m-%d %H:%M:%S")))
        self.ui.log_widget.setItem(currow, 1, QtWidgets.QTableWidgetItem(message))
        self.ui.log_widget.resizeColumnsToContents()

    def update_job_buttons(self):
        if self.worker is not None:
            self.ui.start_button.setEnabled(False)
            self.ui.stop_button.setEnabled(True)
            self.ui.pause_button.setEnabled(True)
        else:
            self.ui.start_button.setEnabled(True)
            self.ui.stop_button.setEnabled(False)
            self.ui.pause_button.setEnabled(False)

    def on_start_job(self):
        if self.worker:
            return

        self.ui.log_widget.clear()

        self.worker = Worker(
            conn=self.conn,
            conf=self.conf,
            board_setup=self.sb,
            polarimeter=self.ui.list_channels.currentText(),
            delay_sec=self.ui.delay_spinbox.value(),
        )
        self.worker.signals.log.connect(self.worker_on_log)
        self.worker.signals.command.connect(self.worker_on_command)
        self.worker.signals.finished.connect(self.worker_on_finished)
        self.threadpool.start(self.worker)

        self.update_job_buttons()

    def on_pause_job(self):
        if not self.worker:
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
        if not self.worker:
            return

        self.worker.signals.stop.emit()
        self.update_job_buttons()

    def worker_on_log(self, message):
        assert self.worker
        self.log_message(message)

    def worker_on_command(self, url_command):
        log.info(f"In worker_on_command: {url_command}")
        url, command = url_command
        self.ui.commands_widget.append(
            """{{
    "url": {url},
    "cmd": {cmd}
}},""".format(
                url=url, cmd=command
            )
        )

    def worker_on_finished(self):
        time.sleep(1)
        self.worker = None
        self.update_job_buttons()
        self.log_message("Job has completed, the board has been turned on")

    def on_board_changed(self):
        # Every time the user changes the board in the combo box, the list
        # of polarimeters commanded by that board needs to be changed.
        self.ui.list_channels.clear()
        board_name = self.ui.list_boards.itemText(self.ui.list_boards.currentIndex())
        self.sb = SetupBoard(config=self.conf, board_name=board_name, post_command=None)
        for (pol, _) in self.sb.pols:
            self.ui.list_channels.addItem(pol)

    def on_exit(self):
        self.close()


if __name__ == "__main__":
    import sys

    log.basicConfig(
        level=log.INFO,
        format="[%(asctime)s %(levelname)s] %(message)s",
    )

    app = QtWidgets.QApplication(sys.argv)
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec_())
