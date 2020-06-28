#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demonstration of multithreaded live Arduino data
- CLI output only
- Mode: INTERNAL_TIMER
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo"
__date__ = "28-06-2020"
__version__ = "2.1"

import sys
from pathlib import Path

import numpy as np
import time

from PyQt5 import QtCore, QtWidgets as QtWid
from DvG_debug_functions import dprint, print_fancy_traceback as pft

from DvG_dev_Arduino__fun_serial import Arduino  # I.e. the `device`
from DvG_QDeviceIO import QDeviceIO, DAQ_trigger

# Constants
DAQ_INTERVAL = 10  # 10 [ms]
TIMESTAMP_PC = True

# Show debug info in terminal? Warning: Slow! Do not leave on unintentionally.
DEBUG = False

# ------------------------------------------------------------------------------
#   Device state
# ------------------------------------------------------------------------------


class State(object):
    """Reflects the actual readings, parsed into separate variables, of the
    Arduino. There should only be one instance of the State class.
    """

    def __init__(self):
        self.time = np.nan  # [s]
        self.reading_1 = np.nan


state = State()


# ------------------------------------------------------------------------------
#   MainWindow
# ------------------------------------------------------------------------------


class MainWindow(QtWid.QWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.setGeometry(300, 300, 300, 100)
        self.setWindowTitle("Multithread PyQt & Arduino demo")

        self.lbl = QtWid.QLabel("Press `Esc` to quit.")
        vbox = QtWid.QVBoxLayout(self)
        vbox.addWidget(self.lbl)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            app.quit()
        event.accept()


# ------------------------------------------------------------------------------
#   Program termination routines
# ------------------------------------------------------------------------------


@QtCore.pyqtSlot()
def notify_connection_lost():
    print("\nCRITICAL ERROR: Connection lost")
    app.quit()


@QtCore.pyqtSlot()
def about_to_quit():
    print("\nAbout to quit")
    qdev.quit()
    ard.close()


# ------------------------------------------------------------------------------
#   update_terminal
# ------------------------------------------------------------------------------


@QtCore.pyqtSlot()
def update_terminal():
    print(
        "%i\t%.3f\t%.4f"
        % (qdev.update_counter_DAQ - 1, state.time, state.reading_1),
        # end="\r",
        # flush=True,
    )


# ------------------------------------------------------------------------------
#   Your Arduino update function
# ------------------------------------------------------------------------------


def DAQ_function():
    # Query the Arduino for its state
    [success, tmp_state] = ard.query_ascii_values("?", separator="\t")
    if not (success):
        dprint("'%s' reports IOError" % ard.name)
        return False

    # Parse readings into separate state variables
    try:
        [state.time, state.reading_1] = tmp_state
        state.time /= 1000
    except Exception as err:
        pft(err, 3)
        dprint("'%s' reports IOError" % ard.name)
        return False

    # Use Arduino time or PC time?
    # Arduino time is more accurate, but rolls over ~49 days for a 32 bit timer.
    if True:
        if qdev.update_counter_DAQ == 1:
            state.time_0 = time.perf_counter()
            state.time = 0
        else:
            state.time = time.perf_counter() - state.time_0

    # # For demo purposes: Quit automatically after 200 updates
    # if qdev.update_counter_DAQ > 200:
    #     app.quit()

    return True


# ------------------------------------------------------------------------------
#   Main
# ------------------------------------------------------------------------------

if __name__ == "__main__":

    # Connect to Arduino
    ard = Arduino(name="Ard", baudrate=115200)
    ard.auto_connect(
        Path("last_used_port.txt"), match_identity="Wave generator"
    )

    if not (ard.is_alive):
        print("\nCheck connection and try resetting the Arduino.")
        print("Exiting...\n")
        sys.exit(0)

    # Create application
    # app = QtCore.QCoreApplication(sys.argv)
    app = QtWid.QApplication(sys.argv)
    app.aboutToQuit.connect(about_to_quit)

    window = MainWindow()

    # Set up multithreaded communication with the Arduino
    qdev = QDeviceIO(ard)
    qdev.create_worker_DAQ(
        DAQ_trigger=DAQ_trigger.INTERNAL_TIMER,
        DAQ_function=DAQ_function,
        DAQ_interval_ms=DAQ_INTERVAL,
        debug=DEBUG,
    )

    # Connect signals to slots
    qdev.signal_DAQ_updated.connect(update_terminal)
    qdev.signal_connection_lost.connect(notify_connection_lost)

    # Start workers
    qdev.start()

    # --------------------------------------------------------------------------
    #   Start the main event loop
    # --------------------------------------------------------------------------

    # app.exec()
    window.show()
    sys.exit(app.exec_())
