from __future__ import print_function

import os

from glue.qt.widgets.data_viewer import DataViewer

from specview.external.qt import QtGui, QtCore
from specview.ui.qt.subwindows import SpectraMdiSubWindow
from specview.ui.models import DataTreeModel
from specview.ui.qt.docks import ModelDockWidget, EquivalentWidthDockWidget,\
     MeasurementDockWidget, SmoothingDockWidget
from specview.ui.qt.views import LayerDataTree
from specview.ui.items import LayerDataTreeItem, ModelDataTreeItem
from specview.analysis import model_fitting
from specview.analysis.smoothing import spectral_smoothing
from specview.tools import model_io, model_registry

from ..clients.spectra_client import SpectraClient

# To memorize last visited directory.
_model_directory = os.environ["HOME"]


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

        print("New spectra widget has been created.")

    def register_to_hub(self, hub):
        super(SpectraWindow, self).register_to_hub(hub)
        self.client.register_to_hub(hub)

    def unregister(self, hub):
        super(SpectraWindow, self).unregister(hub)
        self.client.unregister(hub)

    def add_data(self, data):
        print("[Debug] Adding data.")

        if 'cube' in [x.label for x in data.components]:
            layer_data_item = self.client.add_data(data.data['cube'],
                                                   data.label)

            self.current_layer_item = layer_data_item
            # self.model_editor_dock.wgt_model_tree.set_root_item(layer_data_item)
            return True
        else:
            layer_data_item = self.client.add_data(data.data['spec1d'],
                                                   "Spectrum 1D")

            self.current_layer_item = layer_data_item
            # self.model_editor_dock.wgt_model_tree.set_root_item(layer_data_item)
            return True

        return False

    def set_data(self, data, layer_data_item=None):
        if layer_data_item is None:
            return self.client.add_data(data, "Hover spectrum")

        layer_data_item.update_data(item=data)
        self.sub_window.graph.update_item(layer_data_item)

    def update_data(self, data):
        print("Updating data")
        pass

    def add_subset(self, subset):
        print("Adding subset")
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
                self.model_editor_dock,
                str(model_selector.currentText())))

        # Connect perform fit button
        self.model_editor_dock.btn_perform_fit.clicked.connect(lambda:
            self._perform_fit(self.layer_dock.current_item))

        # Connect Read and Save model buttons
        self.model_editor_dock.btn_read.clicked.connect(lambda:
            self._read_model(self.layer_dock.current_item))
        self.model_editor_dock.btn_save.clicked.connect(lambda:
            self._save_model(self.layer_dock.current_item))

        # Connect removing layers
        self.model.sig_removed_item.connect(self.sub_window.graph.remove_item)
        self.model.sig_removed_item.connect(self._reconfigureSpectralModel)

        # Connect toggling layer visibility on graphs
        self.model.sig_set_visibility.connect(
            self.sub_window.graph.set_visibility)

        # Connect toggling error display in plot
        self.sub_window.plot_toolbar.atn_toggle_errs.triggered.connect(lambda:
            self.sub_window.graph.set_error_visibility(
                # self.layer_dock.current_item,
                show=self.sub_window.plot_toolbar.atn_toggle_errs.isChecked()))

        # Connect smoothing functionality
        self.smoothing_dock.btn_perform.clicked.connect(lambda:
            self._perform_smoothing(self.layer_dock.current_item))

    # It's not enough that we remove an item. The internal structure
    # of the spectral model may require further processing. For now,
    # it just needs to report a new model expression in the GUI, but
    # future enhancements may need more work in here.
    def _reconfigureSpectralModel(self):
        self.model.updateModelExpression(self.model_editor_dock, self.layer_dock.current_item)

    def _read_model(self, layer):
        # any pre-existing compound model must be deleted before adding
        # new spectral components. Although it would be nice to be able
        # to add new components defined in a file to the existing compound
        # model, that operation cannot be done if the existing compound
        # model resulted from a previous fitting operation. The following
        # example can be used to verify this at the command-line level:
        #
        # % python
        # Python 2.7.10 |Continuum Analytics, Inc.| (default, May 28 2015, 17:04:42)
        # [GCC 4.2.1 (Apple Inc. build 5577)] on darwin
        # Type "help", "copyright", "credits" or "license" for more information.
        # Anaconda is brought to you by Continuum Analytics.
        # Please check out: http://continuum.io/thanks and https://binstar.org
        # >>> from astropy.modeling import models, fitting
        # >>> import numpy as np
        # >>> fitter = fitting.LevMarLSQFitter()
        # >>> g1 = models.Gaussian1D(1.,1.,1.)
        # >>> g2 = models.Gaussian1D(2.,2.,2.)
        # >>> initial_model = g1 + g2
        # >>> initial_model
        # <CompoundModel0(amplitude_0=1.0, mean_0=1.0, stddev_0=1.0, amplitude_1=2.0, mean_1=2.0, stddev_1=2.0)>
        # >>> x = np.array([1.,2.,3.,4.,5.,6.,7.])
        # >>> y = np.array([0.1,0.2,0.35,0.43,0.56,0.61,0.69])
        # >>> fit_result = fitter(initial_model, x, y)
        # >>> fit_result
        # <CompoundModel0(amplitude_0=-0.738532388970048, mean_0=-1.7107256329301135, stddev_0=4.13731791035706, amplitude_1=0.8553623423732329, mean_1=23.06935094019223, stddev_1=33.944748624197345)>
        # >>> g3 = models.Gaussian1D(3.,3.,3.)
        # >>> modified_result = fit_result + g3
        # >>> modified_result
        # <CompoundModel2(amplitude_0=1.0, mean_0=1.0, stddev_0=1.0, amplitude_1=2.0, mean_1=2.0, stddev_1=2.0, amplitude_2=3.0, mean_2=3.0, stddev_2=3.0)>
        # >>>
        #
        # Note the problem here: adding a new component to the compound model created
        # by the fitter erases the fitted values and returns them to whatever values
        # they have in the initial model.

        length = len(layer._model_items)
        for model_item in layer._model_items:
            layer.remove_model(model_item)

        # for an unknown reason, the loop above won't exhaust the layer._model_items list.
        # One element is left behind in the list and has to be forcibly removed. Why????
        if len(layer._model_items) > 0:
            model_item = layer._model_items[0]
            layer.remove_model(model_item)

        layer.removeRows(0, length)

        # Now we can read from file.

        global _model_directory # retains memory of last visited directory
        fname = QtGui.QFileDialog.getOpenFileName(self, 'Open file', _model_directory)
        # note that under glue, QFileDialog.getOpenFileName returns a tuple.
        # Under plain PyQt it returns a simple QString. It is like it's
        # overriding getOpenFileNameAndFilter, but why?? So, under glue we
        # need to get the first element in the tuple.
        compound_model, _model_directory = model_io.buildModelFromFile(fname[0])

        self._model_items = model_registry.getComponents(compound_model)

        for model_item in self._model_items:
            model_name = model_registry.get_component_name(model_item)
            model_data_item = ModelDataTreeItem(layer, model_item, model_name)

            layer.add_model_item(model_data_item)
            # model_data_item.setIcon(QtGui.QIcon(path.join(PATH, 'model_item.png')))

            layer.appendRow(model_data_item)

        # It's not clear that signals must be emitted at this point.
        # self.sig_added_item.emit(model_data_item.index())
        # self.sig_added_fit_model.emit(model_data_item)

        layer.setCompoundModel(compound_model)

        self.model.updateModelExpression(self.model_editor_dock, layer)

    def _save_model(self, layer):
        global _model_directory # retains memory of last visited directory
        model_io.saveModelToFile(self, layer.model, _model_directory)

    def _perform_fit(self, layer_data_item):
        mask = self.sub_window.graph.get_roi_mask(layer_data_item)

        fit_spec_data = model_fitting.fit_model(
            layer_data_item,
            fitter_name=str(
                self.model_editor_dock.wgt_fit_selector.currentText()),
            roi_mask=mask)

        new_spec_data_item = self.model.create_spec_data_item(fit_spec_data)

        # Display
        self.client.add_layer(new_spec_data_item,
                              filter_mask=mask,
                              name="Model Fit ({}: {})".format(
                                  layer_data_item.parent.text(),
                                  layer_data_item.text()))

    def _perform_smoothing(self, layer_data_item):
        name, kwargs = self.smoothing_dock.get_kwargs()

        new_spec_data = spectral_smoothing(
            layer_data_item.item, method=name, kwargs=kwargs)

        new_spec_data_item = self.model.create_spec_data_item(new_spec_data)

        self.client.add_layer(new_spec_data_item,
                              name="Smoothed " + layer_data_item.text())

    def display_graph(self, data_item, sub_window=None, set_active=True,
                      style='line'):
        if not isinstance(data_item, LayerDataTreeItem):
            layer_data_item = self.model.create_layer_item(data_item)

        self.sub_window.graph.add_item(layer_data_item, style=style)

    @QtCore.Slot(QtCore.QModelIndex)
    def set_selected_item(self, index):
        layer_data_item = self.model.itemFromIndex(index)
        print("Setting new root item {}".format(layer_data_item))

        self.model_editor_dock.wgt_model_tree.set_root_item(layer_data_item)
        self.current_layer_item = layer_data_item

        if type(layer_data_item.model) == type([]):
            compound_model = self.model.buildSummedCompoundModel(layer_data_item.model)
        else:
            compound_model = layer_data_item.model

        if self.model_editor_dock:
            if hasattr(compound_model, '_format_expression'):
                self.model_editor_dock.expression_field.setText(compound_model._format_expression())
            else:
                self.model_editor_dock.expression_field.setText('')

