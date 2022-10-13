#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demonstration of multithreaded real-time plotting and logging of live Arduino
data using PyQt/PySide and PyQtGraph.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo"
__date__ = "13-09-2022"
__version__ = "8.2"
# pylint: disable=bare-except, broad-except

import os
import sys
import time

# Constants
# fmt: off
DAQ_INTERVAL_MS    = 10  # 10 [ms]
CHART_INTERVAL_MS  = 20  # 20 [ms]
CHART_HISTORY_TIME = 10  # 10 [s]
# fmt: on

# Global flags
TRY_USING_OPENGL = True
SIMULATE_ARDUINO = False  # Simulate an Arduino, instead?
if sys.argv[-1] == "simulate":
    SIMULATE_ARDUINO = True

# Show debug info in terminal? Warning: Slow! Do not leave on unintentionally.
DEBUG = False

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
    from PyQt5 import QtCore, QtWidgets as QtWid           # type: ignore
    from PyQt5.QtCore import pyqtSlot as Slot              # type: ignore
elif QT_LIB == PYQT6:
    from PyQt6 import QtCore, QtWidgets as QtWid           # type: ignore
    from PyQt6.QtCore import pyqtSlot as Slot              # type: ignore
elif QT_LIB == PYSIDE2:
    from PySide2 import QtCore, QtWidgets as QtWid         # type: ignore
    from PySide2.QtCore import Slot                        # type: ignore
elif QT_LIB == PYSIDE6:
    from PySide6 import QtCore, QtWidgets as QtWid         # type: ignore
    from PySide6.QtCore import Slot                        # type: ignore
# fmt: on

QT_VERSION = (
    QtCore.QT_VERSION_STR if QT_LIB in (PYQT5, PYQT6) else QtCore.__version__
)

# pylint: enable=import-error, no-name-in-module, c-extension-no-member
# \end[Mechanism to support both PyQt and PySide]
# -----------------------------------------------

import psutil
import numpy as np
import pyqtgraph as pg

print(f"{QT_LIB:9s} {QT_VERSION}")
print(f"PyQtGraph {pg.__version__}")

from dvg_debug_functions import dprint, print_fancy_traceback as pft
from dvg_pyqtgraph_threadsafe import HistoryChartCurve

from dvg_fakearduino import FakeArduino
from dvg_devices.Arduino_protocol_serial import Arduino
from dvg_qdeviceio import QDeviceIO

if TRY_USING_OPENGL:
    try:
        import OpenGL.GL as gl  # pylint: disable=unused-import
        from OpenGL.version import __version__ as gl_version
    except:
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


def get_current_date_time():
    cur_date_time = QtCore.QDateTime.currentDateTime()
    return (
        cur_date_time.toString("dd-MM-yyyy"),  # Date
        cur_date_time.toString("HH:mm:ss"),  # Time
        cur_date_time.toString("yyMMdd_HHmmss"),  # Reverse notation date-time
    )


# ------------------------------------------------------------------------------
#   Arduino state
# ------------------------------------------------------------------------------


class State(object):
    """Reflects the actual readings, parsed into separate variables, of the
    Arduino. There should only be one instance of the State class.
    """

    def __init__(self):
        self.time = None  # [s]
        self.reading_1 = np.nan

        # Mutex for proper multithreading. If the state variables are not
        # atomic or thread-safe, you should lock and unlock this mutex for each
        # read and write operation. In this demo we don't need it, but I keep it
        # as reminder.
        self.mutex = QtCore.QMutex()


state = State()

# ------------------------------------------------------------------------------
#   MainWindow
# ------------------------------------------------------------------------------


class MainWindow(QtWid.QWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.setWindowTitle("Arduino & PyQt multithread demo")
        self.setGeometry(350, 50, 800, 660)

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


# ------------------------------------------------------------------------------
#   Program termination routines
# ------------------------------------------------------------------------------


@Slot()
def about_to_quit():
    print("\nAbout to quit")
    app.processEvents()
    qdev_ard.quit()

    print("Stopping timers: ", end="")
    timer_chart.stop()
    print("done.")

    ard.close()


# ------------------------------------------------------------------------------
#   Your Arduino update function
# ------------------------------------------------------------------------------


def DAQ_function():
    # Date-time keeping
    str_cur_date, str_cur_time, _ = get_current_date_time()

    # Query the Arduino for its state
    success, tmp_state = ard.query_ascii_values("?", delimiter="\t")
    if not (success):
        dprint(f"'{ard.name}' reports IOError @ {str_cur_date} {str_cur_time}")
        return False

    # Parse readings into separate state variables
    try:
        state.time, state.reading_1 = tmp_state
        state.time /= 1000
    except Exception as err:
        pft(err, 3)
        dprint(f"'{ard.name}' reports IOError @ {str_cur_date} {str_cur_time}")
        return False

    # Use Arduino time or PC time?
    USE_PC_TIME = True
    if USE_PC_TIME:
        state.time = time.perf_counter()

    # Add readings to chart history
    window.history_chart_curve.appendData(state.time, state.reading_1)

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
    except:
        print("Warning: Could not set process to maximum priority.\n")

    # --------------------------------------------------------------------------
    #   Connect to Arduino
    # --------------------------------------------------------------------------

    if SIMULATE_ARDUINO:
        ard = FakeArduino()
    else:
        ard = Arduino(name="Ard", connect_to_specific_ID="Wave generator")

    ard.serial_settings["baudrate"] = 115200
    ard.auto_connect()

    if not (ard.is_alive):
        print("\nCheck connection and try resetting the Arduino.")
        print("Exiting...\n")
        sys.exit(0)

    # --------------------------------------------------------------------------
    #   Create application and main window
    # --------------------------------------------------------------------------
    QtCore.QThread.currentThread().setObjectName("MAIN")  # For DEBUG info

    app = QtWid.QApplication(sys.argv)
    app.aboutToQuit.connect(about_to_quit)

    window = MainWindow()

    # --------------------------------------------------------------------------
    #   Set up multithreaded communication with the Arduino
    # --------------------------------------------------------------------------

    # Create QDeviceIO
    qdev_ard = QDeviceIO(ard)

    # Create workers
    qdev_ard.create_worker_DAQ(
        DAQ_function=DAQ_function,
        DAQ_interval_ms=DAQ_INTERVAL_MS,
        DAQ_timer_type=QtCore.Qt.TimerType.PreciseTimer,
        critical_not_alive_count=1,
        debug=DEBUG,
    )

    # Start workers
    qdev_ard.start(DAQ_priority=QtCore.QThread.Priority.TimeCriticalPriority)

    # --------------------------------------------------------------------------
    #   Create timers
    # --------------------------------------------------------------------------

    timer_chart = QtCore.QTimer()
    timer_chart.timeout.connect(window.history_chart_curve.update)
    timer_chart.start(CHART_INTERVAL_MS)

    # --------------------------------------------------------------------------
    #   Start the main GUI event loop
    # --------------------------------------------------------------------------

    window.show()
    if QT_LIB in (PYQT5, PYSIDE2):
        sys.exit(app.exec_())
    else:
        sys.exit(app.exec())
