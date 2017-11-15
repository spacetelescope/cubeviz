from __future__ import print_function, division

import os
from collections import OrderedDict

import numpy as np

from glue.config import qt_fixed_layout_tab
from qtpy import QtWidgets, QtCore
from qtpy.QtWidgets import QMenu, QAction
from glue.viewers.image.qt import ImageViewer
from specviz.third_party.glue.data_viewer import SpecVizViewer
from glue.utils.qt import load_ui, get_text
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
        self._option_buttons = []

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

        self.ui.value_slice.valueChanged.connect(self._on_slider_change)
        self.ui.value_slice.setEnabled(False)

        # Register callbacks for slider and wavelength text boxes
        self.ui.text_slice.returnPressed.connect(self._on_slice_change)
        self.ui.text_wavelength.returnPressed.connect(self._on_wavelength_change)

        self._init_option_buttons()

        self.sync = {}

        app = get_qapp()
        app.installEventFilter(self)
        self._last_click = None
        self._active_widget = None

        self._single_image = False
        self.ui.button_toggle_image_mode.setText('Single Image Viewer')

    def _init_option_buttons(self):
        self._option_buttons = [
            self.ui.view_option_button,
            self.ui.cube_option_button
        ]

        view_menu = self._dict_to_menu(OrderedDict([
            ('Something', lambda: None),
            ('Anything', lambda: None),
            ('Testing', lambda: None)
        ]))
        self.ui.view_option_button.setMenu(view_menu)

        cube_menu = self._dict_to_menu(OrderedDict([
            ('Filter', lambda: self._open_dialog('Filter', None)),
            ('Moment Maps', lambda: self._open_dialog('Moment Maps', None)),
            ('Spatial Smoothing', lambda: self._open_dialog('Spatial Smoothing', None)),
            ('Arithmetic Operations', lambda: self._open_dialog('Arithmetic Operations', None))
        ]))
        self.ui.cube_option_button.setMenu(cube_menu)

    def _dict_to_menu(self, menu_dict):
        '''Stolen shamelessly from specviz. Thanks!'''
        menu_widget = QMenu()
        for k, v in menu_dict.items():
            if isinstance(v, dict):
                new_menu = menu_widget.addMenu(k)
                self._dict_to_menu(v, menu_widget=new_menu)
            else:
                act = QAction(k, menu_widget)

                if isinstance(v, list):
                    if v[0] == 'checkable':
                        v = v[1]
                        act.setCheckable(True)
                        act.setChecked(True)

                act.triggered.connect(v)
                menu_widget.addAction(act)
        return menu_widget

    def _open_dialog(self, name, widget):
        get_text(name, "What's your name?")

    def _enable_option_buttons(self):
        for button in self._option_buttons:
            button.setEnabled(True)

    def _toggle_flux(self, event=None):
        self.image1._widget.state.layers[0].visible = self.ui.toggle_flux.isChecked()

    def _toggle_error(self, event=None):
        self.image1._widget.state.layers[1].visible = self.ui.toggle_error.isChecked()

    def _toggle_quality(self, event=None):
        self.image1._widget.state.layers[2].visible = self.ui.toggle_quality.isChecked()

    def _on_slice_change(self, event=None):
        try:
            index = int(self.ui.text_slice.text())
        except ValueError:
            # If invalid value is given, revert to current value
            index = self.image1._widget.state.slices[0]

        if index < 0:
            index = 0
        if index > len(self._wavelengths) - 1:
            index = len(self._wavelengths) - 1

        self._update_slice(index)
        self.ui.value_slice.setValue(index)

    def _on_wavelength_change(self, event=None):
        try:
            # Do an approximate reverse lookup of the wavelength to find the slice
            wavelength = float(self.ui.text_wavelength.text())
            index = np.argsort(abs(self._wavelengths - wavelength))[0]
        except ValueError:
            # If invalid value is given, revert to current value
            index = self.image1._widget.state.slices[0]

        self._update_slice(index)
        self.ui.value_slice.setValue(index)

    def _on_slider_change(self, event):
        index = self.ui.value_slice.value()
        self._update_slice(index)

    def _update_slice(self, index):
        if not self.ui.bool_sync.isChecked:
            images = self.images
        else:
            images = self.images[:2]

        for image in images:
            z, y, x = image._widget.state.slices
            image._widget.state.slices = (index, y, x)

        self.ui.text_slice.setText(str(index))
        self.ui.text_wavelength.setText(str(self._wavelengths[index]))

    def _enable_slider(self):
        self.ui.value_slice.setEnabled(True)
        self.ui.value_slice.setMinimum(0)

        # Grab the wavelengths so they can be displayed in the text box
        self._wavelengths = self.image1._widget._data[0].get_component('Wave')[:,0,0]
        self.ui.value_slice.setMaximum(len(self._wavelengths) - 1)

        # Set the default display to the middle of the cube
        middle_index = len(self._wavelengths) // 2
        self._update_slice(middle_index)
        self.ui.value_slice.setValue(middle_index)

    def add_data(self, data):
        self.specviz._widget.add_data(data)

        self._setup_syncing()
        self._enable_slider()
        self._enable_option_buttons()

        self._toggle_flux()
        self._toggle_error()
        self._toggle_quality()

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

    def _setup_syncing(self):
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
