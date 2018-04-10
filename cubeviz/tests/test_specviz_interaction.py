# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os

import pytest

from glue.core import roi


def test_create_roi(cubeviz_layout):
    viewer = cubeviz_layout.split_views[0]._widget
    # Create a pretty arbitrary circular ROI
    viewer.apply_roi(roi.CircularROI(xc=10, yc=10, radius=5))
    assert len(cubeviz_layout._data.subsets) == 1

    subset = cubeviz_layout._data.subsets[0]
    specviz = cubeviz_layout.specviz._widget
    assert subset in specviz._specviz_data_cache
    assert len(specviz._specviz_data_cache) == 2

    layer = specviz._specviz_data_cache[subset]
    assert layer in specviz._layer_list.all_layers
    # TODO: once this is fixed, there should be a test here to make sure the
    # ROI is the only spectrum that is currently displayed

def test_delete_roi(cubeviz_layout):
    # This test assumes that an ROI was created by the previous test
    dc = cubeviz_layout.session.application.data_collection
    dc.remove_subset_group(dc.subset_groups[0])
    assert len(cubeviz_layout._data.subsets) == 0

    specviz = cubeviz_layout.specviz._widget
    assert cubeviz_layout._data in specviz._specviz_data_cache
    assert len(specviz._specviz_data_cache) == 1

    layer = specviz._specviz_data_cache[cubeviz_layout._data]
    assert layer in specviz._layer_list.all_layers
    assert len(specviz._layer_list.all_layers) == 1
