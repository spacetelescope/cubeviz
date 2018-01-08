# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os

from .helpers import toggle_viewer, select_viewer


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
    """Make sure that the active viewer in the current layout is remembered"""

    # Change active viewer in the split mode viewer
    select_viewer(qtbot, cubeviz_layout.right_view)
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.right_view)

    # Change to the single mode viewer
    toggle_viewer(qtbot, cubeviz_layout)
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.single_view)
    # Change active viewer in the single mode viewer
    select_viewer(qtbot, cubeviz_layout.specviz)
    assert cubeviz_layout._active_view == cubeviz_layout.specviz
    assert cubeviz_layout._active_cube == cubeviz_layout.single_view

    # Change back to the split mode viewer
    toggle_viewer(qtbot, cubeviz_layout)
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.right_view)

    # Change back to the single mode viewer
    toggle_viewer(qtbot, cubeviz_layout)
    assert cubeviz_layout._active_view == cubeviz_layout.specviz
    assert cubeviz_layout._active_cube == cubeviz_layout.single_view
