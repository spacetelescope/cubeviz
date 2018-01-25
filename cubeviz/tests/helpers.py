# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os
from qtpy import QtCore
from glue.app.qt import GlueApplication


__all__ = ['toggle_viewer', 'select_viewer', 'create_glue_app',
           'reset_app_state']


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


def left_click(qtbot, widget):
    qtbot.mouseClick(widget, QtCore.Qt.LeftButton)

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

def create_glue_app():
    filename = os.path.join(TEST_DATA_PATH, 'data_cube.fits.gz')

    # We need to make sure that the data factories have been instantiated
    # before creating the glue application below. Otherwise the test data file
    # will not be recognized and the application will hang waiting for user input.
    from ..data_factories import DataFactoryConfiguration
    dfc = DataFactoryConfiguration()

    app = GlueApplication()
    app.run_startup_action('cubeviz')
    app.load_data(filename)
    app.setVisible(True)

    return app

def reset_app_state(qtbot, layout):
    sync_all_viewers(qtbot, layout)
    # Restore the text and index to a known state
    enter_slice_text(qtbot, layout, '1024')
    if layout._single_viewer_mode:
        toggle_viewer(qtbot, layout)
    if layout._active_view is not layout.left_view:
        select_viewer(qtbot, layout.left_view)
