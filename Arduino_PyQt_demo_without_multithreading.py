#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demonstration of single-threaded real-time plotting and logging of live Arduino
data using PyQt5 and PyQtGraph.

NOTE: This demonstrates the bad case of what happens when both the acquisition
and the plotting happen on the same thread. You should observe a drop in the
acquisition rate (DAQ rate) when you e.g. rapidly resize the window.
"""
__author__      = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__         = "https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo"
__date__        = "07-09-2018"
__version__     = "1.0.0"

import os
import sys
from pathlib import Path

import numpy as np
import psutil

from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets as QtWid
from PyQt5.QtCore import QDateTime
import pyqtgraph as pg

from DvG_pyqt_FileLogger   import FileLogger
from DvG_pyqt_ChartHistory import ChartHistory
from DvG_pyqt_controls     import create_Toggle_button, SS_GROUP
from DvG_debug_functions   import dprint, print_fancy_traceback as pft

import DvG_dev_Arduino__fun_serial as Arduino_functions

# Constants
UPDATE_INTERVAL_ARDUINO = 10  # 10 [ms]
UPDATE_INTERVAL_CHART   = 10  # 10 [ms]
CHART_HISTORY_TIME      = 10  # 10 [s]

# Global variables for date-time keeping
cur_date_time = QDateTime.currentDateTime()
str_cur_date  = cur_date_time.toString("dd-MM-yyyy")
str_cur_time  = cur_date_time.toString("HH:mm:ss")

# Show debug info in terminal? Warning: Slow! Do not leave on unintentionally.
DEBUG = False

# ------------------------------------------------------------------------------
#   Arduino state
# ------------------------------------------------------------------------------

class State(object):
    """Reflects the actual readings, parsed into separate variables, of the
    Arduino(s). There should only be one instance of the State class.
    """
    def __init__(self):
        self.time = np.nan          # [ms]
        self.reading_1 = np.nan
        
        self.update_counter = 0
        self.calc_DAQ_rate_every_N_iter = round(1e3/UPDATE_INTERVAL_ARDUINO)
        self.obtained_DAQ_rate = np.nan
        self.prev_tick = 0

state = State()

# ------------------------------------------------------------------------------
#   MainWindow
# ------------------------------------------------------------------------------

class MainWindow(QtWid.QWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.setGeometry(50, 50, 800, 660)
        self.setWindowTitle("Single-thread PyQt & Arduino demo")
        
        # -------------------------
        #   Top frame
        # -------------------------
        
        # Left box
        self.qlbl_update_counter = QtWid.QLabel("0")
        self.qlbl_DAQ_rate = QtWid.QLabel("DAQ: 0 Hz")
        self.qlbl_DAQ_rate.setMinimumWidth(100)

        vbox_left = QtWid.QVBoxLayout()
        vbox_left.addWidget(self.qlbl_update_counter, stretch=0)
        vbox_left.addStretch(1)
        vbox_left.addWidget(self.qlbl_DAQ_rate, stretch=0)
        
         # Middle box
        self.qlbl_title = QtWid.QLabel("Single-thread PyQt & Arduino demo",
                font=QtGui.QFont("Palatino", 14, weight=QtGui.QFont.Bold))
        self.qlbl_title.setAlignment(QtCore.Qt.AlignCenter)
        self.qlbl_cur_date_time = QtWid.QLabel("00-00-0000    00:00:00")
        self.qlbl_cur_date_time.setAlignment(QtCore.Qt.AlignCenter)
        self.qpbt_record = create_Toggle_button(
                "Click to start recording to file", minimumHeight=40)
        self.qpbt_record.clicked.connect(self.process_qpbt_record)

        vbox_middle = QtWid.QVBoxLayout()
        vbox_middle.addWidget(self.qlbl_title)
        vbox_middle.addWidget(self.qlbl_cur_date_time)
        vbox_middle.addWidget(self.qpbt_record)
        
        # Right box
        self.qpbt_exit = QtWid.QPushButton("Exit")
        self.qpbt_exit.clicked.connect(self.close)
        self.qpbt_exit.setMinimumHeight(30)

        vbox_right = QtWid.QVBoxLayout()
        vbox_right.addWidget(self.qpbt_exit, stretch=0)
        vbox_right.addStretch(1)

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

        # Create PlotItem
        self.gw_chart = pg.GraphicsWindow()
        self.gw_chart.setBackground([20, 20, 20])
        self.pi_chart = self.gw_chart.addPlot()
        
        p = {'color': '#BBB', 'font-size': '10pt'}
        self.pi_chart.showGrid(x=1, y=1)
        self.pi_chart.setTitle('Arduino timeseries', **p)
        self.pi_chart.setLabel('bottom', text='history (sec)', **p)
        self.pi_chart.setLabel('left', text='readings', **p)
        self.pi_chart.setRange(
            xRange=[-1.04 * CHART_HISTORY_TIME, CHART_HISTORY_TIME * 0.04],
            yRange=[-1.1, 1.1],
            disableAutoRange=True)
        
        # Create ChartHistory and PlotDataItem and link them together
        PEN_01 = pg.mkPen(color=[0, 200, 0], width=3)
        num_samples = round(CHART_HISTORY_TIME*1e3/UPDATE_INTERVAL_ARDUINO)
        self.CH_1 = ChartHistory(num_samples, self.pi_chart.plot(pen=PEN_01))
        self.CH_1.x_axis_divisor = 1000     # From [ms] to [s]
        
        # 'Readings'
        p = {'readOnly': True}
        self.qlin_reading_t = QtWid.QLineEdit(**p)
        self.qlin_reading_1 = QtWid.QLineEdit(**p)

        grid = QtWid.QGridLayout()
        grid.addWidget(QtWid.QLabel("time"), 0, 0)
        grid.addWidget(self.qlin_reading_t , 0, 1)
        grid.addWidget(QtWid.QLabel("#01") , 1, 0)
        grid.addWidget(self.qlin_reading_1 , 1, 1)
        grid.setAlignment(QtCore.Qt.AlignTop)

        qgrp_readings = QtWid.QGroupBox("Readings")
        qgrp_readings.setStyleSheet(SS_GROUP)
        qgrp_readings.setLayout(grid)
        
        # 'Wave type'
        self.qpbt_wave_sine = QtWid.QPushButton("Sine")
        self.qpbt_wave_sine.clicked.connect(self.process_qpbt_wave_sine)
        self.qpbt_wave_square = QtWid.QPushButton("Square")
        self.qpbt_wave_square.clicked.connect(self.process_qpbt_wave_square)
        self.qpbt_wave_sawtooth = QtWid.QPushButton("Sawtooth")
        self.qpbt_wave_sawtooth.clicked.connect(self.process_qpbt_wave_sawtooth)
        
        grid = QtWid.QGridLayout()
        grid.addWidget(self.qpbt_wave_sine    , 0, 0)
        grid.addWidget(self.qpbt_wave_square  , 1, 0)
        grid.addWidget(self.qpbt_wave_sawtooth, 2, 0)
        grid.setAlignment(QtCore.Qt.AlignTop)
        
        qgrp_wave_type = QtWid.QGroupBox("Wave type")
        qgrp_wave_type.setStyleSheet(SS_GROUP)
        qgrp_wave_type.setLayout(grid)

        # 'Chart'
        self.qpbt_clear_chart = QtWid.QPushButton("Clear")
        self.qpbt_clear_chart.clicked.connect(self.process_qpbt_clear_chart)

        grid = QtWid.QGridLayout()
        grid.addWidget(self.qpbt_clear_chart, 0, 0)
        grid.setAlignment(QtCore.Qt.AlignTop)

        qgrp_chart = QtWid.QGroupBox("Chart")
        qgrp_chart.setStyleSheet(SS_GROUP)
        qgrp_chart.setLayout(grid)

        vbox = QtWid.QVBoxLayout()
        vbox.addWidget(qgrp_readings)
        vbox.addWidget(qgrp_wave_type)
        vbox.addWidget(qgrp_chart)
        vbox.addStretch()

        # Round up bottom frame
        hbox_bot = QtWid.QHBoxLayout()
        hbox_bot.addWidget(self.gw_chart, 1)
        hbox_bot.addLayout(vbox, 0)
        
        # -------------------------
        #   Round up full window
        # -------------------------
        
        vbox = QtWid.QVBoxLayout(self)
        vbox.addLayout(hbox_top, stretch=0)
        vbox.addSpacerItem(QtWid.QSpacerItem(0, 20))
        vbox.addLayout(hbox_bot, stretch=1)

    # --------------------------------------------------------------------------
    #   Handle controls
    # --------------------------------------------------------------------------

    @QtCore.pyqtSlot()
    def process_qpbt_clear_chart(self):
        str_msg = "Are you sure you want to clear the chart?"
        reply = QtWid.QMessageBox.warning(window, "Clear chart", str_msg,
                                          QtWid.QMessageBox.Yes |
                                          QtWid.QMessageBox.No,
                                          QtWid.QMessageBox.No)
    
        if reply == QtWid.QMessageBox.Yes:
            self.CH_1.clear()

    @QtCore.pyqtSlot()
    def process_qpbt_record(self):
        if self.qpbt_record.isChecked():
            file_logger.starting = True
        else:
            file_logger.stopping = True

    @QtCore.pyqtSlot()
    def process_qpbt_wave_sine(self):
        ard.write("sine")
        
    @QtCore.pyqtSlot()
    def process_qpbt_wave_square(self):
        ard.write("square")
        
    @QtCore.pyqtSlot()
    def process_qpbt_wave_sawtooth(self):
        ard.write("sawtooth")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

@QtCore.pyqtSlot()
def update_GUI():
    window.qlbl_cur_date_time.setText("%s    %s" % (str_cur_date, str_cur_time))
    window.qlbl_update_counter.setText("%i" % state.update_counter)
    window.qlbl_DAQ_rate.setText("DAQ: %.1f Hz" % state.obtained_DAQ_rate)
    window.qlin_reading_t.setText("%i" % state.time)
    window.qlin_reading_1.setText("%.4f" % state.reading_1)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

@QtCore.pyqtSlot()
def update_chart():
    if DEBUG:
        tick = QDateTime.currentDateTime()

    window.CH_1.update_curve()
    
    if DEBUG:
        tack = QDateTime.currentDateTime()
        dprint("  update_curve done in %d ms" % tick.msecsTo(tack))

# ------------------------------------------------------------------------------
#   Program termination routines
# ------------------------------------------------------------------------------

@QtCore.pyqtSlot()
def about_to_quit():
    print("\nAbout to quit")
    app.processEvents()
    file_logger.close_log()
    
    print("Stopping timers: ", end='')
    timer_chart.stop()
    print("done.")

    ard.close()

# ------------------------------------------------------------------------------
#   Your Arduino update function
# ------------------------------------------------------------------------------

@QtCore.pyqtSlot()
def my_Arduino_DAQ_update():
    # Date-time keeping
    global cur_date_time, str_cur_date, str_cur_time
    cur_date_time = QDateTime.currentDateTime()
    str_cur_date = cur_date_time.toString("dd-MM-yyyy")
    str_cur_time = cur_date_time.toString("HH:mm:ss")

    state.update_counter += 1
    
    # Keep track of the obtained DAQ rate
    # Start at iteration 2 to ensure we have stabilized
    now = QDateTime.currentDateTime()
    if state.update_counter == 2:
        state.prev_tick = now
    elif (state.update_counter %
          state.calc_DAQ_rate_every_N_iter == 2):
        state.obtained_DAQ_rate = (state.calc_DAQ_rate_every_N_iter /
                                   state.prev_tick.msecsTo(now) * 1e3)
        state.prev_tick = now

    # Query the Arduino for its state
    [success, tmp_state] = ard.query_ascii_values("?", separator='\t')
    if not(success):
        dprint("'%s' reports IOError @ %s %s" %
               (ard.name, str_cur_date, str_cur_time))
    
    # Parse readings into separate state variables
    try:
        [state.time, state.reading_1] = tmp_state
    except Exception as err:
        pft(err, 3)
        dprint("'%s' reports IOError @ %s %s" % 
               (ard.name, str_cur_date, str_cur_time))

    # Use Arduino time or PC time?
    # Arduino time is more accurate, but rolls over ~49 days for a 32 bit timer.
    use_PC_time = True
    if use_PC_time: state.time = cur_date_time.toMSecsSinceEpoch()

    # Add readings to chart histories
    window.CH_1.add_new_reading(state.time, state.reading_1)

    # Logging to file    
    if file_logger.starting:
        fn_log = cur_date_time.toString("yyMMdd_HHmmss") + ".txt"
        if file_logger.create_log(state.time, fn_log, mode='w'):
            window.qpbt_record.setText("Recording to file: " + fn_log)           
            file_logger.write("elapsed [s]\treading_1\n")
            
    if file_logger.stopping:
        window.qpbt_record.setText("Click to start recording to file")
        file_logger.close_log()

    if file_logger.is_recording:
        log_elapsed_time = (state.time - file_logger.start_time)/1e3  # [sec]
        file_logger.write("%.3f\t%.4f\n" % (log_elapsed_time, state.reading_1))
        
    # We update the GUI right now because this is a single-thread demo
    update_GUI()

# ------------------------------------------------------------------------------
#   Main
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    # Set priority of this process to maximum in the operating system
    print("PID: %s\n" % os.getpid())
    try:
        proc = psutil.Process(os.getpid())
        if os.name == "nt": proc.nice(psutil.REALTIME_PRIORITY_CLASS) # Windows
        else: proc.nice(-20)                                          # Other
    except:
        print("Warning: Could not set process to maximum priority.\n")
    
    # --------------------------------------------------------------------------
    #   Connect to Arduino
    # --------------------------------------------------------------------------
    
    ard = Arduino_functions.Arduino(name="Ard", baudrate=115200)
    ard.auto_connect(Path("last_used_port.txt"), 
                     match_identity="Wave generator")

    if not(ard.is_alive):
        print("\nCheck connection and try resetting the Arduino.")
        print("Exiting...\n")
        sys.exit(0)
        
    # --------------------------------------------------------------------------
    #   Create application and main window
    # --------------------------------------------------------------------------
    
    app = 0    # Work-around for kernel crash when using Spyder IDE
    app = QtWid.QApplication(sys.argv)
    app.aboutToQuit.connect(about_to_quit)

    window = MainWindow()
    
    # --------------------------------------------------------------------------
    #   File logger
    # --------------------------------------------------------------------------

    file_logger = FileLogger()

    # --------------------------------------------------------------------------
    #   Create timers
    # --------------------------------------------------------------------------

    timer_state = QtCore.QTimer()
    timer_state.timeout.connect(my_Arduino_DAQ_update)
    timer_state.setTimerType(QtCore.Qt.PreciseTimer)
    timer_state.start(UPDATE_INTERVAL_ARDUINO)

    timer_chart = QtCore.QTimer()
    timer_chart.timeout.connect(update_chart)
    timer_chart.start(UPDATE_INTERVAL_CHART)

    # --------------------------------------------------------------------------
    #   Start the main GUI event loop
    # --------------------------------------------------------------------------
    
    window.show()
    sys.exit(app.exec_())