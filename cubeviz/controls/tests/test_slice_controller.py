# Licensed under a 3-clause BSD style license - see LICENSE.rst

import pytest
from qtpy import QtCore


def enter_slice_text(qtbot, layout, text):
    widget = layout._slice_controller._slice_textbox
    widget.setText(text)
    qtbot.keyClick(widget, QtCore.Qt.Key_Enter)

def assert_viewer_indices(layout, index):
    for viewer in layout.all_views:
        assert viewer._widget.slice_index == index

@pytest.mark.parametrize('slice_index', [0, 100, 1000, 1024])
def test_enter_valid_slice_text(qtbot, cubeviz_layout, slice_index):
    enter_slice_text(qtbot, cubeviz_layout, str(slice_index))
    assert_viewer_indices(cubeviz_layout, slice_index)

def test_enter_oob_slice_text(qtbot, cubeviz_layout):
    # Enter a negative slice value
    enter_slice_text(qtbot, cubeviz_layout, "-42")
    assert_viewer_indices(cubeviz_layout, 0)

    max_slice = len(cubeviz_layout._data['FLUX']) - 1

    # Enter an impossibly large slice value
    enter_slice_text(qtbot, cubeviz_layout, str(2**20))
    assert_viewer_indices(cubeviz_layout, max_slice)
