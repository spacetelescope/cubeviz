# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os
from qtpy import QtCore
from glue.app.qt import GlueApplication

from cubeviz.cubeviz import create_app
from cubeviz.data_factories import DataFactoryConfiguration


__all__ = ['toggle_viewer', 'select_viewer', 'create_glue_app',
           'enter_slice_text', 'enter_wavelength_text', 'reset_app_state',
           'sync_all_viewers', 'assert_all_viewer_indices',
           'assert_slice_text']


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


def left_click(qtbot, widget):
    qtbot.mouseClick(widget, QtCore.Qt.LeftButton)

def left_button_press(qtbot, layout):
    widget = layout._slice_controller._slice_slider
    qtbot.keyPress(widget, QtCore.Qt.Key_Left)

def right_button_press(qtbot, layout):
    widget = layout._slice_controller._slice_slider
    qtbot.keyPress(widget, QtCore.Qt.Key_Right)

def toggle_viewer(qtbot, layout):
    left_click(qtbot, layout.button_toggle_image_mode)

def select_viewer(qtbot, viewer):
    left_click(qtbot, viewer._widget)

def enter_slice_text(qtbot, layout, text):
    widget = layout._slice_controller._slice_textbox
    widget.setText(str(text))
    qtbot.keyClick(widget, QtCore.Qt.Key_Enter)

def enter_wavelength_text(qtbot, layout, text):
    widget = layout._slice_controller._wavelength_textbox
    widget.setText(str(text))
    qtbot.keyClick(widget, QtCore.Qt.Key_Enter)

def sync_all_viewers(qtbot, layout):
    left_click(qtbot, layout.ui.sync_button)

def assert_viewer_indices(viewer_array, index):
    for viewer in viewer_array:
        assert viewer._widget.slice_index == index

def assert_all_viewer_indices(layout, index):
    assert_viewer_indices(layout.cube_views, index)

def assert_wavelength_text(layout, text):
    current_text = layout._slice_controller._wavelength_textbox.text()
    assert current_text == str(text), "expected={}, current={}".format(text, current_text)

def assert_slice_text(layout, text):
    assert layout._slice_controller._slice_textbox.text() == str(text)


def create_glue_app():
    filename = os.path.join(TEST_DATA_PATH, 'data_cube.fits.gz')

    app = create_app(interactive=False)
    app.load_data(filename)
    app.setVisible(True)
    return app


def reset_app_state(qtbot, layout):
    sync_all_viewers(qtbot, layout)
    # Restore the text and index to a known state
    enter_slice_text(qtbot, layout, '1024')
    if layout._single_viewer_mode:
        toggle_viewer(qtbot, layout)
    if layout._active_view is not layout.split_views[0]:
        select_viewer(qtbot, layout.split_views[0])
