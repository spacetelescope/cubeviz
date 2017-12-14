from __future__ import print_function, division

import os
from collections import OrderedDict

import numpy as np

from astropy import units as u
from astropy.coordinates import SkyCoord
from glue.core import Hub
from glue.core.message import SettingsChangeMessage
from glue.config import qt_fixed_layout_tab, viewer_tool
from glue.viewers.common.qt.tool import CheckableTool
from qtpy import QtWidgets, QtCore
from qtpy.QtWidgets import QMenu, QAction, QLabel
from glue.viewers.image.qt import ImageViewer
from specviz.third_party.glue.data_viewer import SpecVizViewer
from glue.utils.qt import load_ui, get_text
from glue.external.echo import keep_in_sync
from glue.utils.qt import get_qapp


from .controls.slice import SliceController
from .controls.overlay import OverlayController
from .tools import arithmetic_gui, moment_maps, smoothing

FLUX = 'FLUX'
ERROR = 'ERROR'
MASK = 'MASK'
DEFAULT_DATA_LABELS = [FLUX, ERROR, MASK]

COLOR = {}
COLOR[FLUX] = '#888888'
COLOR[ERROR] = '#ffaa66'
COLOR[MASK] = '#66aaff'


@viewer_tool
class SyncButtonBox(CheckableTool):
    """
    SyncButtonBox derived from the Glue CheckableTool that will be placed on the Matplotlib toolbar
    in order to allow syncing between the different views in cubeviz.

    We need to store the "synced" state of this button so that we can check it in other parts of the code.
    """

    icon = 'glue_link'
    tool_id = 'sync_checkbox'
    action_text = 'Sync this viewer with other viewers'
    tool_tip = 'Sync this viewer with other viewers'
    status_tip = 'This viewer is synced'
    shortcut = 'D'

    def __init__(self, viewer):
        super(SyncButtonBox, self).__init__(viewer)
        self._viewer = viewer
        self._synced = True
        self._hub = None

    def activate(self):
        self._synced = True
        if self._hub is not None:
            msg = SettingsChangeMessage(self, [self._viewer])
            self._hub.broadcast(msg)

    def deactivate(self):
        self._synced = False

    def close(self):
        pass


class CubevizImageViewer(ImageViewer):

    # Add the sync button to the front of the list so it is more prominent
    # on smaller screens.
    tools = ['sync_checkbox', 'select:rectangle', 'select:xrange',
             'select:yrange', 'select:circle',
             'select:polygon', 'image:contrast_bias']

    def __init__(self, *args, **kwargs):
        super(CubevizImageViewer, self).__init__(*args, **kwargs)
        self._sync_button = None
        self._slice_index = None

        self.is_mouse_over = False  # If mouse cursor is over viewer
        self.hold_coords = False  # Switch to hold current displayed coords
        self._coords_in_degrees = True  # Switch display coords to True=deg or False=Deg/Hr:Min:Sec
        self._coords_format_function = self._format_to_degree_string  # Function to format ra and dec
        self.x_mouse = None  # x position of mouse in pix
        self.y_mouse = None  # y position of mouse in pix

        self.coord_label = QLabel("")  # Coord display
        self.statusBar().addPermanentWidget(self.coord_label)

        # Connect matplotlib events to event handlers
        self.figure.canvas.mpl_connect('motion_notify_event', self.mouse_move)
        self.figure.canvas.mpl_connect('axes_leave_event', self.mouse_exited)

    def enable_toolbar(self):
        self._sync_button = self.toolbar.tools[SyncButtonBox.tool_id]
        self._sync_button._hub = self.parent().tab_widget.session.hub
        self.enable_button()

    def enable_button(self):
        button = self.toolbar.actions[SyncButtonBox.tool_id]
        button.setChecked(True)

    def update_slice_index(self, index):
        self._slice_index = index
        z, y, x = self.state.slices
        self.state.slices = (self._slice_index, y, x)

    @property
    def synced(self):
        return self._sync_button._synced

    @property
    def slice_index(self):
        return self._slice_index

    def get_coords(self):
        """
        Returns coord display string.
        """
        if not self.is_mouse_over:
            return None
        return self.coord_label.text()

    def toggle_hold_coords(self):
        """
        Switch hold_coords state
        """
        if self.hold_coords:
            self.hold_coords = False
        else:
            self.statusBar().showMessage("Frozen Coordinates")
            self.hold_coords = True

    def toggle_coords_in_degrees(self):
        """
        Switch coords_in_degrees state
        """
        if self._coords_in_degrees:
            self._coords_in_degrees = False
            self._coords_format_function = self._format_to_hex_string
        else:
            self._coords_in_degrees = True
            self._coords_format_function = self._format_to_degree_string

    def clear_coords(self):
        """
        Reset coord display and mouse tracking variables.
        If hold_coords is active (True), make changes
        only to indicate that the mouse is no longer over viewer.
        """
        self.is_mouse_over = False
        if self.hold_coords:
            return
        self.x_mouse = None
        self.y_mouse = None
        self.coord_label.setText('')

    def _format_to_degree_string(self, ra, dec):
        """
        Format RA and Dec in degree format. If wavelength
        is available add it to the output sting.
        :return: string
        """
        coord_string = "({:0>8.4f}, {:0>8.4f}".format(ra, dec)

        # Check if wavelength is available
        if self.slice_index is not None and self.parent().tab_widget._wavelengths is not None:
            wave = self.parent().tab_widget._wavelengths[self.slice_index]
            coord_string += ", {:1.2e}m)".format(wave)
        else:
            coord_string += ")"

        return coord_string

    def _format_to_hex_string(self, ra, dec):
        """
        Format RA and Dec in D:M:S and H:M:S formats respectively. If wavelength
        is available add it to the output sting.
        :return: string
        """
        c = SkyCoord(ra=ra * u.degree, dec=dec * u.degree)
        coord_string = "("
        coord_string += "{0:0>2.0f}h:{1:0>2.0f}m:{2:0>2.0f}s".format(*c.ra.hms)
        coord_string += "  "
        coord_string += "{0:0>3.0f}d:{1:0>2.0f}m:{2:0>2.0f}s".format(*c.dec.dms)

        # Check if wavelength is available
        if self.slice_index is not None and self.parent().tab_widget._wavelengths is not None:
            wave = self.parent().tab_widget._wavelengths[self.slice_index]
            coord_string += "  {:1.2e}m)".format(wave)
        else:
            coord_string += ")"

        return coord_string

    def mouse_move(self, event):
        """
        Event handler for matplotlib motion_notify_event.
        Updates coord display and vars.
        :param event: matplotlib event.
        """
        # Check if mouse is in widget but not on plot
        if not event.inaxes:
            self.clear_coords()
            return
        self.is_mouse_over = True

        # If hold_coords is active, return
        if self.hold_coords:
            return

        # Get x and y of the pixel under the mouse
        x, y = [int(event.xdata + 0.5), int(event.ydata + 0.5)]
        self.x_mouse, self.y_mouse = [x, y]

        # Create coord display string
        if self._slice_index is not None:
            string = "({:1.0f}, {:1.0f}, {:1.0f})".format(x, y, self._slice_index)
        else:
            string = "({:1.0f}, {:1.0f})".format(x, y)

        # If viewer has a layer.
        if len(self.state.layers) > 0:
            # Get array arr that contains the image values
            # Default layer is layer at index 0.
            arr = self.state.layers[0].get_sliced_data()
            if 0 <= y < arr.shape[0] and 0 <= x < arr.shape[1]:
                # if x and y are in bounds. Note: x and y are swapped in array.
                # get value and check if wcs is obtainable
                # WCS:
                if len(self.figure.axes) > 0:
                    wcs = self.figure.axes[0].wcs.celestial
                    if wcs is not None:
                        # Check the number of axes in the WCS and add to string
                        ra = dec = None
                        if wcs.naxis == 3 and self.slice_index is not None:
                            ra, dec, wave = wcs.wcs_pix2world([[x, y, self._slice_index]], 0)[0]
                        elif wcs.naxis == 2:
                            ra, dec = wcs.wcs_pix2world([[x, y]], 0)[0]

                        if ra is not None and dec is not None:
                            string = string + " " + self._coords_format_function(ra, dec)
                # Pixel Value:
                v = arr[y][x]
                string = "{:1.4f} ".format(v) + string
        # Add a gap to string and add to viewer.
        string += " "
        self.coord_label.setText(string)
        return

    def mouse_exited(self, event):
        """
        Event handler for matplotlib axes_leave_event.
        Clears coord display and vars.
        :param event: matplotlib event
        """
        self.clear_coords()
        return

    def leaveEvent(self, event):
        """
        Event handler for Qt widget leave events.
        Clears coord display and vars.
        Overrides default.
        :param event: QEvent
        """
        self.clear_coords()
        return


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
        self._has_data = False
        self._wavelengths = None
        self._option_buttons = []

        self._data = None

        self.ui = load_ui('layout.ui', self,
                          directory=os.path.dirname(__file__))

        # Create the views and register to the hub.
        self.single_view = WidgetWrapper(CubevizImageViewer(self.session), tab_widget=self)
        self.left_view = WidgetWrapper(CubevizImageViewer(self.session), tab_widget=self)
        self.middle_view = WidgetWrapper(CubevizImageViewer(self.session), tab_widget=self)
        self.right_view = WidgetWrapper(CubevizImageViewer(self.session), tab_widget=self)
        self.specviz = WidgetWrapper(SpecVizViewer(self.session), tab_widget=self)

        self.single_view._widget.register_to_hub(self.session.hub)
        self.left_view._widget.register_to_hub(self.session.hub)
        self.middle_view._widget.register_to_hub(self.session.hub)
        self.right_view._widget.register_to_hub(self.session.hub)
        self.specviz._widget.register_to_hub(self.session.hub)

        self.views = [self.single_view, self.left_view, self.middle_view, self.right_view]
        self.cubes = self.views[1:]

        # Add the views to the layouts.
        self.ui.single_image_layout.addWidget(self.single_view)
        self.ui.image_row_layout.addWidget(self.left_view)
        self.ui.image_row_layout.addWidget(self.middle_view)
        self.ui.image_row_layout.addWidget(self.right_view)

        self.ui.specviz_layout.addWidget(self.specviz)

        self.subWindowActivated.connect(self._update_active_view)

        self.ui.sync_button.clicked.connect(self._on_sync_click)
        self.ui.button_toggle_sidebar.clicked.connect(self._toggle_sidebar)
        self.ui.button_toggle_image_mode.clicked.connect(
            self._toggle_image_mode)

        # TODO: udpate the active view with the new component

        # Leave these to reenable for the single image viewer if desired
        #self.ui.toggle_flux.setStyleSheet('background-color: {0};'.format(COLOR[FLUX]))
        #self.ui.toggle_error.setStyleSheet('background-color: {0};'.format(COLOR[ERROR]))
        #self.ui.toggle_quality.setStyleSheet('background-color: {0};'.format(COLOR[MASK]))

        #self.ui.toggle_flux.setChecked(True)
        #self.ui.toggle_error.setChecked(False)
        #self.ui.toggle_quality.setChecked(False)

        #self.ui.toggle_flux.toggled.connect(self._toggle_flux)
        #self.ui.toggle_error.toggled.connect(self._toggle_error)
        #self.ui.toggle_quality.toggled.connect(self._toggle_quality)

        self._slice_controller = SliceController(self)
        self._overlay_controller = OverlayController(self)


        # Add menu buttons to the cubeviz toolbar.
        self._init_menu_buttons()

        self._component_labels = DEFAULT_DATA_LABELS.copy()

        self.sync = {}

        app = get_qapp()
        app.installEventFilter(self)
        self._last_click = None
        self._active_view = None
        self._active_cube = None

        self._single_image = False
        self.ui.button_toggle_image_mode.setText('Single Image Viewer')

    def _init_menu_buttons(self):
        """
        Add the two menu buttons to the tool bar. Currently two are defined:
            View - for changing the view of the active window
            Data Processing - for applying a data processing step to the data.

        :return:
        """
        self._option_buttons = [
            self.ui.view_option_button,
            self.ui.cube_option_button
        ]

        # Create the View Menu
        view_menu = self._dict_to_menu(OrderedDict([
            ('RA-DEC', lambda: None),
            ('RA-Spectral', lambda: None),
            ('DEC-Spectral', lambda: None),
        ]))
        self.ui.view_option_button.setMenu(view_menu)

        # Create the Data Processing Menu
        cube_menu = self._dict_to_menu(OrderedDict([
            ('Smoothing', lambda: self._open_dialog('Smoothing', None)),
            ('Moment Maps', lambda: self._open_dialog('Moment Maps', None)),
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

    def _handle_settings_change(self, message):
        print(message)

    def _open_dialog(self, name, widget):

        if name == 'Smoothing':
            ex = smoothing.SelectSmoothing(self._data, parent=self)

        if name == 'Arithmetic Operations':
            ex = arithmetic_gui.SelectArithmetic(self._data, self.session.data_collection, parent=self)


        if name == "Moment Maps":
            moment_maps.MomentMapsGUI(
                self._data, self.session.data_collection, parent=self)

    def add_new_data_component(self, name):
        for i, combo in enumerate(self._viewer_combos):
            combo.addItem(str(name))
        self._component_labels.append(str(name))

        # TODO: udpate the active view with the new component

    def _enable_option_buttons(self):
        for button in self._option_buttons:
            button.setEnabled(True)
        self.ui.sync_button.setEnabled(True)

    def _toggle_flux(self, event=None):
        self.single_view._widget.state.layers[0].visible = self.ui.toggle_flux.isChecked()

    def _toggle_error(self, event=None):
        self.single_view._widget.state.layers[1].visible = self.ui.toggle_error.isChecked()

    def _toggle_quality(self, event=None):
        self.single_view._widget.state.layers[2].visible = self.ui.toggle_quality.isChecked()

    def _get_change_viewer_func(self, view_index):
        def change_viewer(dropdown_index):
            view = self.cubes[view_index]
            label = self._component_labels[dropdown_index]
            view._widget.state.layers[0].attribute = self._data.id[label]
        return change_viewer

    def _enable_viewer_combos(self):
        """
        Setup the dropdown boxes that correspond to each of the left, middle, and right views.  The combo boxes
        initially are set to have FLUX, Error, DQ but will be dynamic depending on the type of data available either
        from being loaded in or by being processed.

        :return:
        """

        self._viewer_combos = [
            self.ui.viewer1_combo,
            self.ui.viewer2_combo,
            self.ui.viewer3_combo
        ]

        # Add the options to each of the dropdowns.
        # TODO: Maybe should make this a function of the loaded data.
        for i, combo in enumerate(self._viewer_combos):
            for item in ['Flux', 'Error', 'DQ']:
                combo.addItem(item)
            combo.setEnabled(True)
            combo.currentIndexChanged.connect(self._get_change_viewer_func(i))

            # First view will be flux, second error and third DQ.
            combo.setCurrentIndex(i)

    def add_overlay(self, data, label):
        self._overlay_controller.add_overlay(data, label)

    def add_data(self, data):
        """
        Called by a function outside the class in order to add data to cubeviz.

        :param data:
        :return:
        """
        self._data = data
        self.specviz._widget.add_data(data)

        for view in self.views:
            view._widget.enable_toolbar()

        self._has_data = True
        self._active_view = self.left_view
        self._active_cube = self.left_view

        self._enable_viewer_combos()

        # Store pointer to wavelength information
        self._wavelengths = self.single_view._widget._data[0].get_component('Wave')[:,0,0]

        # Pass WCS and wavelength information to slider controller and enable
        wcs = self.session.data_collection.data[0].coords.wcs
        self._slice_controller.enable(wcs, self._wavelengths)

        self._enable_option_buttons()
        self._setup_syncing()

        self.subWindowActivated.emit(self._active_view)

        #self._toggle_flux()
        #self._toggle_error()
        #self._toggle_quality()

    def eventFilter(self, obj, event):

        if event.type() == QtCore.QEvent.MouseButtonPress:

            if not (self.isVisible() and self.isActiveWindow()):
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

        # TODO:  Might be a bug here, should the hsizes be based on vsizes? If so, not sure we need to calculate
        # TODO:  the hsizes above.
        hsizes = 0, max(10, vsizes[0] + vsizes[1])
        vsplitter.setSizes(vsizes)
        hsplitter.setSizes(hsizes)

    def _update_active_view(self, view):
        if self._has_data:
            self._active_view = view
            if isinstance(view._widget, CubevizImageViewer):
                self._active_cube = view
                index = self._active_cube._widget.slice_index
                self._slice_controller.update_index(index)

    def activeSubWindow(self):
        return self._active_view

    def subWindowList(self):
        return [self.single_view, self.left_view, self.middle_view, self.right_view, self.specviz]

    def _setup_syncing(self):
        for attribute in ['x_min', 'x_max', 'y_min', 'y_max']:
            sync1 = keep_in_sync(self.left_view._widget.state, attribute,
                                 self.middle_view._widget.state, attribute)
            sync2 = keep_in_sync(self.middle_view._widget.state, attribute,
                                 self.right_view._widget.state, attribute)
            self.sync[attribute] = sync1, sync2
        self._on_sync_click()

    def _on_sync_click(self, event=None):
        index = self._active_cube._widget.slice_index
        for view in self.cubes:
            view._widget.enable_button()
            if view != self._active_cube:
                view._widget.update_slice_index(index)

    def showEvent(self, event):
        super(CubeVizLayout, self).showEvent(event)
        # Make split image mode the default layout
        self._split_image_mode()
        self._update_active_view(self.left_view)
