import numpy as np
from astropy.table import Table
from collections import namedtuple

from glue.core.client import Client

from ..core.data_objects import SpectrumData, ImageData
from ..core.utils import SubsetParsedMessage


class MOSClient(Client):
    MOSObject = namedtuple('MOSObject', ['id', 'spec1d', 'spec2d', 'image',
                                         'table'])

    def __init__(self, data=None):
        super(MOSClient, self).__init__(data)
        self._loaded_data = {}
        self.selected_rows = []
        self.hub = None

    def register_to_hub(self, hub):
        super(MOSClient, self).register_to_hub(hub)
        self.hub = hub

        # hub.subscribe(self,
        #               msg.SubsetCreateMessage,
        #               handler=self._add_subset)
        # hub.subscribe(self,
        #               msg.SubsetUpdateMessage,
        #               handler=self._update_subset)
        # hub.subscribe(self,
        #               msg.SubsetDeleteMessage,
        #               handler=self._remove_subset)
        # hub.subscribe(self,
        #               msg.DataUpdateMessage,
        #               handler=self._update_data)
        # hub.subscribe(self,
        #               msg.DataCollectionDeleteMessage,
        #               handler=self._remove_data)
        # hub.subscribe(self,
        #               msg.NumericalDataChangedMessage,
        #               handler=self._numerical_data_changed)

    def unregister(self, hub):
        hub.unsubscribe_all(self)

    def notify(self, message):
        pass

    def _add_subset(self, message):
        print("[MOSClient] Adding subset.")

    def _remove_data(self, message):
        print("[MOSClient] Removing data.")

    def _update_data(self, message):
        print("[MOSClient] Updating data.")

    def _update_subset(self, message):
        print("[MOSClient] Updating subset.")
        subset = message.sender
        mask = subset.to_mask()

        col_names = subset.data.components[3:]
        table = Table()

        for id in col_names:
            try:
                val = subset.data.get_component(id).labels
            except AttributeError:
                val = subset.data.get_component(id).data

            table[id.label] = val[mask]

        self.update_display(table)

    def update_display(self, table):
        self.selected_rows = []

        for row in table:
            id = row['Object_ID']

            if id in self._loaded_data:
                self.selected_rows.append(self._loaded_data[id])
                continue

            path2d = "/Users/nearl/Desktop/mos_spec/z1Galaxies_Kassin" \
                     "/Spectra/{}".format(row['Spectrum2D_B'])

            path_im = "/Users/nearl/Desktop/mos_spec/z1Galaxies_Kassin/" \
                      "Pstg/Pstg/{}.acs.i_6ac_.fits".format(id)

            path1d = None

            if path1d and path2d:
                spec1d = SpectrumData.read(path1d)
                spec2d = SpectrumData.read(path2d, hdu=1, is_record=True)
            elif path2d and not path1d:
                spec2d = SpectrumData.read(path2d, hdu=1, is_record=True)
                spec1d = spec2d.collapse(method='sum', axis=0)

            image = ImageData.read(path_im)
            tab = {k: row[k] for k in row.colnames}

            new_mos_object = self.MOSObject(id, spec1d, spec2d, image, tab)
            self._loaded_data[id] = new_mos_object
            self.selected_rows.append(new_mos_object)

        self.hub.broadcast(SubsetParsedMessage(self))

    def _remove_subset(self, message):
        print("[MOSClient] Removing subset.")

    def apply_roi(self, roi):
        pass

    def _numerical_data_changed(self, message):
        pass
