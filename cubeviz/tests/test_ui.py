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


def test_active_viewer(qtbot, cubeviz_layout):
    qtbot.mouseClick(cubeviz_layout.middle_view._widget, QtCore.Qt.LeftButton)
    assert cubeviz_layout._active_view is cubeviz_layout.middle_view
    assert cubeviz_layout._active_cube is cubeviz_layout.middle_view

    qtbot.mouseClick(cubeviz_layout.right_view._widget, QtCore.Qt.LeftButton)
    assert cubeviz_layout._active_view is cubeviz_layout.right_view
    assert cubeviz_layout._active_cube is cubeviz_layout.right_view

    qtbot.mouseClick(cubeviz_layout.specviz._widget, QtCore.Qt.LeftButton)
    assert cubeviz_layout._active_view is cubeviz_layout.specviz
    # Selecting the specviz viewer should not affect the last active cube
    assert cubeviz_layout._active_cube is cubeviz_layout.right_view

    qtbot.mouseClick(cubeviz_layout.left_view._widget, QtCore.Qt.LeftButton)
    assert cubeviz_layout._active_view is cubeviz_layout.left_view
    assert cubeviz_layout._active_cube is cubeviz_layout.left_view
