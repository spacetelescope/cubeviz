from glue.config import keyboard_shortcut
from qtpy import QtCore, QtWidgets, QtGui, compat


@keyboard_shortcut(QtCore.Qt.Key_Left, None)
def move_slider_left(session):
    return