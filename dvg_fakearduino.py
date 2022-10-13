#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simulates the Arduino communication stream as expected by demo A and C.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo"
__date__ = "13-10-2022"
__version__ = "0.0.1"
# pylint: disable=unused-argument

import os
import sys
import time

# Mechanism to support both PyQt and PySide
# -----------------------------------------

PYQT5 = "PyQt5"
PYQT6 = "PyQt6"
PYSIDE2 = "PySide2"
PYSIDE6 = "PySide6"
QT_LIB_ORDER = [PYQT5, PYSIDE2, PYSIDE6, PYQT6]
QT_LIB = os.getenv("PYQTGRAPH_QT_LIB")

# pylint: disable=import-error, no-name-in-module, c-extension-no-member
if QT_LIB is None:
    for lib in QT_LIB_ORDER:
        if lib in sys.modules:
            QT_LIB = lib
            break

if QT_LIB is None:
    for lib in QT_LIB_ORDER:
        try:
            __import__(lib)
            QT_LIB = lib
            break
        except ImportError:
            pass

if QT_LIB is None:
    this_file = __file__.split(os.sep)[-1]
    raise Exception(
        f"{this_file} requires PyQt5, PyQt6, PySide2 or PySide6; "
        "none of these packages could be imported."
    )

# fmt: off
if QT_LIB == PYQT5:
    from PyQt5 import QtCore    # type: ignore
elif QT_LIB == PYQT6:
    from PyQt6 import QtCore    # type: ignore
elif QT_LIB == PYSIDE2:
    from PySide2 import QtCore  # type: ignore
elif QT_LIB == PYSIDE6:
    from PySide6 import QtCore  # type: ignore
# fmt: on

# pylint: enable=import-error, no-name-in-module
# \end[Mechanism to support both PyQt and PySide]
# -----------------------------------------------

import numpy as np


class FakeArduino:
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self.serial_settings = dict()
        self.name = "FakeArd"
        self.long_name = "FakeArduino"
        self.is_alive = True
        self.mutex = QtCore.QMutex()

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
