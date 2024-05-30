|demos| |black| |license|

.. |demos| image:: https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo/actions/workflows/python-demos.yml/badge.svg
    :target: https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo/actions/workflows/python-demos.yml
.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
.. |license| image:: https://img.shields.io/badge/License-MIT-purple.svg
    :target: https://github.com/Dennis-van-Gils/DvG_Arduino_PyQt_multithread_demo/blob/master/LICENSE.txt

Arduino PyQt multithread demo
=============================

Demonstration of multithreaded communication, real-time plotting and logging of live Arduino data using PyQt/PySide and PyQtGraph.

This demo needs just a bare Arduino(-like) device that, for demonstration purposes, will act as a numerical waveform generator. The source files are included and they should compile over a wide range of Arduino boards. Connect the Arduino to any USB port on your computer and run this Python demo. It should automatically find the Arduino and show you a fully functioning GUI with live data at a stable acquisition rate of 100 Hz.

::

  Alternatively, you can simulate the Arduino by running `python demo_A_GUI_full.py simulate`.

It features a graphical user-interface, with a PyQtGraph plot for fast real-time plotting of data. The main thread handles the GUI and redrawing of the plot, another thread deals with acquiring data (DAQ) from the Arduino at a fixed rate and a third thread maintains a thread-safe queue where messages to be sent out to the Arduino are managed.


.. image:: /images/Arduino_PyQt_demo_with_multithreading.PNG

Supports PyQt5, PyQt6, PySide2 and PySide6, one of which you'll have to have
installed already in your Python environment.

Other depencies you'll need for this demo can be installed by running::

  pip install -r requirements.txt

PyQtGraph & OpenGL performance
==============================

Enabling OpenGL for plotting within PyQtGraph has major benefits as the drawing will get offloaded to the GPU, instead of being handled by the CPU. However, when PyOpenGL is installed in the Python environment and OpenGL acceleration is enabled inside PyQtGraph as such in order to get full OpenGL support::

    import pyqtgraph as pg
    pg.setConfigOptions(useOpenGL=True)
    pg.setConfigOptions(enableExperimental=True)

the specific version of PyQtGraph will have a major influence on the timing stability of the DAQ routine, even though it is running in a separate dedicated thread. This becomes visible as a fluctuating time stamp in the recorded log file. Remarkably, I observe that ``PyQtGraph==0.11.1 leads to a superior timing stability`` of +/- 1 ms in the recorded time stamps, whereas ``0.12.x`` and ``0.13.1`` are very detrimental to the stability with values of +/- 20 ms. The cause for this lies in the different way that PyQtGraph v0.12+ handles `PlotDataItem()` with PyOpenGL. I suspect that the Python GIL (Global Interpreter Lock) is responsible for this, somehow. There is nothing I can do about that and hopefully this gets resolved in future PyQtGraph versions.

Note to myself
--------------
You can circumvent the DAQ stability issue by going to a more advanced scheme. It would involve having the Arduino perform measurements at a fixed rate *autonomously* and sending this data including the Arduino time stamp over to Python in chunks. The DAQ_worker inside Python should not be of type ``DAQ_TRIGGER.INTERNAL_TIMER`` as per this repo, i.e. Python should not act as a 'master' device, but rather should be of type ``DAQ_TRIGGER.CONTINUOUS`` to act as a slave to the Arduino and continously listen for its data. This advanced scheme is actually implemented in my `Arduino Lock-in Amplifier <https://github.com/Dennis-van-Gils/DvG_Arduino_lock-in_amp>`__ project with good success.

Recommendation
--------------

``Stick with pyqtgraph==0.11.1`` when OpenGL is needed and when consistent and high (> 10 Hz) DAQ rates are required. Unfortunately, ``0.11.1`` only supports PyQt5 or PySide2, not PyQt6 or PySide6 which get supported from of version ``0.12+``.

Note: ``pyqtgraph==0.11.0`` has a line width issue with OpenGL curves and is stuck at 1 pixel, unless you apply `my monkeypatch <https://github.com/Dennis-van-Gils/python-dvg-pyqtgraph-monkeypatch>`_.

