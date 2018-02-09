from glue.config import keyboard_shortcut
from qtpy import QtCore, QtWidgets, QtGui, compat


@keyboard_shortcut(QtCore.Qt.Key_A, None)
def move_slider_left(session):
    """
    Move slider index one to the left
    :param session:
    :return:
    """
    curr_layout = session.application.current_tab.ui
    curr_layout.change_slice_index(-1)


@keyboard_shortcut(QtCore.Qt.Key_D, None)
def move_slider_right(session):
    """
    Move slider index one to the right
    :param session:
    :return:
    """
    curr_layout = session.application.current_tab.ui
    curr_layout.change_slice_index(1)
