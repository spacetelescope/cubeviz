import numpy as np
from glue.core import roi


def test_stats_box_with_subset(cubeviz_layout):
    """
    Tests the stat box underneath the ImageViewer when there is an ROI
    """
    cl_viewer = cubeviz_layout.split_views[1]._widget

    # Create a subset (ROI) if there is none
    if cl_viewer._subset is None:
        cl_viewer.apply_roi(roi.CircularROI(xc=6, yc=10, radius=3))

    assert cl_viewer._subset is not None

    # Need to make parameters for the calculate_stats method
    mask = cl_viewer._subset.to_mask()[cl_viewer._slice_index]
    data = cl_viewer._data[0][cl_viewer.current_component_id][cl_viewer._slice_index][mask]

    assert data is not None
    assert cl_viewer._calculate_stats(data) == cl_viewer.show_roi_stats(cl_viewer.current_component_id,
                                                                        cl_viewer._subset)


def test_stats_box_without_subset(cubeviz_layout):
    """
    Tests the stat box underneath the ImageViewer when it is the full spectrum
    """
    cl_viewer = cubeviz_layout.split_views[1]._widget

    if cl_viewer._subset is not None:
        cl_viewer._subset = None

    data = cl_viewer._data[0][cl_viewer.current_component_id][cl_viewer._slice_index]

    assert data is not None

    # Creating copy since that is how it is done in image_viewer.py
    # Using allclose because the NaN values in the two arrays will cause the assert to fail otherwise
    assert np.allclose(cl_viewer._calculate_stats(data.copy()), cl_viewer.show_slice_stats(), equal_nan=True)
