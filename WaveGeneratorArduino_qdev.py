#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provides class `WaveGeneratorArduino_qdev`.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo"
__date__ = "11-06-2024"
__version__ = "9.0"

from typing import Union, Callable

from qtpy import QtCore

from dvg_qdeviceio import QDeviceIO, DAQ_TRIGGER
from WaveGeneratorArduino import WaveGeneratorArduino, FakeWaveGeneratorArduino

# ------------------------------------------------------------------------------
#   WaveGeneratorArduino_qdev
# ------------------------------------------------------------------------------


class WaveGeneratorArduino_qdev(QDeviceIO):
    """Manages multithreaded communication and periodical data acquisition
    for an Arduino that is programmed as a wave generator, referred to as the
    'device'."""

    def __init__(
        self,
        dev: Union[WaveGeneratorArduino, FakeWaveGeneratorArduino],
        DAQ_function: Union[Callable[[], bool], None] = None,
        DAQ_interval_ms=10,
        DAQ_timer_type=QtCore.Qt.TimerType.PreciseTimer,
        critical_not_alive_count=1,
        debug=False,
        **kwargs,
    ):
        super().__init__(dev, **kwargs)  # Pass kwargs onto QtCore.QObject()
        self.dev: WaveGeneratorArduino  # Enforce type: removes `_NoDevice()`

        self.create_worker_DAQ(
            DAQ_trigger=DAQ_TRIGGER.INTERNAL_TIMER,
            DAQ_function=DAQ_function,
            DAQ_interval_ms=DAQ_interval_ms,
            DAQ_timer_type=DAQ_timer_type,
            critical_not_alive_count=critical_not_alive_count,
            debug=debug,
        )
        self.create_worker_jobs(debug=debug)

    def request_set_waveform_to_sine(self):
        """Request sending out a new instruction to the Arduino to change to a
        sine wave."""
        self.send(self.dev.set_waveform_to_sine)

    def request_set_waveform_to_square(self):
        """Request sending out a new instruction to the Arduino to change to a
        square wave."""
        self.send(self.dev.set_waveform_to_square)

    def request_set_waveform_to_sawtooth(self):
        """Request sending out a new instruction to the Arduino to change to a
        sawtooth wave."""
        self.send(self.dev.set_waveform_to_sawtooth)
