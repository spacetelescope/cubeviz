from qtpy import QtGui, QtCore

from glue.qt.widgets.data_viewer import DataViewer
from cube_tools.clients.spectra_client import SpectraClient

from cube_tools.core import SpectrumData as NewSpectrumData
import astropy.units as u
import numpy as np

from specview.ui.qt.subwindows import SpectraMdiSubWindow
from specview.ui.models import DataTreeModel
from specview.ui.items import LayerDataTreeItem
from specview.core import SpectrumData, SpectrumArray
from specview.ui.qt.docks import ModelDockWidget, DataDockWidget
from specview.analysis import model_fitting


class SpectraWindow(DataViewer):
    LABEL = "Spectra Plot"

    def __init__(self, session, parent=None):
        super(SpectraWindow, self).__init__(session, parent)
        self.client = SpectraClient(self._data)
        self.sub_window = SpectraMdiSubWindow()
        self.sub_window.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setCentralWidget(self.sub_window)

        self.model = DataTreeModel()

        # Setup model dock
        self.model_editor_dock = ModelDockWidget()

        # Setup layers view
        self.layer_dock = DataDockWidget()

        self.current_layer_item = None
        self._connect()

    def add_data(self, data):
        data_comp = data.get_component(data.id['data'])
        uncert_comp = data.get_component(data.id['uncertainty'])
        mask_comp = data.get_component(data.id['mask'])
        # wcs_comp = data.get_component(data.id['wcs'])

        self.client.add_data(data)

        spdata = NewSpectrumData(data=data_comp.data[:,
                                      data_comp.data.shape[1] // 2,
                                      data_comp.data.shape[2] // 2],
                                      unit=u.Unit(data_comp.units))

        spectrum = SpectrumData()
        spectrum.set_x(spdata.dispersion.value, unit=spdata.dispersion.unit)
        spectrum.set_y(spdata.flux.value, unit=spdata.flux.unit)

        spec_data_item = self.model.create_data_item(spectrum, "Data")
        layer_data_item = self.model.create_layer_item(spec_data_item)

        self.current_layer_item = layer_data_item
        self.display_graph(self.current_layer_item)
        self.model_editor_dock.wgt_model_tree.set_root_item(layer_data_item)

        return True

    def add_subset(self, subset):
        return True

    def layer_view(self):
        return self.layer_dock

    def options_widget(self):
        return self.model_editor_dock

    def _connect(self):
        # Set model editor's model
        self.model_editor_dock.wgt_model_tree.setModel(self.model)

        # Get the model selector combobox
        model_selector = self.model_editor_dock.wgt_model_selector

        # Connect the combobox signal to a lambda slot for generating fit
        model_selector.activated.connect(lambda:
            self.model.create_fit_model(
                self.current_layer_item,
                str(model_selector.currentText())))

        # Connect perform fit button
        self.model_editor_dock.btn_perform_fit.clicked.connect(
            self._perform_fit)

    def _perform_fit(self):
        layer_data_item = self.current_layer_item

        if len(layer_data_item._model_items) == 0:
            return

        fitter = model_fitting.get_fitter(
            str(self.model_editor_dock.wgt_fit_selector.currentText()))

        init_model = layer_data_item.model

        x, y, x_unit, y_unit = self.sub_window.graph.get_roi_data(
            layer_data_item)

        fit_model = fitter(init_model, x, y)
        new_y = fit_model(x)

        # Create new data object
        fit_spec_data = SpectrumData()
        fit_spec_data.set_x(x, wcs=layer_data_item.item.x.wcs,
                            unit=x_unit)
        fit_spec_data.set_y(new_y, wcs=layer_data_item.item.y.wcs,
                            unit=y_unit)

        # Add data object to model
        spec_data_item = self.model.create_data_item(
            fit_spec_data, name="Model Fit ({}: {})".format(
                layer_data_item.parent.text(), layer_data_item.text()))

        # Display
        self.display_graph(spec_data_item)

        # Update using model approach
        for model_idx in range(layer_data_item.rowCount()):
            model_data_item = layer_data_item.child(model_idx)

            for param_idx in range(model_data_item.rowCount()):
                parameter_data_item = model_data_item.child(param_idx, 1)

                if layer_data_item.rowCount() > 1:
                    value = fit_model[model_idx].parameters[param_idx]
                else:
                    value = fit_model.parameters[param_idx]
                parameter_data_item.setData(value)
                parameter_data_item.setText(str(value))

    def display_graph(self, layer_data_item, sub_window=None, set_active=True,
                      style='line'):
        if not isinstance(layer_data_item, LayerDataTreeItem):
            layer_data_item = self.model.create_layer_item(layer_data_item)

        self.sub_window.graph.add_item(layer_data_item, style=style,
                                       set_active=False)
