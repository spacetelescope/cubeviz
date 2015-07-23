from __future__ import print_function

import numpy as np
from glue.qt.widgets.data_viewer import DataViewer

from specview.external.qt import QtGui, QtCore
from specview.ui.qt.subwindows import SpectraMdiSubWindow
from specview.ui.models import DataTreeModel
from specview.ui.qt.docks import ModelDockWidget, EquivalentWidthDockWidget,\
    MeasurementDockWidget, SmoothingDockWidget
from specview.ui.qt.views import LayerDataTree
from specview.ui.items import LayerDataTreeItem
from specview.analysis import model_fitting
from specview.analysis.smoothing import spectral_smoothing

from ..clients.spectra_client import SpectraClient
from ..core.data_objects import SpectrumData, BaseData


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
        self.smoothing_dock = SmoothingDockWidget()
        self.smoothing_dock.setTitleBarWidget(QtGui.QWidget(None))

        # Add docks to the tabbed widget
        self.wgt_options.addItem(self.model_editor_dock, 'Model Editor')
        self.wgt_options.addItem(self.equiv_width_dock, 'Equivalent Width')
        self.wgt_options.addItem(self.measurement_dock, 'Measurements')
        self.wgt_options.addItem(self.smoothing_dock, 'Smoothing')

        self.layer_dock = LayerDataTree()
        self.layer_dock.setModel(self.model)

        self.client = SpectraClient(data=self._data, model=self.model,
                                    graph=self.sub_window.graph)
        self.layer_dock.set_root_item(self.client._node_parent)

        self._connect()

    def register_to_hub(self, hub):
        super(SpectraWindow, self).register_to_hub(hub)
        self.client.register_to_hub(hub)

    def add_data(self, data):
        print("[Debug] Adding data.")
        for id in data.components:
            print("[Debug] Checking {}".format(type(data.data)))
            print(type(data.data[id]))
            if not issubclass(type(data.data[id]), BaseData):
                continue


            layer_data_item = self.client.add_data(data.data[id],
                                                   data.label)

            self.current_layer_item = layer_data_item
            self.model_editor_dock.wgt_model_tree.set_root_item(layer_data_item)

        return True

    def set_data(self, data):
        print("[Debug] Setting data {}".format(type(data)))
        if self.current_layer_item is None:
            layer_data_item = self.client.add_data(data, "Hover spectrum")
            self.current_layer_item = layer_data_item
            self.model_editor_dock.wgt_model_tree.set_root_item(layer_data_item)
        else:
            self.current_layer_item.update_data(item=data)
            self.sub_window.graph.update_item(self.current_layer_item)

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
        self.model_editor_dock.btn_perform_fit.clicked.connect(lambda:
            self._perform_fit(self.layer_dock.current_item))

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

        # Connect smoothing functionality
        self.smoothing_dock.btn_perform.clicked.connect(lambda:
            self._perform_smoothing(self.layer_dock.current_item))

    def _perform_fit(self, layer_data_item):
        mask = self.sub_window.graph.get_roi_mask(layer_data_item)

        fit_spec_data = model_fitting.fit_model(
            layer_data_item,
            fit_method=str(
                self.model_editor_dock.wgt_fit_selector.currentText()),
            roi_mask=mask
        )

        new_spec_data_item = self.model.create_spec_data_item(fit_spec_data)

        print(fit_spec_data.shape, mask.shape)
        # Display
        self.client.add_layer(new_spec_data_item,
                              filter_mask=mask,
                              name="Model Fit ({}: {})".format(
                                  layer_data_item.parent.text(),
                                  layer_data_item.text()))

    def _perform_smoothing(self, layer_data_item):
        new_spec_data = spectral_smoothing(
            layer_data_item.item,
            self.smoothing_dock.wgt_method_select.currentText(),
            stddev=float(self.smoothing_dock.wgt_sigma.text()))

        new_spec_data_item = self.model.create_spec_data_item(new_spec_data)

        self.client.add_layer(new_spec_data_item,
                              name="Smoothed" +
        self.current_layer_item.parent.text())

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
