#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyQt5 module to provide multithreaded communication and periodical data
acquisition for an Arduino(-like) device.
"""
__author__      = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__         = "https://github.com/Dennis-van-Gils/DvG_dev_Arduino"
__date__        = "06-09-2018"
__version__     = "2.0.0"

from PyQt5 import QtCore
import DvG_dev_Arduino__fun_serial as Arduino_functions

# Show debug info in terminal? Warning: Slow! Do not leave on unintentionally.
DEBUG_worker_DAQ  = False
DEBUG_worker_send = False

# ------------------------------------------------------------------------------
#   Arduino_pyqt
# ------------------------------------------------------------------------------

class Arduino_pyqt(QtCore.QObject):
    """Manages multithreaded communication and periodical data acquisition for
    an Arduino(-like) device.

    All device I/O operations will be offloaded to 'workers' that each will be
    running in a newly created thread, instead of in the main/GUI thread.

    !! No direct changes to the GUI should be performed inside these workers. If
    !! needed, use the 'QtCore.pyqtSignal()' mechanism to instigate GUI changes.

    See 'DvG_dev_Base__PyQt_lib.py' for more details.

    Args:
        dev:
            Reference to a 'DvG_dev_Arduino__fun_serial.Arduino' instance.

        DAQ_update_interval_ms:
            Desired data acquisition update interval in milliseconds.

        DAQ_function_to_run_each_update:
            Reference to a user-supplied function containing the device query
            operations and subsequent data processing, to be invoked every DAQ
            update. It should return True when everything went successful, and
            False otherwise.

        DAQ_critical_not_alive_count:
            Allow for up to a certain number of communication failures with the
            device before a 'connection lost' signal is emitted.

        DAQ_timer_type:
            The accuracy of the DAQ timer.

    Class instances:
        worker_DAQ:
            Periodically acquires data from the device.

        worker_send:
            Maintains a thread-safe queue where desired device I/O operations
            can be put onto, and sends the queued operations first in first out
            (FIFO) to the device.

    Methods:
        start_thread_worker_DAQ(...)
        start_thread_worker_send(...)
        close_threads()
        send_write(...):
            Send out a write message operation to the Arduino.

    Signals:
        worker_DAQ.signal_DAQ_updated():
            Emitted by the worker when 'update' has finished.

        worker_DAQ.signal_connection_lost():
            Emitted by the worker during 'update' when 'not_alive_counter'
            is equal to or larger than 'critical_not_alive_count'.
    """
    from DvG_dev_Base__PyQt_lib import (Worker_DAQ,
                                        Worker_send,
                                        create_and_set_up_threads,
                                        start_thread_worker_DAQ,
                                        start_thread_worker_send,
                                        close_threads)

    def __init__(self,
                 dev: Arduino_functions.Arduino,
                 DAQ_update_interval_ms,
                 DAQ_function_to_run_each_update=None,
                 DAQ_critical_not_alive_count=3,
                 DAQ_timer_type=QtCore.Qt.PreciseTimer,
                 parent=None):
        super(Arduino_pyqt, self).__init__(parent=parent)

        self.dev = dev
        self.dev.mutex = QtCore.QMutex()

        self.worker_DAQ = self.Worker_DAQ(
                dev,
                DAQ_update_interval_ms,
                DAQ_function_to_run_each_update,
                DAQ_critical_not_alive_count,
                DAQ_timer_type,
                DEBUG=DEBUG_worker_DAQ)

        self.worker_send = self.Worker_send(
                dev,
                DEBUG=DEBUG_worker_send)

        self.create_and_set_up_threads()

    # --------------------------------------------------------------------------
    #   send_write
    # --------------------------------------------------------------------------

    def send_write(self, msg_str):
        """Send out a write message operation to the Arduino via the worker_send
        queue.
        """
        self.worker_send.add_to_queue(self.dev.write, msg_str)
        self.worker_send.process_queue()