#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demonstration of multithreaded live Arduino data
- CLI output only
- Mode: SINGLE_SHOT_WAKE_UP
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo"
__date__ = "26-06-2020"
__version__ = "2.1"

import os
import sys
from pathlib import Path

import numpy as np
import psutil
import time

from PyQt5 import QtCore
from DvG_debug_functions import dprint, print_fancy_traceback as pft

import DvG_dev_Arduino__fun_serial as Arduino_functions
import DvG_QDeviceIO

# Constants
DAQ_INTERVAL_ARDUINO = 10  # 10 [ms]

# Show debug info in terminal? Warning: Slow! Do not leave on unintentionally.
DEBUG = False

# ------------------------------------------------------------------------------
#   Arduino state
# ------------------------------------------------------------------------------


class State(object):
    """Reflects the actual readings, parsed into separate variables, of the
    Arduino(s). There should only be one instance of the State class.
    """

    def __init__(self):
        self.time = np.nan  # [ms]
        self.reading_1 = np.nan


state = State()


# ------------------------------------------------------------------------------
#   Program termination routines
# ------------------------------------------------------------------------------


@QtCore.pyqtSlot()
def notify_connection_lost():
    print("\nCRITICAL ERROR: Connection lost")
    exit_program()


@QtCore.pyqtSlot()
def exit_program():
    print("\nAbout to quit")

    app.processEvents()

    timer.stop()
    qdev.quit()
    ard.close()

    app.quit()


# ------------------------------------------------------------------------------
#   update_CLI
# ------------------------------------------------------------------------------


@QtCore.pyqtSlot()
def update_CLI():
    print(
        "%i\t%.3f\t%.4f"
        % (qdev.update_counter_DAQ, state.time, state.reading_1)
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
    except Exception as err:
        pft(err, 3)
        dprint("'%s' reports IOError" % ard.name)
        return False

    # Use Arduino time or PC time?
    # Arduino time is more accurate, but rolls over ~49 days for a 32 bit timer.
    use_PC_time = True
    if use_PC_time:
        state.time = time.perf_counter()

    return True


# ------------------------------------------------------------------------------
#   Main
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # Set priority of this process to maximum in the operating system
    print("PID: %s\n" % os.getpid())
    try:
        proc = psutil.Process(os.getpid())
        if os.name == "nt":
            proc.nice(psutil.REALTIME_PRIORITY_CLASS)  # Windows
        else:
            proc.nice(-20)  # Other
    except:
        print("Warning: Could not set process to maximum priority.\n")

    # --------------------------------------------------------------------------
    #   Connect to Arduino
    # --------------------------------------------------------------------------

    ard = Arduino_functions.Arduino(name="Ard", baudrate=115200)
    ard.auto_connect(
        Path("last_used_port.txt"), match_identity="Wave generator"
    )

    if not (ard.is_alive):
        print("\nCheck connection and try resetting the Arduino.")
        print("Exiting...\n")
        sys.exit(0)

    # --------------------------------------------------------------------------
    #   Create application
    # --------------------------------------------------------------------------
    QtCore.QThread.currentThread().setObjectName("MAIN")  # For DEBUG info

    app = 0  # Work-around for kernel crash when using Spyder IDE
    app = QtCore.QCoreApplication(sys.argv)
    app.aboutToQuit.connect(exit_program)

    # --------------------------------------------------------------------------
    #   Set up multithreaded communication with the Arduino
    # --------------------------------------------------------------------------

    # Create QDeviceIO
    qdev = DvG_QDeviceIO.QDeviceIO(ard)

    # Create workers
    # fmt: off
    qdev.create_worker_DAQ(
        DAQ_trigger  = DvG_QDeviceIO.DAQ_trigger.SINGLE_SHOT_WAKE_UP,
        DAQ_function = DAQ_function,
        debug        = DEBUG,)
    # fmt: on

    qdev.create_worker_jobs(debug=DEBUG)

    # Connect signals to slots
    qdev.signal_DAQ_updated.connect(update_CLI)
    qdev.signal_connection_lost.connect(notify_connection_lost)

    # Start workers
    qdev.start(DAQ_priority=QtCore.QThread.TimeCriticalPriority)

    # --------------------------------------------------------------------------
    #   Create wake-up timer
    # --------------------------------------------------------------------------

    timer = QtCore.QTimer()
    timer.setInterval(DAQ_INTERVAL_ARDUINO)
    timer.setTimerType(QtCore.Qt.PreciseTimer)
    timer.timeout.connect(qdev.wake_up_DAQ)
    timer.start()

    # --------------------------------------------------------------------------
    #   Start the main loop
    # --------------------------------------------------------------------------

    while True:
        app.processEvents()

        if qdev.update_counter_DAQ >= 20:
            exit_program()
            break