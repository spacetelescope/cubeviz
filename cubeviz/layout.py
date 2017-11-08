from __future__ import print_function, division

import os

from glue.config import qt_fixed_layout_tab
from qtpy import QtWidgets, QtCore
from glue.viewers.image.qt import ImageViewer
from specviz.third_party.glue.data_viewer import SpecVizViewer
from glue.utils.qt import load_ui
from glue.external.echo import keep_in_sync
from glue.utils.qt import get_qapp

FLUX = 'FLUX'
ERROR = 'ERROR'
MASK = 'MASK'

COLOR = {}
COLOR[FLUX] = '#888888'
COLOR[ERROR] = '#ffaa66'
COLOR[MASK] = '#66aaff'


class CubevizImageViewer(ImageViewer):

    tools = ['select:rectangle', 'select:xrange',
             'select:yrange', 'select:circle',
             'select:polygon', 'image:contrast_bias']


class WidgetWrapper(QtWidgets.QWidget):

    def __init__(self, widget=None, tab_widget=None, parent=None):
        super(WidgetWrapper, self).__init__(parent=parent)
        self.tab_widget = tab_widget
        self._widget = widget
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(widget)
        self.setLayout(self.layout)

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
        self._wavelengths = None

        self.ui = load_ui('layout.ui', self,
                          directory=os.path.dirname(__file__))

        self.image1 = WidgetWrapper(CubevizImageViewer(self.session), tab_widget=self)
        self.image2 = WidgetWrapper(CubevizImageViewer(self.session), tab_widget=self)
        self.image3 = WidgetWrapper(CubevizImageViewer(self.session), tab_widget=self)
        self.image4 = WidgetWrapper(CubevizImageViewer(self.session), tab_widget=self)
        self.specviz = WidgetWrapper(SpecVizViewer(self.session), tab_widget=self)

        self.image1._widget.register_to_hub(self.session.hub)
        self.image2._widget.register_to_hub(self.session.hub)
        self.image3._widget.register_to_hub(self.session.hub)
        self.image4._widget.register_to_hub(self.session.hub)
        self.specviz._widget.register_to_hub(self.session.hub)

        self.images = [self.image1, self.image2, self.image3, self.image4]

        self.ui.single_image_layout.addWidget(self.image1)

        self.ui.image_row_layout.addWidget(self.image2)
        self.ui.image_row_layout.addWidget(self.image3)
        self.ui.image_row_layout.addWidget(self.image4)

        self.ui.specviz_layout.addWidget(self.specviz)

        self.subWindowActivated.connect(self._update_active_widget)

        self.ui.bool_sync.clicked.connect(self._on_sync_change)
        self.ui.button_toggle_sidebar.clicked.connect(self._toggle_sidebar)
        self.ui.button_toggle_image_mode.clicked.connect(
            self._toggle_image_mode)

        self.ui.toggle_flux.setStyleSheet('background-color: {0};'.format(COLOR[FLUX]))
        self.ui.toggle_error.setStyleSheet('background-color: {0};'.format(COLOR[ERROR]))
        self.ui.toggle_quality.setStyleSheet('background-color: {0};'.format(COLOR[MASK]))

        self.ui.toggle_flux.setChecked(True)
        self.ui.toggle_error.setChecked(False)
        self.ui.toggle_quality.setChecked(False)

        self.ui.toggle_flux.toggled.connect(self._toggle_flux)
        self.ui.toggle_error.toggled.connect(self._toggle_error)
        self.ui.toggle_quality.toggled.connect(self._toggle_quality)

        self.ui.value_slice.valueChanged.connect(self._on_slice_change)
        self.ui.value_slice.setEnabled(False)

        self.sync = {}

        app = get_qapp()
        app.installEventFilter(self)
        self._last_click = None
        self._active_widget = None

        self._single_image = False
        self.ui.button_toggle_image_mode.setText('Single Image Viewer')

    def _toggle_flux(self, event=None):
        self.image1._widget.state.layers[0].visible = self.ui.toggle_flux.isChecked()

    def _toggle_error(self, event=None):
        self.image1._widget.state.layers[1].visible = self.ui.toggle_error.isChecked()

    def _toggle_quality(self, event=None):
        self.image1._widget.state.layers[2].visible = self.ui.toggle_quality.isChecked()

    def _on_slice_change(self, event):
        value = self.ui.value_slice.value()

        if not self.ui.bool_sync.isChecked:
            images = self.images
        else:
            images = self.images[:2]

        for image in images:
            z, y, x = image._widget.state.slices
            image._widget.state.slices = (value, y, x)

        self.ui.text_slice.setText(str(value))
        self.ui.text_wavelength.setText(str(self._wavelengths[value]))

    def initialize_slider(self):
        self.ui.value_slice.setEnabled(True)
        self.ui.value_slice.setMinimum(0)

        self._wavelengths = self.image1._widget._data[0].get_component('Wave')[:,0,0]
        self.ui.value_slice.setMaximum(len(self._wavelengths) - 1)

        self.ui.text_slice.setText('0')
        self.ui.text_wavelength.setText(str(self._wavelengths[0]))

    def eventFilter(self, obj, event):

        if event.type() == QtCore.QEvent.MouseButtonPress:

            if not self.isVisible():
                return super(CubeVizLayout, self).eventFilter(obj, event)

            # Find global click position
            click_pos = event.globalPos()

            # If the click position is the same as the last one, we shouldn't
            # do anything.
            if click_pos != self._last_click:

                # Determine if the event falls inside any of the viewers
                for viewer in self.subWindowList():
                    relative_click_pos = viewer.mapFromGlobal(click_pos)
                    if viewer.rect().contains(relative_click_pos):
                        self.subWindowActivated.emit(viewer)
                        break

                self._last_click = click_pos

        return super(CubeVizLayout, self).eventFilter(obj, event)

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

    def _toggle_image_mode(self, event=None):
        if self._single_image:
            self._split_image_mode(event)
            self._single_image = False
            self.ui.button_toggle_image_mode.setText('Single Image Viewer')
        else:
            self._single_image_mode(event)
            self._single_image = True
            self.ui.button_toggle_image_mode.setText('Split Image Viewer')

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

    def showEvent(self, event):
        super(CubeVizLayout, self).showEvent(event)
        # Make split image mode the default layout
        self._split_image_mode()
        self._update_active_widget(self.image2)
