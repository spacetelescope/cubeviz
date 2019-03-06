import numpy as np

def test_stats_box(cubeviz_layout):
    cl_viewer = cubeviz_layout.split_views[1]._widget

    if cl_viewer._subset is not None:
        mask = cl_viewer._subset.to_mask()[cl_viewer._slice_index]
        data = cl_viewer._data[0][cl_viewer.current_component_id][cl_viewer._slice_index][mask]

        assert data is not None
        assert cl_viewer._calculate_stats(data) == cl_viewer.show_roi_stats(cl_viewer.current_component_id,
                                                                            cl_viewer._subset)
    else:
        data = cl_viewer._data[0][cl_viewer.current_component_id][cl_viewer._slice_index]

        assert data is not None
        assert np.allclose(cl_viewer._calculate_stats(data.copy()), cl_viewer.show_slice_stats(), equal_nan=True)

