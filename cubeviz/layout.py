from __future__ import print_function, division

import os

from glue.config import qt_fixed_layout_tab, startup_action
from qtpy import QtWidgets, QtCore
from glue.viewers.image.qt import ImageViewer
from specviz.external.glue.data_viewer import SpecVizViewer
from glue.utils.qt import load_ui
from glue.external.echo import keep_in_sync


class WidgetWrapper(QtWidgets.QWidget):

    def __init__(self, widget=None, tab_widget=None, parent=None):
        super(WidgetWrapper, self).__init__(parent=parent)
        self.tab_widget = tab_widget
        self._widget = widget
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(widget)
        self.setLayout(self.layout)
        for child in self.children():
            if child.isWidgetType():
                child.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            self.tab_widget.subWindowActivated.emit(self)
        return super(WidgetWrapper, self).eventFilter(obj, event)

    def widget(self):
        return self._widget


@qt_fixed_layout_tab
class CubeVizLayout(QtWidgets.QWidget):
    """
    The 'CubeViz' layout, with three image viewers and one spectrum viewer.
    """

    LABEL = "CubeViz"
    subWindowActivated = QtCore.Signal(object)

    def __init__(self, session=None, parent=None):
        super(CubeVizLayout, self).__init__(parent=parent)

        self.session = session

        self.ui = load_ui('layout.ui', self,
                          directory=os.path.dirname(__file__))

        self.image1 = WidgetWrapper(ImageViewer(self.session), tab_widget=self)
        self.image2 = WidgetWrapper(ImageViewer(self.session), tab_widget=self)
        self.image3 = WidgetWrapper(ImageViewer(self.session), tab_widget=self)
        self.image4 = WidgetWrapper(ImageViewer(self.session), tab_widget=self)
        self.specviz = WidgetWrapper(SpecVizViewer(self.session), tab_widget=self)

        self.image1._widget.register_to_hub(self.session.hub)
        self.image2._widget.register_to_hub(self.session.hub)
        self.image3._widget.register_to_hub(self.session.hub)
        self.image4._widget.register_to_hub(self.session.hub)
        self.specviz._widget.register_to_hub(self.session.hub)

        self.ui.single_image_layout.addWidget(self.image1)

        self.ui.image_row_layout.addWidget(self.image2)
        self.ui.image_row_layout.addWidget(self.image3)
        self.ui.image_row_layout.addWidget(self.image4)

        self.ui.specviz_layout.addWidget(self.specviz)

        self.subWindowActivated.connect(self._update_active_widget)

        self.ui.bool_sync.clicked.connect(self._on_sync_change)
        self.ui.button_toggle_sidebar.clicked.connect(self._toggle_sidebar)
        self.ui.button_single_image.clicked.connect(self._single_image_mode)
        self.ui.button_split_image.clicked.connect(self._split_image_mode)

        self.sync = {}

    def _toggle_sidebar(self, event=None):
        splitter = self.session.application._ui.main_splitter
        sizes = list(splitter.sizes())
        if sizes[0] == 0:
            sizes[0] += 10
            sizes[1] -= 10
        else:
            sizes[1] = sizes[0] + sizes[1]
            sizes[0] = 0
        splitter.setSizes(sizes)

    def _single_image_mode(self, event=None):
        vsplitter = self.ui.vertical_splitter
        hsplitter = self.ui.horizontal_splitter
        vsizes = list(vsplitter.sizes())
        hsizes = list(hsplitter.sizes())
        vsizes = 0, max(10, vsizes[0] + vsizes[1])
        hsizes = max(10, sum(hsizes) * 0.4), max(10, sum(hsizes) * 0.6)
        vsplitter.setSizes(vsizes)
        hsplitter.setSizes(hsizes)

    def _split_image_mode(self, event=None):
        vsplitter = self.ui.vertical_splitter
        hsplitter = self.ui.horizontal_splitter
        vsizes = list(vsplitter.sizes())
        hsizes = list(hsplitter.sizes())
        vsizes = max(10, sum(vsizes) / 2), max(10, sum(vsizes) / 2)
        hsizes = 0, max(10, vsizes[0] + vsizes[1])
        vsplitter.setSizes(vsizes)
        hsplitter.setSizes(hsizes)

    def _update_active_widget(self, widget):
        self._active_widget = widget

    def activeSubWindow(self):
        return self._active_widget

    def subWindowList(self):
        return [self.image1, self.image2, self.image3, self.image4, self.specviz]

    def setup_syncing(self):
        for attribute in ['slices', 'x_min', 'x_max', 'y_min', 'y_max']:
            sync1 = keep_in_sync(self.image2._widget.state, attribute,
                                 self.image3._widget.state, attribute)
            sync2 = keep_in_sync(self.image3._widget.state, attribute,
                                 self.image4._widget.state, attribute)
            self.sync[attribute] = sync1, sync2
        self._on_sync_change()

    def _on_sync_change(self, event=None):
        if self.ui.bool_sync.isChecked():
            for attribute in self.sync:
                sync1, sync2 = self.sync[attribute]
                sync1.enable_syncing()
                sync2.enable_syncing()
        else:
            for attribute in self.sync:
                sync1, sync2 = self.sync[attribute]
                sync1.disable_syncing()
                sync2.disable_syncing()


@startup_action('cubeviz')
def cubeviz_setup(session, data_collection):

    app = session.application
    cubeviz = app.add_fixed_layout_tab(CubeVizLayout)

    app._ui.main_splitter.setSizes([0, 300])

    app.close_tab(0, warn=False)

    # TEMPORARY - generalize this
    if len(data_collection) != 1:
        raise Exception("The cubeviz loader requires exactly one dataset to be present")

    data = data_collection[0]

    # Automatically add data to viewers and set attribute for split viewers

    image_viewers = [cubeviz.image1._widget, cubeviz.image2._widget,
                     cubeviz.image3._widget, cubeviz.image4._widget]

    color = {}
    color['DATA'] = '#888888'
    color['VAR'] = '#ffaa66'
    color['QUALITY'] = '#66aaff'

    for i, attribute in enumerate(['DATA', 'VAR', 'QUALITY']):

        image_viewers[0].add_data(data)
        image_viewers[0].state.aspect = 'auto'
        image_viewers[0].state.color_mode = 'One color per layer'
        image_viewers[0].state.layers[i].attribute = data.id[attribute]

        image_viewers[1 + i].add_data(data)
        image_viewers[i].state.aspect = 'auto'
        image_viewers[i].state.layers[0].attribute = data.id[attribute]

    cubeviz.ui.toggle_flux.setStyleSheet('background-color: {0};'.format(color['DATA']))
    cubeviz.ui.toggle_error.setStyleSheet('background-color: {0};'.format(color['VAR']))
    cubeviz.ui.toggle_quality.setStyleSheet('background-color: {0};'.format(color['QUALITY']))

    image_viewers[0].state.layers[0].color = color['DATA']
    image_viewers[0].state.layers[1].color = color['VAR']
    image_viewers[0].state.layers[2].color = color['QUALITY']

    app.show()
    cubeviz._split_image_mode()

    # Set up linking of data slices and views
    cubeviz.setup_syncing()
