# Licensed under a 3-clause BSD style license - see LICENSE.rst

import pytest
from qtpy import QtCore


def enter_slice_text(qtbot, layout, text):
    widget = layout._slice_controller._slice_textbox
    widget.setText(text)
    qtbot.keyClick(widget, QtCore.Qt.Key_Enter)

@pytest.mark.parametrize('slice_index', [0, 100, 1000, 1024])
def test_enter_valid_slice_text(qtbot, cubeviz_layout, slice_index):
    enter_slice_text(qtbot, cubeviz_layout, str(slice_index))
    for viewer in cubeviz_layout.all_views:
        assert viewer._widget.slice_index == slice_index
