# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os

import pytest

from qtpy import QtCore
from glue.app.qt import GlueApplication


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


@pytest.fixture(scope='module')
def cubeviz_layout():
    filename = os.path.join(TEST_DATA_PATH, 'data_cube.fits.gz')

    app = GlueApplication()
    app.run_startup_action('cubeviz')
    app.load_data(filename)
    app.setVisible(True)
    #app.activateWindow()

    return app.tab(0)


def test_starting_state(cubeviz_layout):
    assert cubeviz_layout.isVisible() == True

    assert cubeviz_layout._single_viewer_mode == False
    assert cubeviz_layout._active_view is cubeviz_layout.left_view
    assert cubeviz_layout._active_cube is cubeviz_layout.left_view

    for viewer in cubeviz_layout.all_views:
        assert viewer._widget.synced == True


def select_viewer(qtbot, viewer):
    qtbot.mouseClick(viewer._widget, QtCore.Qt.LeftButton)

def assert_active_view_and_cube(layout, viewer):
    assert layout._active_view is viewer
    assert layout._active_cube is viewer

def test_active_viewer(qtbot, cubeviz_layout):
    select_viewer(qtbot, cubeviz_layout.middle_view)
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.middle_view)

    select_viewer(qtbot, cubeviz_layout.right_view)
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.right_view)

    select_viewer(qtbot, cubeviz_layout.specviz)
    assert cubeviz_layout._active_view is cubeviz_layout.specviz
    # Selecting the specviz viewer should not affect the last active cube
    assert cubeviz_layout._active_cube is cubeviz_layout.right_view

    select_viewer(qtbot, cubeviz_layout.left_view)
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.left_view)

def test_viewer_mode(qtbot, cubeviz_layout):
    def toggle_viewer():
        qtbot.mouseClick(
            cubeviz_layout.button_toggle_image_mode, QtCore.Qt.LeftButton)

    # Make sure we start in split image mode
    assert cubeviz_layout._single_viewer_mode == False

    toggle_viewer()
    assert cubeviz_layout._single_viewer_mode == True
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.single_view)

    toggle_viewer()
    assert cubeviz_layout._single_viewer_mode == False
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.left_view)
