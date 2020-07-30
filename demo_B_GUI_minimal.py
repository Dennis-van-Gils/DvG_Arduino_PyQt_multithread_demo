#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demonstration of multithreaded real-time plotting and logging of live Arduino
data using PyQt5 and PyQtGraph.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo"
__date__ = "30-07-2020"
__version__ = "6.0"
# pylint: disable=bare-except, broad-except

import os
import sys
import time

import numpy as np
import psutil

from PyQt5 import QtCore
from PyQt5 import QtWidgets as QtWid
from PyQt5.QtCore import QDateTime
import pyqtgraph as pg

from dvg_debug_functions import dprint, print_fancy_traceback as pft
from dvg_pyqtgraph_threadsafe import HistoryChartCurve
from dvg_devices.Arduino_protocol_serial import Arduino
from dvg_qdeviceio import QDeviceIO

try:
    import OpenGL.GL as gl  # pylint: disable=unused-import
except:
    print("OpenGL acceleration: Disabled")
    print("To install: `conda install pyopengl` or `pip install pyopengl`")
else:
    print("OpenGL acceleration: Enabled")
    pg.setConfigOptions(useOpenGL=True)
    pg.setConfigOptions(antialias=True)
    pg.setConfigOptions(enableExperimental=True)

# Global pyqtgraph configuration
pg.setConfigOptions(leftButtonPan=False)
pg.setConfigOption("foreground", "#EEE")

# Constants
# fmt: off
DAQ_INTERVAL_MS    = 10  # 10 [ms]
CHART_INTERVAL_MS  = 20  # 20 [ms]
CHART_HISTORY_TIME = 10  # 10 [s]
# fmt: on

# Show debug info in terminal? Warning: Slow! Do not leave on unintentionally.
DEBUG = False


def get_current_date_time():
    cur_date_time = QDateTime.currentDateTime()
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

        self.setGeometry(350, 50, 800, 660)
        self.setWindowTitle("Arduino & PyQt multithread demo")

        # GraphicsWindow
        self.gw_chart = pg.GraphicsWindow()
        self.gw_chart.setBackground([20, 20, 20])
        self.pi_chart = self.gw_chart.addPlot()

        p = {"color": "#EEE", "font-size": "10pt"}
        self.pi_chart.showGrid(x=1, y=1)
        self.pi_chart.setLabel("bottom", text="history (sec)", **p)
        self.pi_chart.setLabel("left", text="amplitude", **p)
        self.pi_chart.setRange(
            xRange=[-1.04 * CHART_HISTORY_TIME, CHART_HISTORY_TIME * 0.04],
            yRange=[-1.1, 1.1],
            disableAutoRange=True,
        )

        self.history_chart_curve = HistoryChartCurve(
            capacity=round(CHART_HISTORY_TIME * 1e3 / DAQ_INTERVAL_MS),
            linked_curve=self.pi_chart.plot(
                pen=pg.mkPen(color=[255, 255, 90], width=3)
            ),
        )

        vbox = QtWid.QVBoxLayout(self)
        vbox.addWidget(self.gw_chart, 1)


# ------------------------------------------------------------------------------
#   Program termination routines
# ------------------------------------------------------------------------------


@QtCore.pyqtSlot()
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
        dprint(
            "'%s' reports IOError @ %s %s"
            % (ard.name, str_cur_date, str_cur_time)
        )
        return False

    # Parse readings into separate state variables
    try:
        state.time, state.reading_1 = tmp_state
        state.time /= 1000
    except Exception as err:
        pft(err, 3)
        dprint(
            "'%s' reports IOError @ %s %s"
            % (ard.name, str_cur_date, str_cur_time)
        )
        return False

    # Use Arduino time or PC time?
    use_PC_time = True
    if use_PC_time:
        state.time = time.perf_counter()

    # Add readings to chart history
    window.history_chart_curve.append_data(state.time, state.reading_1)

    return True


# ------------------------------------------------------------------------------
#   Main
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # Set priority of this process to maximum in the operating system
    print("PID: %s\n" % os.getpid())
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

    ard = Arduino(name="Ard", connect_to_specific_ID="Wave generator")

    ard.serial_settings["baudrate"] = 115200
    ard.auto_connect("last_used_port.txt")

    if not (ard.is_alive):
        print("\nCheck connection and try resetting the Arduino.")
        print("Exiting...\n")
        sys.exit(0)

    # --------------------------------------------------------------------------
    #   Create application and main window
    # --------------------------------------------------------------------------
    QtCore.QThread.currentThread().setObjectName("MAIN")  # For DEBUG info

    app = 0  # Work-around for kernel crash when using Spyder IDE
    app = QtWid.QApplication(sys.argv)
    app.aboutToQuit.connect(about_to_quit)

    window = MainWindow()

    # --------------------------------------------------------------------------
    #   Set up multithreaded communication with the Arduino
    # --------------------------------------------------------------------------

    # Create QDeviceIO
    qdev_ard = QDeviceIO(ard)

    # Create workers
    # fmt: off
    qdev_ard.create_worker_DAQ(
        DAQ_function             = DAQ_function,
        DAQ_interval_ms          = DAQ_INTERVAL_MS,
        critical_not_alive_count = 1,
        debug                    = DEBUG,
    )
    # fmt: on

    # Start workers
    qdev_ard.start(DAQ_priority=QtCore.QThread.TimeCriticalPriority)

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
    sys.exit(app.exec_())
