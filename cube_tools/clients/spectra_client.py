from __future__ import print_function

import time
import numpy as np
import astropy.units as u
from glue.core.client import Client
from glue.core import message as msg
from glue.plugins.tools.spectrum_tool import Extractor

from ..core.data_objects import SpectrumData, CubeData


class SpectraClient(Client):
    def __init__(self, data=None, model=None, graph=None):
        super(SpectraClient, self).__init__(data)
        self.graph = graph
        self.model = model
        self.artists = {}
        self._data_dict = {}
        self.main_data = None
        self.current_item = None
        self._node_parent = self.model.create_cube_data_item(None, name='Node')

    def unregister(self, hub):
        super(SpectraClient, self).unregister(hub)

    def notify(self, message):
        pass

    def _remove_data(self, message):
        print("Removing data")

    def _update_data(self, message):
        # data = message.sender
        # self._update_layer(data)
        print("Updating data")

    def _update_subset(self, message):
        print("Updating subset")
        subset = message.sender
        cube_data = subset.data['cube']

        filter_mask_cube = subset.to_mask()
        # mask = np.invert(mask)
        print("Finished creating mask")

        if subset in self.artists:
            layer_data_item = self.artists[subset]
            layer_data_item.update_data(filter_mask=filter_mask_cube)

            self.update_graph(layer_data_item)
        else:
            print("this parent item", self._data_dict[subset.data])
            self.artists[subset] = self.add_layer(
                parent=self._data_dict[subset.data],
                filter_mask=filter_mask_cube,
                name="{} ({})".format(subset.label, subset.data.label))

    def _add_subset(self, message):
        print("Adding subset")
        subset = message.sender

    def add_data(self, data):
        cube_data = data.data['cube']

        # Create data and layer items
        cube_data_item = self.model.create_cube_data_item(cube_data)
        print("this cube data item", cube_data_item)
        self._data_dict[data] = cube_data_item

        layer_data_item = self.add_layer(parent=cube_data_item,
                                         name=data.label,
                                         set_active=True,
                                         style='line')

        return layer_data_item

    def add_layer(self, parent, filter_mask=None, collapse='mean',
                  name='Layer',
                  set_active=True, style='line'):
        print("Adding layer {}".format(name))

        layer_data_item = self.model.create_layer_item(parent,
                                                       node_parent=self._node_parent,
                                                       filter_mask=filter_mask,
                                                       collapse=collapse,
                                                       name=name)
        print("in add layer", filter_mask, layer_data_item._filter_mask)
        self.graph.add_item(layer_data_item, style=style,
                            set_active=set_active)

        return layer_data_item

    def register_to_hub(self, hub):
        super(SpectraClient, self).register_to_hub(hub)
        dfilter = lambda x: self.data
        dcfilter = lambda x: self.data
        subfilter = lambda x: self.data

        hub.subscribe(self,
                      msg.SubsetCreateMessage,
                      handler=self._add_subset,
                      filter=dfilter)
        hub.subscribe(self,
                      msg.SubsetUpdateMessage,
                      handler=self._update_subset,
                      filter=subfilter)
        hub.subscribe(self,
                      msg.SubsetDeleteMessage,
                      handler=self._remove_subset)
        hub.subscribe(self,
                      msg.DataUpdateMessage,
                      handler=self._update_data,
                      filter=dfilter)
        hub.subscribe(self,
                      msg.DataCollectionDeleteMessage,
                      handler=self._remove_data)
        hub.subscribe(self,
                      msg.NumericalDataChangedMessage,
                      handler=self._numerical_data_changed)
        # hub.subscribe(self,
        #               msg.ComponentReplacedMessage,
        #               handler=self._on_component_replaced)

    def data(self):
        return super(SpectraClient, self).data()

    def _numerical_data_changed(self, message):
        pass

    def apply_roi(self, roi):
        print("Apply roi")

    def _remove_subset(self, message):
        subset = message.sender

        if subset in self.artists:
            layer_data_item = self.artists[subset]
            self.graph.remove_item(self.artists[message.sender])
            index = self.model.indexFromItem(layer_data_item)
            parent_index = self.model.indexFromItem(layer_data_item.parent)
            self.model.remove_data_item(index, parent_index)
            del self.artists[message.sender]

    def update_graph(self, layer_data_item):
        self.graph.update_item(layer_data_item)
