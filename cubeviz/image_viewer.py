# -*- coding: utf-8 -*-
# This file contains a sub-class of the glue image viewer with further
# customizations.

import numpy as np

from matplotlib.axes import Axes
import matplotlib.image as mimage
from matplotlib.patches import Circle

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.wcs.utils import wcs_to_celestial_frame
from astropy.coordinates import BaseRADecFrame

from qtpy.QtWidgets import (QLabel, QMessageBox)

from glue.core.message import SettingsChangeMessage

from glue.utils.qt import pick_item, get_text

from glue.viewers.image.qt import ImageViewer
from glue.viewers.image.layer_artist import ImageLayerArtist
from glue.viewers.image.state import ImageLayerState, ImageViewerState
from glue.viewers.image.qt.layer_style_editor import ImageLayerStyleEditor
from glue.viewers.common.qt.tool import Tool
from glue.viewers.matplotlib.state import DeferredDrawCallbackProperty as DDCProperty

from qtpy.QtWidgets import QToolTip
from qtpy.QtGui import QCursor

from .messages import (SliceIndexUpdateMessage, WavelengthUpdateMessage,
                       WavelengthUnitUpdateMessage, FluxUnitsUpdateMessage)
from .utils.contour import ContourSettings

CONTOUR_DEFAULT_NUMBER_OF_LEVELS = 8
CONTOUR_MAX_NUMBER_OF_LEVELS = 1000

__all__ = ['CubevizImageViewer']


def only_draw_axes_images(ax):
    """
    This function is a modified version of
    matplotlib.axes._base._AxesBase.draw
    This version only updates the images
    of the axes.
    :param ax: axes with images to update
    """
    if not ax.get_visible():
        return

    renderer = ax._cachedRenderer
    renderer.open_group('axes')

    # prevent triggering call backs during the draw process
    ax._stale = True

    locator = ax.get_axes_locator()
    if locator:
        pos = locator(ax, renderer)
        ax.apply_aspect(pos)
    else:
        ax.apply_aspect()

    # This is the biggest modification
    # Restrict the artists list to images
    artists = ax.images
    artists = sorted(artists, key=lambda x: x.zorder)

    # rasterize artists with negative zorder
    # if the minimum zorder is negative, start rasterization
    rasterization_zorder = ax._rasterization_zorder
    if (rasterization_zorder is not None and
            artists and artists[0].zorder < rasterization_zorder):
        renderer.start_rasterizing()
        artists_rasterized = [a for a in artists
                              if a.zorder < rasterization_zorder]
        artists = [a for a in artists
                   if a.zorder >= rasterization_zorder]
    else:
        artists_rasterized = []

    if artists_rasterized:
        for a in artists_rasterized:
            a.draw(renderer)
        renderer.stop_rasterizing()

    # This function will draw the images in the artist list
    mimage._draw_list_compositing_images(renderer, ax, artists)

    if hasattr(ax, "coords"):
        ax.coords.frame.draw(renderer)

    renderer.close_group('axes')
    ax._cachedRenderer = renderer
    ax.stale = False


class CubevizImageViewerState(ImageViewerState):

    # Override and modify ImageViewerState, so as to override the slice index
    # if needed.

    _slice_index_override = None

    @property
    def slice_index_override(self):
        return self._slice_index_override

    @slice_index_override.setter
    def slice_index_override(self, value):
        # The image viewer state uses smart caching to only update the data
        # when needed - some of which relies on checking for changes in the
        # slices - we therefore need to tell it about the change in the override
        slices_before = self.numpy_slice_aggregation_transpose[0]
        self._slice_index_override = value
        slices_after = self.numpy_slice_aggregation_transpose[0]
        for layer in self.layers:
            layer.reset_cache_from_slices(slices_before, slices_after)

    @property
    def numpy_slice_aggregation_transpose(self):
        slices, agg_func, transpose = super(CubevizImageViewerState, self).numpy_slice_aggregation_transpose
        if self.slice_index_override is not None:
            slices[0] = self.slice_index_override
        return slices, agg_func, transpose


class CubevizImageLayerState(ImageLayerState):
    """
    Sub-class of ImageLayerState that includes the ability to include smoothing
    on-the-fly.
    """

    preview_function = None

    # Override glue default
    global_sync = DDCProperty(False)

    def get_sliced_data(self, view=None):
        """
        Override and modify ImageLayerState.get_sliced_data so that if
        CubevizImageLayerState.preview_function is defined, it is applied to the
        data before return.
        """
        self._cache = None
        if self.preview_function is None:
            return super(CubevizImageLayerState, self).get_sliced_data(view=view)
        else:
            image = super(CubevizImageLayerState, self).get_sliced_data()
            image = self.preview_function(image)
            if view is not None:
                image = image[view]
            return image


class CubevizImageLayerStyleEditor(ImageLayerStyleEditor):

    # Override this in order to get rid of the sync button

    def __init__(self, *args, **kwargs):
        super(CubevizImageLayerStyleEditor, self).__init__(*args, **kwargs)
        self.ui.bool_global_sync.setVisible(False)


class CubevizImageLayerArtist(ImageLayerArtist):

    _state_cls = CubevizImageViewerState
    _layer_state_cls = CubevizImageLayerState


class CubevizImageViewer(ImageViewer):

    tools = ['select:rectangle', 'select:xrange', 'select:yrange',
             'select:circle', 'select:polygon', 'image:contrast_bias',
             'cubeviz:contour']

    _state_cls = CubevizImageViewerState
    _close_on_last_layer_removed = False

    def __init__(self,  *args, cubeviz_layout=None, **kwargs):
        super(CubevizImageViewer, self).__init__(*args, **kwargs)
        self.cubeviz_layout = cubeviz_layout
        self._layer_style_widget_cls[CubevizImageLayerArtist] = CubevizImageLayerStyleEditor
        self._hub = cubeviz_layout.session.hub
        self._synced_checkbox = None
        self._slice_index = None

        self.current_component_id = None  # Current component id

        self.cubeviz_unit = None
        self.component_unit_label = ""  # String to hold units of data values

        self.is_mouse_over = False  # If mouse cursor is over viewer
        self.hold_coords = False  # Switch to hold current displayed coords
        self._coords_in_degrees = False  # Switch display coords to True=deg or False=Deg/Hr:Min:Sec
        self._coords_format_function = self._format_to_hex_string  # Function to format ra and dec
        self.x_mouse = None  # x position of mouse in pix
        self.y_mouse = None  # y position of mouse in pix
        self.mouse_value = ""  # Value under mouse as string
        self._is_tooltip_on = True  # Display mouse_value as tool tip

        self.is_contour_active = False  # Is contour being displayed
        self.is_contour_preview_active = False # Is contour in preview mode
        self.contour = None  # matplotlib.axes.Axes.contour
        self.contour_component = None  # component label for contour
        self.contour_settings = ContourSettings(self)  # ContourSettings
        self.contour_preview_settings = None  # Temporary ContourSettings

        self.is_smoothing_preview_active = False  # Smoothing preview flag
        self.smoothing_preview_title = ""

        self.is_axes_hidden = False  # True if axes is hidden
        self.axes_title = ""  # Plot title

        self._has_2d_data = False  # True if currently displayed data is 2D
        self._toggle_3d = False  # True if we just toggled from 2D to 3D

        self._subset = None # Keep track of currently active subset

        self.coord_label = QLabel("")  # Coord display
        self.statusBar().addPermanentWidget(self.coord_label)

        # These are updated by listeners. See hub subscribers below
        self._wavelengths = None  # Array of wavelengths to display
        self._wavelength_units = None  # Units to use for wavelength values

        # Connect matplotlib events to event handlers
        self.statusBar().messageChanged.connect(self.message_changed_callback)
        self.figure.canvas.mpl_connect('motion_notify_event', self.mouse_move)
        self.figure.canvas.mpl_connect('figure_enter_event', self.turn_mouse_on)

        self._dont_update_status = False  # Don't save statusBar message when coords are changing
        self.status_message = self.statusBar().currentMessage()

        # Allow the CubeViz slider to respond to viewer-specific sliders in the glue pane
        self.state.add_callback('slices', self._slice_callback)

        self._hub.subscribe(self, SliceIndexUpdateMessage, handler=self._update_viewer_index)
        self._hub.subscribe(self, WavelengthUpdateMessage, handler=self._update_wavelengths)
        self._hub.subscribe(self, WavelengthUnitUpdateMessage, handler=self._update_wavelength_units)
        self._hub.subscribe(self, FluxUnitsUpdateMessage, handler=self._update_flux_units)

    def _slice_callback(self, new_slice):
        if self._slice_index is not None and not self.has_2d_data:
            self.cubeviz_layout._slice_controller.update_index(new_slice[0])
        # When toggling from 2D to 3D data component, update to synced index
        elif self._toggle_3d:
            self._toggle_3d = False
            self.cubeviz_layout._slice_controller.update_index(self.cubeviz_layout.synced_index)
            self.update_slice_index(self.cubeviz_layout.synced_index)

    def get_data_layer_artist(self, layer=None, layer_state=None):
        if layer.ndim == 1:
            cls = self._scatter_artist
        else:
            cls = CubevizImageLayerArtist
        return self.get_layer_artist(cls, layer=layer, layer_state=layer_state)

    def _update_stats_text(self, label, min_, max_, median, mu, sigma):
        text = r"min={:.4}, max={:.4}, median={:.4}, μ={:.4}, σ={:.4}".format(min_, max_, median, mu, sigma)
        self.parent().set_stats_text(label, text)

    def _calculate_stats(self, data):
        if self.cubeviz_unit is not None:
            wave = self.cubeviz_layout.get_wavelength(self.slice_index)
            data = self.cubeviz_unit.convert_from_original_unit(data, wave=wave)
        return np.nanmin(data), np.nanmax(data), np.median(data), data.mean(), data.std()

    def show_roi_stats(self, component, subset):

        if self._has_2d_data or subset.ndim != 3:
            self.parent().set_stats_text('', '')
            return

        self._subset = subset

        mask = subset.to_mask()[self._slice_index]
        data = self._data[0][component][self._slice_index][mask]

        results = self._calculate_stats(data)
        label = '{} Statistics:'.format(subset.label)
        self._update_stats_text(label, *results)

    def show_slice_stats(self):

        if self._has_2d_data:
            self.parent().set_stats_text('', '')
            return

        self._subset = None

        data = self._data[0][self.current_component_id][self._slice_index]
        results = self._calculate_stats(data.copy())
        self._update_stats_text('Slice Statistics:', *results)

    def update_stats(self):

        if self._subset is not None:
            self.show_roi_stats(self.current_component_id, self._subset)
        else:
            self.show_slice_stats()

    def update_component(self, component):
        self.update_stats()

    @property
    def is_preview_active(self):
        return self.is_contour_preview_active or self.is_smoothing_preview_active

    @property
    def has_2d_data(self):
        return self._has_2d_data or self._toggle_3d

    @has_2d_data.setter
    def has_2d_data(self, value):
        if self._has_2d_data and not value:
            self._toggle_3d = True
        self._has_2d_data = value

    def update_axes_title(self, title=None):
        """
        Update plot title.
        :param title: str: Plot title
        """
        if title is not None:
            if self.component_unit_label:
                self.axes_title = "{0} [{1}]".format(title, self.component_unit_label)
            else:
                self.axes_title = title

        if self.is_contour_preview_active:
            return

        self.axes.set_title(self.axes_title, color="black")
        self.axes.figure.canvas.draw()

        # Disabled feature:
        #self.statusBar().showMessage(self.axes_title)

    def show_preview_title(self):
        """
        Override normal plot title to show smoothing preview title.
        """
        if self.is_smoothing_preview_active:
            title = self.smoothing_preview_title
        elif self.is_contour_preview_active:
            title = "Contour Preview"
        else:
            return

        if self.is_axes_hidden:
            st = self.figure.suptitle(title, color="black")
            st.set_bbox(dict(facecolor='red', edgecolor='red'))
            self.axes.set_title("", color="black")
        else:
            self.axes.set_title(title, color="r")

    def hide_preview_title(self):
        """
        You should always call this after setting the is_preview flag
        """
        self.figure.suptitle("", color="black")
        if self.is_preview_active:
            self.show_preview_title()
        else:
            self.update_axes_title()

    def set_smoothing_preview(self, preview_function, preview_title=None):
        """
        Sets up on the fly smoothing and displays smoothing preview title.
        :param preview_function: function: Single-slice smoothing function
        :param preview_title: str: Title displayed when previewing
        """
        self.is_smoothing_preview_active = True

        if preview_title is None:
            self.smoothing_preview_title = "Smoothing Preview"
        else:
            self.smoothing_preview_title = preview_title
        self.show_preview_title()

        for layer in self.layers:
            if isinstance(layer, CubevizImageLayerArtist):
                layer.state.preview_function = preview_function
        self.axes._composite_image.invalidate_cache()
        if self.is_contour_active:
            self.draw_contour()
        else:
            self.axes.figure.canvas.draw()

    def end_smoothing_preview(self):
        """
        Ends on the fly smoothing.
        Warning: A change of combo index should always happen
        after calling this function!
        """
        self.is_smoothing_preview_active = False
        self.hide_preview_title()
        self.smoothing_preview_title = "Smoothing Preview"
        for layer in self.layers:
            if isinstance(layer, CubevizImageLayerArtist):
                layer.state.preview_function = None
        self.axes._composite_image.invalidate_cache()
        if self.is_contour_active:
            self.draw_contour()
        else:
            self.axes.figure.canvas.draw()

    def toggle_hidden_axes(self, is_axes_hidden):
        """
        Opertations to execute when axes is hidden/shown.
        :param is_axes_hidden: bool: True if axes is now hidden
        """
        self.is_axes_hidden = is_axes_hidden

        # Plot title operations
        if self.is_preview_active:
            self.show_preview_title()
        else:
            self.update_axes_title()

    def _delete_contour(self):
        if self.contour is not None:
            for c in self.contour.collections:
                c.remove()

            for c in self.contour.labelTexts:
                c.remove()
            del self.contour
            self.contour = None

    def get_contour_array(self):
        if self.contour_component is None:
            layer_artist = self.first_visible_layer()
            arr = layer_artist.state.get_sliced_data()
        else:
            data = self.state.layers_data[0]
            arr = data[self.contour_component][self.slice_index]

        if self.cubeviz_unit is not None:
            arr = arr.copy()
            wave = self.cubeviz_layout.get_wavelength(self.slice_index)
            arr = self.cubeviz_unit.convert_from_original_unit(arr, wave=wave)

        return arr

    def draw_contour(self, draw=True):
        self._delete_contour()

        if len(self.visible_layers()) == 0:
            return

        if self.is_contour_preview_active:
            settings = self.contour_preview_settings
        else:
            settings = self.contour_settings

        arr = self.get_contour_array()

        vmax = np.nanmax(arr)
        if settings.vmax is not None:
            vmax = settings.vmax

        vmin = np.nanmin(arr)
        if settings.vmin is not None:
            vmin = settings.vmin

        if settings.spacing is None:
            spacing = 1
            if vmax != vmin:
                spacing = (vmax - vmin)/CONTOUR_DEFAULT_NUMBER_OF_LEVELS
        else:
            spacing = settings.spacing

        levels = np.arange(vmin, vmax, spacing)
        levels = np.append(levels, vmax)

        if levels.size > CONTOUR_MAX_NUMBER_OF_LEVELS:
            message = "The current contour spacing is too small and " \
                      "results in too many levels. Contour spacing " \
                      "settings have been reset to auto."
            info = QMessageBox.critical(self, "Error", message)

            settings.spacing = None
            settings.data_spacing = spacing
            if settings.dialog is not None:
                settings.dialog.custom_spacing_checkBox.setChecked(False)
            spacing = (vmax - vmin)/CONTOUR_DEFAULT_NUMBER_OF_LEVELS
            levels = np.arange(vmin, vmax, spacing)
            levels = np.append(levels, vmax)

        self.contour = self.axes.contour(arr, levels=levels, **settings.options)

        if settings.add_contour_label:
            if abs(levels).max() > 1000 \
                    or 0.0 < abs(levels).min() < 0.001 \
                    or 0.0 < abs(levels).max() < 0.001:
                self.axes.clabel(self.contour,
                                 fmt='%.2E',
                                 fontsize=settings.font_size)
            else:
                self.axes.clabel(self.contour, fontsize=settings.font_size)

        settings.data_max = arr.max()
        settings.data_min = arr.min()
        settings.data_spacing = spacing
        if settings.dialog is not None:
            settings.update_dialog()
        if draw:
            self.axes.figure.canvas.draw()

    def default_contour(self, *args):
        """
        Draw contour of current component
        :param args: arguments from toolbar
        """
        self.is_contour_active = True
        self.contour_component = None
        self.draw_contour()

    def custom_contour(self, *args):
        """
        Draw contour of a specified component
        To change component programmatically
        change the `contour_component` class var
        :param args: arguments from toolbar
        """

        components = self.cubeviz_layout.component_labels
        self.contour_component = pick_item(components, components,
                                           title='Custom Contour',
                                           label='Pick a component')
        if self.contour_component is None:
            return
        else:
            self.is_contour_active = True
            self.draw_contour()

    def remove_contour(self, *args):
        """
        Turn contour off
        :param args: arguments from toolbar
        """
        self.is_contour_active = False
        self._delete_contour()
        self.axes.figure.canvas.draw()

    def edit_contour_settings(self, *args):
        """
        Edit contour settings using UI
        :param args: arguments from toolbar
        :return: settings UI
        """
        arr = self.get_contour_array()
        vmax = arr.max()
        vmin = arr.min()
        spacing = 1
        if vmax != vmin:
            spacing = (vmax - vmin)/CONTOUR_DEFAULT_NUMBER_OF_LEVELS
        self.contour_settings.data_max = vmax
        self.contour_settings.data_min = vmin
        self.contour_settings.data_spacing = spacing

        return self.contour_settings.options_dialog()

    def set_contour_preview(self, contour_preview_settings):
        """
        Apply contour preview settings.
        :param contour_preview_settings: ContourSettings
        """
        self.is_contour_preview_active = True
        self.show_preview_title()
        self.contour_preview_settings = contour_preview_settings
        self.draw_contour()

    def end_contour_preview(self):
        """ End contour preview"""
        self.is_contour_preview_active = False
        self.hide_preview_title()
        self.contour_preview_settings = None
        if self.is_contour_active:
            self.draw_contour()
        else:
            self.remove_contour()

    def _synced_checkbox_callback(self, event):
        if self._synced_checkbox.isChecked():
            msg = SettingsChangeMessage(self, [self])
            self.parent().tab_widget.session.hub.broadcast(msg)
            self.update_slice_index(self.parent().tab_widget.synced_index)

    def assign_synced_checkbox(self, checkbox):
        self._synced_checkbox = checkbox
        self._synced_checkbox.stateChanged.connect(self._synced_checkbox_callback)

    def _update_viewer_index(self, message):

        index = message.index
        active_cube = self.cubeviz_layout._active_cube
        active_widget = active_cube._widget

        # If the active widget is synced then we need to update the image
        # in all the other synced views.
        if (active_widget.synced and self.synced and not \
            self.cubeviz_layout._single_viewer_mode) or \
                active_widget is self:
            if message.slider_down:
                self.fast_draw_slice_at_index(index)
            else:
                self.update_slice_index(index)

        self.parent().slice_text.setText('slice: {:5}'.format(self._slice_index))

    def update_slice_index(self, index):
        """
        Function to update image and slice index.
        Redraws figure.
        :param index: (int) slice index
        """

        # Reset slice index override
        self.state.slice_index_override = None

        # Do not update if displaying a 2D data component
        if len(self.state.slices) == 2:
            return

        self._slice_index = index
        z, y, x = self.state.slices
        self.state.slices = (self._slice_index, y, x)
        if self.is_contour_active:
            self.draw_contour()

        self.update_stats()

    def fast_draw_slice_at_index(self, index):
        """
        Function to update the displayed image at a slice index
        quickly. Used when the user is scrolling using a slider.
        Utilizes a modified version of matplotlib's `axes.draw()`
        function to only draw images then uses `fig.canvas.blit()`
        to update the canvas.
        :param index: (int) slice index
        """

        if self._slice_index == index:
            return

        # draw_artist can only be used after an
        # initial draw which caches the render
        if self.axes._cachedRenderer is None:
            self.update_slice_index(index)
            return

        self._slice_index = index

        # Set main image's slice index to index
        self.state.slice_index_override = index

        # Invalidate cached data for image viewer
        # Or else it will not be redrawn
        self.axes._composite_image.invalidate_cache()

        # Redraw canvas images
        fig = self.axes.figure
        for ax in fig.axes:
            only_draw_axes_images(ax)

        # Draw contour and its labels
        ax = self.axes
        if self.is_contour_active and self.contour is not None:
            self.draw_contour(draw=False)
            for c in self.contour.collections:
                ax.draw_artist(c)
            for t in self.contour.labelTexts:
                ax.draw_artist(t)

        # update canvas using blit
        fig.canvas.blit()

    @property
    def synced(self):
        return self._synced_checkbox.isChecked() and not self.has_2d_data

    @synced.setter
    def synced(self, value):
        self._synced_checkbox.setChecked(value)

    @property
    def slice_index(self):
        return self._slice_index

    def _update_flux_units(self, message):
        target_component_id = message.component_id
        if str(self.current_component_id) == str(target_component_id):
            self.update_component_unit_label(target_component_id)
            self.update_axes_title(str(target_component_id))
            self.update_slice_index(self.slice_index)

    def update_component_unit_label(self, component_id=None):
        """
        Update component's unit label.
        :param component_id: component id
        """
        if component_id is None:
            if self.current_component_id is None:
                self.component_unit_label = ""
                return self.component_unit_label
            component_id = self.current_component_id
        data = component_id.parent
        unit = str(data.get_component(component_id).units)
        if unit:
            self.component_unit_label = "{0}".format(unit)
        else:
            self.component_unit_label = ""
        return self.component_unit_label

    def get_coords(self):
        """
        Returns coord display string.
        """
        if self.is_mouse_over:
            return self.coord_label.text()
        return None

    def toggle_hold_coords(self):
        """
        Switch hold_coords state
        """
        if self.hold_coords:
            self.statusBar().showMessage("")
            self.hold_coords = False
        else:
            self.statusBar().showMessage("Frozen Coordinates")
            self.hold_coords = True

    def init_ra_dec(self):
        """
        Initialize the format of RA and DEC
        on the image viewers.
        Options:
            1) Sexagesimal:
                _coords_in_degrees -> False
                formatter_0 -> 'hh:mm:ss'
                formatter_1 -> 'dd:mm:ss'
            2) Decimal Degrees:
                _coords_in_degrees -> True
                formatter_0 -> 'd.dddd'
                formatter_1 -> 'd.dddd'
        """
        self._coords_in_degrees = False
        self.axes.coords[0].set_major_formatter('hh:mm:ss.s')
        self.axes.coords[1].set_major_formatter('dd:mm:ss')
        self.figure.canvas.draw()

    def toggle_coords_in_degrees(self):
        """
        Switch coords_in_degrees state
        """
        data = self.state.layers_data[0]
        is_ra_dec = isinstance(wcs_to_celestial_frame(data.coords.wcs),
                               BaseRADecFrame)
        if self._coords_in_degrees:
            self._coords_in_degrees = False
            self._coords_format_function = self._format_to_hex_string
            if is_ra_dec:
                self.axes.coords[0].set_major_formatter('hh:mm:ss.s')
                self.axes.coords[1].set_major_formatter('dd:mm:ss')
                self.figure.canvas.draw()
        else:
            self._coords_in_degrees = True
            self._coords_format_function = self._format_to_degree_string
            if is_ra_dec:
                self.axes.coords[0].set_major_formatter('d.dddd')
                self.axes.coords[1].set_major_formatter('d.dddd')
                self.figure.canvas.draw()

    def message_changed_callback(self, event):
        """
        This will be used to swap tool messages and coords messages.
        When coords are displayed, tool message is cleared.
        So we save the tool message and update it when it changes.
        This callback is for when the tool message changes and the
        boolean associated is to ignore the tool messages from the
        coordinate display.
        :param event: str: New status bar message.
        """
        if self._dont_update_status:
            return
        self.status_message = event

    def clear_coords(self):
        """
        Reset coord display and mouse tracking variables.
        If hold_coords is active (True), make changes
        only to indicate that the mouse is no longer over viewer.
        """
        if self.hold_coords:
            return
        if QToolTip.text() == self.mouse_value:
            QToolTip.hideText()
        self.x_mouse = None
        self.y_mouse = None
        self.coord_label.setText('')
        self.statusBar().showMessage(self.status_message)

    def _update_wavelengths(self, message):
        self._wavelengths = message.wavelengths

    def _update_wavelength_units(self, message):
        self._wavelength_units = message.units

    def _format_to_degree_string(self, ra, dec):
        """
        Format RA and Dec in degree format. If wavelength
        is available add it to the output sting.
        :return: string
        """
        coord_string = "({:0>8.4f}, {:0>8.4f}".format(ra, dec)

        # Check if wavelength is available
        if self.slice_index is not None and self._wavelengths is not None:
            wave = self._wavelengths[self.slice_index]
            coord_string += ", {:1.2e}{})".format(wave, self._wavelength_units)
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
        coord_string += ", "
        coord_string += "{0:0>3.0f}d:{1:0>2.0f}m:{2:0>2.0f}s".format(*c.dec.dms)

        # Check if wavelength is available
        if self.slice_index is not None and self._wavelengths is not None:
            wave = self._wavelengths[self.slice_index]
            coord_string += ", {:1.2e}{})".format(wave, self._wavelength_units)
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
            self.is_mouse_over = False
            self.clear_coords()
            return
        mouse_pos = QCursor.pos()
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

        self.mouse_value = ""

        # If viewer has a layer.
        if len(self.visible_layers()) > 0:

            arr = self.first_visible_layer().state.get_sliced_data()

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
                if self.cubeviz_unit is not None:
                    wave = self.cubeviz_layout.get_wavelength(self.slice_index)
                    v = self.cubeviz_unit.convert_from_original_unit(v, wave=wave)

                unit_string = ""
                if self.component_unit_label:
                    unit_string = "[{0}] ".format(self.component_unit_label)

                if 0.01 <= abs(v) <= 1000 or abs(v) == 0.0:
                    value_string = "{0:.3f} ".format(v)
                else:
                    value_string = "{0:.3e} ".format(v)

                self.mouse_value = value_string + unit_string
                string = value_string + string
        # Add a gap to string and add to viewer.
        string += " "
        self._dont_update_status = True
        self.statusBar().clearMessage()
        self._dont_update_status = False
        self.coord_label.setText(string)

        if self._is_tooltip_on:
            if self.mouse_value:
                QToolTip.showText(mouse_pos, "...", self)
                QToolTip.showText(mouse_pos, self.mouse_value, self)
            else:
                QToolTip.showText(mouse_pos, "...", self)
                QToolTip.showText(mouse_pos, " ", self)

        return

    def first_visible_layer(self):
        layers = self.visible_layers()
        if len(layers) == 0:
            raise Exception("Couldn't find any visible layers")
        else:
            return layers[0]

    def visible_layers(self):
        layers = []
        for layer_artist in self.layers:
            if layer_artist.enabled and layer_artist.visible:
                layers.append(layer_artist)
        return layers

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
        self.is_mouse_over = False
        return

    def turn_mouse_on(self, event):
        self.is_mouse_over = True
