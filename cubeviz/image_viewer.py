# This file contains a sub-class of the glue image viewer with further
# customizations.

from __future__ import print_function, division

from glue.config import viewer_tool
from glue.viewers.common.qt.tool import CheckableTool
from glue.viewers.image.qt import ImageViewer


__all__ = ['CubevizImageViewer']


@viewer_tool
class SyncButtonBox(CheckableTool):
    """
    SyncButtonBox derived from the Glue CheckableTool that will be placed on the
    Matplotlib toolbar in order to allow syncing between the different views in
    cubeviz.

    We need to store the "synced" state of this button so that we can check it
    in other parts of the code.
    """

    icon = 'glue_link'
    tool_id = 'sync_checkbox'
    action_text = 'Sync this viewer with other viewers'
    tool_tip = 'Sync this viewer with other viewers'
    status_tip = 'This viewer is synced'
    shortcut = 'D'

    def __init__(self, viewer):
        super(SyncButtonBox, self).__init__(viewer)
        self._synced = True

    def activate(self):
        self._synced = True

    def deactivate(self):
        self._synced = False

    def close(self):
        pass


class CubevizImageViewer(ImageViewer):

    # Add the sync button to the front of the list so it is more prominent
    # on smaller screens.
    tools = ['sync_checkbox', 'select:rectangle', 'select:xrange',
             'select:yrange', 'select:circle',
             'select:polygon', 'image:contrast_bias']

    def __init__(self, *args, **kwargs):
        super(CubevizImageViewer, self).__init__(*args, **kwargs)
        self._sync_button = None
        self._slice_index = None

    def enable_toolbar(self):
        self._sync_button = self.toolbar.tools[SyncButtonBox.tool_id]
        self.enable_button()

    def enable_button(self):
        button = self.toolbar.actions[SyncButtonBox.tool_id]
        button.setChecked(True)

    def update_slice_index(self, index):
        self._slice_index = index
        z, y, x = self.state.slices
        self.state.slices = (self._slice_index, y, x)

    @property
    def synced(self):
        return self._sync_button._synced

    @property
    def slice_index(self):
        return self._slice_index
