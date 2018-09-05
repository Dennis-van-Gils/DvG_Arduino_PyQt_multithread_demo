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

import queue
import numpy as np

from PyQt5 import QtCore
from PyQt5 import QtWidgets as QtWid
from PyQt5.QtCore import QDateTime

from DvG_debug_functions import ANSI, dprint

import DvG_dev_Arduino__fun_serial as Arduino_functions

# Show debug info in terminal? Warning: slow! Do not leave on unintentionally.
DEBUG = False

# Short-hand alias for DEBUG information
def curThreadName(): return QtCore.QThread.currentThread().objectName()

# ------------------------------------------------------------------------------
#   Arduino_pyqt
# ------------------------------------------------------------------------------

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
        self.worker_send = self.Worker_send(dev)

        # Create and set up threads
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

    # --------------------------------------------------------------------------
    #   Worker_DAQ
    # --------------------------------------------------------------------------

    class Worker_DAQ(QtCore.QObject):
        """This Worker runs on an internal timer and will acquire data from the
        device at a fixed update interval.

        Args:
            dev:
                Reference to 'DvG_dev_Arduino__fun_serial.Arduino()' instance.

            update_interval_ms:
                Update interval in milliseconds.

            function_to_run_each_update (optional, default=None):
                Every 'update' it will invoke the function that is pointed to by
                'function_to_run_each_update'. This function should contain your
                device query operations and subsequent data processing. It
                should return True when everything went successful, and False
                otherwise. NOTE: No changes to the GUI should run inside this
                function! If you do anyhow, expect a penalty in the timing
                stability of this worker.

                E.g. (pseudo-code), where 'dev' is an instance of
                DvG_dev_Arduino__fun_serial.Arduino():

                def my_update_function():
                    # Query the Arduino for its state
                    [success, tmp_state] = dev.query_ascii_values("state?")
                    if not(success):
                        print("Arduino IOerror")
                        return False

                    # Parse readings into separate variables.
                    try:
                        [time, reading_1] = tmp_state
                    except Exception as err:
                        print(err)
                        return False

                    # Print [time, reading_1] to open file with handle 'f'
                    try:
                        f.write("%.3f\t%.3f\n" % (time, reading_1))
                    except Exception as err:
                        print(err)

                    return True

            critical_not_alive_count (optional, default=3):
                Worker_DAQ will allow for up to a certain number of
                communication failures with the device before hope is given up
                and a 'connection lost' signal is emitted. Use at your own
                discretion.

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
                     dev: Arduino_functions.Arduino,
                     update_interval_ms,
                     function_to_run_each_update=None,
                     critical_not_alive_count=3):
            super().__init__(None)
            self.DEBUG_color=ANSI.CYAN

            self.dev = dev
            self.dev.update_counter = 0
            self.dev.not_alive_counter = 0
            self.update_interval_ms = update_interval_ms
            self.function_to_run_each_update = function_to_run_each_update
            self.dev.critical_not_alive_count = critical_not_alive_count

            # Calculate the DAQ rate around every 1 sec
            self.calc_DAQ_rate_every_N_iter = round(1e3/self.update_interval_ms)
            self.obtained_DAQ_rate = np.nan
            self.prev_tick = 0

            if DEBUG:
                dprint("Worker_DAQ  %s init: thread %s" %
                       (self.dev.name, curThreadName()), self.DEBUG_color)

        @QtCore.pyqtSlot()
        def run(self):
            if DEBUG:
                dprint("Worker_DAQ  %s run : thread %s" %
                       (self.dev.name, curThreadName()), self.DEBUG_color)

            self.timer = QtCore.QTimer()
            self.timer.setInterval(self.update_interval_ms)
            self.timer.timeout.connect(self.update)
            # CRITICAL, 1 ms resolution
            self.timer.setTimerType(QtCore.Qt.PreciseTimer)
            self.timer.start()

        @QtCore.pyqtSlot()
        def update(self):
            self.dev.update_counter += 1
            locker = QtCore.QMutexLocker(self.dev.mutex)

            if DEBUG:
                dprint("Worker_DAQ  %s: iter %i" %
                       (self.dev.name, self.dev.update_counter),
                       self.DEBUG_color)

            # Keep track of the obtained DAQ rate
            # Start at iteration 2 to ensure we have stabilized
            now = QDateTime.currentDateTime()
            if self.dev.update_counter == 2:
                self.prev_tick = now
            elif (self.dev.update_counter %
                  self.calc_DAQ_rate_every_N_iter == 2):
                self.obtained_DAQ_rate = (self.calc_DAQ_rate_every_N_iter /
                                          self.prev_tick.msecsTo(now) * 1e3)
                self.prev_tick = now

            # Check the alive counter
            if (self.dev.not_alive_counter >=
                self.dev.critical_not_alive_count):
                dprint("\nWorker_DAQ determined Arduino '%s' is not alive." %
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

            if DEBUG:
                dprint("Worker_DAQ  %s: unlocked" % self.dev.name,
                       self.DEBUG_color)

            self.signal_DAQ_updated.emit()

    # --------------------------------------------------------------------------
    #   Worker_send
    # --------------------------------------------------------------------------

    class Worker_send(QtCore.QObject):
        """This worker maintains a thread-safe queue where messages to be sent
        to the device can be put on the stack. The worker will send out the
        messages to the device, first in first out (FIFO), until the stack is
        empty again. It sends messages whenever it is woken up by calling
        'Worker_send.qwc.wakeAll()'

        Args:
            dev: Reference to 'DvG_dev_Arduino__fun_serial.Arduino()' instance.

        No changes to the GUI are allowed inside this class!
        """

        def __init__(self, dev: Arduino_functions.Arduino):
            super().__init__(None)
            self.DEBUG_color=ANSI.YELLOW

            self.dev = dev
            self.running = True
            self.mutex = QtCore.QMutex()
            self.qwc = QtCore.QWaitCondition()

            # Use a 'sentinel' value to signal the start and end of the queue
            # to ensure proper multithreaded operation.
            self.sentinel = None
            self.queue = queue.Queue()
            self.queue.put(self.sentinel)

            if DEBUG:
                dprint("Worker_send %s init: thread %s" %
                       (self.dev.name, curThreadName()), self.DEBUG_color)

        @QtCore.pyqtSlot()
        def run(self):
            if DEBUG:
                dprint("Worker_send %s run : thread %s" %
                       (self.dev.name, curThreadName()), self.DEBUG_color)

            while self.running:
                locker_worker = QtCore.QMutexLocker(self.mutex)

                if DEBUG:
                    dprint("Worker_send %s: waiting for trigger" %
                           self.dev.name, self.DEBUG_color)
                self.qwc.wait(self.mutex)
                if DEBUG:
                    dprint("Worker_send %s: trigger received" %
                           self.dev.name, self.DEBUG_color)

                # Process all jobs until the queue is empty.
                # We must iterate 2 times because we use a sentinel in a FIFO
                # queue. First iter removes the old sentinel. Second iter
                # processes the remaining queue items and will put back a new
                # sentinel again.
                #
                # Note: Instead of just write operations, you can also put
                # query operations in the queue and process each reply of
                # the device. You could do this by creating a special value
                # value for 'func', like:
                #
                # if func == "query_id?":
                #     [success, ans_str] = self.dev.query("id?")
                #     # And store the reply 'ans_str' in another variable
                #     # at a higher scope or do stuff with it here.
                # elif:
                #     # Default situation where
                #     # func = self.dev.write
                #     # args = "toggle LED"     # E.g.
                #     func(*args)
                #
                # The (somewhat) complex 'func(*args)' method is used on
                # purpose, because it allows for more flexible schemes.
                for i in range(2):
                    for job in iter(self.queue.get_nowait, self.sentinel):
                        func = job[0]
                        args = job[1:]

                        if DEBUG:
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

            if DEBUG:
                dprint("Worker_send %s: done running" % self.dev.name,
                       self.DEBUG_color)

        @QtCore.pyqtSlot()
        def stop(self):
            self.running = False

    # --------------------------------------------------------------------------
    #   queued_send
    # --------------------------------------------------------------------------

    def queued_send(self, dev_io_function_call, pass_args=()):
        """Put a device I/O function call on the worker_send queue and trigger
        processing the queue.

        Args:
            dev_io_function_call:
                E.g. self.dev.write

            pass_args (optional, default=()):
                Argument(s) to be passed to the function call. Must be a tuple,
                but for convenience any other type will also be accepted if it
                concerns just a single argument that needs to be passed.
        """
        if type(pass_args) is not tuple: pass_args = (pass_args,)
        self.worker_send.queue.put((dev_io_function_call, *pass_args))
        self.worker_send.qwc.wakeAll()

    # --------------------------------------------------------------------------
    #   send
    # --------------------------------------------------------------------------

    def send(self, msg_str):
        """Put a 'write a string message' operation on the worker_send queue and
        process the queue.
        
        Note: This 'send' method is fixed to a 'write' operation to keep things
        simple. The more powerful method is 'queued_send', which allows to put
        any I/O operation on the queue.
        """
        self.queued_send(self.dev.write, msg_str)

    # --------------------------------------------------------------------------
    #   Start threads
    # --------------------------------------------------------------------------

    def start_thread_worker_DAQ(self):
        if self.thread_DAQ is not None:
            self.thread_DAQ.start()
            # Bump up the thread priority in the operating system
            self.thread_DAQ.setPriority(QtCore.QThread.TimeCriticalPriority)
        else:
            print("Worker_DAQ  %s: Can't start because device is not alive" %
                  self.dev.name)

    def start_thread_worker_send(self):
        if self.thread_send is not None:
            self.thread_send.start()
        else:
            print("Worker_send %s: Can't start because device is not alive" %
                  self.dev.name)

    # --------------------------------------------------------------------------
    #   close_threads
    # --------------------------------------------------------------------------

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