import time

from glue.core.client import Client
from glue.core import message as msg

from cube_tools.core.data_objects import SpectrumData
import astropy.units as u
from glue.plugins.tools.spectrum_tool import Extractor

import numpy as np


class SpectraClient(Client):
    def __init__(self, data=None, model=None, graph=None):
        super(SpectraClient, self).__init__(data)
        self.graph = graph
        self.model = model
        self.artists = {}
        self.spec_data_item = None
        self.main_data = None
        self.current_item = None

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

        mask = subset.to_mask()
        print("Finished creating mask")

        data = subset.data['cube']
        print("Retrieved data")

        mdata = np.ma.array(data.data, mask=~mask)
        print("Created mdata")

        clp_data = mdata.mean(axis=1).mean(axis=1)
        # np.nanmean(np.nanmean(mdata, axis=1), axis=1)

        if subset in self.artists:
            layer_data_item = self.artists[subset]
            layer_data_item.update_data(clp_data)

            self.update_graph(layer_data_item)
        else:
            self.artists[subset] = self.add_layer(data=clp_data,
                                                  name="{} ({})".format(
                                                      subset.label,
                                                      subset.data.label))

    def _add_subset(self, message):
        print("Adding subset")
        subset = message.sender

    def add_layer(self, data=None, mask=None, name='Layer', set_active=True,
                  style='line'):
        print("Adding layer {}".format(name))
        layer_data_item = self.model.create_layer_item(self.spec_data_item,
                                                       mask=mask,
                                                       name=name)

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

    def add_data(self, cube_data):
        spec_data = cube_data.data['cube'].collapse_to_spectrum()
        print("RIGHT HERE", spec_data.shape)

        # Create data and layer items
        self.spec_data_item = self.model.create_data_item(spec_data, "Data")

        layer_data_item = self.add_layer(name=cube_data.label,
                                         set_active=True,
                                         style='line')

        return layer_data_item

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
