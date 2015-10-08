from __future__ import print_function

import numpy as np
from glue.qt.widgets.data_viewer import DataViewer

import pyqtgraph as pg


class PGWindow(DataViewer):
    LABEL = "PyQtGraph Test Plot"

    def __init__(self, session, parent=None):
        super(PGWindow, self).__init__(session, parent)

        self.central_widget = pg.PlotWidget()
        self.central_widget.setContentsMargins(0,0,0,0)
        self.setCentralWidget(self.central_widget)
        
        data = np.random.sample(size=10000) * 1e10
        self.plot_item = self.central_widget.getPlotItem()
        self.plot = self.plot_item.plot()
        self.plot.setData(data)

    def add_data(self, data):
        return True

    def add_subset(self, subset):
        return True