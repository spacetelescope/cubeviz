from __future__ import print_function

import numpy as np
from glue.qt.widgets.data_viewer import DataViewer

from specview.external.qt import QtGui

import pyqtgraph as pg


class PGWindow(DataViewer):
    LABEL = "PyQtGraph Test Plot"

    def __init__(self, session, parent=None):
        super(PGWindow, self).__init__(session, parent)

        # Define the central widget
        self.central_widget = QtGui.QWidget()
        self.central_widget.setContentsMargins(0,0,0,0)
        self.setCentralWidget(self.central_widget)

        # Define a layout so we can see both line plots and image plots
        self.layout = QtGui.QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Line plot
        line_data = np.random.sample(size=10000) * 1e10
        self.wgt_plot = pg.PlotWidget()
        self.plot_item = self.wgt_plot.getPlotItem()
        self.plot = self.plot_item.plot()
        self.plot.setData(line_data)

        # Image plot
        img_data = np.random.sample(size=(100,100))
        self.image_item = pg.ImageItem()
        self.image_item.setImage(img_data)

        # Add the widgets to the layout
        self.layout.addWidget(self.wgt_plot)
        self.layout.addWidget(self.image_item)


    def add_data(self, data):
        return True

    def add_subset(self, subset):
        return True