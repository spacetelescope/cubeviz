# This file contains a sub-class of the glue image viewer with further
# customizations.

import numpy as np

from astropy import units as u
from astropy.coordinates import SkyCoord

from qtpy.QtWidgets import QLabel

from glue.core.message import SettingsChangeMessage

from glue.viewers.image.qt import ImageViewer
from glue.viewers.image.layer_artist import ImageLayerArtist
from glue.viewers.image.state import ImageLayerState
from glue.viewers.image.qt.layer_style_editor import ImageLayerStyleEditor

__all__ = ['CubevizImageViewer']

class CubevizImageLayerState(ImageLayerState):
    """
    Sub-class of ImageLayerState that includes the ability to include smoothing
    on-the-fly.
    """

    preview_function = None

    def get_sliced_data(self, view=None):
        if self.preview_function is None:
            return super(CubevizImageLayerState, self).get_sliced_data(view=view)
        else:
            data = super(CubevizImageLayerState, self).get_sliced_data()
            return self.preview_function(data)


class CubevizImageLayerArtist(ImageLayerArtist):

    _layer_state_cls = CubevizImageLayerState


class CubevizImageViewer(ImageViewer):

    tools = ['select:rectangle', 'select:xrange', 'select:yrange',
             'select:circle', 'select:polygon', 'image:contrast_bias']

    def __init__(self, *args, **kwargs):
        super(CubevizImageViewer, self).__init__(*args, **kwargs)
        self. _layer_style_widget_cls[CubevizImageLayerArtist] = ImageLayerStyleEditor
        self._synced_checkbox = None
        self._slice_index = None

        self.is_mouse_over = False  # If mouse cursor is over viewer
        self.hold_coords = False  # Switch to hold current displayed coords
        self._coords_in_degrees = True  # Switch display coords to True=deg or False=Deg/Hr:Min:Sec
        self._coords_format_function = self._format_to_degree_string  # Function to format ra and dec
        self.x_mouse = None  # x position of mouse in pix
        self.y_mouse = None  # y position of mouse in pix

        self.is_smoothing_preview_active = False  # Smoothing preview flag
        self.smoothing_preview_title = ""

        self.is_axes_hidden = False  # True if axes is hidden
        self.axes_title = ""  # Plot title

        self.coord_label = QLabel("")  # Coord display
        self.statusBar().addPermanentWidget(self.coord_label)

        # Connect matplotlib events to event handlers
        self.figure.canvas.mpl_connect('motion_notify_event', self.mouse_move)
        self.figure.canvas.mpl_connect('axes_leave_event', self.mouse_exited)

    def get_data_layer_artist(self, layer=None, layer_state=None):
        if layer.ndim == 1:
            cls = self._scatter_artist
        else:
            cls = CubevizImageLayerArtist
        return self.get_layer_artist(cls, layer=layer, layer_state=layer_state)

    def update_axes_title(self, title=None):
        """
        Update plot title.
        :param title: str: Plot title
        """
        if title is not None:
            self.axes_title = title

        self.axes.set_title(self.axes_title, color="black")
        self.axes.figure.canvas.draw()

        # Disabled feature:
        #self.statusBar().showMessage(self.axes_title)

    def show_smoothing_title(self):
        """
        Override normal plot title to show smoothing preview title.
        """
        if self.is_axes_hidden:
            if self.is_smoothing_preview_active:
                st = self.figure.suptitle(self.smoothing_preview_title, color="black")
                st.set_bbox(dict(facecolor='red', edgecolor='red'))
                self.axes.set_title("", color="black")
        else:
            if self.is_smoothing_preview_active:
                self.axes.set_title(self.smoothing_preview_title, color="r")

    def hide_smoothing_title(self):
        self.figure.suptitle("", color="black")

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
        self.show_smoothing_title()

        for layer in self.layers:
            if isinstance(layer, CubevizImageLayerArtist):
                layer.state.preview_function = preview_function
        self.axes._composite_image.invalidate_cache()
        self.axes.figure.canvas.draw()

    def end_smoothing_preview(self):
        """
        Ends on the fly smoothing.
        Warning: A change of combo index should always happen
        after calling this function!
        """
        self.is_smoothing_preview_active = False
        self.hide_smoothing_title()
        self.update_axes_title()
        self.smoothing_preview_title = "Smoothing Preview"
        for layer in self.layers:
            if isinstance(layer, CubevizImageLayerArtist):
                layer.state.preview_function = None
        self.axes._composite_image.invalidate_cache()
        self.axes.figure.canvas.draw()

    def toggle_hidden_axes(self, is_axes_hidden):
        """
        Opertations to execute when axes is hidden/shown.
        :param is_axes_hidden: bool: True if axes is now hidden
        """
        self.is_axes_hidden = is_axes_hidden

        # Plot title operations
        if self.is_smoothing_preview_active:
            self.hide_smoothing_title()
            self.show_smoothing_title()
        else:
            self.update_axes_title()

    def _synced_checkbox_callback(self, event):
        if self._synced_checkbox.isChecked():
            msg = SettingsChangeMessage(self, [self])
            self.parent().tab_widget.session.hub.broadcast(msg)
            self.update_slice_index(self.parent().tab_widget.synced_index)

    def assign_synced_checkbox(self, checkbox):
        self._synced_checkbox = checkbox
        self._synced_checkbox.stateChanged.connect(self._synced_checkbox_callback)

    def update_slice_index(self, index):
        self._slice_index = index
        z, y, x = self.state.slices
        self.state.slices = (self._slice_index, y, x)

    @property
    def synced(self):
        return self._synced_checkbox.isChecked()

    @synced.setter
    def synced(self, value):
        self._synced_checkbox.setChecked(value)

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
