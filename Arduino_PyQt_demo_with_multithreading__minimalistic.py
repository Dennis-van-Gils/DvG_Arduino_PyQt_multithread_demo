#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Multithreaded demonstration of real-time plotting of live Arduino data using
PyQt5 and PyQtGraph.
"""
__author__      = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__         = "https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo"
__date__        = "23-08-2018"
__version__     = "1.0.0"

import os
import sys
import psutil
from pathlib import Path

from PyQt5 import QtCore
from PyQt5 import QtWidgets as QtWid
from PyQt5.QtCore import QDateTime

import pyqtgraph as pg
import numpy as np

from DvG_PyQt_ChartHistory import ChartHistory
from DvG_debug_functions   import dprint, print_fancy_traceback as pft

import DvG_dev_Arduino__fun_serial as Arduino_functions
import DvG_dev_Arduino__PyQt_lib   as Arduino_pyqt_lib

# Constants
UPDATE_INTERVAL_ARDUINO = 10  # 10 [ms]
UPDATE_INTERVAL_CHART   = 10  # 10 [ms]
CHART_HISTORY_TIME = 10       # 10 [s]

# Global variables for date-time keeping
cur_date_time = QDateTime.currentDateTime()
str_cur_date  = cur_date_time.toString("dd-MM-yyyy")
str_cur_time  = cur_date_time.toString("HH:mm:ss")

# Show debug info in terminal? Warning: slow! Do not leave on unintentionally.
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
        
        # Mutex for proper multithreading. If the state variables are not
        # atomic or thread-safe, you should lock and unlock this mutex for each
        # read and write operation. In this demo we don't need it.
        self.mutex = QtCore.QMutex()

state = State()

# ------------------------------------------------------------------------------
#   MainWindow
# ------------------------------------------------------------------------------

class MainWindow(QtWid.QWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.setGeometry(50, 50, 800, 660)
        self.setWindowTitle("Multithread PyQt & Arduino demo")
        
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
        
        vbox = QtWid.QVBoxLayout(self)
        vbox.addWidget(self.gw_chart, 1)

# ------------------------------------------------------------------------------
#   Program termination routines
# ------------------------------------------------------------------------------

@QtCore.pyqtSlot()
def about_to_quit():
    print("\nAbout to quit")
    
    # First make sure to process all pending events
    app.processEvents()
    
    # Close Arduino worker threads
    ard_pyqt.close_threads()
    
    # Stop timers
    print("Stopping timers: ", end='')
    timer_chart.stop()
    print("done.")
    
    # Close serial connections
    ard.close()

# ------------------------------------------------------------------------------
#   Your Arduino update function(s)
# ------------------------------------------------------------------------------

def my_Arduino_DAQ_update():
    # Date-time keeping
    global cur_date_time, str_cur_date, str_cur_time
    cur_date_time = QDateTime.currentDateTime()
    str_cur_date = cur_date_time.toString("dd-MM-yyyy")
    str_cur_time = cur_date_time.toString("HH:mm:ss")

    # Query the Arduino for its state
    [success, tmp_state] = ard.query_ascii_values("?", separator='\t')
    if not(success):
        dprint("'%s' reports IOError @ %s %s" %
               (ard.name, str_cur_date, str_cur_time))
        return False
    
    # Parse readings into separate state variables
    try:
        [state.time, state.reading_1] = tmp_state
    except Exception as err:
        pft(err, 3)
        dprint("'%s' reports IOError @ %s %s" % 
               (ard.name, str_cur_date, str_cur_time))
        return False

    # Use Arduino time or PC time?
    # Arduino time is more accurate, but rolls over ~49 days for a 32 bit timer.
    use_PC_time = False
    if use_PC_time: state.time = cur_date_time.toMSecsSinceEpoch()

    # Add readings to chart histories
    window.CH_1.add_new_reading(state.time, state.reading_1)

    return True

# ------------------------------------------------------------------------------
#   Main
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    # Set this process priority to maximum in the operating system
    print("PID: %s" % os.getpid())
    try:
        proc = psutil.Process(os.getpid())
        if os.name == "nt":
            # Windows
            proc.nice(psutil.REALTIME_PRIORITY_CLASS)
        else:
            # Other OS's
            proc.nice(-20)
    except:
        print("Warning: Could not set process to maximum priority.")
    
    # --------------------------------------------------------------------------
    #   Connect to Arduino(s)
    # --------------------------------------------------------------------------
    
    ard = Arduino_functions.Arduino(name="Ard", baudrate=115200)
    ard.auto_connect(Path("last_used_port.txt"), 
                     match_identity="Wave generator")

    if not(ard.is_alive):
        print("\nCheck connection and try resetting the Arduino(s)")
        print("Exiting...\n")
        sys.exit(0)
        
    # --------------------------------------------------------------------------
    #   Create application and main window
    # --------------------------------------------------------------------------
    
    app = 0    # Work-around for kernel crash when using Spyder IDE
    app = QtWid.QApplication(sys.argv)
    app.aboutToQuit.connect(about_to_quit)
    
    # For DEBUG info
    QtCore.QThread.currentThread().setObjectName('MAIN')

    window = MainWindow()
    
    # --------------------------------------------------------------------------
    #   Set up communication threads for the Arduino(s)
    # --------------------------------------------------------------------------

    # Create workers and threads
    ard_pyqt = Arduino_pyqt_lib.Arduino_pyqt(
                ard=ard,
                worker_DAQ_update_interval_ms=UPDATE_INTERVAL_ARDUINO,
                worker_DAQ_function_to_run_each_update=my_Arduino_DAQ_update)
    
    # Start threads
    ard_pyqt.start_thread_worker_DAQ()

    # --------------------------------------------------------------------------
    #   Create timers
    # --------------------------------------------------------------------------

    timer_chart = QtCore.QTimer()
    timer_chart.timeout.connect(lambda: window.CH_1.update_curve())
    timer_chart.start(UPDATE_INTERVAL_CHART)

    # --------------------------------------------------------------------------
    #   Start the main GUI loop
    # --------------------------------------------------------------------------
    
    window.show()

    sys.exit(app.exec_())