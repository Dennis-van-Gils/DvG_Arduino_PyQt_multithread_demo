#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import queue

from PyQt5 import QtCore

from DvG_debug_functions import ANSI, dprint

# Short-hand alias for DEBUG information
def curThreadName(): return QtCore.QThread.currentThread().objectName()

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
        dev: Reference to an 'device' instance.

    No changes to the GUI are allowed inside this class!
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

def start_thread_worker_DAQ(self):
    if self.thread_DAQ is not None:
        self.thread_DAQ.start()
    else:
        print("Worker_DAQ  %s: Can't start because device is not alive" %
              self.dev.name)

def start_thread_worker_send(self):
    if self.thread_send is not None:
        self.thread_send.start()
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