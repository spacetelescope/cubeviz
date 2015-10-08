import numpy as np

from glue.qt.widgets.data_viewer import DataViewer
from glue.core import message as msg
from glue.core import Data, Component
from ..clients.mos_client import MOSClient
from ..core.utils import SubsetParsedMessage
from ..qt.spectra_widget import SpectraWindow

from specview.external.qt import QtGui, QtCore
from specview.ui.qt.subwindows import MultiMdiSubWindow
from specview.ui.models import DataTreeModel


class MOSWindow(DataViewer):
    LABEL = "Multi-Object Viewer"

    def __init__(self, session, parent=None):
        super(MOSWindow, self).__init__(session, parent)
        self.client = MOSClient(data=self._data)
        self.model = DataTreeModel()

        self.sub_window = MultiMdiSubWindow()
        self.sub_window.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setCentralWidget(self.sub_window)

        self._current_index = 0

        self._connect()
        # self._open_specview()

        # import pyqtgraph as pg
        # self.test_plot = pg.PlotWidget()
        # plot = self.test_plot.plot(np.random.sample(10000) * 1e10)
        # # self.setCentralWidget(test_plot)
        # self.test_plot.show()

    def register_to_hub(self, hub):
        super(MOSWindow, self).register_to_hub(hub)
        self.client.register_to_hub(hub)

        hub.subscribe(self,
                      SubsetParsedMessage,
                      handler=self._parsed_subset)

    def unregister(self, hub):
        super(MOSWindow, self).unregister(hub)
        self.client.unregister(hub)

    def add_data(self, data):
        print("[MOSWidget] Added data to widget.")
        return True

    def _parsed_subset(self, message):
        print("[MOSWidget] Data has been parsed; updating display")
        self._load_row_collection()

    def _load_row_collection(self):
        # Set the drop down list values
        toolbar = self.sub_window.toolbar
        toolbar.wgt_stack_items.clear()
        toolbar.wgt_stack_items.addItems([str(x.id) for x in
                                          self.client.selected_rows])
        self._load_mos_object(0)

    def _load_mos_object(self, index=None):
        toolbar = self.sub_window.toolbar
        self._current_index = self._current_index if index is None else index

        # Clamp index range
        self._current_index = max(0, min(self._current_index,
                                         len(self.client.selected_rows)-1))

        toolbar.wgt_stack_items.setCurrentIndex(self._current_index)

        # Display graphs with the data
        current_data = self.client.selected_rows[self._current_index]
        # spec_data_item = self.model.create_spec_data_item(current_data.spec1d)
        # layer_data_item = self.model.create_layer_item(spec_data_item)

        self.sub_window.set_data(current_data)
        self.sub_window.set_label(current_data.table)

        # If there is more than one selection, enable forward/back buttons
        if len(self.client.selected_rows) > 1:
            toolbar.enable_all(True)
        else:
            toolbar.enable_all(False)

    def _connect(self):
        self.sub_window.toolbar.atn_nav_right.triggered.connect(
            lambda: self._load_mos_object(self._current_index + 1))
        self.sub_window.toolbar.atn_nav_left.triggered.connect(
            lambda: self._load_mos_object(self._current_index - 1))

        self.sub_window.toolbar.wgt_stack_items.currentIndexChanged[
            int].connect(
            self._load_mos_object)

        # Connect toggling x axes
        self.sub_window.toolbar.atn_toggle_lock_x.triggered.connect(
            lambda: self.sub_window.toggle_lock_x(
                self.sub_window.toolbar.atn_toggle_lock_x.isChecked()))

        # Connect toggling y axes
        self.sub_window.toolbar.atn_toggle_lock_y.triggered.connect(
            lambda: self.sub_window.toggle_lock_y(
                self.sub_window.toolbar.atn_toggle_lock_y.isChecked()))

        # Connect toggling error display in plot
        self.sub_window.toolbar.atn_toggle_errs.triggered.connect(lambda:
            self.sub_window.graph1d.set_error_visibility(
                show=self.sub_window.toolbar.atn_toggle_errs.isChecked()))

        # Connect toggling mask display in plot
        self.sub_window.toolbar.atn_toggle_mask.triggered.connect(lambda:
            self.sub_window.graph1d.set_mask_visibility(
                show=self.sub_window.toolbar.atn_toggle_mask.isChecked()))

        # Connect toggling of color maps
        self.sub_window.toolbar.atn_toggle_color_map.triggered.connect(
            lambda: self.sub_window.toggle_color_maps(
                self.sub_window.toolbar.atn_toggle_color_map.isChecked()))

        # Connect toggling of color maps
        self.sub_window.toolbar.atn_open_sv.triggered.connect(self._open_specview)

    def _open_specview(self):
        current_data = self.client.selected_rows[self._current_index]
        new_data = Data()
        new_data.add_component(Component(current_data.spec1d), label="spec1d")
        self.session.application.new_data_viewer(SpectraWindow,
                                                 data=new_data)
