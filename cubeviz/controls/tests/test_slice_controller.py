# Licensed under a 3-clause BSD style license - see LICENSE.rst

import pytest
from qtpy import QtCore

import numpy as np

from ...tests.helpers import (enter_slice_text, enter_wavelength_text,
                              left_click, select_viewer, enter_slice_text,
                              toggle_viewer, assert_viewer_indices,
                              assert_all_viewer_indices,
                              assert_wavelength_text, assert_slice_text)


def set_slider_index(layout, index):
    layout._slice_controller._slice_slider.setSliderPosition(index)

def find_nearest_slice(wavelengths, value):
    return np.argsort(abs(wavelengths - value))[0]

def all_but_index(array, index):
    return array[:index] + array[index+1:]

@pytest.fixture(scope='module')
def cube_bounds(cubeviz_layout):
    wavelengths = cubeviz_layout._wavelength_controller.wavelengths

    bounds = {
        'max_slice': len(cubeviz_layout._data['018.DATA']) - 1,
        'wavelengths': wavelengths,
        'min_wavelength': wavelengths[0],
        'max_wavelength': wavelengths[-1]
    }

    yield bounds

@pytest.mark.parametrize('slice_index', [0, 100, 1000, 1024])
def test_enter_valid_slice_text(qtbot, cubeviz_layout, slice_index):
    enter_slice_text(qtbot, cubeviz_layout, slice_index)
    assert_all_viewer_indices(cubeviz_layout, slice_index)
    assert_slice_text(cubeviz_layout, slice_index)

def test_enter_oob_slice_text(qtbot, cubeviz_layout, cube_bounds):
    # Enter a negative slice value
    enter_slice_text(qtbot, cubeviz_layout, "-42")
    assert_all_viewer_indices(cubeviz_layout, 0)
    assert_slice_text(cubeviz_layout, 0)

    max_slice = cube_bounds['max_slice']

    # Enter an impossibly large slice value
    enter_slice_text(qtbot, cubeviz_layout, str(2**20))
    assert_all_viewer_indices(cubeviz_layout, max_slice)
    assert_slice_text(cubeviz_layout, max_slice)

@pytest.mark.parametrize('bad_text', ['garbage', '1e-07', '3.14', ''])
def test_garbage_slice_text(qtbot, cubeviz_layout, bad_text):
    # Get the current index of all viewers (since all are currently synced)
    slice_index = cubeviz_layout.synced_index

    # Make sure that entering garbage text does not change the index
    enter_slice_text(qtbot, cubeviz_layout, bad_text)
    assert_all_viewer_indices(cubeviz_layout, slice_index)
    assert_slice_text(cubeviz_layout, bad_text)

@pytest.mark.parametrize('slice_index', [0, 100, 1000, 1024, 2000])
def test_wavelength_slider(cubeviz_layout, slice_index, cube_bounds):
    set_slider_index(cubeviz_layout, slice_index)
    assert_all_viewer_indices(cubeviz_layout, slice_index)

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
    assert_all_viewer_indices(cubeviz_layout, slice_index)
    assert_slice_text(cubeviz_layout, slice_index)
    wavelength_text = "{:.3}".format(wavelengths[slice_index])
    assert_wavelength_text(cubeviz_layout, wavelength_text)

def test_enter_oob_wavelength_text(qtbot, cubeviz_layout, cube_bounds):
    enter_wavelength_text(qtbot, cubeviz_layout, '0')
    assert_all_viewer_indices(cubeviz_layout, 0)
    # We use the slice value as a proxy for the correct wavelength value
    assert_slice_text(cubeviz_layout, 0)

    max_slice = cube_bounds['max_slice']

    # enter an impossibly large wavelength value
    enter_wavelength_text(qtbot, cubeviz_layout, '42')
    assert_all_viewer_indices(cubeviz_layout, max_slice)
    assert_slice_text(cubeviz_layout, max_slice)

    # enter a negative wavelength value
    enter_wavelength_text(qtbot, cubeviz_layout, '-42')
    assert_all_viewer_indices(cubeviz_layout, 0)
    assert_slice_text(cubeviz_layout, 0)

@pytest.mark.parametrize('bad_text', ['garbage', ''])
def test_garbage_wavelength_text(qtbot, cubeviz_layout, bad_text):
    # Get the current index of all viewers (since all are currently synced)
    slice_index = cubeviz_layout.synced_index

    # Make sure that entering garbage text does not change the index
    enter_wavelength_text(qtbot, cubeviz_layout, bad_text)
    assert_all_viewer_indices(cubeviz_layout, slice_index)
    assert_wavelength_text(cubeviz_layout, bad_text)

def unsync_and_verify(qtbot, layout, sync_params, synced_index, unsynced_index):
    unsynced_viewer = sync_params['unsynced_viewer']

    # Unsync the selected viewer
    left_click(qtbot, sync_params['checkbox'])
    # At this point no slice indices should have changed yet
    assert layout.synced_index == synced_index
    assert_all_viewer_indices(layout, synced_index)

    # Activate the unsynced viewer
    select_viewer(qtbot, unsynced_viewer)
    # Change the slice index
    enter_slice_text(qtbot, layout, str(unsynced_index))
    # Make sure the active (unsynced) viewer's index has been updated
    assert unsynced_viewer._widget.slice_index == unsynced_index
    # Make sure no other viewer indices have been updated
    assert_viewer_indices(sync_params['other_viewers'], synced_index)
    # Make sure the displayed slice index reflects the active viewer
    assert_slice_text(layout, str(unsynced_index))

def update_synced_index_and_verify(qtbot, layout, sync_params, new_synced_index,
                                   unsynced_index):
    old_synced_index = layout.synced_index
    unsynced_viewer = sync_params['unsynced_viewer']
    other_viewers = sync_params['other_viewers']

    select_viewer(qtbot, sync_params['synced_viewer'])
    assert_slice_text(layout, str(old_synced_index))

    # Make sure that no indices have changed
    assert unsynced_viewer._widget.slice_index == unsynced_index
    assert_viewer_indices(other_viewers, old_synced_index)

    # Update the synced index
    enter_slice_text(qtbot, layout, str(new_synced_index))
    assert unsynced_viewer._widget.slice_index == unsynced_index
    assert_viewer_indices(other_viewers, new_synced_index)
    import time
    time.sleep(0.5)
    assert_slice_text(layout, str(new_synced_index))

@pytest.fixture(scope='function')
def sync_params(cubeviz_layout, request):
    """This fixture expects indirect parametrization providing the viewer index"""
    viewer_index = request.param
    # See comment in ``test_unsync_viewer`` below about this workaround
    if viewer_index == 0:
        return None

    params = dict(
        checkbox=cubeviz_layout._synced_checkboxes[viewer_index],
        unsynced_viewer=cubeviz_layout.cube_views[viewer_index],
        other_viewers=all_but_index(cubeviz_layout.cube_views, viewer_index),
        synced_viewer=all_but_index(
            cubeviz_layout.split_views, viewer_index-1)[0]
    )

    return params

# The 0 index is used to enable a workaround for running the tests on Travis
# CI. The single cube viewer will be tested by a separate test case.
@pytest.mark.parametrize('sync_params', [0, 1, 2, 3], indirect=True)
def test_unsync_viewer(qtbot, cubeviz_layout, sync_params):
    # This is a workaround for an issue when running tests on Linux VMs in
    # Travis CI. It does not appear to be an actual bug with CubeViz, but it
    # might be due to a race condition between the application and the test
    # framework. The solution is to make sure to toggle the viewer mode prior
    # to running the rest of these tests. It will be toggled back to single
    # mode by the reset_state fixture defined in the top-level conftest.py.
    if sync_params is None:
        toggle_viewer(qtbot, cubeviz_layout)
        pytest.skip()

    # Get the current index of all viewers
    synced_index = cubeviz_layout.synced_index
    # Sanity check to make sure all viewers are actually synced
    assert_all_viewer_indices(cubeviz_layout, synced_index)

    unsynced_viewer = sync_params['unsynced_viewer']
    other_viewers = sync_params['other_viewers']

    # Activate the unsynced viewer
    unsynced_index = 42
    unsync_and_verify(
        qtbot, cubeviz_layout, sync_params, synced_index, unsynced_index)

    # Toggle to single image mode
    toggle_viewer(qtbot, cubeviz_layout)
    assert_slice_text(cubeviz_layout, str(synced_index))

    # Toggle back to split image mode
    toggle_viewer(qtbot, cubeviz_layout)
    assert_slice_text(cubeviz_layout, str(unsynced_index))

    synced_index = 1234
    # Now activate one of the synced viewers
    update_synced_index_and_verify(
        qtbot, cubeviz_layout, sync_params, synced_index, unsynced_index)

    # Activate the unsynced viewer again
    select_viewer(qtbot, unsynced_viewer)
    assert_slice_text(cubeviz_layout, str(unsynced_index))

    # Sync the unsynced viewer
    left_click(qtbot, sync_params['checkbox'])
    assert_all_viewer_indices(cubeviz_layout, synced_index)
    assert_slice_text(cubeviz_layout, str(synced_index))

@pytest.mark.parametrize('sync_params', [1, 2, 3], indirect=True)
def test_resync_inactive_viewer(qtbot, cubeviz_layout, sync_params):
    """In contrast to the previous test, this test makes sure the unsynced
    viewer is successfully re-synced even when it is not the active viewer.
    """
    # Get the current index of all viewers
    synced_index = cubeviz_layout.synced_index

    unsynced_viewer = sync_params['unsynced_viewer']
    other_viewers = sync_params['other_viewers']

    unsynced_index = 42
    unsync_and_verify(
        qtbot, cubeviz_layout, sync_params, synced_index, unsynced_index)

    synced_index = 1234
    # Now activate one of the synced viewers
    update_synced_index_and_verify(
        qtbot, cubeviz_layout, sync_params, synced_index, unsynced_index)

    # Sync the (inactive) unsynced viewer
    left_click(qtbot, sync_params['checkbox'])
    assert_all_viewer_indices(cubeviz_layout, synced_index)
    assert_slice_text(cubeviz_layout, str(synced_index))

    # Activate the unsynced viewer again
    select_viewer(qtbot, unsynced_viewer)
    assert_slice_text(cubeviz_layout, str(synced_index))

def test_multiple_unsynced_viewers(qtbot, cubeviz_layout):
    # Get the current index of all viewers
    synced_index = cubeviz_layout.synced_index
    # Sanity check to make sure all viewers are actually synced
    assert_all_viewer_indices(cubeviz_layout, synced_index)

    unsync1 = cubeviz_layout.cube_views[1]
    checkbox1 = cubeviz_layout._synced_checkboxes[1]
    unsync_index1 = 42

    unsync2 = cubeviz_layout.cube_views[3]
    checkbox2 = cubeviz_layout._synced_checkboxes[3]
    unsync_index2 = 1234

    remain_synced = [
        cubeviz_layout.cube_views[0],
        cubeviz_layout.cube_views[2]
    ]

    # Unsync the first viewer
    left_click(qtbot, checkbox1)
    # Activate the first viewer
    select_viewer(qtbot, unsync1)
    enter_slice_text(qtbot, cubeviz_layout, unsync_index1)
    assert_slice_text(cubeviz_layout, str(unsync_index1))
    assert_viewer_indices(remain_synced + [unsync2], synced_index)

    # Unsync the second viewer: the order of activation/unsync shouldn't
    # matter, so we do it differently here than we did above
    select_viewer(qtbot, unsync2)
    left_click(qtbot, checkbox2)
    # Nothing should have changed yet
    assert_slice_text(cubeviz_layout, str(synced_index))
    assert_viewer_indices(remain_synced + [unsync2], synced_index)
    assert_viewer_indices([unsync1], unsync_index1)

    # Update the second synced viewer
    enter_slice_text(qtbot, cubeviz_layout, unsync_index2)
    assert_slice_text(cubeviz_layout, str(unsync_index2))
    # Make sure the first unsynced viewer is unchanged
    assert_viewer_indices([unsync1], unsync_index1)
    # Make sure the synced viewers are unchanged
    assert_viewer_indices(remain_synced, synced_index)

    # Update the synced viewers
    synced_index = 1234
    select_viewer(qtbot, remain_synced[1])
    enter_slice_text(qtbot, cubeviz_layout, str(synced_index))
    assert_slice_text(cubeviz_layout, str(synced_index))
    assert_viewer_indices(remain_synced, synced_index)
    assert_viewer_indices([unsync1], unsync_index1)
    assert_viewer_indices([unsync2], unsync_index2)

    # Activate the first unsynced viewer again
    select_viewer(qtbot, unsync1)
    assert_slice_text(cubeviz_layout, str(unsync_index1))
    assert_viewer_indices([unsync2], unsync_index2)
    assert_viewer_indices(remain_synced, synced_index)

    # Sync the first unsynced viewer
    left_click(qtbot, checkbox1)
    assert_slice_text(cubeviz_layout, str(synced_index))
    assert_viewer_indices(remain_synced + [unsync1], synced_index)
    assert_viewer_indices([unsync2], unsync_index2)

    # Activate the second (and still) unsynced viewer again
    select_viewer(qtbot, unsync2)
    assert_slice_text(cubeviz_layout, str(unsync_index2))

    # Sync the remaining unsynced viewer
    left_click(qtbot, checkbox2)
    assert_slice_text(cubeviz_layout, str(synced_index))
    assert_all_viewer_indices(cubeviz_layout, synced_index)

# Wavelength redshift and units testing
def test_wavelength_ui(qtbot, cubeviz_layout, slice_index=1000):
    from ...tools.wavelengths_ui import WavelengthUI

    wui = WavelengthUI(cubeviz_layout._wavelength_controller)

    # First move to the a specific slice
    enter_slice_text(qtbot, cubeviz_layout, slice_index)
    assert_slice_text(cubeviz_layout, slice_index)
    assert_wavelength_text(cubeviz_layout, '2.21e-06')

    # Now change the units
    wui.do_calculation(wavelength_redshift=0, wavelength_units='um')
    assert_wavelength_text(cubeviz_layout, '2.21')

    # Units and redshift
    wui.do_calculation(wavelength_redshift=1, wavelength_units='um')
    assert_wavelength_text(cubeviz_layout, '1.1')

    # Units and negative redshift
    wui.do_calculation(wavelength_redshift=-3, wavelength_units='um')
    assert_wavelength_text(cubeviz_layout, '-1.1')

    # with the units and redshift, go to another slice
    enter_slice_text(qtbot, cubeviz_layout, 2000)
    assert_wavelength_text(cubeviz_layout, '-1.24')

    wui.do_calculation(wavelength_redshift=0, wavelength_units='m')
