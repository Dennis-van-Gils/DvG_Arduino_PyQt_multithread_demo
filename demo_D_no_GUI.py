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
from typing import Union
import signal  # To catch CTRL+C and quit

import qtpy
from qtpy import QtCore
from qtpy.QtCore import Slot  # type: ignore

import psutil

from dvg_debug_functions import dprint, print_fancy_traceback as pft
from dvg_qdeviceio import QDeviceIO, DAQ_TRIGGER

from WaveGeneratorArduino import WaveGeneratorArduino, FakeWaveGeneratorArduino

# Constants
DAQ_INTERVAL_MS = 10  # 10 [ms]

# Global flags
USE_PC_TIME = True  # Use Arduino time or PC time?
SIMULATE_ARDUINO = False  # Simulate an Arduino, instead?
if sys.argv[-1] == "simulate":
    SIMULATE_ARDUINO = True

# Show debug info in terminal? Warning: Slow! Do not leave on unintentionally.
DEBUG = False

print(f"{qtpy.API_NAME:9s} {qtpy.QT_VERSION}")

# ------------------------------------------------------------------------------
#   WaveGeneratorArduino_qdev
# ------------------------------------------------------------------------------


class WaveGeneratorArduino_qdev(QDeviceIO):
    """Manages multithreaded communication and periodical data acquisition for
    a wave generator Arduino, referred to as the 'device'."""

    def __init__(
        self,
        dev: Union[WaveGeneratorArduino, FakeWaveGeneratorArduino],
        DAQ_interval_ms=DAQ_INTERVAL_MS,
        DAQ_timer_type=QtCore.Qt.TimerType.PreciseTimer,
        critical_not_alive_count=1,
        debug=False,
        **kwargs,
    ):
        super().__init__(dev, **kwargs)  # Pass kwargs onto QtCore.QObject()
        self.dev: WaveGeneratorArduino  # Enforce type: removes `_NoDevice()`

        self.create_worker_DAQ(
            DAQ_trigger=DAQ_TRIGGER.INTERNAL_TIMER,
            DAQ_function=self.DAQ_function,
            DAQ_interval_ms=DAQ_interval_ms,
            DAQ_timer_type=DAQ_timer_type,
            critical_not_alive_count=critical_not_alive_count,
            debug=debug,
        )
        self.create_worker_jobs(debug=debug)

    def set_waveform_to_sine(self):
        self.send(self.dev.set_waveform_to_sine)

    def set_waveform_to_square(self):
        self.send(self.dev.set_waveform_to_square)

    def set_waveform_to_sawtooth(self):
        self.send(self.dev.set_waveform_to_sawtooth)

    # --------------------------------------------------------------------------
    #   DAQ_function
    # --------------------------------------------------------------------------

    def DAQ_function(self) -> bool:
        # Query the Arduino for its state
        success, tmp_state = self.dev.query_ascii_values("?", delimiter="\t")
        if not success:
            dprint(f"'{self.dev.name}' reports IOError")
            return False

        # Parse readings into separate state variables
        try:
            self.dev.state.time, self.dev.state.reading_1 = tmp_state
            self.dev.state.time /= 1000
        except Exception as err:  # pylint: disable=broad-except
            pft(err, 3)
            dprint(f"'{self.dev.name}' reports IOError")
            return False

        # Use Arduino time or PC time?
        now = time.perf_counter() if USE_PC_TIME else self.dev.state.time
        if self.update_counter_DAQ == 1:
            self.dev.state.time_0 = now
            self.dev.state.time = 0
        else:
            self.dev.state.time = now - self.dev.state.time_0

        # For demo purposes: Quit automatically after N updates
        if self.update_counter_DAQ > 1000:
            app.quit()

        return True


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

    ard_qdev = WaveGeneratorArduino_qdev(dev=ard, debug=DEBUG)

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
        print("\nCRITICAL ERROR: Lost connection to Arduino.")
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
