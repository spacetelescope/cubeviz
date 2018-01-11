# Licensed under a 3-clause BSD style license - see LICENSE.rst

import pytest
from qtpy import QtCore

import numpy as np

from ...tests.helpers import enter_slice_text, enter_wavelength_text


def set_slider_index(layout, index):
    layout._slice_controller._slice_slider.setSliderPosition(index)

def assert_viewer_indices(layout, index):
    for viewer in layout.all_views:
        assert viewer._widget.slice_index == index

def assert_slice_text(layout, text):
    assert layout._slice_controller._slice_textbox.text() == str(text)

def assert_wavelength_text(layout, text):
    assert layout._slice_controller._wavelength_textbox.text() == str(text)

def find_nearest_slice(wavelengths, value):
    return np.argsort(abs(wavelengths - value))[0]

@pytest.fixture(scope='module')
def cube_bounds(cubeviz_layout):
    bounds = {
        'max_slice': len(cubeviz_layout._data['FLUX']) - 1,
        'wavelengths': cubeviz_layout._wavelengths,
        'min_wavelength': cubeviz_layout._wavelengths[0],
        'max_wavelength': cubeviz_layout._wavelengths[-1]
    }

    yield bounds

@pytest.mark.parametrize('slice_index', [0, 100, 1000, 1024])
def test_enter_valid_slice_text(qtbot, cubeviz_layout, slice_index):
    enter_slice_text(qtbot, cubeviz_layout, slice_index)
    assert_viewer_indices(cubeviz_layout, slice_index)
    assert_slice_text(cubeviz_layout, slice_index)

def test_enter_oob_slice_text(qtbot, cubeviz_layout, cube_bounds):
    # Enter a negative slice value
    enter_slice_text(qtbot, cubeviz_layout, "-42")
    assert_viewer_indices(cubeviz_layout, 0)
    assert_slice_text(cubeviz_layout, 0)

    max_slice = cube_bounds['max_slice']

    # Enter an impossibly large slice value
    enter_slice_text(qtbot, cubeviz_layout, str(2**20))
    assert_viewer_indices(cubeviz_layout, max_slice)
    assert_slice_text(cubeviz_layout, max_slice)

@pytest.mark.parametrize('bad_text', ['garbage', '1e-07', '3.14', ''])
def test_garbage_slice_text(qtbot, cubeviz_layout, bad_text):
    # Get the current index of all viewers (since all are currently synced)
    slice_index = cubeviz_layout.synced_index

    # Make sure that entering garbage text does not change the index
    enter_slice_text(qtbot, cubeviz_layout, bad_text)
    assert_viewer_indices(cubeviz_layout, slice_index)
    assert_slice_text(cubeviz_layout, bad_text)

@pytest.mark.parametrize('slice_index', [0, 100, 1000, 1024, 2000])
def test_wavelength_slider(cubeviz_layout, slice_index, cube_bounds):
    set_slider_index(cubeviz_layout, slice_index)
    assert_viewer_indices(cubeviz_layout, slice_index)

    # Make sure that wavelength text matches slice value
    wavelength_text = "{:.3}".format(cube_bounds['wavelengths'][slice_index])
    assert_wavelength_text(cubeviz_layout, wavelength_text)

# These wavelengths are tuned to test the data file data_cube.fits.gz
@pytest.mark.parametrize('wavelength',
    [1.8421e-06, 1.931947e-06, 2.0104081e-06, 2.122048e-06, 2.270e-06, 2.51149e-06])
def test_nearest_slice_index(qtbot, cubeviz_layout, wavelength, cube_bounds):
    # While this test mostly just duplicates the code in
    # _on_text_wavelength_change, it is useful to make sure that the effects
    # carry through in the viewer slices and text boxes
    wavelengths = cube_bounds['wavelengths']

    enter_wavelength_text(qtbot, cubeviz_layout, str(wavelength))
    slice_index = find_nearest_slice(wavelengths, wavelength)
    assert_viewer_indices(cubeviz_layout, slice_index)
    assert_slice_text(cubeviz_layout, slice_index)
    wavelength_text = "{:.3}".format(wavelengths[slice_index])
    assert_wavelength_text(cubeviz_layout, wavelength_text)

def test_enter_oob_wavelength_text(qtbot, cubeviz_layout, cube_bounds):
    enter_wavelength_text(qtbot, cubeviz_layout, '0')
    assert_viewer_indices(cubeviz_layout, 0)
    # We use the slice value as a proxy for the correct wavelength value
    assert_slice_text(cubeviz_layout, 0)

    max_slice = cube_bounds['max_slice']

    # enter an impossibly large wavelength value
    enter_wavelength_text(qtbot, cubeviz_layout, '42')
    assert_viewer_indices(cubeviz_layout, max_slice)
    assert_slice_text(cubeviz_layout, max_slice)

    # enter a negative wavelength value
    enter_wavelength_text(qtbot, cubeviz_layout, '-42')
    assert_viewer_indices(cubeviz_layout, 0)
    assert_slice_text(cubeviz_layout, 0)

@pytest.mark.parametrize('bad_text', ['garbage', ''])
def test_garbage_wavelength_text(qtbot, cubeviz_layout, bad_text):
    # Get the current index of all viewers (since all are currently synced)
    slice_index = cubeviz_layout.synced_index

    # Make sure that entering garbage text does not change the index
    enter_wavelength_text(qtbot, cubeviz_layout, bad_text)
    assert_viewer_indices(cubeviz_layout, slice_index)
    assert_wavelength_text(cubeviz_layout, bad_text)
