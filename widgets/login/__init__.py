# widgets/login/__init__.py --- Login dialog
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it
from widgets.login.ui.login_dialog import Ui_Dialog
from PyQt5 import QtCore, QtGui, QtWidgets

class LoginWidget(QtWidgets.QDialog):
    '''Qt5 widget login dialog.
    '''
    def __init__(self):
        super(LoginWidget, self).__init__()
        self.dialog = Ui_Dialog()
        self.dialog.setupUi(self)
        self.user = None
        self.password = None
        self.dialog.buttonBox.accepted.connect(self.set_auth)

    def set_auth(self):
        '''collects the text form the form and stores it in user and password
           attributes. This funtion is connected to the Ok button on the form.
        '''
        self.user = self.dialog.line_user.text()
        self.password = self.dialog.line_password.text()
        self.accept()

    def exec_(self):
        '''Executes the widget and shows the ui. When the user presses either
           'Ok' on 'Cancel' button, the window closes and the credentials may
           be retreived from the attributes user and password.
        '''
        super(LoginWidget, self).exec_()
