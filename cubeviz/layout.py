from __future__ import print_function, division

import os
from collections import OrderedDict

import numpy as np

from astropy import units as u
from astropy.coordinates import SkyCoord
from matplotlib import pyplot as plt
import matplotlib.ticker as mtick
from glue.core.data import Data
from glue.config import colormaps as glue_colormaps
from glue.config import qt_fixed_layout_tab, viewer_tool
from glue.viewers.common.qt.tool import CheckableTool
from qtpy import QtWidgets, QtCore
from qtpy.QtWidgets import QMenu, QAction, QLabel
from glue.viewers.image.qt import ImageViewer
from specviz.third_party.glue.data_viewer import SpecVizViewer, dispatch
from glue.utils.qt import load_ui, get_text
from glue.external.echo import keep_in_sync
from glue.utils.qt import get_qapp


from .tools import arithmetic_gui, moment_maps, smoothing

FLUX = 'FLUX'
ERROR = 'ERROR'
MASK = 'MASK'
DEFAULT_DATA_LABELS = [FLUX, ERROR, MASK]
DEFAULT_GLUE_COLORMAP_INDEX = 3

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
        self._synced = True

    def activate(self):
        self._synced = True

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
        self.coords_in_degrees = True  # Switch display coords to True=deg or False=Deg:Min:Sec
        self.x_mouse = None  # x position of mouse in pix
        self.y_mouse = None  # y position of mouse in pix

        self.coord_label = QLabel("")  # Coord display
        self.statusBar().addPermanentWidget(self.coord_label)

        # Connect matplotlib events to event handlers
        self.figure.canvas.mpl_connect('motion_notify_event', self.mouse_move)
        self.figure.canvas.mpl_connect('axes_leave_event', self.mouse_exited)

    def enable_toolbar(self):
        self._sync_button = self.toolbar.tools[SyncButtonBox.tool_id]
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
            self.hold_coords = True
            string = "Hold:" + self.get_coords()
        else:
            self.hold_coords = False

    def toggle_coords_in_degrees(self):
        """
        Switch coords_in_degrees state
        """
        if self.coords_in_degrees:
            self.coords_in_degrees = False
        else:
            self.coords_in_degrees = True

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

    def _format_coord_string(self, ra, dec):
        """
        Format RA and Dec for coord display. If wavelength
        is available, add it to this string.
        :param ra: right ascension
        :param dec: declination
        :return: string
        """
        if self.coords_in_degrees:  # If print ra & dec in decimal degrees
            coord_string = "({:1.4f}\N{DEGREE SIGN}, {:1.4f}\N{DEGREE SIGN}".format(ra, dec)
        else:  # else print ra & dec in Deg:Min:Sec
            c = SkyCoord(ra=ra * u.degree, dec=dec * u.degree)
            coord_string = "("
            coord_string += "{0:1.0f}\N{DEGREE SIGN}:{1:1.0f}':{2:1.2f}\"".format(*c.ra.dms)
            coord_string += ", "
            coord_string += "{0:1.0f}\N{DEGREE SIGN}:{1:1.0f}':{2:1.2f}\"".format(*c.dec.dms)

        # Check if wavelength is available
        if self.slice_index is not None and self.parent().tab_widget._wavelengths is not None:
            wave = self.parent().tab_widget._wavelengths[self.slice_index]
            coord_string += ", {:1.2e}m)".format(wave)
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
            if 0 <= x < arr.shape[0] and 0 <= y < arr.shape[1]:
                # if x and y are in bounds get value and check if wcs is obtainable
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
                            string = string + " " + self._format_coord_string(ra, dec)
                # Pixel Value:
                v = arr[x][y]
                string += " {:1.4f}".format(v)
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
        self._wavelength_units = None
        self._wavelength_format = '{}'
        self._option_buttons = []

        self._data = None
        self._overlays = Data('Overlays')
        # This is a list of overlay objects that are currently displayed
        self._active_overlays = []
        # Maps overlays to the data sets they represent
        self._overlay_map = {}
        self._overlay_colorbar_axis = []

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

        self.ui.overlay_image_combo.addItem("No Overlay")
        self.ui.overlay_image_combo.currentIndexChanged.connect(
            self._on_overlay_change)

        self._colormap_index = DEFAULT_GLUE_COLORMAP_INDEX
        self.ui.overlay_colormap_combo.setCurrentIndex(self._colormap_index)
        self.ui.overlay_colormap_combo.currentIndexChanged.connect(
            self._on_colormap_change)

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

        self.ui.value_slice.valueChanged.connect(self._on_slider_change)
        self.ui.value_slice.setEnabled(False)

        self.ui.alpha_slider.valueChanged.connect(self._on_alpha_change)

        # Register callbacks for slider and wavelength text boxes
        self.ui.text_slice.returnPressed.connect(self._on_slice_change)
        self.ui.text_wavelength.returnPressed.connect(self._on_wavelength_change)

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

        # Connect this class to specviz's event dispatch so methods can listen
        # to specviz events
        dispatch.setup(self)

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

    def _open_dialog(self, name, widget):

        if name == 'Smoothing':
            ex = smoothing.SelectSmoothing(self._data, parent=self)

        if name == 'Arithmetic Operations':
            ex = arithmetic_gui.SelectArithmetic(self._data, self.session.data_collection, parent=self)


        if name == "Moment Maps":
            moment_maps.MomentMapsGUI(
                self._data, self.session.data_collection, parent=self)

    def add_overlay(self, data, label):
        self._overlays.add_component(data, label)
        # TODO: Is there a way to get this from the component ???
        self.overlay_image_combo.addItem(label)
        new_index = self.overlay_image_combo.count() - 1
        self._overlay_map[new_index] = data

        self.ui.alpha_slider.setEnabled(True)
        self.ui.overlay_image_combo.setEnabled(True)
        self.ui.overlay_colormap_combo.setEnabled(True)

        # Setting the index will cause _on_overlay_change to fire
        self.overlay_image_combo.setCurrentIndex(new_index)

    def _on_overlay_change(self, index):
        if index == 0:
            data = None
        else:
            data = self._overlay_map[index]
        self.display_overlay(data)

    def _on_colormap_change(self, index):
        self._colormap_index = index
        colormap = glue_colormaps.members[self._colormap_index][1]
        for overlay in self._active_overlays:
            overlay.set_cmap(colormap)
        for cb in self._overlay_colorbar_axis:
            for cbim in cb.get_images():
                cbim.set_cmap(colormap)
        for cube in self.cubes:
            cube._widget.figure.canvas.draw()

    def display_overlay(self, data):
        # Remove all existing overlays
        if self._active_overlays:
            for overlay, view, cb in zip(self._active_overlays, self.cubes, self._overlay_colorbar_axis):
                overlay.remove()
                cb.remove()
                view._widget.figure.canvas.draw()

            self._active_overlays = []
            self._overlay_colorbar_axis = []

        # Just return if no new overlay is to be drawn
        if data is None:
            return

        # Draw new overlay otherwise
        extent = 0, data.shape[0], 0, data.shape[1]

        self._active_overlays = []
        for view in self.cubes:
            axes = view._widget.axes
            aspect = axes.get_aspect()

            colormap = glue_colormaps.members[self._colormap_index][1]
            overlay = view._widget.axes.imshow(
                data, origin='lower', cmap=colormap, alpha=.25,
                interpolation='none', aspect=aspect, extent=extent)

            self._active_overlays.append(overlay)

            # Add the overlay colorbar as an axis
            oca = view._widget.figure.add_axes([0.02, 0.04, 0.3, 0.025], projection='rectilinear')
            mindata, maxdata = np.nanmin(data), np.nanmax(data)
            oca_image = np.zeros((1,100))
            oca_image[0] = np.arange(mindata, maxdata, (maxdata-mindata)/100)
            oca.imshow(oca_image, origin='lower', cmap=colormap, aspect=aspect, extent=[0,100,0,100])
            oca.set_xticks([0, 25, 50, 75, 100])
            oca.set_xticklabels(['%3.2e'%x for x in np.arange(mindata, maxdata, (maxdata-mindata)/5)], fontsize=6)
            oca.set_yticks([])
            self._overlay_colorbar_axis.append(oca)

            view._widget.figure.canvas.draw()

        self.ui.alpha_slider.setValue(25)

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

    def _on_slice_change(self, event=None):
        """
        Callback for a change in the slice index text box.  We will need to
        update the slider and the wavelength value when this changes.

        :param event:
        :return:
        """

        # Get the value they typed in, but if not a number, then let's just use
        # the first slice.
        try:
            index = int(self.ui.text_slice.text())
        except ValueError:
            # If invalid value is given, revert to current value
            index = self.single_view._widget.state.slices[0]

        # If a number and out of range then set to the first or last slice
        # depending if they set the number too low or too high.
        if index < 0:
            index = 0
        if index > len(self._wavelengths) - 1:
            index = len(self._wavelengths) - 1

        # Now update the slice and wavelength text boxes
        self._update_slice_textboxes(index)

        # Update the slider.
        self.ui.value_slice.setValue(index)

    @dispatch.register_listener("change_dispersion_position")
    def _on_wavelength_change(self, event=None, pos=None):
        """
        Callback for a change in wavelength inptu box. We want to find the
        closest wavelength and use the index of it.  We will need to update
        the slice index box and slider as well as the image.

        Listen for events from the specviz viewer for when a user has changed
        the vertical line indicating the current wavelength position. Update
        the image viewers in response.
        """
        try:
            # Find the closest real wavelength and use the index of it
            wavelength = pos or float(self.ui.text_wavelength.text())
            index = np.argsort(abs(self._wavelengths - wavelength))[0]
        except ValueError:
            # If invalid value is given, revert to current value
            index = self.single_view._widget.state.slices[0]

        # Now update the slice and wavelength text boxes
        self._update_slice_textboxes(index)

        # Update the slider.
        self.ui.value_slice.setValue(index)

    def _on_slider_change(self, event):
        """
        Callback for change in slider value.

        :param event:
        :return:
        """
        index = self.ui.value_slice.value()

        # Update the image displayed in the slice in the active view
        self._active_cube._widget.update_slice_index(index)

        # If the active widget is synced then we need to update the image
        # in all the other synced views.
        if self._active_cube._widget.synced:
            for view in self.cubes:
                if view != self._active_cube and view._widget.synced:
                    view._widget.update_slice_index(index)

        # Now update the slice and wavelength text boxes
        self._update_slice_textboxes(index)

        dispatch.changed_dispersion_position.emit(pos=index)

    def _on_alpha_change(self, event):
        """
        Callback for change in alpha value.

        :param event:
        :return:
        """
        for overlay in self._active_overlays:
            overlay.set_alpha(self.ui.alpha_slider.value() / 100.)
            overlay.figure.canvas.draw()

    def _update_slice_textboxes(self, index):
        """
        Update the slice index number text box and the wavelength value displayed in the wavelengths text box.

        :param index: Slice index number displayed.
        :return:
        """

        # Update the input text box for slice number
        self.ui.text_slice.setText(str(index))

        # Update the wavelength for the corresponding slice number.
        self.ui.text_wavelength.setText(self._wavelength_format.format(self._wavelengths[index]))

    def _enable_slider(self):
        """
        Setup the slice slider (min/max, units on description and initial position). 

        :return:
        """
        self.ui.value_slice.setEnabled(True)
        self.ui.value_slice.setMinimum(0)

        # Store the wavelength units and format
        self._wavelength_units = str(self.session.data_collection.data[0].coords.wcs.wcs.cunit[2])
        self._wavelength_format = '{:.3}'
        self.ui.wavelength_slider_text.setText('Wavelength ({})'.format(self._wavelength_units))

        # Grab the wavelengths so they can be displayed in the text box
        self._wavelengths = self.single_view._widget._data[0].get_component('Wave')[:,0,0]
        self.ui.value_slice.setMaximum(len(self._wavelengths) - 1)

        # Set the default display to the middle of the cube
        middle_index = len(self._wavelengths) // 2
        self._update_slice_textboxes(middle_index)
        self.ui.value_slice.setValue(middle_index)
        self.ui.text_wavelength.setText(self._wavelength_format.format(self._wavelengths[middle_index]))

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

        self._enable_slider()
        self._enable_option_buttons()
        self._setup_syncing()

        self._enable_viewer_combos()

        self.subWindowActivated.emit(self._active_view)

        #self._toggle_flux()
        #self._toggle_error()
        #self._toggle_quality()

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
                self.ui.value_slice.setValue(index)
                self._update_slice_textboxes(index)

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
        for view in self.cubes:
            index = self._active_cube._widget.slice_index
            view._widget.enable_button()
            if view != self._active_cube:
                view._widget.update_slice_index(index)

    def showEvent(self, event):
        super(CubeVizLayout, self).showEvent(event)
        # Make split image mode the default layout
        self._split_image_mode()
        self._update_active_view(self.left_view)
