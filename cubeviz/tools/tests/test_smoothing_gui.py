# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os

import pytest
import numpy as np

from qtpy import QtCore
from glue.core import roi
from cubeviz.tools.smoothing import SelectSmoothing

from ...tests.helpers import (toggle_viewer, select_viewer, left_click,
                      left_button_press, right_button_press, enter_slice_text,
                      assert_all_viewer_indices, assert_slice_text)


DATA_LABELS = ['018.DATA', '018.NOISE']


@pytest.fixture(scope='module')
def smoothing(cubeviz_layout):
    cl = cubeviz_layout

    sm = SelectSmoothing(cl._data, parent=cl)

    return sm


def assert_red_stylesheet(widget):
    assert widget.styleSheet() == "color: rgba(255, 0, 0, 128)"


def test_smoothing(qtbot, cubeviz_layout):
    # Create GUI
    sm = smoothing(cubeviz_layout)
    sm.k_size.setText("1")
    sm.combo.setCurrentIndex(0)
    sm.component_combo.setCurrentIndex(0)

    qtbot.mouseClick(sm.okButton, QtCore.Qt.LeftButton)

    # Call calculate function and get result
    # np.warnings.filterwarnings('ignore')
    # sm.call_main()
    #print(cubeviz_layout._data, hasattr(cubeviz_layout._data, "container_2d"), cubeviz_layout._data.container_2d.component_ids())
    if hasattr(cubeviz_layout._data, "container_2d"):
        for i in cubeviz_layout._data.container_2d.component_ids():
            print(str(i))
    smoothing_component_id = [str(x) for x in cubeviz_layout._data.container_2d.component_ids() if str(x).startswith('018.DATA_Smooth')][0]
    np_result = cubeviz_layout._data.container_2d[smoothing_component_id]
    print(np_result)

    # # Expected result
    # np_data = cubeviz_layout._data[DATA_LABELS[0]]
    # import spectral_cube
    # cube = spectral_cube.SpectralCube(np_data, wcs=cubeviz_layout._data.coords.wcs)
    # order = int(sm.order_combobox.currentText())
    # cube_moment = np.asarray(cube.moment(order=order, axis=0))

    # assert np.allclose(np_result, np_result, atol=1.0, equal_nan=True)
