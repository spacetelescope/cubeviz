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

    layer = specviz._specviz_data_cache[subset]
    assert layer in specviz._layer_list.all_layers
