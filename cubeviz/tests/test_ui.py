# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os

import pytest

from qtpy import QtCore
from glue.app.qt import GlueApplication


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


def toggle_viewer(qtbot, cubeviz_layout):
    qtbot.mouseClick(
        cubeviz_layout.button_toggle_image_mode, QtCore.Qt.LeftButton)

def select_viewer(qtbot, viewer):
    qtbot.mouseClick(viewer._widget, QtCore.Qt.LeftButton)

@pytest.fixture(scope='module')
def cubeviz_layout():
    filename = os.path.join(TEST_DATA_PATH, 'data_cube.fits.gz')

    app = GlueApplication()
    app.run_startup_action('cubeviz')
    app.load_data(filename)
    app.setVisible(True)

    return app.tab(0)

@pytest.fixture(autouse=True)
def reset_state(qtbot, cubeviz_layout):
    # This yields the test itself
    yield

    # Make sure to return the application to this state between tests
    if cubeviz_layout._single_viewer_mode:
        toggle_viewer(qtbot, cubeviz_layout)
    if cubeviz_layout._active_view is not cubeviz_layout.left_view:
        select_viewer(qtbot, cubeviz_layout.left_view)

def test_starting_state(cubeviz_layout):
    assert cubeviz_layout.isVisible() == True

    assert cubeviz_layout._single_viewer_mode == False
    assert cubeviz_layout._active_view is cubeviz_layout.left_view
    assert cubeviz_layout._active_cube is cubeviz_layout.left_view

    for viewer in cubeviz_layout.all_views:
        assert viewer._widget.synced == True

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

def test_toggle_viewer_mode(qtbot, cubeviz_layout):
    toggle_viewer(qtbot, cubeviz_layout)
    assert cubeviz_layout._single_viewer_mode == True
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.single_view)

    toggle_viewer(qtbot, cubeviz_layout)
    assert cubeviz_layout._single_viewer_mode == False
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.left_view)

def test_remember_active_viewer(qtbot, cubeviz_layout):
    # Make sure that the active viewer in the current layout is remembered
    select_viewer(qtbot, cubeviz_layout.right_view)
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.right_view)

    toggle_viewer(qtbot, cubeviz_layout)
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.single_view)

    toggle_viewer(qtbot, cubeviz_layout)
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.right_view)
