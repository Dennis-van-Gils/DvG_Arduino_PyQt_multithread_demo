#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simulates the Arduino communication stream as expected by demo A and C.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo"
__date__ = "11-08-2020"
__version__ = "0.0.1"
# pylint: disable=unused-argument

import time
import numpy as np
from PyQt5 import QtCore


class FakeArduino:
    def __init__(
        self, *args, **kwargs,
    ):
        self.serial_settings = dict()
        self.name = "FakeArd"
        self.long_name = "FakeArduino"
        self.is_alive = True
        self.mutex = QtCore.QMutex()

        self.wave_freq = 0.3  # [Hz]
        self.wave_type = "sine"

    def write(self, msg, *args, **kwargs) -> bool:
        self.wave_type = msg
        return True

    def query_ascii_values(self, *args, **kwargs) -> tuple:
        t = time.perf_counter()

        if self.wave_type == "sine":
            wave = np.sin(2 * np.pi * self.wave_freq * t)

        elif self.wave_type == "square":
            wave = 1 if np.mod(self.wave_freq * t, 1.0) > 0.5 else -1

        elif self.wave_type == "sawtooth":
            wave = 2 * np.mod(self.wave_freq * t, 1.0) - 1

        return (True, (t, wave))

    def close(self):
        pass

    def auto_connect(self, *args, **kwargs) -> bool:
        return True
