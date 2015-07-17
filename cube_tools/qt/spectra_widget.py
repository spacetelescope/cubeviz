from specview.external.qt import QtGui, QtCore

from glue.qt.widgets.data_viewer import DataViewer
from cube_tools.clients.spectra_client import SpectraClient
from cube_tools.core.data_objects import SpectrumData

from specview.ui.qt.subwindows import SpectraMdiSubWindow
from specview.ui.models import DataTreeModel
from specview.ui.qt.docks import ModelDockWidget, EquivalentWidthDockWidget, MeasurementDockWidget
from specview.ui.qt.views import LayerDataTree
from specview.ui.items import LayerDataTreeItem
from specview.analysis import model_fitting


class SpectraWindow(DataViewer):
    LABEL = "Spectra Plot"

    def __init__(self, session, parent=None):
        super(SpectraWindow, self).__init__(session, parent)
        self.sub_window = SpectraMdiSubWindow()
        self.sub_window.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setCentralWidget(self.sub_window)

        self.current_layer_item = None

        self.model = DataTreeModel()

        # Define main options widget as a tabbed widget
        self.wgt_options = QtGui.QToolBox()

        # Get the model editor dock widget and remove header
        self.model_editor_dock = ModelDockWidget()
        self.model_editor_dock.setTitleBarWidget(QtGui.QWidget(None))

        # Get equivalent width and measurement info docks, remove headers
        self.equiv_width_dock = EquivalentWidthDockWidget()
        self.equiv_width_dock.setTitleBarWidget(QtGui.QWidget(None))
        self.measurement_dock = MeasurementDockWidget()
        self.measurement_dock.setTitleBarWidget(QtGui.QWidget(None))

        # Add docks to the tabbed widget
        self.wgt_options.addItem(self.model_editor_dock, 'Model Editor')
        self.wgt_options.addItem(self.equiv_width_dock, 'Equivalent Width')
        self.wgt_options.addItem(self.measurement_dock, 'Measurements')

        self.layer_dock = LayerDataTree()

        self.client = SpectraClient(self._data, self.model,
                                    self.sub_window.graph)
        self._connect()

    def register_to_hub(self, hub):
        super(SpectraWindow, self).register_to_hub(hub)
        self.client.register_to_hub(hub)

    def add_data(self, data):
        layer_data_item = self.client.add_data(data)

        self.current_layer_item = layer_data_item

        # Set root items
        self.model_editor_dock.wgt_model_tree.set_root_item(layer_data_item)
        self.layer_dock.set_root_item(layer_data_item.parent)

        return True

    def add_subset(self, subset):
        print("adding subset")
        return True

    def layer_view(self):
        return self.layer_dock

    def options_widget(self):
        return self.wgt_options

    def _connect(self):
        # Set model editor's model
        self.model_editor_dock.wgt_model_tree.setModel(self.model)

        # Set view model
        self.layer_dock.setModel(self.model)

        self.layer_dock.sig_current_changed.connect(
            self.set_selected_item)

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

        # Connect removing layers
        self.model.sig_removed_item.connect(self.sub_window.graph.remove_item)

        # Connect toggling layer visibility on graphs
        self.model.sig_set_visibility.connect(
            self.sub_window.graph.set_visibility)

        # Connect toggling error display in plot
        self.sub_window.plot_toolbar.atn_toggle_errs.triggered.connect(lambda:
            self.sub_window.graph.set_visibility(
                self.layer_dock.current_item,
                self.sub_window.plot_toolbar.atn_toggle_errs.isChecked(),
                errors_only=True))

    def _perform_fit(self):
        layer_data_item = self.layer_dock.current_item

        if len(layer_data_item._model_items) == 0:
            return

        fitter = model_fitting.get_fitter(
            str(self.model_editor_dock.wgt_fit_selector.currentText()))

        init_model = layer_data_item.model

        # x, y, x_unit, y_unit = self.sub_window.graph.get_roi_data(
        #     layer_data_item)
        x, y = layer_data_item.item.dispersion, layer_data_item.item.flux
        mask = self.sub_window.graph.get_roi_mask(layer_data_item)

        print(x.shape, y.shape, layer_data_item.item.dispersion.shape,
              layer_data_item.item.flux.shape)

        fit_model = fitter(init_model, x.value[~mask], y.value[~mask])
        print(fit_model)
        new_y = fit_model(x.value[~mask])

        # Create new data object
        fit_spec_data = SpectrumData(new_y, unit=layer_data_item.item.unit,
                                     mask=layer_data_item.item.mask,
                                     wcs=layer_data_item.item.wcs,
                                     meta=layer_data_item.item.meta,
                                     uncertainty=layer_data_item.item.uncertainty)

        # Add data object to model
        # spec_data_item = self.model.create_data_item(
        #     fit_spec_data, name="Model Fit ({}: {})".format(
        #         layer_data_item.parent.text(), layer_data_item.text()))

        # Display
        # self.display_graph(spec_data_item)
        self.client.add_layer(fit_spec_data, mask=mask,
                              name="Model Fit ({}: {})".format(
                layer_data_item.parent.text(), layer_data_item.text()))

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

    @QtCore.Slot(QtCore.QModelIndex)
    def set_selected_item(self, index):
        layer_data_item = self.model.itemFromIndex(index)
        print("Setting new root item {}".format(layer_data_item))

        self.model_editor_dock.wgt_model_tree.set_root_item(layer_data_item)
        self.current_layer_item = layer_data_item
