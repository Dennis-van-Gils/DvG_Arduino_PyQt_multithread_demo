#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Class FileLogger handles logging data to file, particularly well suited for
multithreaded programs, where one thread is writing data to the log (the logging
thread) and the other thread (the main thread/GUI) requests
starting and stopping of the logging by user interaction (i.e. a button).

The methods `start_recording()` and `stop_recording()` can be directly called
from the main/GUI thread.

In the data acquisitioni thread, place a call to `update()`

Class:
    FileLogger():
        Methods:
            start_recording():
                Prime the start of recording.
            stop_recording():
                Prime the stop of recording.
            update(...):
                ...
            write(...):
                Write data to the open log file.
            close():
                Close the log file.

        Signals:
            signal_recording_started (str):
                Useful for updating text of e.g. a record button when using a
                PyQt GUI.

            signal_recording_stopped (pathlib.Path):
                Useful for updating text of e.g. a record button when using a
                PyQt GUI. Or you could open a file explorer to the newly created
                log file.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/..."
__date__ = "05-08-2020"
__version__ = "1.0.0"
# NOTE: No mutex implemented here! Notify the user.
# NOTE: Everything in this module will run in the Worker_DAQ thread! We need to
# signal any changes we want to the GUI.
# NOTE: Module will struggle on by design when exceptions occur. They are only
# reported to the command line and the module will continue on.

from typing import AnyStr, Callable
from pathlib import Path
import datetime

from PyQt5 import QtCore
from PyQt5.QtCore import QDateTime

from dvg_debug_functions import print_fancy_traceback as pft


class FileLogger(QtCore.QObject):
    signal_recording_started = QtCore.pyqtSignal(str)
    signal_recording_stopped = QtCore.pyqtSignal(Path)

    def __init__(
        self,
        write_header_fun: Callable = None,
        write_data_fun: Callable = None,
    ):
        """
        Instruct user that he should use:
            * self.write()`

        Optionally:
            * self.elapsed() # For PC timestamp, taken from time.perf_counter()
        """
        super().__init__(parent=None)

        self._write_header_fun = write_header_fun
        self._write_data_fun = write_data_fun

        self._filepath = None  # Will be of type pathlib.Path()
        self._filehandle = None
        self._mode = "a"

        self._timer = QtCore.QElapsedTimer()
        self._start = False
        self._stop = False
        self._is_recording = False

    def __del__(self):
        if self._is_recording:
            self._filehandle.close()

    def set_write_header_fun(self, write_header_fun: Callable):
        """
        Instruct user that he should use:
            * self.write()
        """
        self._write_header_fun = write_header_fun

    def set_write_data_fun(self, write_data_fun: Callable):
        """
        Instruct user that he should use:
            * self.write()`

        Optionally:
            * self.elapsed() # For PC timestamp, taken from time.perf_counter()
        """
        self._write_data_fun = write_data_fun

    @QtCore.pyqtSlot(bool)
    def record(self, state):
        """Convenience function
        """
        if state:
            self.start_recording()
        else:
            self.stop_recording()

    @QtCore.pyqtSlot()
    def start_recording(self):
        self._start = True
        self._stop = False

    @QtCore.pyqtSlot()
    def stop_recording(self):
        self._start = False
        self._stop = True

    def is_recording(self) -> bool:
        return self._is_recording

    def update(self, filepath: str == "", mode: str = "a"):
        """
            mode (str):
                Mode in which the file is openend, see 'open()' for more
                details. Defaults to 'a'. Most common options:
                'w': Open for writing, truncating the file first
                'a': Open for writing, appending to the end of the file if it
                     exists
        """
        if self._start:
            if filepath == "":
                filepath = (
                    QDateTime.currentDateTime().toString("yyMMdd_HHmmss")
                    + ".txt"
                )

            self._filepath = Path(filepath)
            self._mode = mode

            # Reset flags
            self._start = False
            self._stop = False

            if self._create_log():
                self.signal_recording_started.emit(filepath)
                self._is_recording = True
                if self._write_header_fun is not None:
                    self._write_header_fun()
                self._timer.start()

            else:
                self._is_recording = False

        if self._is_recording and self._stop:
            self.signal_recording_stopped.emit(self._filepath)
            self._timer.invalidate()
            self.close()

        if self._is_recording:
            if self._write_data_fun is not None:
                self._write_data_fun()

    def elapsed(self) -> float:
        """
        Returns time in seconds since start of recording.
        """
        return self._timer.elapsed() / 1e3

    def pretty_elapsed(self) -> str:
        """
        Returns time as "h:mm:ss" since start of recording.
        """
        return str(datetime.timedelta(seconds=int(self.elapsed())))

    def _create_log(self) -> bool:
        """Open new log file and keep file handle open.
        Returns:
            True if successful, False otherwise.
        """
        try:
            self._filehandle = open(self._filepath, self._mode)
        except Exception as err:  # pylint: disable=broad-except
            pft(err, 3)
            return False
        else:
            return True

    def write(self, data: AnyStr) -> bool:
        """
        Returns:
            True if successful, False otherwise.
        """
        try:
            self._filehandle.write(data)
        except Exception as err:  # pylint: disable=broad-except
            pft(err, 3)
            return False
        else:
            return True

    @QtCore.pyqtSlot()
    def flush(self):
        """Force-flush the contents in the OS buffer to file as soon as
        possible. Do not call repeatedly, because it causes overhead.
        """
        self._filehandle.flush()

    def close(self):
        """
        """
        if self._is_recording:
            self._filehandle.close()
        self._start = False
        self._stop = False
        self._is_recording = False

