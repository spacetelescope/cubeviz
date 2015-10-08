import numpy as np
from astropy.table import Table
from collections import namedtuple

from glue.core.client import Client

from ..core.data_objects import SpectrumData, ImageData
from ..core.utils import SubsetParsedMessage


class MOSClient(Client):
    MOSObject = namedtuple('MOSObject', ['id', 'spec1d', 'spec2d', 'image',
                                         'table', 'slit_shape', 'pix_scale'])

    def __init__(self, data=None):
        super(MOSClient, self).__init__(data)
        self._loaded_data = {}
        self.selected_rows = []
        self.hub = None
        self._current_selected = None

    def register_to_hub(self, hub):
        super(MOSClient, self).register_to_hub(hub)
        self.hub = hub

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
        path = ""

        col_names = subset.data.components#[3:]
        table = Table()

        for id in col_names:
            comp = subset.data.get_component(id)
            print(id)
            if hasattr(comp, 'meta'):
                path = comp.meta['path']
            try:
                val = comp.labels
            except AttributeError:
                val = comp.data

            table[id.label] = val[mask]

        self.update_display(table, path=path)

    def update_display(self, table, path=""):
        self.selected_rows = []

        for row in table:
            id = row['id']

            if id in self._loaded_data:
                self.selected_rows.append(self._loaded_data[id])
                continue

            path2d = "/{}/{}".format(path, row['spectrum2d'])
            path_cutout = "/{}/{}".format(path, row['cutout'])
            path1d = "/{}/{}".format(path, row['spectrum1d'])

            print('-' * 20)
            print(path2d)
            print(path_cutout)
            print(path1d)
            print('-' * 20)

            spec1d = SpectrumData.read(path1d, hdu=1, normalize=True)
            spec2d = SpectrumData.read(path2d, hdu=1)
            image = ImageData.read(path_cutout)
            slit_shape = (float(row['slit_width']), float(row['slit_length']))
            pix_scale = float(row['pix_scale'])

            tab = {k: row[k] for k in row.colnames}

            new_mos_object = self.MOSObject(id, spec1d, spec2d, image, tab,
                                            slit_shape, pix_scale)
            self._loaded_data[id] = new_mos_object
            self.selected_rows.append(new_mos_object)

        self.hub.broadcast(SubsetParsedMessage(self))

    def _remove_subset(self, message):
        print("[MOSClient] Removing subset.")

    def apply_roi(self, roi):
        pass

    def _numerical_data_changed(self, message):
        pass
