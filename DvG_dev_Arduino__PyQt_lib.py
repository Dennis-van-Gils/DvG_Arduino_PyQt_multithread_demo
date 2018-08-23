#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyQt5 module to provide multithreaded functionality to perform periodical
data acquisition and transmission for an Arduino(-like) device.

The communication threads are robust in the following sense. They can be set
to quit as soon as a communication error appears, or they could be set to allow
a certain number of communication errors before they quit. The latter can be
usefull in non-critical implementations where continuity of the program is of
more importance than preventing drops in data transmission. This, obviously, is
a work-around for not having to tackle the source of the communication error,
but sometimes you just need to struggle on. E.g., when electronics are out in
the field and pick up occasional unwanted interference/ground noise that plays
havoc on the data transmission.

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
                successfull, and False otherwise.
                
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
__date__        = "23-08-2018"
__version__     = "1.0.0"

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
curThread = QtCore.QThread.currentThread

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
            the stack. The worker will periodically send out the operations to
            the device as scheduled in the queue.
            See Worker_send for details.
    """

    def __init__(self,
                 ard: Arduino_functions.Arduino,
                 worker_DAQ_update_interval_ms=250,
                 worker_DAQ_function_to_run_each_update=None,
                 worker_send_msleep=50,
                 parent=None):
        super(Arduino_pyqt, self).__init__(parent=parent)

        # Store reference to 'DvG_dev_Arduino__fun_serial.Arduino()' instance
        self.ard = ard

        # Create mutex for proper multithreading
        self.ard.mutex = QtCore.QMutex()

        # Periodically acquires data from the device.
        # !! Will be put in a seperate thread !!
        self.worker_DAQ = self.Worker_DAQ(ard,
                worker_DAQ_update_interval_ms,
                worker_DAQ_function_to_run_each_update)

        # Maintains a queue where desired device I/O operations can be put on
        # the stack. The worker will periodically send out the operations to the
        # device as scheduled in the queue.
        # !! Will be put in a seperate thread !!
        self.worker_send = self.Worker_send(ard, worker_send_msleep)
        
        # Create and set up threads
        if self.ard.is_alive:
            self.thread_DAQ = QtCore.QThread()
            self.thread_DAQ.setObjectName("%s_DAQ" % self.ard.name)
            self.worker_DAQ.moveToThread(self.thread_DAQ)
            self.thread_DAQ.started.connect(self.worker_DAQ.run)

            self.thread_send = QtCore.QThread()
            self.thread_send.setObjectName("%s_send" % self.ard.name)
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
            ard:
                Reference to 'DvG_dev_Arduino__fun_serial.Arduino()' instance.

            update_interval_ms:
                Update interval in milliseconds.
            
            function_to_run_each_update (optional, default=None):
                Every 'update' it will invoke the function that is pointed to by
                'function_to_run_each_update'. This function should contain your
                device query operations and subsequent data processing. It
                should return True when everything went successfull, and False
                otherwise. NOTE: No changes to the GUI should run inside this
                function! If you do anyhow, expect a penalty in the timing
                stability of this worker.
                
                E.g. (pseudo-code), where 'ard' is an instance of
                DvG_dev_Arduino__fun_serial.Arduino():
                
                def my_update_function():
                    # Query the Arduino for its state
                    [success, tmp_state] = ard.query_ascii_values("state?")
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
                
            DEBUG_color (optional):
                ANSI color code string containing the terminal text color for
                outputting debug information, e.g. '\x1b[1;31m' for red.
                
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
                     ard: Arduino_functions.Arduino,
                     update_interval_ms,
                     function_to_run_each_update=None,
                     critical_not_alive_count=3,
                     DEBUG_color=ANSI.CYAN):
            super().__init__(None)

            self.ard = ard
            self.ard.update_counter = 0
            self.ard.not_alive_counter = 0
            self.ard.critical_not_alive_count = critical_not_alive_count
            
            self.update_interval_ms = update_interval_ms
            self.function_to_run_each_update = function_to_run_each_update
            
            # Calculate the DAQ rate around every 1 sec
            self.calc_DAQ_rate_every_N_iter = round(1e3/self.update_interval_ms)
            self.obtained_DAQ_rate = np.nan
            self.prev_tick = 0

            # Terminal text color for DEBUG information
            self.DEBUG_color = DEBUG_color

            if DEBUG:
                dprint("Worker_DAQ  %s init: thread %s" %
                       (self.ard.name, curThread().objectName()),
                       self.DEBUG_color)

        @QtCore.pyqtSlot()
        def run(self):
            if DEBUG:
                dprint("Worker_DAQ  %s run : thread %s" %
                       (self.ard.name, curThread().objectName()),
                       self.DEBUG_color)

            self.timer = QtCore.QTimer()
            self.timer.setInterval(self.update_interval_ms)
            self.timer.timeout.connect(self.update)
            # CRITICAL, 1 ms resolution
            self.timer.setTimerType(QtCore.Qt.PreciseTimer)
            self.timer.start()

        @QtCore.pyqtSlot()
        def update(self):
            self.ard.update_counter += 1
            locker = QtCore.QMutexLocker(self.ard.mutex)
            
            if DEBUG:
                dprint("Worker_DAQ  %s: iter %i" %
                       (self.ard.name, self.ard.update_counter),
                       self.DEBUG_color)
            
            # Keep track of the obtained DAQ rate
            # Start at iteration 2 to ensure we have stabilized
            now = QDateTime.currentDateTime()
            if self.ard.update_counter == 2:
                self.prev_tick = now
            elif (self.ard.update_counter %
                  self.calc_DAQ_rate_every_N_iter == 2):
                self.obtained_DAQ_rate = (self.calc_DAQ_rate_every_N_iter /
                                          self.prev_tick.msecsTo(now) * 1e3)
                self.prev_tick = now
            
            # Check the alive counter
            if (self.ard.not_alive_counter >= 
                self.ard.critical_not_alive_count):
                dprint("\nWorker_DAQ determined Arduino '%s' is not alive." %
                       self.ard.name)
                self.ard.is_alive = False
                
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
                    self.ard.not_alive_counter += 1
            
            # ------------------------
            #   End external code
            # ------------------------
            
            locker.unlock()
            
            if DEBUG:
                dprint("Worker_DAQ  %s: unlocked" % self.ard.name,
                       self.DEBUG_color)

            # Send signal that update is finished
            self.signal_DAQ_updated.emit()
            
    # --------------------------------------------------------------------------
    #   Worker_send
    # --------------------------------------------------------------------------
    
    class Worker_send(QtCore.QObject):
        """This worker maintains a thread-safe queue where messages to be sent
        to the device can be put on the stack. The worker will send out the
        messages to the device, first in first out (FIFO), until the stack is
        empty again. It sends messages at a non-strict time interval (see
        argument 'thread_msleep').
        
        Args:
            ard:
                Reference to 'DvG_dev_Arduino__fun_serial.Arduino()' instance.
                
            thread_msleep (default=50):
                The Worker_send thread is not running on an internal timer and
                must be slowed down to prevent hogging the CPU. Must be 1 ms at
                minimum to allow Worker_DAQ to come in between and work fine.
                
            DEBUG_color (optional):
                ANSI color code string containing the terminal text color for
                outputting debug information, e.g. '\x1b[1;31m'.
        """

        def __init__(self,
                     ard: Arduino_functions.Arduino,
                     thread_msleep=50,
                     DEBUG_color=ANSI.YELLOW):
            super().__init__(None)

            self.ard = ard
            self.running = True
            self.thread_msleep = thread_msleep

            # Put a 'sentinel' value in the queue to signal the end. This way we
            # can prevent a Queue.Empty exception being thrown later on when we
            # will read the queue till the end.
            self.sentinel = None
            self.queue = queue.Queue()
            self.queue.put(self.sentinel)

            # Terminal text color for DEBUG information
            self.DEBUG_color = DEBUG_color

            if DEBUG:
                dprint("Worker_send %s init: thread %s" %
                       (self.ard.name, curThread().objectName()),
                       self.DEBUG_color)

        @QtCore.pyqtSlot()
        def run(self):
            if DEBUG:
                dprint("Worker_send %s run : thread %s" %
                       (self.ard.name, curThread().objectName()),
                       self.DEBUG_color)

            while self.running:
                #if DEBUG:
                #    dprint("Worker_send %s queued: %s" %
                #           (self.ard.name, self.queue.qsize() - 1),
                #           self.DEBUG_color)

                # Process all jobs until the queue is empty
                for job in iter(self.queue.get_nowait, self.sentinel):
                    func = job[0]
                    args = job[1:]
                     
					# Note: Instead of just write operations, you can also put
					# query operations in the queue and process each reply of
					# the device. You could do this by creating a special value
					# value for 'func', like:
					#
					# if func == "query_id?":
					#     [success, ans_str] = self.ard.query("id?")
					#     # And store the reply 'ans_str' in another variable
					#     # at a higher scope or do stuff with it here.
					# elif:
					#     # Default situation where
					#     # func = self.ard.write
					#     # args = "toggle LED"     # E.g.
					#     func(*args)
					#
					# The (somewhat) complex 'func(*args)' method is used on
					# purpose, because it allows for more flexible schemes.
					 
                    if DEBUG:
                        dprint("Worker_send %s: %s %s" %
                               (self.ard.name, func.__name__, args),
                               self.DEBUG_color)

                    # Send message to the device
                    locker = QtCore.QMutexLocker(self.ard.mutex)
                    func(*args)
                    locker.unlock()

                self.queue.put(self.sentinel)  # Put sentinel back in

                # Must slow down thread to prevent hogging the CPU
                QtCore.QThread.msleep(self.thread_msleep)

            if DEBUG:
                dprint("Worker_send %s: done running" % self.ard.name,
                       self.DEBUG_color)

        @QtCore.pyqtSlot()
        def stop(self):
            self.running = False
            
    # --------------------------------------------------------------------------
    #   send
    # --------------------------------------------------------------------------
            
    def send(self, write_msg_str):
        """Put a write operation on the worker_send queue.
        """
        self.worker_send.queue.put([self.ard.write, write_msg_str])

    # --------------------------------------------------------------------------
    #   Start threads
    # --------------------------------------------------------------------------

    def start_thread_worker_DAQ(self):
        if self.thread_DAQ is not None:
            self.thread_DAQ.start()
            
            # Bump up the thread priority in the operating system
            self.thread_DAQ.setPriority(QtCore.QThread.TimeCriticalPriority)
        else:
            print("ERROR: Can't start worker_DAQ thread because '%s' is not "
                  "alive" % self.ard.name)

    def start_thread_worker_send(self):
        if self.thread_send is not None:
            self.thread_send.start()
        else:
            print("ERROR: Can't start worker_send thread because '%s' is not "
                  "alive" % self.ard.name)

    # --------------------------------------------------------------------------
    #   close_threads
    # --------------------------------------------------------------------------

    def close_threads(self):
        if self.thread_DAQ is not None:
            #self.worker_DAQ.stop()  # Not necessary
            self.thread_DAQ.quit()
            print("Closing thread %-9s: " % self.thread_DAQ.objectName(),
                  end='')
            if self.thread_DAQ.wait(2000): print("done.\n", end='')
            else: print("FAILED.\n", end='')

        if self.thread_send is not None:
            self.worker_send.stop()
            self.thread_send.quit()
            print("Closing thread %-9s: " % self.thread_send.objectName(),
                  end='')
            if self.thread_send.wait(2000): print("done.\n", end='')
            else: print("FAILED.\n", end='')
            
