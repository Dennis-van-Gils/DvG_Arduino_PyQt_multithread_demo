.. image:: https://travis-ci.org/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo.svg?branch=master
    :target: https://travis-ci.org/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo
.. image:: https://requires.io/github/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo/requirements.svg?branch=master
    :target: https://requires.io/github/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo/requirements/?branch=master
    :alt: Requirements Status
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
.. image:: https://img.shields.io/badge/License-MIT-purple.svg
    :target: https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo/blob/master/LICENSE.txt

DvG_Arduino_PyQt_multithread_demo
=================================

Demonstration of multithreaded communication, real-time plotting and logging of live Arduino data using PyQt5 and PyQtGraph.

This demo needs just a bare Arduino(-like) device that, for demonstration purposes, will act as a numerical waveform generator. The source files are included and they should compile over a wide range of Arduino boards. Connect the Arduino to any USB port on your computer and run this Python demo. It should automatically find the Arduino and show you a fully functioning GUI with live data at a stable acquisition rate of 100 Hz.

It features a PyQt5 graphical user-interface, with a PyQtGraph plot for fast real-time plotting of data. The main thread handles the GUI and redrawing of the plot, another thread deals with acquiring data from the Arduino at a fixed rate and a third thread maintains a thread-safe queue where messages to be sent out to the Arduino are managed.

.. image:: /images/Arduino_PyQt_demo_with_multithreading.PNG

Other depencies you'll need for this demo can be installed by running::
  
  pip install -r requirements.txt

* `dvg-debug-functions <https://pypi.org/project/dvg-debug-functions/>`_
* `dvg-qdeviceio <https://pypi.org/project/dvg-qdeviceio/>`_
* `dvg-devices <https://pypi.org/project/dvg-devices/>`_
* `dvg-pyqtgraph-threadsafe <https://pypi.org/project/dvg-pyqtgraph-threadsafe/>`_
* `psutil <https://pypi.org/project/psutil/>`_
* `pySerial <https://pypi.org/project/pyserial/>`_
* `NumPy <http://www.numpy.org/>`_
* `PyQt5 <https://pypi.org/project/PyQt5/>`_
* `PyQtGraph <http://pyqtgraph.org/>`_
