from __future__ import print_function

import numpy as np
import astropy.units as u
from glue.qt.widgets.data_viewer import DataViewer

from specview.external.qt import QtGui

from .qt.custom.graphs import ImageGraph
from .qt.custom.toolbars import ImageToolBar
from .core import CubeData, SpectrumData


class ImageWindow(DataViewer):
    LABEL = "Image Plot"

    def __init__(self, session, parent=None):
        super(ImageWindow, self).__init__(session, parent)

        self.central_widget = QtGui.QWidget()
        self.central_widget.setContentsMargins(0,0,0,0)
        self.setCentralWidget(self.central_widget)
        # Define layout
        self.vb_layout = QtGui.QVBoxLayout()
        self.vb_layout.setContentsMargins(0, 0, 0, 0)
        self.central_widget.setLayout(self.vb_layout)

        self.toolbar = ImageToolBar()
        self.toolbar.setContentsMargins(0, 0, 0, 0)
        self.vb_layout.addWidget(self.toolbar)

        self.viewer = ImageGraph()
        self.vb_layout.addWidget(self.viewer)

        self._connect_toolbar()

    def add_data(self, data):
        # data = np.random.sample(size=100)
        # spdata = SpectrumData(data, unit=u.Jy)
        self.viewer.set_image(data)
        return True

    def add_subset(self, subset):
        return True

    def _connect_toolbar(self):
        self.toolbar.atn_insert_roi.triggered.connect(self.viewer.add_roi)