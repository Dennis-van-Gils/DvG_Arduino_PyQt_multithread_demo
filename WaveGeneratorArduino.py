#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provides classes `WaveGeneratorArduino` and `FakeWaveGeneratorArduino`.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo"
__date__ = "11-06-2024"
__version__ = "9.0"

import time

from qtpy import QtCore
import numpy as np

from dvg_devices.Arduino_protocol_serial import Arduino

# ------------------------------------------------------------------------------
#   WaveGeneratorArduino
# ------------------------------------------------------------------------------


class WaveGeneratorArduino(Arduino):
    """Manages serial communication with an Arduino that is programmed as a wave
    generator."""

    class State:
        """Container for the process and measurement variables of the wave
        generator Arduino."""

        time_0 = np.nan  # [s] Start of data acquisition
        time = np.nan  # [s]
        reading_1 = np.nan  # [arbitrary units]

    def __init__(
        self,
        name="Ard",
        long_name="Arduino",
        connect_to_specific_ID="Wave generator",
    ):
        super().__init__(
            name=name,
            long_name=long_name,
            connect_to_specific_ID=connect_to_specific_ID,
        )

        # Container for the process and measurement variables
        self.state = self.State

        # Mutex for proper multithreading. If the state variables are not
        # atomic or thread-safe, you should lock and unlock this mutex for each
        # read and write operation. In this demo we don't need it, but I keep it
        # as reminder.
        self.mutex = QtCore.QMutex()

    def set_waveform_to_sine(self):
        """Send the instruction to the Arduino to change to a sine wave."""
        self.write("sine")

    def set_waveform_to_square(self):
        """Send the instruction to the Arduino to change to a square wave."""
        self.write("square")

    def set_waveform_to_sawtooth(self):
        """Send the instruction to the Arduino to change to a sawtooth wave."""
        self.write("sawtooth")


# ------------------------------------------------------------------------------
#   FakeWaveGeneratorArduino
# ------------------------------------------------------------------------------


class FakeWaveGeneratorArduino:
    """Simulates via software the serial communication with a faked Arduino that
    is programmed as a wave generator. Mimics class `WaveGeneratorArduino`.
    """

    class State:
        """Container for the process and measurement variables of the wave
        generator Arduino."""

        time_0 = np.nan  # [s] Start of data acquisition
        time = np.nan  # [s]
        reading_1 = np.nan  # [arbitrary units]

    def __init__(self, *args, **kwargs):
        self.serial_settings = {}
        self.name = "FakeArd"
        self.long_name = "FakeArduino"
        self.is_alive = True

        # Container for the process and measurement variables
        self.state = self.State

        # Mutex for proper multithreading. If the state variables are not
        # atomic or thread-safe, you should lock and unlock this mutex for each
        # read and write operation. In this demo we don't need it, but I keep it
        # as reminder.
        self.mutex = QtCore.QMutex()

        self.wave_freq = 0.3  # [Hz]
        self.wave_type = "sine"

    def set_waveform_to_sine(self):
        """Send the instruction to the Arduino to change to a sine wave."""
        self.wave_type = "sine"

    def set_waveform_to_square(self):
        """Send the instruction to the Arduino to change to a sine wave."""
        self.wave_type = "square"

    def set_waveform_to_sawtooth(self):
        """Send the instruction to the Arduino to change to a sine wave."""
        self.wave_type = "sawtooth"

    def query_ascii_values(self, *args, **kwargs):
        """Query the Arduino for new readings and return them as a list."""
        t = time.perf_counter()

        if self.wave_type == "sine":
            value = np.sin(2 * np.pi * self.wave_freq * t)

        elif self.wave_type == "square":
            value = 1 if np.mod(self.wave_freq * t, 1.0) > 0.5 else -1

        elif self.wave_type == "sawtooth":
            value = 2 * np.mod(self.wave_freq * t, 1.0) - 1

        success = True
        readings = [t * 1000, value]

        return success, readings

    def close(self):
        """Close the serial connection to the Arduino."""
        return

    def auto_connect(self, *args, **kwargs):
        """Auto connect to the Arduino via serial."""
        return True
