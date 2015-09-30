import numpy as np

from glue.qt.widgets.data_viewer import DataViewer
from glue.core import message as msg
from ..clients.mos_client import MOSClient
from ..core.utils import SubsetParsedMessage

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

        print(data)
        # self.client.update_display(data.data[0][:, 0])

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
        spec_data_item = self.model.create_spec_data_item(current_data.spec1d)
        layer_data_item = self.model.create_layer_item(spec_data_item)

        self.sub_window.set_graph1d_data(layer_data_item)
        self.sub_window.graph2d.set_data(
            np.swapaxes(current_data.spec2d.data, 0, 1))
        self.sub_window.graph_postage.set_data(current_data.image.data)
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

        # Connect toggling error display in plot
        self.sub_window.spec_view.plot_toolbar.atn_toggle_errs.triggered.connect(lambda:
            self.sub_window.spec_view.graph.set_error_visibility(
                show=self.sub_window.spec_view.plot_toolbar.atn_toggle_errs.isChecked()))

