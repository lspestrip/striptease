from widgets.login.ui.login_dialog import Ui_Dialog
from PyQt5 import QtCore, QtGui, QtWidgets

class LoginWidget(QtWidgets.QDialog):
    def __init__(self):
        super(LoginWidget, self).__init__()
        self.dialog = Ui_Dialog()
        self.dialog.setupUi(self)
        self.user = None
        self.password = None
        self.dialog.buttonBox.accepted.connect(self.set_auth)

    def set_auth(self):
        self.user = self.dialog.line_user.text()
        self.password = self.dialog.line_password.text()
        self.accept()

    def exec_(self):
        super(LoginWidget, self).exec_()
