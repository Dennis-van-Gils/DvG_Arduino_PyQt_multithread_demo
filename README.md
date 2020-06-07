# DvG_Arduino_PyQt_multithread_demo
[![Build Status](https://travis-ci.org/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo.svg?branch=master)](https://travis-ci.org/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo)

Demonstration of multithreaded communication, real-time plotting and logging of live Arduino data using PyQt5 and PyQtGraph.

This demo needs just a bare Arduino(-like) device that, for demonstration purposes, will act as a numerical waveform generator. The source files are included and they should compile over a wide range of Arduino boards. Connect the Arduino to any USB port on your computer and run this Python demo. It should automatically find the Arduino and show you a fully functioning GUI with live data at a stable acquisition rate of 100 Hz.

It features a PyQt5 graphical user-interface, with a PyQtGraph plot for fast real-time plotting of data. The main thread handles the GUI and redrawing of the plot, another thread deals with acquiring data from the Arduino at a fixed rate and a third thread maintains a thread-safe queue where messages to be sent out to the Arduino are managed.

Other depencies you'll need for this demo can be installed by running:
`pip install -r requirements.txt`

* [DvG_debug_functions](https://pypi.org/project/dvg-debug-functions/)
* [DvG_QDeviceIO](https://pypi.org/project/dvg-qdeviceio/)
* [psutil](https://pypi.org/project/psutil/)
* [pySerial](https://pypi.org/project/pyserial/)
* [NumPy](http://www.numpy.org/)
* [PyQt5](https://pypi.org/project/PyQt5/)
* [PyQtGraph](http://pyqtgraph.org/)

![Arduino_PyQt_demo_with_multithreading.png](/images/Arduino_PyQt_demo_with_multithreading.PNG)
