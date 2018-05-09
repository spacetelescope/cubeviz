# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os
import time

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

@pytest.mark.parametrize("x", [0,1,2,3,4,5])
def test_smoothing_spatial(qtbot, cubeviz_layout, x):
    # TODO: test spectral as well

    # Create GUI
    sm = smoothing(cubeviz_layout)
    sm.k_size.setText("1")          # Kernel size
    sm.combo.setCurrentIndex(x)         # Kernel type
    sm.component_combo.setCurrentIndex(0)       # Data componenet

    # Call smoothing
    sm.call_main()
    sm.smooth_cube.thread.wait(2*60*1000)
    qtbot.keyPress(sm.abort_window.info_box, QtCore.Qt.Key_Enter)

    # Get Smoothed data
    smoothed_name = "018.DATA_Smoothed(" + sm.combo.currentText() + ", " + sm.component_combo.currentText()
    smoothing_component_id = [str(x) for x in cubeviz_layout._data.main_components if str(x).startswith(smoothed_name)]
    if isinstance(smoothing_component_id, list) and len(smoothing_component_id) > 0:
        smoothing_component_id = smoothing_component_id[0]
    else:
        return
    np_result = np.asarray(cubeviz_layout._data[smoothing_component_id])

    # Get expected results
    cube = sm.smooth_cube.data_to_cube()
    if "median" == sm.smooth_cube.kernel_type:
        if "spatial" == sm.smooth_cube.smoothing_axis:
            new_cube = cube.spatial_smooth_median(sm.smooth_cube.kernel_size)
        else:
            new_cube = cube.spectral_smooth_median(sm.smooth_cube.kernel_size)
    else:
        kernel = sm.smooth_cube.get_kernel()
        if "spatial" == sm.smooth_cube.smoothing_axis:
            new_cube = cube.spatial_smooth(kernel)
        else:
            new_cube = cube.spectral_smooth(kernel)
    expected_result = new_cube._data

    assert np.allclose(np_result, expected_result, rtol=0.01, equal_nan=True)
