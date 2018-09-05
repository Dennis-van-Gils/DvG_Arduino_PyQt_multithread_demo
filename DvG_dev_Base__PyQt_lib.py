#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5 import QtCore

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