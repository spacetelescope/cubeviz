The Spectrum Viewer
===================

The 1D spectrum viewer, or 
`specviz <https://specviz.readthedocs.io/en/stable/>`__
viewer, displays one-dimensional spectra. 
These are typically extracted from regions in the data cube by making selections
in the image viewers. But they could also be imported as separate data sets
or computed via model fitting or mathematical operations on other spectra. 
The spectrum viewer will overlay multiple spectra on the same plot, but they
must all be in the same units.

When the mouse focus is in the spectrum viewer (as indicated by the blue box around it),
the bottom left menu will let you select spectra.  Operations will be performed on the 
spectrum that is selected (highlighted in blue in the menu). Toggle which overlays are
visible using the checkboxes.

The green vertical line on the display shows the wavelength being displayed in
the image viewer (the last one that had the mouse focus if the image viewers
are not synced). 

Zoom and pan are done by left-clicking and moving the mouse (pan), or ctrl-click
and  move the mouse (zoom). Two fingered gestures work for zooming as well on a Mac
trackpad. If the mouse is located within the axes, zoom and pan work on both axes. 
If the mouse is outside of the axes, the zoom and pan operate on a single axis.

The spectrum viewer defaults to showing a statistics box to the right of the spectrum.
This can be hidden by dragging the handle (little dot on its left edge) all the way
to the right. Drag the handle back to make it reappear. The statistics box shows
common statistical quantites for the full spectrum, or for the region of interest
if one is selected.

The common workflow would be to select a region of the spectrum (using the `Add Region`
option on the specviz menu) and do some operations on it (e.g. measure line fluxes). 
Please refer to the 
`specviz <https://specviz.readthedocs.io/en/stable/>`__
documentation for descriptions of all the available
operations.

It is possible to apply some operations back to the cube, spaxel by spaxel. These
are selected using the `Cube Operations` menu item. These are as follows:

    * **Simple linemap:** Will sum the values over the wavelengths selected by the ROI and produce a 2D image available for viewing from the drop-down menus in the image viewers.
    * **Fitted linemap:** If you have fit a model to a spectrum or ROI, this will fit that same model to each spaxel, using the parameters shown in specviz as the initial guesses. 
    * **Spectral smoothing:** Will apply the same smoothing that has been applied to the 1D spectrum to each spaxel. 
