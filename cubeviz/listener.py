# Licensed under a 3-clause BSD style license - see LICENSE.rst

from glue.core import Hub, HubListener, Data, DataCollection
from glue.core.message import (DataCollectionAddMessage,
                               DataAddComponentMessage, SettingsChangeMessage)
from .layout import CubeVizLayout, COLOR, FLUX, ERROR, MASK


CUBEVIZ_LAYOUT = 'cubeviz_layout'


class CubevizManager(HubListener):

    def __init__(self, session):
        self._session = session
        self._hub = session.hub
        self._app = session.application
        self._layout = None

        self._empty_layout = self._app.add_fixed_layout_tab(CubeVizLayout)
        self._app.close_tab(0, warn=False)
        self.hide_sidebar()

        self._hub.subscribe(
            self, DataCollectionAddMessage, handler=self.handle_new_dataset)
        self._hub.subscribe(
            self, DataAddComponentMessage, handler=self.handle_new_component)
        self._hub.subscribe(
            self, SettingsChangeMessage, handler=self.handle_settings_change)

        # Look for any cube data files that were loaded from the command line
        for data in session.data_collection:
            if data.meta.get(CUBEVIZ_LAYOUT, ''):
                self.configure_layout(data)

    def handle_new_dataset(self, message):
        data = message.data
        if data.meta.get(CUBEVIZ_LAYOUT, ''):
            self.configure_layout(data)

    def configure_layout(self, data):
        # Assume for now the data is not yet in any tab
        if self._empty_layout is not None:
            cubeviz_layout = self._empty_layout
        else:
            cubeviz_layout = self._app.add_fixed_layout_tab(CubeVizLayout)

        try:
            self.setup_data(cubeviz_layout, data)
        finally:
            self._empty_layout = None

    def handle_new_component(self, message):
        #self._layout.add_new_data_component(str(message.component_id))
        self._layout.add_new_data_component(message.component_id)

    def handle_settings_change(self, message):
        if self._layout is not None:
            self._layout._handle_settings_change(message)

    def hide_sidebar(self):
        self._app._ui.main_splitter.setSizes([0, 300])

    def setup_data(self, cubeviz_layout, data):
        # Automatically add data to viewers and set attribute for split viewers
        image_viewers = [cubeviz_layout.single_view._widget,
                         cubeviz_layout.left_view._widget,
                         cubeviz_layout.middle_view._widget,
                         cubeviz_layout.right_view._widget]

        for i, attribute in enumerate([FLUX, ERROR, MASK]):

            image_viewers[0].add_data(data)
            image_viewers[0].state.aspect = 'equal'
            image_viewers[0].state.color_mode = 'One color per layer'
            image_viewers[0].state.layers[i].attribute = data.id[attribute]

            image_viewers[1 + i].add_data(data)
            image_viewers[1 + i].state.aspect = 'equal'
            image_viewers[1 + i].state.layers[0].attribute = data.id[attribute]

        image_viewers[0].state.layers[0].color = COLOR[FLUX]
        image_viewers[0].state.layers[1].color = COLOR[ERROR]
        image_viewers[0].state.layers[2].color = COLOR[MASK]

        cubeviz_layout.add_data(data)

        index = self._app.get_tab_index(cubeviz_layout)
        self._app.tab_bar.rename_tab(index, "CubeViz: {}".format(data.label))

        self._layout = cubeviz_layout

        # We want square pixels if the dimensions shown are the spatial
        # dimensions, and we want rectangular pixels if looking at a position-
        # spectral slice. Note that for now we assume below that the spectral
        # slice is axis 0 (in Numpy notation)

        def _change_aspect(*args):
            for image_viewer in image_viewers:
                if (image_viewer.state.x_att.axis > 0 and
                        image_viewer.state.y_att.axis > 0):
                    image_viewer.state.aspect = 'equal'
                else:
                    image_viewer.state.aspect = 'auto'

        for image_viewer in image_viewers:
            image_viewer.state.add_callback('x_att', _change_aspect)
            image_viewer.state.add_callback('y_att', _change_aspect)
