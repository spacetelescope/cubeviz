import os

import numpy as np
from glue.core import Subset
from qtpy.QtWidgets import QDialog
from qtpy.uic import loadUi
from spectral_cube import BooleanArrayMask, SpectralCube

from specviz.core.events import dispatch

UI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                       '..', 'data', 'ui'))


class SpectralOperationHandler(QDialog):
    """
    Widget to handle user interactions with operations that are communicated
    from the SpecViz viewer. This is built to work with 
    :func:`~spectral_cube.SpectralCube.apply_function` method by passing in a 
    callable :class:`specviz.analysis.operations.FunctionalOperation` object.

    Attributes
    ----------
    data : :class:`~
    """

    def __init__(self, data, function, *args, **kwargs):
        super(SpectralOperationHandler, self).__init__(*args, **kwargs)
        self.data = data
        self.function = function
        self.component_id = self.data.component_ids()[0]

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        # Load the ui dialog
        loadUi(os.path.join(UI_PATH, "apply_operation.ui"), self)
        component_ids = [str(i) for i in self.data.component_ids()]

        # Populate combo box
        self.data_component_combo_box.addItems(component_ids)

    def setup_connections(self):
        # When a data component is selected, update the data object reference
        self.data_component_combo_box.currentIndexChanged.connect(
            self.component_changed)

    def _compose_cube(self):
        if issubclass(self.data.__class__, Subset):
            wcs = self.data.data.coords.wcs
            data = self.data.data
            mask = self.data.to_mask()
        else:
            wcs = self.data.coords.wcs
            data = self.data
            mask = np.ones(data.shape).astype(bool)

        mask = BooleanArrayMask(mask=mask, wcs=wcs)

        return SpectralCube(data[self.component_id], wcs=wcs, mask=mask)

    def component_changed(self, index):
        self.component_id = self.data.component_ids()[index]

    def accept(self):
        cube_data = self._compose_cube()
        new_data = cube_data.apply_function(self.function,
                                            spectral_axis=cube_data.spectral_axis,
                                            axis=0
                                            ).reshape(self.data.shape)
        print(cube_data.shape, new_data.shape)

        component_name = "{} [Spectrally Smoothed]".format(self.component_id)

        component_name = "{} {}".format(component_name,
        len([x for x in self.data.component_ids() if component_name in str(x)]))

        self.data.add_component(
            new_data, component_name)

        super(SpectralOperationHandler, self).accept()
