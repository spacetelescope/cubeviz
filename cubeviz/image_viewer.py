# This file contains a sub-class of the glue image viewer with further
# customizations.

import numpy as np

import matplotlib.image as mimage

from astropy import units as u
from astropy.coordinates import SkyCoord

from qtpy.QtWidgets import (QLabel, QMessageBox)

from glue.core.message import SettingsChangeMessage

from glue.utils.qt import pick_item, get_text

from glue.viewers.image.qt import ImageViewer
from glue.viewers.image.layer_artist import ImageLayerArtist
from glue.viewers.image.state import ImageLayerState
from glue.viewers.image.qt.layer_style_editor import ImageLayerStyleEditor
from glue.viewers.common.qt.tool import Tool

from .utils.contour import ContourSettings

CONTOUR_DEFAULT_NUMBER_OF_LEVELSS = 8
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

class CubevizImageLayerState(ImageLayerState):
    """
    Sub-class of ImageLayerState that includes the ability to include smoothing
    on-the-fly.
    """
    preview_function = None
    slice_index_override = None

    def get_sliced_data(self, view=None):
        """
        Override and modify ImageLayerState.get_sliced_data.
        Modifications:
            1)  If CubevizImageLayerState.preview_function is
                defined, apply the function to data before return.
            2)  If CubevizImageLayerState.slice_index_override is
                defined, change slice index to that value
        :param view: image view
        :return: 2D np.ndarray
        """
        slices, agg_func, transpose = self.viewer_state.numpy_slice_aggregation_transpose
        full_view = slices
        if self.slice_index_override is not None:
            full_view[0] = self.slice_index_override
        if view is not None and len(view) == 2:
            x_axis = self.viewer_state.x_att.axis
            y_axis = self.viewer_state.y_att.axis
            full_view[x_axis] = view[1]
            full_view[y_axis] = view[0]
            view_applied = True
        else:
            view_applied = False
        image = self._get_image(view=full_view)

        # Apply aggregation functions if needed
        if image.ndim != len(agg_func):
            raise ValueError("Sliced image dimensions ({0}) does not match "
                             "aggregation function list ({1})"
                             .format(image.ndim, len(agg_func)))
        for axis in range(image.ndim - 1, -1, -1):
            func = agg_func[axis]
            if func is not None:
                image = func(image, axis=axis)
        if image.ndim != 2:
            raise ValueError("Image after aggregation should have two dimensions")
        if transpose:
            image = image.transpose()
        if view_applied or view is None or self.preview_function is not None:
            data = image
        else:
            data = image[view]

        if self.preview_function is not None:
            return self.preview_function(data)
        else:
            return data

class CubevizImageLayerArtist(ImageLayerArtist):

    _layer_state_cls = CubevizImageLayerState


class CubevizImageViewer(ImageViewer):

    tools = ['select:rectangle', 'select:xrange', 'select:yrange',
             'select:circle', 'select:polygon', 'image:contrast_bias',
             'cubeviz:contour']

    def __init__(self,  *args, cubeviz_layout=None, **kwargs):
        super(CubevizImageViewer, self).__init__(*args, **kwargs)
        self.cubeviz_layout = cubeviz_layout
        self. _layer_style_widget_cls[CubevizImageLayerArtist] = ImageLayerStyleEditor
        self._synced_checkbox = None
        self._slice_index = None

        self.component_unit_label = ""  # String to hold units of data values

        self.is_mouse_over = False  # If mouse cursor is over viewer
        self.hold_coords = False  # Switch to hold current displayed coords
        self._coords_in_degrees = False  # Switch display coords to True=deg or False=Deg/Hr:Min:Sec
        self._coords_format_function = self._format_to_hex_string  # Function to format ra and dec
        self.x_mouse = None  # x position of mouse in pix
        self.y_mouse = None  # y position of mouse in pix

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

        self.coord_label = QLabel("")  # Coord display
        self.statusBar().addPermanentWidget(self.coord_label)

        # Connect matplotlib events to event handlers
        self.statusBar().messageChanged.connect(self.message_changed_callback)
        self.figure.canvas.mpl_connect('motion_notify_event', self.mouse_move)
        self.figure.canvas.mpl_connect('figure_enter_event', self.turn_mouse_on)

        self._dont_update_status = False  # Don't save statusBar message when coords are changing
        self.status_message = self.statusBar().currentMessage()

        # Allow the CubeViz slider to respond to viewer-specific sliders in the glue pane
        self.state.add_callback('slices', self._slice_callback)

    def _slice_callback(self, new_slice):
        if self._slice_index is not None:
            self.cubeviz_layout._slice_controller.update_index(new_slice[0])

    def get_data_layer_artist(self, layer=None, layer_state=None):
        if layer.ndim == 1:
            cls = self._scatter_artist
        else:
            cls = CubevizImageLayerArtist
        return self.get_layer_artist(cls, layer=layer, layer_state=layer_state)

    @property
    def is_preview_active(self):
        return self.is_contour_preview_active or self.is_smoothing_preview_active

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
            arr = self.state.layers[0].get_sliced_data()
        else:
            data = self.state.layers_data[0]
            arr = data[self.contour_component][self.slice_index]
        return arr

    def draw_contour(self, draw=True):
        self._delete_contour()

        if self.is_contour_preview_active:
            settings = self.contour_preview_settings
        else:
            settings = self.contour_settings

        arr = self.get_contour_array()

        vmax = arr.max()
        if settings.vmax is not None:
            vmax = settings.vmax

        vmin = arr.min()
        if settings.vmin is not None:
            vmin = settings.vmin

        if settings.spacing is None:
            spacing = 1
            if vmax != vmin:
                spacing = (vmax-vmin)/CONTOUR_DEFAULT_NUMBER_OF_LEVELSS
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
            spacing = (vmax - vmin)/CONTOUR_DEFAULT_NUMBER_OF_LEVELSS
            levels = np.arange(vmin, vmax, spacing)
            levels = np.append(levels, vmax)

        self.contour = self.axes.contour(arr, levels=levels, **settings.options)

        if settings.add_contour_label:
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
            spacing = (vmax - vmin)/CONTOUR_DEFAULT_NUMBER_OF_LEVELSS
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

    def update_slice_index(self, index):
        """
        Function to update image and slice index.
        Redraws figure.
        :param index: (int) slice index
        """
        # Reset slice index override
        for layer in self.layers:
            if isinstance(layer, CubevizImageLayerArtist):
                layer.state.slice_index_override = None

        self._slice_index = index
        z, y, x = self.state.slices
        self.state.slices = (self._slice_index, y, x)
        if self.is_contour_active:
            self.draw_contour()

    def fast_draw_slice_at_index(self, index):
        """
        Function to update the displayed image at a slice index
        quickly. Used when the user is scrolling using a slider.
        Utilizes a modified version of matplotlib's `axes.draw()`
        function to only draw images then uses `fig.canvas.blit()`
        to update the canvas.
        :param index: (int) slice index
        """
        # draw_artist can only be used after an
        # initial draw which caches the render
        if self.axes._cachedRenderer is None:
            self.update_slice_index(index)
            return

        self._slice_index = index

        # Set main image's slice index to index
        for layer in self.layers:
            if isinstance(layer, CubevizImageLayerArtist):
                layer.state.slice_index_override = index
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
        return self._synced_checkbox.isChecked()

    @synced.setter
    def synced(self, value):
        self._synced_checkbox.setChecked(value)

    @property
    def slice_index(self):
        return self._slice_index

    def update_component_unit_label(self, component_id):
        """
        Update component's unit label.
        :param component_id: component id
        """

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
        self.x_mouse = None
        self.y_mouse = None
        self.coord_label.setText('')
        self.statusBar().showMessage(self.status_message)

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
            wavelength_unit = self.parent().tab_widget.get_wavelengths_units().short_names[0]
            coord_string += ", {:1.2e}{})".format(wave, wavelength_unit)
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
            wavelength_unit = self.parent().tab_widget._units_controller._new_units.short_names[0]
            coord_string += ", {:1.2e}{})".format(wave, wavelength_unit)
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
            for layer in self.state.layers:
                if layer.layer is self.state.reference_data:
                    arr = layer.get_sliced_data()
                    break
            else:
                raise Exception("Couldn't find layer corresponding to reference data")

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
                string = "{0:.3e} {1} ".format(v, self.component_unit_label) + string
        # Add a gap to string and add to viewer.
        string += " "
        self._dont_update_status = True
        self.statusBar().clearMessage()
        self._dont_update_status = False
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
        self.is_mouse_over = False
        return

    def turn_mouse_on(self, event):
        self.is_mouse_over = True
