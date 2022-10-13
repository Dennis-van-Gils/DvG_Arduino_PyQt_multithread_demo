.. image:: https://app.travis-ci.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo.svg?branch=master
    :target: https://app.travis-ci.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo
.. image:: https://requires.io/github/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo/requirements.svg?branch=master
    :target: https://requires.io/github/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo/requirements/?branch=master
    :alt: Requirements Status
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
.. image:: https://img.shields.io/badge/License-MIT-purple.svg
    :target: https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo/blob/master/LICENSE.txt

DvG_Arduino_PyQt_multithread_demo
=================================

Demonstration of multithreaded communication, real-time plotting and logging of live Arduino data using PyQt/PySide and PyQtGraph.

This demo needs just a bare Arduino(-like) device that, for demonstration purposes, will act as a numerical waveform generator. The source files are included and they should compile over a wide range of Arduino boards. Connect the Arduino to any USB port on your computer and run this Python demo. It should automatically find the Arduino and show you a fully functioning GUI with live data at a stable acquisition rate of 100 Hz.

Alternatively, you can simulate the Arduino by running ``python demo_A_GUI_full.py simulate``.

It features a graphical user-interface, with a PyQtGraph plot for fast real-time plotting of data. The main thread handles the GUI and redrawing of the plot, another thread deals with acquiring data from the Arduino at a fixed rate and a third thread maintains a thread-safe queue where messages to be sent out to the Arduino are managed.


.. image:: /images/Arduino_PyQt_demo_with_multithreading.PNG

Supports PyQt5, PyQt6, PySide2 and PySide6, one of which you'll have to have
installed already in your Python environment.

Other depencies you'll need for this demo can be installed by running::

  pip install -r requirements.txt

PyQtGraph performance
=====================

The specific version of PyQtGraph *can* have major influence on the timing stability of the DAQ routine whenever OpenGL is enabled, visible as a fluctuating time stamp in a recorded log file. I observe that ``PyQtGraph==0.11`` leads to a great timing stability of +/- 1 ms, whereas ``0.12.4`` and ``0.13.1`` are very detrimental to the stability with values of +/- 20 ms. The reason for this is still unknown. I have to investigate further.
