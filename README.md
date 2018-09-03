# DvG_Arduino_PyQt_multithread_demo
[![Build Status](https://travis-ci.org/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo.svg?branch=master)](https://travis-ci.org/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo)

Multithreaded demonstration of real-time plotting and logging of live Arduino data.

It has a PyQt5 graphical user-interface, with a PyQtGraph plot for fast real-time plotting of data, which are obtained from a waveform generating Arduino(-like) device (source files included) at an acquisition rate of 100 Hz, and it provides logging this data to a file. The main thread handles the GUI and redrawing of the plot, another thread deals with acquiring data from the Arduino at a fixed rate and the last thread maintains a thread-safe queue where messages to be sent out to the Arduino are managed.

For convenience all dependendies on my libraries are already embedded in this package. If you want you can find the separate repositories here:

* [DvG_dev_Arduino](https://github.com/Dennis-van-Gils/DvG_dev_Arduino)
* [DvG_debug_functions](https://github.com/Dennis-van-Gils/DvG_debug_functions)
* [DvG_PyQt_misc](https://github.com/Dennis-van-Gils/DvG_PyQt_misc)

Third-party depencies you'll need for this demo:

* [psutil](https://pypi.org/project/psutil/)
* [pySerial](https://pypi.org/project/pyserial/)
* [NumPy](http://www.numpy.org/)
* [PyQt5](https://pypi.org/project/PyQt5/)
* [PyQtGraph](http://pyqtgraph.org/)

![Arduino_PyQt_demo_with_multithreading.png](/images/Arduino_PyQt_demo_with_multithreading.PNG)
