#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demonstration of multithreaded live Arduino data
- CLI output only
- Mode: INTERNAL_TIMER
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo"
__date__ = "02-07-2020"
__version__ = "3.0"

import sys
from pathlib import Path
import time
import signal  # To catch CTRL+C and quit

from PyQt5 import QtCore
from dvg_debug_functions import dprint, print_fancy_traceback as pft

from dvg_devices.Arduino_protocol_serial import Arduino  # I.e. the `device`
from dvg_qdeviceio import QDeviceIO, DAQ_TRIGGER

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
        self.reading_1 = None


state = State()


# ------------------------------------------------------------------------------
#   Program termination routines
# ------------------------------------------------------------------------------


def keyboardInterruptHandler(signal, frame):
    app.quit()


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
    use_PC_time = True
    now = time.perf_counter() if use_PC_time else state.time
    if qdev.update_counter_DAQ == 1:
        state.time_0 = now
        state.time = 0
    else:
        state.time = now - state.time_0

    # For demo purposes: Quit automatically after N updates
    if qdev.update_counter_DAQ > 1000:
        app.quit()

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
    app.aboutToQuit.connect(about_to_quit)

    # Set up multithreaded communication with the Arduino
    # fmt: off
    qdev = QDeviceIO(ard)
    qdev.create_worker_DAQ(
        DAQ_trigger     = DAQ_TRIGGER.INTERNAL_TIMER,
        DAQ_function    = DAQ_function,
        DAQ_interval_ms = DAQ_INTERVAL_MS,
        debug           = DEBUG,
    )
    # fmt: on

    # Connect signals to slots
    qdev.signal_DAQ_updated.connect(update_terminal)
    qdev.signal_connection_lost.connect(notify_connection_lost)

    # Start workers
    qdev.start(DAQ_priority=QtCore.QThread.TimeCriticalPriority)

    # --------------------------------------------------------------------------
    #   Start the main event loop
    # --------------------------------------------------------------------------

    # Catch CTRL+C
    signal.signal(signal.SIGINT, keyboardInterruptHandler)

    sys.exit(app.exec_())
