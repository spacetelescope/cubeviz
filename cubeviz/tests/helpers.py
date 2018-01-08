# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os
from qtpy import QtCore
from glue.app.qt import GlueApplication


__all__ = ['toggle_viewer', 'select_viewer', 'create_glue_app',
           'reset_app_state']


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


def toggle_viewer(qtbot, layout):
    qtbot.mouseClick(
        layout.button_toggle_image_mode, QtCore.Qt.LeftButton)

def select_viewer(qtbot, viewer):
    qtbot.mouseClick(viewer._widget, QtCore.Qt.LeftButton)

def create_glue_app():
    filename = os.path.join(TEST_DATA_PATH, 'data_cube.fits.gz')

    app = GlueApplication()
    app.run_startup_action('cubeviz')
    app.load_data(filename)
    app.setVisible(True)

    return app

def reset_app_state(qtbot, layout):
    if layout._single_viewer_mode:
        toggle_viewer(qtbot, layout)
    if layout._active_view is not layout.left_view:
        select_viewer(qtbot, layout.left_view)
