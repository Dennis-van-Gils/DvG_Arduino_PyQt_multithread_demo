#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demonstration of singlethreaded real-time plotting and logging of live Arduino
data using PyQt5 and PyQtGraph.

NOTE: This demonstrates the bad case of what happens when both the acquisition
and the plotting happen on the same thread. You should observe a drop in the
acquisition rate (DAQ rate) when you rapidly resize the window, for instance.
And you should notice the timestamps in the recorded data file being all over
the place.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo"
__date__ = "07-08-2020"
__version__ = "7.0"
# pylint: disable=bare-except, broad-except, unnecessary-lambda

import os
import sys
import time

import numpy as np
import psutil

from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets as QtWid
from PyQt5.QtCore import QDateTime
import pyqtgraph as pg

from dvg_debug_functions import tprint, dprint, print_fancy_traceback as pft
from dvg_pyqtgraph_threadsafe import HistoryChartCurve, PlotManager
from dvg_pyqt_filelogger import FileLogger
from dvg_pyqt_controls import (
    create_Toggle_button,
    SS_TEXTBOX_READ_ONLY,
    SS_GROUP,
)

from dvg_fakearduino import FakeArduino
from dvg_devices.Arduino_protocol_serial import Arduino


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
# pg.setConfigOptions(leftButtonPan=False)
pg.setConfigOption("foreground", "#EEE")

# Constants
# fmt: off
DAQ_INTERVAL_MS    = 10  # 10 [ms]
CHART_INTERVAL_MS  = 20  # 20 [ms]
CHART_HISTORY_TIME = 10  # 10 [s]
# fmt: on

# Global flags
USE_PC_TIME = True  # Use Arduino time or PC time?
SIMULATE_ARDUINO = False  # Simulate an Arduino, instead?
if sys.argv[-1] == "simulate":
    SIMULATE_ARDUINO = True

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

        # Keep track of the obtained DAQ rate
        self.update_counter_DAQ = 0
        self.obtained_DAQ_rate_Hz = np.nan
        self.QET_rate = QtCore.QElapsedTimer()
        self.rate_accumulator = 0


state = State()

# ------------------------------------------------------------------------------
#   MainWindow
# ------------------------------------------------------------------------------


class MainWindow(QtWid.QWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.setWindowTitle("Arduino & PyQt singlethread demo")
        self.setStyleSheet(SS_TEXTBOX_READ_ONLY + SS_GROUP)
        self.setGeometry(50, 50, 960, 660)

        # -------------------------
        #   Top frame
        # -------------------------

        # Left box
        self.qlbl_update_counter = QtWid.QLabel("0")
        self.qlbl_DAQ_rate = QtWid.QLabel("DAQ: nan Hz")
        self.qlbl_DAQ_rate.setStyleSheet("QLabel {min-width: 7em}")

        vbox_left = QtWid.QVBoxLayout()
        vbox_left.addWidget(self.qlbl_update_counter, stretch=0)
        vbox_left.addStretch(1)
        vbox_left.addWidget(self.qlbl_DAQ_rate, stretch=0)

        # Middle box
        self.qlbl_title = QtWid.QLabel(
            "Arduino & PyQt singlethread demo",
            font=QtGui.QFont("Palatino", 14, weight=QtGui.QFont.Bold),
        )
        self.qlbl_title.setAlignment(QtCore.Qt.AlignCenter)
        self.qlbl_cur_date_time = QtWid.QLabel("00-00-0000    00:00:00")
        self.qlbl_cur_date_time.setAlignment(QtCore.Qt.AlignCenter)
        self.qpbt_record = create_Toggle_button(
            "Click to start recording to file"
        )
        self.qpbt_record.clicked.connect(lambda state: log.record(state))

        vbox_middle = QtWid.QVBoxLayout()
        vbox_middle.addWidget(self.qlbl_title)
        vbox_middle.addWidget(self.qlbl_cur_date_time)
        vbox_middle.addWidget(self.qpbt_record)

        # Right box
        self.qpbt_exit = QtWid.QPushButton("Exit")
        self.qpbt_exit.clicked.connect(self.close)
        self.qpbt_exit.setMinimumHeight(30)
        self.qlbl_recording_time = QtWid.QLabel(alignment=QtCore.Qt.AlignRight)

        vbox_right = QtWid.QVBoxLayout()
        vbox_right.addWidget(self.qpbt_exit, stretch=0)
        vbox_right.addStretch(1)
        vbox_right.addWidget(self.qlbl_recording_time, stretch=0)

        # Round up top frame
        hbox_top = QtWid.QHBoxLayout()
        hbox_top.addLayout(vbox_left, stretch=0)
        hbox_top.addStretch(1)
        hbox_top.addLayout(vbox_middle, stretch=0)
        hbox_top.addStretch(1)
        hbox_top.addLayout(vbox_right, stretch=0)

        # -------------------------
        #   Bottom frame
        # -------------------------

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

        # 'Readings'
        p = {"readOnly": True, "maximumWidth": 7 * em}
        self.qlin_reading_t = QtWid.QLineEdit(**p)
        self.qlin_reading_1 = QtWid.QLineEdit(**p)
        self.qpbt_running = create_Toggle_button("Running", checked=True)
        self.qpbt_running.clicked.connect(
            lambda state: self.qpbt_running.setText(
                "Running" if state else "Run"
            )
        )

        # fmt: off
        grid = QtWid.QGridLayout()
        grid.addWidget(self.qpbt_running   , 0, 0, 1, 2)
        grid.addWidget(QtWid.QLabel("time"), 1, 0)
        grid.addWidget(self.qlin_reading_t , 1, 1)
        grid.addWidget(QtWid.QLabel("#01") , 2, 0)
        grid.addWidget(self.qlin_reading_1 , 2, 1)
        grid.setAlignment(QtCore.Qt.AlignTop)
        # fmt: on

        qgrp_readings = QtWid.QGroupBox("Readings")
        qgrp_readings.setLayout(grid)

        # 'Wave type'
        self.qpbt_wave_sine = QtWid.QPushButton("Sine")
        self.qpbt_wave_sine.clicked.connect(self.process_qpbt_wave_sine)
        self.qpbt_wave_square = QtWid.QPushButton("Square")
        self.qpbt_wave_square.clicked.connect(self.process_qpbt_wave_square)
        self.qpbt_wave_sawtooth = QtWid.QPushButton("Sawtooth")
        self.qpbt_wave_sawtooth.clicked.connect(self.process_qpbt_wave_sawtooth)

        # fmt: off
        grid = QtWid.QGridLayout()
        grid.addWidget(self.qpbt_wave_sine    , 0, 0)
        grid.addWidget(self.qpbt_wave_square  , 1, 0)
        grid.addWidget(self.qpbt_wave_sawtooth, 2, 0)
        grid.setAlignment(QtCore.Qt.AlignTop)
        # fmt: on

        qgrp_wave_type = QtWid.QGroupBox("Wave type")
        qgrp_wave_type.setLayout(grid)

        # 'Chart'
        self.plot_manager = PlotManager(parent=self)
        self.plot_manager.add_autorange_buttons(linked_plots=self.plot)
        self.plot_manager.add_preset_buttons(
            linked_plots=self.plot,
            linked_curves=self.history_chart_curve,
            presets=[
                {
                    "button_label": "0.100",
                    "x_axis_label": "history (msec)",
                    "x_axis_divisor": 1e-3,
                    "x_axis_range": (-101, 0),
                },
                {
                    "button_label": "0:05",
                    "x_axis_label": "history (sec)",
                    "x_axis_divisor": 1,
                    "x_axis_range": (-5.05, 0),
                },
                {
                    "button_label": "0:10",
                    "x_axis_label": "history (sec)",
                    "x_axis_divisor": 1,
                    "x_axis_range": (-10.1, 0),
                },
            ],
        )
        self.plot_manager.add_clear_button(
            linked_curves=self.history_chart_curve
        )
        self.plot_manager.perform_preset(1)

        qgrp_chart = QtWid.QGroupBox("Chart")
        qgrp_chart.setLayout(self.plot_manager.grid)

        vbox = QtWid.QVBoxLayout()
        vbox.addWidget(qgrp_readings)
        vbox.addWidget(qgrp_wave_type)
        vbox.addWidget(qgrp_chart)
        vbox.addStretch()

        # Round up bottom frame
        hbox_bot = QtWid.QHBoxLayout()
        hbox_bot.addWidget(self.gw, 1)
        hbox_bot.addLayout(vbox, 0)

        # -------------------------
        #   Round up full window
        # -------------------------

        vbox = QtWid.QVBoxLayout(self)
        vbox.addLayout(hbox_top, stretch=0)
        vbox.addSpacerItem(QtWid.QSpacerItem(0, 10))
        vbox.addLayout(hbox_bot, stretch=1)

    # --------------------------------------------------------------------------
    #   Handle controls
    # --------------------------------------------------------------------------

    @QtCore.pyqtSlot()
    def process_qpbt_wave_sine(self):
        ard.write("sine")

    @QtCore.pyqtSlot()
    def process_qpbt_wave_square(self):
        ard.write("square")

    @QtCore.pyqtSlot()
    def process_qpbt_wave_sawtooth(self):
        ard.write("sawtooth")

    @QtCore.pyqtSlot()
    def update_GUI(self):
        str_cur_date, str_cur_time, _ = get_current_date_time()
        self.qlbl_cur_date_time.setText(
            "%s    %s" % (str_cur_date, str_cur_time)
        )
        self.qlbl_update_counter.setText("%i" % state.update_counter_DAQ)
        self.qlbl_DAQ_rate.setText("DAQ: %.1f Hz" % state.obtained_DAQ_rate_Hz)
        if log.is_recording():
            self.qlbl_recording_time.setText(log.pretty_elapsed())
        self.qlin_reading_t.setText("%.3f" % state.time)
        self.qlin_reading_1.setText("%.4f" % state.reading_1)

    @QtCore.pyqtSlot()
    def update_chart(self):
        if DEBUG:
            tprint("update_curve")

        self.history_chart_curve.update()


# ------------------------------------------------------------------------------
#   Program termination routines
# ------------------------------------------------------------------------------


@QtCore.pyqtSlot()
def about_to_quit():
    print("\nAbout to quit")
    app.processEvents()
    log.close()

    print("Stopping timers: ", end="")
    timer_chart.stop()
    print("done.")

    ard.close()


# ------------------------------------------------------------------------------
#   Your Arduino update function
# ------------------------------------------------------------------------------


@QtCore.pyqtSlot()
def DAQ_function():
    # Date-time keeping
    str_cur_date, str_cur_time, str_cur_datetime = get_current_date_time()

    state.update_counter_DAQ += 1

    # Keep track of the obtained DAQ rate
    if not state.QET_rate.isValid():
        state.QET_rate.start()
    else:
        # Obtained DAQ rate
        state.rate_accumulator += 1
        dT = state.QET_rate.elapsed()

        if dT >= 1000:  # Evaluate every N elapsed milliseconds. Hard-coded.
            state.QET_rate.restart()
            try:
                state.obtained_DAQ_rate_Hz = state.rate_accumulator / dT * 1e3
            except ZeroDivisionError:
                state.obtained_DAQ_rate_Hz = np.nan

            state.rate_accumulator = 0

    # Query the Arduino for its state
    success, tmp_state = ard.query_ascii_values("?", delimiter="\t")
    if not (success):
        dprint(
            "'%s' reports IOError @ %s %s"
            % (ard.name, str_cur_date, str_cur_time)
        )
        sys.exit(0)

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
        sys.exit(0)

    if USE_PC_TIME:
        state.time = time.perf_counter()

    # Add readings to chart histories
    window.history_chart_curve.appendData(state.time, state.reading_1)

    # Logging to file
    log.update(filepath=str_cur_datetime + ".txt")

    # We update the GUI right now because this is a singlethread demo
    window.update_GUI()


def write_header_to_log():
    log.write("elapsed [s]\treading_1\n")


def write_data_to_log():
    if USE_PC_TIME:
        timestamp = log.elapsed()  # Starts at 0 s every recording
    else:
        timestamp = state.time

    log.write("%.3f\t%.4f\n" % (timestamp, state.reading_1))


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

    app = QtWid.QApplication(sys.argv)
    app.aboutToQuit.connect(about_to_quit)

    # Width in pixels of character 'm' in the current font
    em = app.fontMetrics().widthChar("m")

    window = MainWindow()

    # --------------------------------------------------------------------------
    #   File logger
    # --------------------------------------------------------------------------

    log = FileLogger(
        write_header_function=write_header_to_log,
        write_data_function=write_data_to_log,
    )
    log.signal_recording_started.connect(
        lambda filepath: window.qpbt_record.setText(
            "Recording to file: %s" % filepath
        )
    )
    log.signal_recording_stopped.connect(
        lambda: window.qpbt_record.setText("Click to start recording to file")
    )

    # --------------------------------------------------------------------------
    #   Create timers
    # --------------------------------------------------------------------------

    timer_state = QtCore.QTimer()
    timer_state.timeout.connect(DAQ_function)
    timer_state.setTimerType(QtCore.Qt.PreciseTimer)
    timer_state.start(DAQ_INTERVAL_MS)

    window.qpbt_running.clicked.connect(
        lambda state: timer_state.start() if state else timer_state.stop()
    )

    timer_chart = QtCore.QTimer()
    # timer_chart.setTimerType(QtCore.Qt.PreciseTimer)
    timer_chart.timeout.connect(window.update_chart)
    timer_chart.start(CHART_INTERVAL_MS)

    # --------------------------------------------------------------------------
    #   Start the main GUI event loop
    # --------------------------------------------------------------------------

    window.show()
    sys.exit(app.exec_())
