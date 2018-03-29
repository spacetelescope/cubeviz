from glue.config import keyboard_shortcut
from qtpy import QtCore, QtWidgets, QtGui, compat
from qtpy.QtWidgets import QApplication
from glue.config import viewer_tool
import matplotlib.pyplot as plt

from .tools.wavelengths_ui import WavelengthUI

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


@keyboard_shortcut(QtCore.Qt.Key_F, None)
def lock_coordinates(session):
    """
    Lock coordinates in the bottom right of the viewer window
    :param session:
    :return:
    """
    lay = session.application.current_tab
    for w in lay.cube_views:
        civ = w._widget
        if civ.is_mouse_over:
            civ.toggle_hold_coords()


@keyboard_shortcut(QtCore.Qt.Key_P, None)
def copy_coordinates_to_clipboard(session):
    """
    Copy coordinates to clipboard so user can paste them elsewhere
    :param session:
    :return:
    """
    coords_status = False
    lay = session.application.current_tab
    for w in lay.cube_views:
        civ = w._widget
        if civ.is_mouse_over:
            coords_status = civ.get_coords()
            break

    if coords_status:
        cb = QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText(coords_status, mode=cb.Clipboard)


@keyboard_shortcut(QtCore.Qt.Key_1, None)
def show_wavelength_dialog(session):
    """
    Popup the Wavelength dialog in order to change the units or redshift.

    :param session:
    :return:
    """
    WavelengthUI(session.application.tab(0)._wavelength_controller, parent=session.application.tab(0))


def remove_mpl_shortcuts_and_check_dupes():
    """
    Makes sure that shortcut keys do not overlap between the three things (glue.config.viewer_tool, MatPlotLib,
    and keyboard_shortcuts) that use them
    :return:
    """
    # Get all shortcuts from glue.config.viewer_tools
    vt_shortcuts = []
    for vt in viewer_tool.members:
        if viewer_tool.members[vt].shortcut is not None:
            vt_shortcuts.append(viewer_tool.members[vt].shortcut)

    # If shortcut already exists in glue.config.viewer_tool, raise error
    ks_shortcuts = []
    for ks in keyboard_shortcut.members[None]:
        if ks < 128 and chr(ks) in vt_shortcuts:
            print("Make sure the shortcuts are NOT one of the following {0}\n\n".format(vt_shortcuts))
            print("Keyboard shortcut '{0}' already registered in {1}".format(chr(ks), "glue.config.viewer_tool"))
        elif ks < 128:
            ks_shortcuts.append(chr(ks))
        elif ks >= 128:
            print("Please refrain from using non-ASCII values for shortcuts")

    # Remove MatPlotLib default shortcuts if they conflict with other shortcuts
    for param in plt.rcParams:
        if 'keymap' in param:
            for key in plt.rcParams[param]:
                if key.upper() in vt_shortcuts or key.upper() in ks_shortcuts:
                    plt.rcParams[param].remove(key)


remove_mpl_shortcuts_and_check_dupes()
