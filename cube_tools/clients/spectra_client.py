from glue.core.client import Client
from glue.core import message as msg


class SpectraClient(Client):
    def __init__(self, data=None):
        super(SpectraClient, self).__init__(data)

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

    def register_to_hub(self, hub):
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
        hub.subscribe(self,
                      msg.ComponentReplacedMessage,
                      handler=self._on_component_replaced)

    def data(self):
        return super(SpectraClient, self).data()

    def add_data(self, data):
        # result = self.add_layer(data)
        # for subset in data.subsets:
        #     self.add_layer(subset)
        # return result
        print("Adding data")

    def _add_subset(self, message):
        # subset = message.sender
        # # only add subset if data layer present
        # if subset.data not in self.artists:
        #     return
        # subset.do_broadcast(False)
        # self.add_layer(subset)
        # subset.do_broadcast(True)
        print("Adding subset")

    def add_layer(self, layer):
        # if layer.data not in self.data:
        #     raise TypeError("Layer not in data collection")
        # if layer in self.artists:
        #     return self.artists[layer][0]
        #
        # result = ScatterLayerArtist(layer, self.axes)
        # self.artists.append(result)
        # self._update_layer(layer)
        # self._ensure_subsets_added(layer)
        # return result
        print("Adding layer")

    def _numerical_data_changed(self, message):
        pass

    def apply_roi(self, roi):
        print("Apply roi")

    def _remove_subset(self, message):
        print("Removing subset")
