#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyQt5 module to provide the base framework for multithreaded communication
and periodical data acquisition for an I/O device.

MODUS OPERANDI:
---------------
    
All device I/O operations will be offloaded to 'workers' that each will be
running in a newly created thread, instead of in the main/GUI thread.

    - Worker_DAQ
        Periodically acquires data from the device.
        See Worker_DAQ for details.

    - Worker_send
        Maintains a thread-safe queue where desired device I/O operations can be
        put onto, and sends the queued operations first in first out (FIFO) to
        the device.
        See Worker_send for details.

CONTENTS:
---------

Classes:
    Worker_DAQ(...)
        Signals:
            signal_DAQ_updated()
            signal_connection_lost()
            
    Worker_send(...)        
        Methods:
            add_to_queue(...)
            process_queue()
    
Functions:
    create_and_set_up_threads()
    start_thread_worker_DAQ(...)
    start_thread_worker_send(...)
    close_threads()
    
"""
__author__      = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__         = "https://github.com/Dennis-van-Gils/DvG_dev_Arduino"
__date__        = "06-09-2018"
__version__     = "2.0.0"

import queue
import numpy as np
from PyQt5 import QtCore
from DvG_debug_functions import ANSI, dprint

# Short-hand alias for DEBUG information
def curThreadName(): return QtCore.QThread.currentThread().objectName()

# ------------------------------------------------------------------------------
#   Worker_DAQ
# ------------------------------------------------------------------------------

class Worker_DAQ(QtCore.QObject):
    """This worker acquires data from the device at a fixed update interval.
    It does so by calling a user-supplied function containing your device I/O
    operations (and data parsing, processing or more), every update period.
    
    The worker should be placed inside a separate thread. No direct changes to
    the GUI should be performed inside this class. If needed, use the
    QtCore.pyqtSignal() mechanism to instigate GUI changes.
    
    The Worker_DAQ routine is robust in the following sense. It can be set to
    quit as soon as a communication error appears, or it could be set to allow
    a certain number of communication errors before it quits. The latter can be
    useful in non-critical implementations where continuity of the program is of
    more importance than preventing drops in data transmission. This, obviously,
    is a work-around for not having to tackle the source of the communication
    error, but sometimes you just need to struggle on. E.g., when your Arduino
    is out in the field and picks up occasional unwanted interference/ground
    noise that messes with your data transmission.

    Args:
        dev:
            Reference to a 'device' instance with I/O methods.

        update_interval_ms:
            Desired data acquisition update interval in milliseconds.

        function_to_run_each_update (optional, default=None):
            Reference to a user-supplied function containing the device query
            operations and subsequent data processing, to be invoked every DAQ
            update. It should return True when everything went successful, and
            False otherwise.
            
            NOTE: No changes to the GUI should run inside this function! If you
            do anyhow, expect a penalty in the timing stability of this worker.

            E.g. pseudo-code, where 'time' and 'reading_1' are variables that
            live at a higher scope, presumably at main/GUI scope level.

            def my_update_function():
                # Query the device for its state
                [success, tmp_state] = dev.query_ascii_values("state?")
                if not(success):
                    print("Device IOerror")
                    return False

                # Parse readings into separate variables
                try:
                    [time, reading_1] = tmp_state
                except Exception as err:
                    print(err)
                    return False

                return True

        critical_not_alive_count (optional, default=1):
            The worker will allow for up to a certain number of communication
            failures with the device before hope is given up and a 'connection
            lost' signal is emitted. Use at your own discretion.
            
        timer_type (PyQt5.QtCore.Qt.TimerType, optional, default=
                    PyQt5.QtCore.Qt.CoarseTimer):
            The update interval is timed to a QTimer running inside Worker_DAQ.
            The accuracy of the timer can be improved by setting it to
            PyQt5.QtCore.Qt.PreciseTimer with ~1 ms granularity, but it is
            resource heavy. Use sparingly.
            
        DEBUG (bool, optional, default=False):
            Show debug info in terminal? Warning: Slow! Do not leave on
            unintentionally.

    Signals:
        signal_DAQ_updated:
            Emitted by the worker when 'update' has finished.
            
        signal_connection_lost:
            Emitted by the worker during 'update' when 'not_alive_counter'
            is equal to or larger than 'critical_not_alive_count'.
    """
    signal_DAQ_updated     = QtCore.pyqtSignal()
    signal_connection_lost = QtCore.pyqtSignal()

    def __init__(self,
                 dev,
                 update_interval_ms,
                 function_to_run_each_update=None,
                 critical_not_alive_count=3,
                 timer_type=QtCore.Qt.CoarseTimer,
                 DEBUG=False):
        super().__init__(None)
        self.DEBUG = DEBUG
        self.DEBUG_color=ANSI.CYAN

        self.dev = dev
        self.dev.update_counter = 0
        self.dev.not_alive_counter = 0
        self.dev.critical_not_alive_count = critical_not_alive_count

        self.update_interval_ms = update_interval_ms
        self.function_to_run_each_update = function_to_run_each_update
        self.timer_type = timer_type

        # Calculate the DAQ rate around every 1 sec
        self.calc_DAQ_rate_every_N_iter = round(1e3/self.update_interval_ms)
        self.dev.obtained_DAQ_rate = np.nan
        self.prev_tick = 0

        if self.DEBUG:
            dprint("Worker_DAQ  %s init: thread %s" %
                   (self.dev.name, curThreadName()), self.DEBUG_color)

    @QtCore.pyqtSlot()
    def run(self):
        if self.DEBUG:
            dprint("Worker_DAQ  %s run : thread %s" %
                   (self.dev.name, curThreadName()), self.DEBUG_color)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.update_interval_ms)
        self.timer.timeout.connect(self.update)
        self.timer.setTimerType(self.timer_type)
        self.timer.start()

    @QtCore.pyqtSlot()
    def update(self):
        self.dev.update_counter += 1
        locker = QtCore.QMutexLocker(self.dev.mutex)

        if self.DEBUG:
            dprint("Worker_DAQ  %s: iter %i" %
                   (self.dev.name, self.dev.update_counter),
                   self.DEBUG_color)

        # Keep track of the obtained DAQ rate
        # Start at iteration 5 to ensure we have stabilized
        now = QtCore.QDateTime.currentDateTime()
        if self.dev.update_counter == 5:
            self.prev_tick = now
        elif (self.dev.update_counter %
              self.calc_DAQ_rate_every_N_iter == 5):
            self.dev.obtained_DAQ_rate = (self.calc_DAQ_rate_every_N_iter /
                                          self.prev_tick.msecsTo(now) * 1e3)
            self.prev_tick = now

        # Check the alive counter
        if (self.dev.not_alive_counter >=
            self.dev.critical_not_alive_count):
            dprint("\nWorker_DAQ %s: Determined device is not alive anymore." %
                   self.dev.name)
            self.dev.is_alive = False

            locker.unlock()
            self.timer.stop()
            self.signal_DAQ_updated.emit()
            self.signal_connection_lost.emit()
            return

        # ------------------------
        #   External code
        # ------------------------

        if not(self.function_to_run_each_update is None):
            if not(self.function_to_run_each_update()):
                self.dev.not_alive_counter += 1

        # ------------------------
        #   End external code
        # ------------------------

        locker.unlock()

        if self.DEBUG:
            dprint("Worker_DAQ  %s: unlocked" % self.dev.name,
                   self.DEBUG_color)

        self.signal_DAQ_updated.emit()

# ------------------------------------------------------------------------------
#   Worker_send
# ------------------------------------------------------------------------------

class Worker_send(QtCore.QObject):
    """This worker maintains a thread-safe queue where desired device I/O
    operations can be put onto. The worker will send out the operations to the
    device, first in first out (FIFO), until the queue is empty again. 
    
    The worker should be placed inside a separate thread. This worker uses the
    QWaitCondition mechanism. Hence, it will only send out all operations
    collected in the queue, whenever the thread it lives in is woken up by
    calling 'Worker_send.process_queue()'. When it has emptied the queue, the
    thread will go back to sleep again.
    
    No direct changes to the GUI should be performed inside this class. If
    needed, use the QtCore.pyqtSignal() mechanism to instigate GUI changes.
    
    Args:
        dev:
            Reference to a 'device' instance with I/O methods.
        
        DEBUG (bool, optional, default=False):
            Show debug info in terminal? Warning: Slow! Do not leave on
            unintentionally.
            
    Methods:
        add_to_queue(...):
            Put a device I/O function call on the worker_send queue.
            
        process_queue():
            Trigger processing the worker_send queue.
    """

    def __init__(self, dev, DEBUG=False):
        super().__init__(None)
        self.DEBUG = DEBUG
        self.DEBUG_color = ANSI.YELLOW

        self.dev = dev
        self.running = True
        self.mutex = QtCore.QMutex()
        self.qwc = QtCore.QWaitCondition()

        # Use a 'sentinel' value to signal the start and end of the queue
        # to ensure proper multithreaded operation.
        self.sentinel = None
        self.queue = queue.Queue()
        self.queue.put(self.sentinel)

        if self.DEBUG:
            dprint("Worker_send %s init: thread %s" %
                   (self.dev.name, curThreadName()), self.DEBUG_color)

    @QtCore.pyqtSlot()
    def run(self):
        if self.DEBUG:
            dprint("Worker_send %s run : thread %s" %
                   (self.dev.name, curThreadName()), self.DEBUG_color)

        while self.running:
            locker_worker = QtCore.QMutexLocker(self.mutex)

            if self.DEBUG:
                dprint("Worker_send %s: waiting for trigger" %
                       self.dev.name, self.DEBUG_color)
            self.qwc.wait(self.mutex)
            if self.DEBUG:
                dprint("Worker_send %s: trigger received" %
                       self.dev.name, self.DEBUG_color)

            """Process all jobs until the queue is empty. We must iterate 2
            times because we use a sentinel in a FIFO queue. First iter removes
            the old sentinel. Second iter processes the remaining queue items
            and will put back a new sentinel again.
            
            Note: Instead of just write operations, you can also put query
            operations in the queue and process each reply of the device. You
            could do this by creating a special value for 'func', like:
            
              if func == "query_id?":
                  [success, ans_str] = self.dev.query("id?")
                  # And store the reply 'ans_str' in another variable
                  # at a higher scope or do stuff with it here.
              elif:
                  # Default situation where, e.g.
                  # func = self.dev.write
                  # args = "toggle LED"
                  func(*args)
             
            The (somewhat) complex 'func(*args)' method is used on purpose,
            because it allows for more flexible schemes.
            """
            for i in range(2):
                for job in iter(self.queue.get_nowait, self.sentinel):
                    func = job[0]
                    args = job[1:]

                    if self.DEBUG:
                        dprint("Worker_send %s: %s %s" %
                               (self.dev.name, func.__name__, args),
                               self.DEBUG_color)

                    # Send I/O operation to the device
                    locker = QtCore.QMutexLocker(self.dev.mutex)
                    func(*args)
                    locker.unlock()

                # Put sentinel back in
                self.queue.put(self.sentinel)

            locker_worker.unlock()

        if self.DEBUG:
            dprint("Worker_send %s: done running" % self.dev.name,
                   self.DEBUG_color)

    @QtCore.pyqtSlot()
    def stop(self):
        self.running = False

    def add_to_queue(self, dev_io_function_call, pass_args=()):
        """Put a device I/O function call on the worker_send queue.

        Args:
            dev_io_function_call:
                E.g. self.dev.write

            pass_args (optional, default=()):
                Argument(s) to be passed to the function call. Must be a tuple,
                but for convenience any other type will also be accepted if it
                concerns just a single argument that needs to be passed.
        """
        if type(pass_args) is not tuple: pass_args = (pass_args,)
        self.queue.put((dev_io_function_call, *pass_args))

    def process_queue(self):
        """Trigger processing the worker_send queue.
        """
        self.qwc.wakeAll()

# ------------------------------------------------------------------------------
#   create_and_set_up_threads
# ------------------------------------------------------------------------------

def create_and_set_up_threads(self):
    if self.dev.is_alive:
        self.thread_DAQ = QtCore.QThread()
        self.thread_DAQ.setObjectName("%s_DAQ" % self.dev.name)
        self.worker_DAQ.moveToThread(self.thread_DAQ)
        self.thread_DAQ.started.connect(self.worker_DAQ.run)

        self.thread_send = QtCore.QThread()
        self.thread_send.setObjectName("%s_send" % self.dev.name)
        self.worker_send.moveToThread(self.thread_send)
        self.thread_send.started.connect(self.worker_send.run)
    else:
        self.thread_DAQ = None
        self.thread_send = None

# ------------------------------------------------------------------------------
#   Start threads
# ------------------------------------------------------------------------------

def start_thread_worker_DAQ(self, priority=QtCore.QThread.InheritPriority):
    if self.thread_DAQ is not None:
        self.thread_DAQ.start(priority)
    else:
        print("Worker_DAQ  %s: Can't start because device is not alive" %
              self.dev.name)

def start_thread_worker_send(self, priority=QtCore.QThread.InheritPriority):
    if self.thread_send is not None:
        self.thread_send.start(priority)
    else:
        print("Worker_send %s: Can't start because device is not alive" %
              self.dev.name)

# ------------------------------------------------------------------------------
#   close_threads
# ------------------------------------------------------------------------------

def close_threads(self):
    if self.thread_DAQ is not None:
        self.thread_DAQ.quit()
        print("Closing thread %-9s: " %
              self.thread_DAQ.objectName(), end='')
        if self.thread_DAQ.wait(2000): print("done.\n", end='')
        else: print("FAILED.\n", end='')

    if self.thread_send is not None:
        self.worker_send.stop()
        self.worker_send.qwc.wakeAll()
        self.thread_send.quit()
        print("Closing thread %-9s: " %
              self.thread_send.objectName(), end='')
        if self.thread_send.wait(2000): print("done.\n", end='')
        else: print("FAILED.\n", end='')