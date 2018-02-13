# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This file provides custom toolbar modes for glue image viewers. These toolbar
modes override the glue default behavior for ROI selection. This means that
every time an ROI selection tool is used, it will automatically create a new
ROI and subset, instead of updating the current ROI and subset.

The toolbar modes in this module must be imported in order for them to be
registered by glue. This is currently handled in the __init__.py file.
"""

from glue.config import viewer_tool
from glue.viewers.common.qt.toolbar_mode import (RectangleMode, CircleMode,
                                                 PolyMode)

__all__ = ['CubevizRectangleMode', 'CubevizCircleMode', 'CubevizPolyMode']


@viewer_tool
class CubevizRectangleMode(RectangleMode):
    tool_id = 'cubeviz:rectangle'
    create_new_subset = True


@viewer_tool
class CubevizCircleMode(CircleMode):
    tool_id = 'cubeviz:circle'
    create_new_subset = True


@viewer_tool
class CubevizPolyMode(PolyMode):
    tool_id = 'cubeviz:polygon'
    creat_new_subset = True
