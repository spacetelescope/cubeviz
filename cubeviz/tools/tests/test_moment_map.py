# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os

import pytest
import numpy as np

from qtpy import QtCore
from glue.core import roi
from cubeviz.tools.moment_maps import MomentMapsGUI

from ...tests.helpers import (toggle_viewer, select_viewer, left_click,
                      left_button_press, right_button_press, enter_slice_text,
                      assert_all_viewer_indices, assert_slice_text)


DATA_LABELS = ['018.DATA', '018.NOISE']


@pytest.fixture(scope='module')
def moment_maps(cubeviz_layout):
    cl = cubeviz_layout

    mm = MomentMapsGUI(cl._data, cl.session.data_collection, parent=cl)

    return mm


def assert_red_stylesheet(widget):
    assert widget.styleSheet() == "color: rgba(255, 0, 0, 128)"


def test_moment_display(qtbot, cubeviz_layout):
    # Create GUI
    mm = moment_maps(cubeviz_layout)
    mm.display()
    mm.order_combobox.setCurrentIndex(0)
    mm.data_combobox.setCurrentIndex(0)

    # Call calculate function and get result
    mm.calculate_callback()
    moment_component_id = [str(x) for x in cubeviz_layout._data.container_2d.component_ids() if str(x).startswith('018.DATA-mom')][0]
    np_result = cubeviz_layout._data.container_2d[moment_component_id]

    # Expected result
    np_data = cubeviz_layout._data[DATA_LABELS[0]]
    import spectral_cube
    cube = spectral_cube.SpectralCube(np_data, wcs=cubeviz_layout._data.coords.wcs)
    order = int(mm.order_combobox.currentText())
    cube_moment = np.asarray(cube.moment(order=order, axis=0))

    # Visually check differences
    print('np_data_sum {}, {}'.format(cube_moment, type(cube_moment)))
    print('np_result {}, {}'.format(np_result, type(np_result)))
    # print('sum', np.sum(np.abs(cube_moment - np_result)))
    # print('how many nans in cube_moment', np.sum(not np.isfinite(cube_moment.all())))

    assert np.allclose(cube_moment, np_result, atol=1.0, equal_nan=True)

