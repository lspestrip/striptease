#from program_viewer import main
from PyQt5 import QtCore, QtWidgets
import sys
import os
from program_viewer import ApplicationWindow
import asyncio
from threading import Thread

loop0 = asyncio.new_event_loop()
loop1 = asyncio.new_event_loop()

def f(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()
    print("STOPPED")

t0 = Thread(target=f, args=(loop0,))
#t0.start()

t1 = Thread(target=f, args=(loop1,))
#t1.start()

if __name__ == "__main__":
    import time
    app = QtWidgets.QApplication(sys.argv)
    application = ApplicationWindow()
    application.show()
    ec = app.exec_()
    print("stop loop")
    application.stop()
    sys.exit(ec)
