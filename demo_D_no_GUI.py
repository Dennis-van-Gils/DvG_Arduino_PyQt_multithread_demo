#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demonstration of multithreaded live Arduino data
- Terminal output only
- Mode: INTERNAL_TIMER
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo"
__date__ = "11-06-2024"
__version__ = "9.0"
# pylint: disable=missing-function-docstring

import os
import sys
import time
import datetime
import signal  # To catch CTRL+C and quit

import qtpy
from qtpy import QtCore
from qtpy.QtCore import Slot  # type: ignore

import psutil

from WaveGeneratorArduino import WaveGeneratorArduino, FakeWaveGeneratorArduino
from WaveGeneratorArduino_qdev import WaveGeneratorArduino_qdev

# Constants
DAQ_INTERVAL_MS = 10
"""[ms] Update interval for the data acquisition (DAQ)"""

# Global flags
USE_PC_TIME = True
"""Use Arduino time or PC time?"""
SIMULATE_ARDUINO = False
"""Simulate an Arduino in software?"""
if sys.argv[-1] == "simulate":
    SIMULATE_ARDUINO = True

DEBUG = False
"""Show debug info in terminal? Warning: Slow! Do not leave on unintentionally.
"""

print(
    f"{qtpy.API_NAME:9s} "
    f"{qtpy.QT_VERSION}"  # pyright: ignore[reportPrivateImportUsage]
)

# ------------------------------------------------------------------------------
#   Main
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # Set priority of this process to maximum in the operating system
    print(f"PID: {os.getpid()}\n")
    try:
        proc = psutil.Process(os.getpid())
        if os.name == "nt":
            proc.nice(psutil.REALTIME_PRIORITY_CLASS)  # Windows
        else:
            proc.nice(-20)  # Other
    except Exception:  # pylint: disable=broad-except
        print("Warning: Could not set process to maximum priority.\n")

    # --------------------------------------------------------------------------
    #   Connect to Arduino
    # --------------------------------------------------------------------------

    if SIMULATE_ARDUINO:
        ard = FakeWaveGeneratorArduino()
    else:
        ard = WaveGeneratorArduino()

    ard.serial_settings["baudrate"] = 115200
    ard.auto_connect()

    if not ard.is_alive:
        print("\nCheck connection and try resetting the Arduino.")
        print("Exiting...\n")
        sys.exit(0)

    # --------------------------------------------------------------------------
    #   Create application
    # --------------------------------------------------------------------------

    app = QtCore.QCoreApplication(sys.argv)

    # --------------------------------------------------------------------------
    #   Set up multithreaded communication with the Arduino
    # --------------------------------------------------------------------------

    def DAQ_function() -> bool:
        """Perform a single data acquisition.

        Returns: True if successful, False otherwise.
        """
        # Query the Arduino for new readings, parse them and update the
        # corresponding variables of its `state` member.
        if not ard.perform_DAQ():
            return False

        # Use Arduino time or PC time?
        now = time.perf_counter() if USE_PC_TIME else ard.state.time
        if ard_qdev.update_counter_DAQ == 1:
            ard.state.time_0 = now
            ard.state.time = 0
        else:
            ard.state.time = now - ard.state.time_0

        # For demo purposes: Quit automatically after N updates
        if ard_qdev.update_counter_DAQ > 1000:
            app.quit()

        return True

    ard_qdev = WaveGeneratorArduino_qdev(
        dev=ard,
        DAQ_function=DAQ_function,
        DAQ_interval_ms=DAQ_INTERVAL_MS,
        debug=DEBUG,
    )

    # --------------------------------------------------------------------------
    #   update_terminal
    # --------------------------------------------------------------------------

    @Slot()
    def update_terminal():
        print(
            f"{ard_qdev.update_counter_DAQ - 1}\t"
            f"{ard.state.time:.3f}\t"
            f"{ard.state.reading_1:.4f}",
            # end="\r",
            # flush=True,
        )

    # --------------------------------------------------------------------------
    #   Program termination routines
    # --------------------------------------------------------------------------

    def keyboardInterruptHandler(
        keysig, frame
    ):  # pylint: disable=unused-argument
        app.quit()

    # Catch CTRL+C
    signal.signal(signal.SIGINT, keyboardInterruptHandler)

    @Slot()
    def notify_connection_lost():
        str_msg = (
            f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "Lost connection to Arduino."
        )
        print(f"\nCRITICAL ERROR @ {str_msg}")
        app.quit()

    @Slot()
    def about_to_quit():
        app.processEvents()
        print("\nAbout to quit")
        ard_qdev.quit()
        ard.close()

    # --------------------------------------------------------------------------
    #   Start the main event loop
    # --------------------------------------------------------------------------

    ard_qdev.signal_DAQ_updated.connect(update_terminal)
    ard_qdev.signal_connection_lost.connect(notify_connection_lost)
    ard_qdev.start(DAQ_priority=QtCore.QThread.Priority.TimeCriticalPriority)

    app.aboutToQuit.connect(about_to_quit)
    sys.exit(app.exec())
