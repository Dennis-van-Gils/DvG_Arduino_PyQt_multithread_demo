#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mishmash of PyQt5 stylesheets and custom controls that I personally use in
many of my projects.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/python-dvg-pyqt-controls"
__date__ = "05-08-2020"
__version__ = "1.0.0"

from PyQt5 import QtCore
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QCursor

COLOR_INDIAN_RED_2 = "rgb(225, 102, 102)"
COLOR_SPRING_GREEN_2 = "rgb(0, 238, 118)"
COLOR_BISQUE_5 = "rgb(252, 218, 183)"
COLOR_READ_ONLY = "rgb(252, 240, 227)"
COLOR_BUTTON_BG = "rgb(232, 232, 232)"
COLOR_LED_NEUTRAL = "rgb(240, 240, 240)"

# ------------------------------------------------------------------------------
#   Style sheets
# ------------------------------------------------------------------------------

# fmt: off
SS_TEXTBOX_READ_ONLY = (
    "QLineEdit {"
        "padding: 0 2px;"
        "border: 1px solid gray;}"

    "QLineEdit:read-only {"
        "background: " + COLOR_READ_ONLY + ";}"

    "QLineEdit::hover {"
        "border-color: black;}"

    "QPlainTextEdit {"
        "border: 1px solid gray;}"

    'QPlainTextEdit[readOnly="true"] {'
        "background-color: " + COLOR_READ_ONLY + ";}"

    "QPlainTextEdit::hover {"
        "border-color: black;}"
)

SS_TEXTBOX_ERRORS = (
    "QLineEdit {"
        "padding: 0 2px;"
        "border: 1px solid gray;"
        "background: " + COLOR_READ_ONLY + ";}"

    "QLineEdit:read-only {"
        "border: 2px solid red;"
        "background: yellow;"
        "color: black;}"

    "QLineEdit::hover {"
            "border-color: black;}"

    "QLineEdit:read-only::hover {"
        "border-color: red;}"

    "QPlainTextEdit {"
        "border: 1px solid gray;"
        "background-color: " + COLOR_READ_ONLY + ";}"

    'QPlainTextEdit[readOnly="true"] {'
        "border: 2px solid red;"
        "background-color: yellow;"
        "color: black;}"

    "QPlainTextEdit::hover {"
        "border-color: black;}"

    'QPlainTextEdit[readOnly="true"]::hover {'
        "border-color: red;}"
)

SS_GROUP = (
    "QGroupBox {"
        "background-color: " + COLOR_BISQUE_5 + ";"
        "border: 2px solid gray;"
        "border-radius: 5px;"
        "font: bold;"
        "padding: 8 0 0 0px;"
        "margin-top: 2ex;}"

    "QGroupBox:title {"
        "subcontrol-origin: margin;"
        "subcontrol-position: top left;"
        "padding: 0 3px;}"

    "QGroupBox:flat {"
        "border: 0px;"
        "border-radius: 0 0px;"
        "padding: 0;}"
)

SS_TITLE = (
    "QLabel {"
        "background-color: " + COLOR_BISQUE_5 + ";"
        "padding: 10px;"
        "border-radius: 5px;"
        "font: bold;}"
)
# fmt: on

# ------------------------------------------------------------------------------
#   LEDs
# ------------------------------------------------------------------------------


def create_LED_indicator(**kwargs) -> QPushButton:
    """
    False: dim red
    True : green
    """
    # fmt: off
    SS = (
        "QPushButton {"
            "background-color: " + COLOR_INDIAN_RED_2 + ";"
            "color: black;"
            "border: 1px solid black;"
            "border-radius: 15px;"
            "max-height: 30px;"
            "max-width: 30px;"
            "height: 30px;"
            "width: 30px;}"

        "QPushButton:checked {"
            "background-color: " + COLOR_SPRING_GREEN_2 + ";}"
    )
    # fmt: on
    button = QPushButton(checkable=True, enabled=False, **kwargs)
    button.setStyleSheet(SS)
    return button


def create_LED_indicator_rect(**kwargs) -> QPushButton:
    """
    False: dim red
    True : green
    """
    # fmt: off
    SS = (
        "QPushButton {"
            "background-color: " + COLOR_INDIAN_RED_2 + ";"
            "color: black;"
            "border: 1px solid black;"
            "border-radius: 0px;"
            "min-height: 30px;"
            "min-width: 76px;}"

        "QPushButton:checked {"
            "background-color: " + COLOR_SPRING_GREEN_2 + ";}"
    )
    # fmt: on
    button = QPushButton(checkable=True, enabled=False, **kwargs)
    button.setStyleSheet(SS)
    return button


def create_error_LED(**kwargs) -> QPushButton:
    """
    False: green
    True : red
    """
    # fmt: off
    SS = (
        "QPushButton {"
            "background-color: " + COLOR_SPRING_GREEN_2 + ";"
            "color: black;"
            "border: 1px solid black;"
            "border-radius: 0px;"
            "min-height: 30px;"
            "min-width: 30px;}"

        "QPushButton:checked {"
            "font-weight: bold;"
            "background-color: red;}"
    )
    # fmt: on
    button = QPushButton(checkable=True, enabled=False, **kwargs)
    button.setStyleSheet(SS)
    return button


def create_tiny_LED(**kwargs) -> QPushButton:
    """
    False: neutral
    True : green
    """
    # fmt: off
    SS = (
        "QPushButton {"
            "background-color: " + COLOR_LED_NEUTRAL + ";"
            "color: black;"
            "border: 1px solid black;"
            "border-radius: 5px;"
            "max-height: 10px;"
            "max-width: 10px;"
            "height: 10px;"
            "width: 10px;}"

        "QPushButton:checked {"
            "background-color: " + COLOR_SPRING_GREEN_2 + ";}"
    )
    # fmt: on
    button = QPushButton(checkable=True, enabled=False, **kwargs)
    button.setStyleSheet(SS)
    return button


def create_tiny_error_LED(**kwargs) -> QPushButton:
    """
    False: neutral
    True : red
    """
    # fmt: off
    SS = (
        "QPushButton {"
            "background-color: " + COLOR_LED_NEUTRAL + ";"
            "color: black;"
            "border: 1px solid black;"
            "border-radius: 5px;"
            "max-height: 10px;"
            "max-width: 10px;"
            "height: 10px;"
            "width: 10px;}"

        "QPushButton:checked {"
            "background-color: red;}"
    )
    # fmt: on
    button = QPushButton(checkable=True, enabled=False, **kwargs)
    button.setStyleSheet(SS)
    return button


# ------------------------------------------------------------------------------
#   Toggle buttons
# ------------------------------------------------------------------------------

DFLT_TOGGLE_BTN_PADDING = "6px 6px 6px 6px"
DFLT_TOGGLE_BTN_BORDER_WIDTH = "2px"
DFLT_TOGGLE_BTN_BORDER_RADIUS = "5px"


def create_Relay_button(text: str = "", **kwargs) -> QPushButton:
    """
    False: dim red
    True : green
    """
    # fmt: off
    SS = (
        "QPushButton {"
            "border-style: inset;"
            "border-width: 1px;"
            "max-height: 30px;"
            "max-width: 30px;"
            "height: 30px;"
            "width: 30px;"
            "background-color: " + COLOR_INDIAN_RED_2 + ";}"

        "QPushButton:disabled {"
            "border: 1px solid black;"
            "border-radius: 15px;"
            "color: black;}"

        "QPushButton:checked {"
            "border-style: outset;"
            "background-color: " + COLOR_SPRING_GREEN_2 + ";}"

        "QPushButton::hover {"
            "border-color: black;}"
    )
    # fmt: on
    button = QPushButton(text=text, checkable=True, **kwargs)
    button.setStyleSheet(SS)
    button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))

    # NOTE: Do not enable below code. There is a good reason to not change the
    # relay button label immediately at click. The text-value "0" or "1" can
    # better be set after the relay operation was deemed successful by the main
    # program.
    #
    # def set_text_clicked(button):
    #    button.setText("1" if button.isChecked() else "0")
    # button.clicked.connect(lambda: set_text_clicked(button))
    # set_text_clicked(button)

    return button


def create_Toggle_button(text: str = "", **kwargs) -> QPushButton:
    """
    False: default
    True : green
    """
    # fmt: off
    SS = (
        "QPushButton {"
            "background-color: " + COLOR_BUTTON_BG + ";"
            "border-style: outset;"
            "border-color: gray dimgray dimgray gray;"
            "border-width: " + DFLT_TOGGLE_BTN_BORDER_WIDTH + ";"
            "border-radius: " + DFLT_TOGGLE_BTN_BORDER_RADIUS + ";"
            "padding: " + DFLT_TOGGLE_BTN_PADDING + ";"
            "color: black;}"

        "QPushButton:disabled {"
            "color: dimgray;}"

        "QPushButton:checked {"
            "background-color: " + COLOR_SPRING_GREEN_2 + ";"
            "border-style: inset;"
            "border-color: dimgray mediumspringgreen mediumspringgreen dimgray;}"
    )
    # fmt: on
    button = QPushButton(text=text, checkable=True, **kwargs)
    button.setStyleSheet(SS)
    button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
    return button


def create_Toggle_button_2(text: str = "", **kwargs) -> QPushButton:
    """
    False: default
    True : warning red-lined yellow
    """
    # fmt: off
    SS = (
        "QPushButton {"
            "background-color: " + COLOR_BUTTON_BG + ";"
            "border-style: outset;"
            "border-color: gray dimgray dimgray gray;"
            "border-width: " + DFLT_TOGGLE_BTN_BORDER_WIDTH + ";"
            "border-radius: " + DFLT_TOGGLE_BTN_BORDER_RADIUS + ";"
            "padding: " + DFLT_TOGGLE_BTN_PADDING + ";"
            "color: black;}"

        "QPushButton:disabled {"
            "color: dimgray;}"

        "QPushButton:checked {"
            "background-color: yellow;"
            "border-style: groove;"
            "border-color: firebrick red red firebrick;"
            "font-weight: bold;}"
    )
    # fmt: on
    button = QPushButton(text=text, checkable=True, **kwargs)
    button.setStyleSheet(SS)
    button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
    return button


def create_Toggle_button_3(text: str = "", **kwargs) -> QPushButton:
    """
    False: warning red-lined yellow
    True : green
    """
    # fmt: off
    SS = (
        "QPushButton {"
            "background-color: yellow;"
            "border-style: ridge;"
            "border-color: red firebrick firebrick red;"
            "border-width: " + DFLT_TOGGLE_BTN_BORDER_WIDTH + ";"
            "border-radius: " + DFLT_TOGGLE_BTN_BORDER_RADIUS + ";"
            "padding: " + DFLT_TOGGLE_BTN_PADDING + ";"
            "color: black;"
            "font-weight: bold;}"

        "QPushButton:disabled {"
            "color: dimgray;}"

        "QPushButton:checked {"
            "background-color: " + COLOR_SPRING_GREEN_2 + ";"
            "border-style: inset;"
            "border-color: dimgray mediumspringgreen mediumspringgreen dimgray;"
            "border-width: " + DFLT_TOGGLE_BTN_BORDER_WIDTH + ";"
            "font-weight: normal;}"
    )
    # fmt: on
    button = QPushButton(text=text, checkable=True, **kwargs)
    button.setStyleSheet(SS)
    button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
    return button
