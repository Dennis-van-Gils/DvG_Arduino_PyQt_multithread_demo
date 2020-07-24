#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demonstration of multithreaded live Arduino data
- Terminal output only
- Mode: INTERNAL_TIMER
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo"
__date__ = "24-07-2020"
__version__ = "5.0"
# pylint: disable=bare-except, broad-except

import os
import sys
import time
import signal  # To catch CTRL+C and quit

import psutil

from PyQt5 import QtCore
from dvg_debug_functions import dprint, print_fancy_traceback as pft

from dvg_devices.Arduino_protocol_serial import Arduino
from dvg_qdeviceio import QDeviceIO

# Constants
DAQ_INTERVAL_MS = 10  # 10 [ms]

# Show debug info in terminal? Warning: Slow! Do not leave on unintentionally.
DEBUG = False


# ------------------------------------------------------------------------------
#   Arduino state
# ------------------------------------------------------------------------------


class State(object):
    """Reflects the actual readings, parsed into separate variables, of the
    Arduino. There should only be one instance of the State class.
    """

    def __init__(self):
        self.time = None  # [s]
        self.time_0 = None
        self.reading_1 = None


state = State()


# ------------------------------------------------------------------------------
#   Program termination routines
# ------------------------------------------------------------------------------


def keyboardInterruptHandler(keysig, frame):  # pylint: disable=unused-argument
    app.quit()


@QtCore.pyqtSlot()
def notify_connection_lost():
    print("\nCRITICAL ERROR: Lost connection to Arduino.")
    app.quit()


@QtCore.pyqtSlot()
def about_to_quit():
    print("\nAbout to quit")
    qdev_ard.quit()
    ard.close()


# ------------------------------------------------------------------------------
#   update_terminal
# ------------------------------------------------------------------------------


@QtCore.pyqtSlot()
def update_terminal():
    print(
        "%i\t%.3f\t%.4f"
        % (qdev_ard.update_counter_DAQ - 1, state.time, state.reading_1),
        # end="\r",
        # flush=True,
    )


# ------------------------------------------------------------------------------
#   Your Arduino update function
# ------------------------------------------------------------------------------


def DAQ_function():
    # Query the Arduino for its state
    success, tmp_state = ard.query_ascii_values("?", delimiter="\t")
    if not (success):
        dprint("'%s' reports IOError" % ard.name)
        return False

    # Parse readings into separate state variables
    try:
        state.time, state.reading_1 = tmp_state
        state.time /= 1000
    except Exception as err:
        pft(err, 3)
        dprint("'%s' reports IOError" % ard.name)
        return False

    # Use Arduino time or PC time?
    use_PC_time = True
    now = time.perf_counter() if use_PC_time else state.time
    if qdev_ard.update_counter_DAQ == 1:
        state.time_0 = now
        state.time = 0
    else:
        state.time = now - state.time_0

    # For demo purposes: Quit automatically after N updates
    if qdev_ard.update_counter_DAQ > 1000:
        app.quit()

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

    ard = Arduino(name="Ard", connect_to_specific_ID="Wave generator")

    ard.serial_settings["baudrate"] = 115200
    ard.auto_connect("last_used_port.txt")

    if not (ard.is_alive):
        print("\nCheck connection and try resetting the Arduino.")
        print("Exiting...\n")
        sys.exit(0)

    # --------------------------------------------------------------------------
    #   Create application
    # --------------------------------------------------------------------------
    app = QtCore.QCoreApplication(sys.argv)
    app.aboutToQuit.connect(about_to_quit)

    # --------------------------------------------------------------------------
    #   Set up multithreaded communication with the Arduino
    # --------------------------------------------------------------------------

    # Create QDeviceIO
    qdev_ard = QDeviceIO(ard)

    # Create workers
    # fmt: off
    qdev_ard.create_worker_DAQ(
        DAQ_function             = DAQ_function,
        DAQ_interval_ms          = DAQ_INTERVAL_MS,
        critical_not_alive_count = 3,
        debug                    = DEBUG,
    )
    # fmt: on

    # Connect signals to slots
    qdev_ard.signal_DAQ_updated.connect(update_terminal)
    qdev_ard.signal_connection_lost.connect(notify_connection_lost)

    # Start workers
    qdev_ard.start(DAQ_priority=QtCore.QThread.TimeCriticalPriority)

    # --------------------------------------------------------------------------
    #   Start the main event loop
    # --------------------------------------------------------------------------

    # Catch CTRL+C
    signal.signal(signal.SIGINT, keyboardInterruptHandler)

    sys.exit(app.exec_())
