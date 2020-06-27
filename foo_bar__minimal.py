#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demonstration of multithreaded live Arduino data
- CLI output only
- Mode: INTERNAL_TIMER
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

from DvG_dev_Arduino__fun_serial import Arduino  # I.e. the `device`
from DvG_QDeviceIO import QDeviceIO, DAQ_trigger

# Constants
DAQ_INTERVAL = 10  # 10 [ms]

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
    app = QtCore.QCoreApplication(sys.argv)
    app.aboutToQuit.connect(exit_program)

    # Set up multithreaded communication with the Arduino
    qdev = QDeviceIO(ard)
    qdev.create_worker_DAQ(
        DAQ_trigger     = DAQ_trigger.INTERNAL_TIMER,
        DAQ_function    = DAQ_function,
        DAQ_interval_ms = DAQ_INTERVAL,
        debug           = DEBUG,)

    # Connect signals to slots
    qdev.signal_DAQ_updated.connect(update_CLI)
    qdev.signal_connection_lost.connect(notify_connection_lost)

    # Start workers
    qdev.start()

    # --------------------------------------------------------------------------
    #   Start the main loop
    # --------------------------------------------------------------------------

    while True:
        app.processEvents()

        if qdev.update_counter_DAQ >= 20:
            exit_program()
            break
