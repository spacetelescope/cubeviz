from __future__ import print_function

import numpy as np
from glue.qt.widgets.data_viewer import DataViewer

import pyqtgraph as pg


class PGWindow(DataViewer):
    LABEL = "PyQtGraph Test Plot"

    def __init__(self, session, parent=None):
        super(PGWindow, self).__init__(session, parent)

        # Define the central widget
        self.central_widget = pg.ImageView()
        self.central_widget.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self.central_widget)

        data = np.random.sample(size=(1000, 1000)) * 1e10
        self.central_widget.setImage(data)

    def add_data(self, data):
        return True

    def add_subset(self, subset):
        return True