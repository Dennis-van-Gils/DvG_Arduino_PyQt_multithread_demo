#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demonstration of multithreaded real-time plotting and logging of live Arduino
data using PyQt/PySide and PyQtGraph.
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

import qtpy
from qtpy import QtCore, QtWidgets as QtWid
from qtpy.QtCore import Slot  # type: ignore

import psutil
import pyqtgraph as pg

from dvg_debug_functions import dprint, print_fancy_traceback as pft
from dvg_pyqtgraph_threadsafe import HistoryChartCurve
from dvg_qdeviceio import QDeviceIO, DAQ_TRIGGER

from WaveGeneratorArduino import WaveGeneratorArduino, FakeWaveGeneratorArduino

# fmt: off
# Constants
DAQ_INTERVAL_MS    = 10  # 10 [ms]
CHART_INTERVAL_MS  = 20  # 20 [ms]
CHART_HISTORY_TIME = 10  # 10 [s]

# Global flags
TRY_USING_OPENGL = True
USE_PC_TIME      = True   # Use Arduino time or PC time?
SIMULATE_ARDUINO = False  # Simulate an Arduino, instead?
# fmt: on
if sys.argv[-1] == "simulate":
    SIMULATE_ARDUINO = True

# Show debug info in terminal? Warning: Slow! Do not leave on unintentionally.
DEBUG = False

print(f"{qtpy.API_NAME:9s} {qtpy.QT_VERSION}")
print(f"PyQtGraph {pg.__version__}")

if TRY_USING_OPENGL:
    try:
        import OpenGL.GL as gl  # pylint: disable=unused-import
        from OpenGL.version import __version__ as gl_version
    except Exception:  # pylint: disable=broad-except
        print("PyOpenGL  not found")
        print("To install: `conda install pyopengl` or `pip install pyopengl`")
    else:
        print(f"PyOpenGL  {gl_version}")
        pg.setConfigOptions(useOpenGL=True)
        pg.setConfigOptions(antialias=True)
        pg.setConfigOptions(enableExperimental=True)
else:
    print("PyOpenGL  disabled")

# Global pyqtgraph configuration
# pg.setConfigOptions(leftButtonPan=False)
pg.setConfigOption("foreground", "#EEE")

# ------------------------------------------------------------------------------
#   current_date_time_strings
# ------------------------------------------------------------------------------


def current_date_time_strings():
    cur_date_time = QtCore.QDateTime.currentDateTime()
    return (
        cur_date_time.toString("dd-MM-yyyy"),  # Date
        cur_date_time.toString("HH:mm:ss"),  # Time
    )


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

        # Pause/resume mechanism
        self.DAQ_is_enabled = True

        self.create_worker_DAQ(
            DAQ_trigger=DAQ_TRIGGER.INTERNAL_TIMER,
            DAQ_function=self.DAQ_function,
            DAQ_interval_ms=DAQ_interval_ms,
            DAQ_timer_type=DAQ_timer_type,
            critical_not_alive_count=critical_not_alive_count,
            debug=debug,
        )
        self.create_worker_jobs(debug=debug)

    def set_DAQ_enabled(self, state: bool):
        self.DAQ_is_enabled = state
        if self.DAQ_is_enabled:
            self.worker_DAQ.DAQ_function = self.DAQ_function
        else:
            self.worker_DAQ.DAQ_function = None

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
            str_cur_date, str_cur_time = current_date_time_strings()
            dprint(
                f"'{self.dev.name}' reports IOError @ "
                f"{str_cur_date} {str_cur_time}"
            )
            return False

        # Parse readings into separate state variables
        try:
            self.dev.state.time, self.dev.state.reading_1 = tmp_state
            self.dev.state.time /= 1000
        except Exception as err:  # pylint: disable=broad-except
            pft(err, 3)
            str_cur_date, str_cur_time = current_date_time_strings()
            dprint(
                f"'{self.dev.name}' reports IOError @ "
                f"{str_cur_date} {str_cur_time}"
            )
            return False

        # Use Arduino time or PC time?
        now = time.perf_counter() if USE_PC_TIME else self.dev.state.time
        if self.update_counter_DAQ == 1:
            self.dev.state.time_0 = now
            self.dev.state.time = 0
        else:
            self.dev.state.time = now - self.dev.state.time_0

        # Return success
        return True


# ------------------------------------------------------------------------------
#   MainWindow
# ------------------------------------------------------------------------------


class MainWindow(QtWid.QWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.setWindowTitle("Arduino & PyQt multithread demo")
        self.setGeometry(40, 60, 800, 660)

        # GraphicsLayoutWidget
        self.gw = pg.GraphicsLayoutWidget()
        self.plot = self.gw.addPlot()

        p = {"color": "#EEE", "font-size": "10pt"}
        self.plot.setClipToView(True)
        self.plot.showGrid(x=1, y=1)
        self.plot.setLabel("bottom", text="history (sec)", **p)
        self.plot.setLabel("left", text="amplitude", **p)
        self.plot.setRange(
            xRange=[-1.04 * CHART_HISTORY_TIME, CHART_HISTORY_TIME * 0.04],
            yRange=[-1.1, 1.1],
            disableAutoRange=True,
        )

        self.history_chart_curve = HistoryChartCurve(
            capacity=round(CHART_HISTORY_TIME * 1e3 / DAQ_INTERVAL_MS),
            linked_curve=self.plot.plot(
                pen=pg.mkPen(color=[255, 255, 0], width=3)
            ),
        )

        vbox = QtWid.QVBoxLayout(self)
        vbox.addWidget(self.gw, 1)

        # Chart refresh timer
        self.timer_chart = QtCore.QTimer()
        self.timer_chart.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
        self.timer_chart.timeout.connect(self.history_chart_curve.update)


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

    main_thread = QtCore.QThread.currentThread()
    if isinstance(main_thread, QtCore.QThread):
        main_thread.setObjectName("MAIN")  # For DEBUG info

    app = QtWid.QApplication(sys.argv)

    # --------------------------------------------------------------------------
    #   Set up multithreaded communication with the Arduino
    # --------------------------------------------------------------------------

    ard_qdev = WaveGeneratorArduino_qdev(dev=ard, debug=DEBUG)

    # --------------------------------------------------------------------------
    #   postprocess_DAQ_updated
    # --------------------------------------------------------------------------

    @Slot()
    def postprocess_DAQ_updated():
        # Add readings to chart history
        window.history_chart_curve.appendData(
            ard.state.time, ard.state.reading_1
        )

    # --------------------------------------------------------------------------
    #   Program termination routines
    # --------------------------------------------------------------------------

    @Slot()
    def about_to_quit():
        print("\nAbout to quit")
        app.processEvents()
        ard_qdev.quit()
        ard.close()

        print("Stopping timers: ", end="")
        window.timer_chart.stop()
        print("done.")

    # --------------------------------------------------------------------------
    #   Start the main GUI event loop
    # --------------------------------------------------------------------------

    ard_qdev.signal_DAQ_updated.connect(postprocess_DAQ_updated)
    ard_qdev.start(DAQ_priority=QtCore.QThread.Priority.TimeCriticalPriority)

    app.aboutToQuit.connect(about_to_quit)

    window = MainWindow()
    window.timer_chart.start(CHART_INTERVAL_MS)
    window.show()

    sys.exit(app.exec())
