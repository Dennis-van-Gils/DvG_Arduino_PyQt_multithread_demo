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

import qtpy
from qtpy import QtCore, QtWidgets as QtWid
from qtpy.QtCore import Slot  # type: ignore

import psutil
import pyqtgraph as pg

from dvg_pyqtgraph_threadsafe import HistoryChartCurve

from WaveGeneratorArduino import WaveGeneratorArduino, FakeWaveGeneratorArduino
from WaveGeneratorArduino_qdev import WaveGeneratorArduino_qdev

# Constants
DAQ_INTERVAL_MS = 10
"""[ms] Update interval for the data acquisition (DAQ)"""
CHART_INTERVAL_MS = 20
"""[ms] Update interval for the chart"""
CHART_HISTORY_TIME = 10
"""[s] History length of the chart"""

# Global flags
TRY_USING_OPENGL = True
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

    def DAQ_function() -> bool:
        """Perform a single data acquisition and append this data to the chart.

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

        # Add readings to chart history
        window.history_chart_curve.appendData(
            ard.state.time, ard.state.reading_1
        )

        return True

    ard_qdev = WaveGeneratorArduino_qdev(
        dev=ard,
        DAQ_function=DAQ_function,
        DAQ_interval_ms=DAQ_INTERVAL_MS,
        debug=DEBUG,
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

    window = MainWindow()
    window.timer_chart.start(CHART_INTERVAL_MS)
    window.show()

    ard_qdev.start(DAQ_priority=QtCore.QThread.Priority.TimeCriticalPriority)

    app.aboutToQuit.connect(about_to_quit)
    sys.exit(app.exec())
