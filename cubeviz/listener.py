# Licensed under a 3-clause BSD style license - see LICENSE.rst

from glue.core import Hub, HubListener, Data, DataCollection
from glue.core.message import (DataCollectionAddMessage, SettingsChangeMessage,
                               DataRemoveComponentMessage, SubsetMessage,
                               EditSubsetMessage, DataAddComponentMessage)
from .layout import CubeVizLayout
from .messages import FluxUnitsUpdateMessage


CUBEVIZ_LAYOUT = 'cubeviz_layout'


class CubevizManager(HubListener):

    def __init__(self, session):
        self._session = session
        self._hub = session.hub
        self._app = session.application
        self._layout = None

        self._empty_layout = self._app.add_fixed_layout_tab(CubeVizLayout)
        self._app.close_tab(0, warn=False)

        # For cubeviz, ROI selection should be in 'NewMode' by default
        self._app._mode_toolbar.set_mode('new')

        self._hub.subscribe(
            self, DataCollectionAddMessage, handler=self.handle_new_dataset)
        self._hub.subscribe(
            self, DataAddComponentMessage, handler=self.handle_new_component)
        self._hub.subscribe(
            self, SettingsChangeMessage, handler=self.handle_settings_change)
        self._hub.subscribe(
            self, DataRemoveComponentMessage, handler=self.handle_remove_component)
        self._hub.subscribe(
            self, SubsetMessage, handler=self.handle_subset_message)
        self._hub.subscribe(
            self, EditSubsetMessage, handler=self.handle_subset_message)
        self._hub.subscribe(
            self, FluxUnitsUpdateMessage, handler=self.handle_flux_units_update)

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
        component_id = message.component_id
        data = component_id.parent
        if data is self._layout._flux_unit_controller.data:
            units = data.get_component(component_id).units
            self._layout._flux_unit_controller.add_component_unit(component_id, units)
        self._layout.display_component(component_id)

    def handle_remove_component(self, message):
        self._layout.remove_data_component(message.component_id)

    def handle_settings_change(self, message):
        if self._layout is not None:
            self._layout.handle_settings_change(message)

    def handle_subset_message(self, message):
        if self._layout is not None:
            self._layout.handle_subset_action(message)

    def handle_flux_units_update(self, message):
        if self._layout is not None:
            self._layout.refresh_flux_units(message)

    def hide_sidebar(self):
        self._app._ui.main_splitter.setSizes([0, 300])

    def setup_data(self, cubeviz_layout, data):
        # Automatically add data to viewers and set attribute for split viewers
        image_viewers = [cubeviz_layout.single_view._widget,
                         cubeviz_layout.split_views[0]._widget,
                         cubeviz_layout.split_views[1]._widget,
                         cubeviz_layout.split_views[2]._widget]

        data_headers = [str(x).strip() for x in data.component_ids() if not x in data.coordinate_components]

        # Single viewer should display FLUX only by default
        image_viewers[0].add_data(data)
        image_viewers[0].state.aspect = 'auto'
        image_viewers[0].state.layers[0].attribute = data.id[data_headers[0]]

        # Split image viewers should each show different component by default
        for ii, dh in enumerate(data_headers[:3]):
            view = image_viewers[1+ii]
            view.add_data(data)
            view.state.aspect = 'auto'
            view.state.layers[0].attribute = data.id[dh]

        # And then for the "other" viewers, load the data up
        for jj in range(ii+1,3):
            view = image_viewers[1+jj]
            view.add_data(data)
            view.state.aspect = 'auto'
            view.state.layers[0].attribute = data.id[dh]

        cubeviz_layout.add_data(data)

        index = self._app.get_tab_index(cubeviz_layout)
        self._app.tab_bar.rename_tab(index, "CubeViz: {}".format(data.label))

        self._layout = cubeviz_layout
