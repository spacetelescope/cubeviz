import numpy as np
from glue.core.data import Data
from glue.config import colormaps as glue_colormaps


DEFAULT_GLUE_COLORMAP_INDEX = 3


class OverlayController:

    def __init__(self, cubeviz_layout):
        self._cv_layout = cubeviz_layout
        self._cube_views = cubeviz_layout.cube_views
        ui = cubeviz_layout.ui

        self._overlays = Data('Overlays')
        # This is a list of overlay objects that are currently displayed
        self._active_overlays = []
        # Maps overlays to the data sets they represent
        self._overlay_map = {}
        self._overlay_colorbar_axis = []

        self._overlay_image_combo = ui.overlay_image_combo
        self._overlay_colormap_combo = ui.overlay_colormap_combo
        self._alpha_slider = ui.alpha_slider
        self._colormap_index = DEFAULT_GLUE_COLORMAP_INDEX

        self._overlay_image_combo.addItem("No Overlay")
        self._overlay_image_combo.currentIndexChanged.connect(
            self._on_overlay_change)

        self._overlay_colormap_combo.setCurrentIndex(self._colormap_index)
        self._overlay_colormap_combo.currentIndexChanged.connect(
            self._on_colormap_change)

        self._alpha_slider.valueChanged.connect(self._on_alpha_change)

    def add_overlay(self, data, label, display=True):
        self._overlays.add_component(data, label)
        # TODO: Is there a way to get this from the component ???
        self._overlay_image_combo.addItem(label)
        new_index = self._overlay_image_combo.count() - 1
        self._overlay_map[new_index] = data

        self._alpha_slider.setEnabled(True)
        self._overlay_image_combo.setEnabled(True)
        self._overlay_colormap_combo.setEnabled(True)

        if display:
            # Setting the index will cause _on_overlay_change to fire
            self._overlay_image_combo.setCurrentIndex(new_index)

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
        for cube in self._cube_views:
            cube._widget.figure.canvas.draw()

    def _draw_mpl_overlay(self, data, view):
        axes = view._widget.axes
        aspect = axes.get_aspect()

        extent = 0, data.shape[0], 0, data.shape[1]

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

    def display_overlay(self, data):
        # Remove all existing overlays
        if self._active_overlays:
            for overlay, view, cb in zip(
                    self._active_overlays, self._cube_views, self._overlay_colorbar_axis):
                overlay.remove()
                cb.remove()
                view._widget.figure.canvas.draw()

            self._active_overlays = []
            self._overlay_colorbar_axis = []

        # Just return if no new overlay is to be drawn
        if data is None:
            return

        self._active_overlays = []
        for view in self._cube_views:
            self._draw_mpl_overlay(data, view)

        self._alpha_slider.setValue(25)

    def _on_alpha_change(self, event):
        """
        Callback for change in alpha value.

        :param event:
        :return:
        """
        for overlay in self._active_overlays:
            overlay.set_alpha(self._alpha_slider.value() / 100.)
            overlay.figure.canvas.draw()
