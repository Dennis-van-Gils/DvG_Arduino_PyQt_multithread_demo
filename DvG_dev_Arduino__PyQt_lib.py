#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyQt5 module to provide multithreaded periodical data acquisition and
transmission for an Arduino(-like) device.

The communication threads are robust in the following sense. They can be set
to quit as soon as a communication error appears, or they could be set to allow
a certain number of communication errors before they quit. The latter can be
useful in non-critical implementations where continuity of the program is of
more importance than preventing drops in data transmission. This, obviously, is
a work-around for not having to tackle the source of the communication error,
but sometimes you just need to struggle on. E.g., when your Arduino is out in
the field and picks up occasional unwanted interference/ground noise that
messes with your data transmission.

Classes:
    Arduino_pyqt(...):
        Manages multithreaded periodical data acquisition and transmission for
        an Arduino(-like) device.

        Sub-classes:
            Worker_DAQ(...):
                Acquires data from the Arduino at a fixed update interval.
            Worker_send(...):
                Sends out messages to the Arduino using a thread-safe queue.

        Methods:
            send(...):
                Put a write operation on the worker_send queue.
            start_thread_worker_DAQ():
                Must be called to start the worker_DAQ thread.
            start_thread_worker_send():
                Must be called to start the worker_send thread.
            close_threads():
                Close the worker_DAQ and worker_send threads.

        Important member:
            worker_DAQ.function_to_run_each_update:
                Reference to an external function containing the Arduino query
                operations and subsequent data processing, to be invoked every
                DAQ update. It should return True when everything went
                successful, and False otherwise.

        Signals:
            worker_DAQ.signal_DAQ_updated:
                Emitted by the worker when 'update' has finished.
            worker_DAQ.signal_connection_lost:
                Emitted by the worker during 'update' when 'not_alive_counter'
                is equal to or larger than 'critical_not_alive_count'.
"""
__author__      = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__         = "https://github.com/Dennis-van-Gils/DvG_dev_Arduino"
__date__        = "05-09-2018"
__version__     = "1.2.0"

from PyQt5 import QtCore
from PyQt5 import QtWidgets as QtWid

import DvG_dev_Arduino__fun_serial as Arduino_functions

# Show debug info in terminal? Warning: slow! Do not leave on unintentionally.
DEBUG = False

# Short-hand alias for DEBUG information
def curThreadName(): return QtCore.QThread.currentThread().objectName()

# ------------------------------------------------------------------------------
#   Arduino_pyqt
# ------------------------------------------------------------------------------

# INVESTIGATE: Arduino_pyqt should inherit from class QtCore.QObject or from
# QtWidgets.QWidget?

class Arduino_pyqt(QtWid.QWidget):
    """This class provides multithreaded periodical data acquisition and
    transmission for an Arduino(-like) board, from now on referred to as the
    'device'.

    All device I/O operations will be offloaded to separate 'Workers', which
    reside as sub-classes inside of this class. Instances of these workers
    will be moved onto separate threads and will not run on the same thread as
    the GUI. This will keep the GUI and main routines responsive when
    communicating with the device.
    !! No changes to the GUI should be done inside these sub-classes !!

    Two workers are created as class members at init of this class:
        - worker_DAQ
            Periodically acquires data from the device.
            See Worker_DAQ for details.

        - worker_send
            Maintains a queue where desired device I/O operations can be put on
            the stack. First in, first out (FIFO). The worker will send out the
            operations to the device whenever its internal QWaitCondition is
            woken up from sleep by calling 'Worker_send.qwc.wakeAll()'.
            See Worker_send for details.
    """
    from DvG_dev_Base__PyQt_lib import (Worker_DAQ,
                                        Worker_send,
                                        create_and_set_up_threads,
                                        start_thread_worker_DAQ,
                                        start_thread_worker_send,
                                        close_threads)

    def __init__(self,
                 dev: Arduino_functions.Arduino,
                 DAQ_update_interval_ms=250,
                 DAQ_function_to_run_each_update=None,
                 parent=None):
        super(Arduino_pyqt, self).__init__(parent=parent)

        self.dev = dev
        self.dev.mutex = QtCore.QMutex()

        self.worker_DAQ = self.Worker_DAQ(dev,
                                          DAQ_update_interval_ms,
                                          DAQ_function_to_run_each_update)
        self.worker_send = self.Worker_send(dev, DEBUG=False)

        self.create_and_set_up_threads()

    # --------------------------------------------------------------------------
    #   send
    # --------------------------------------------------------------------------

    def send(self, msg_str):
        """Put a 'write a string message' operation on the worker_send queue and
        process the queue.
        """
        self.worker_send.add_to_queue(self.dev.write, msg_str)
        self.worker_send.process_queue()