#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simulates the Arduino communication stream as expected by demo A and C.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo"
__date__ = "30-05-2024"
__version__ = "0.0.1"
# pylint: disable=unused-argument, missing-function-docstring

import time

from qtpy import QtCore
import numpy as np


class FakeArduino:
    class State:
        """Reflects the actual readings, parsed into separate variables, of the
        wave generator Arduino.
        """

        time = np.nan  # [s]
        reading_1 = np.nan  # [arbitrary units]

        # Keep track of the obtained DAQ rate. Only needed for the singlethread
        # demo C.
        update_counter_DAQ = 0
        obtained_DAQ_rate_Hz = np.nan
        QET_rate = QtCore.QElapsedTimer()
        rate_accumulator = 0

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self.serial_settings = {}
        self.name = "FakeArd"
        self.long_name = "FakeArduino"
        self.is_alive = True
        self.mutex = QtCore.QMutex()

        # Container for the process and measurement variables
        self.state = self.State

        self.wave_freq = 0.3  # [Hz]
        self.wave_type = "sine"

    def write(self, msg, *args, **kwargs):
        self.wave_type = msg
        return True

    def query_ascii_values(self, *args, **kwargs):
        t = time.perf_counter()

        if self.wave_type == "sine":
            wave = np.sin(2 * np.pi * self.wave_freq * t)

        elif self.wave_type == "square":
            wave = 1 if np.mod(self.wave_freq * t, 1.0) > 0.5 else -1

        elif self.wave_type == "sawtooth":
            wave = 2 * np.mod(self.wave_freq * t, 1.0) - 1

        return (True, (t * 1000, wave))

    def close(self):
        pass

    def auto_connect(self, *args, **kwargs):
        return True
