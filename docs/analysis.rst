.. DANGER:: 

      Please note that this version of CubeViz is **no longer being actively supported
      or maintained**. The functionality of CubeViz is now available and being actively
      developed as part of `Jdaviz <https://github.com/spacetelescope/jdaviz>`_.

Analysis Tasks
==============

This section walks through a few basic analysis tasks.

Collapsing cubes over selected wavelength regions
-------------------------------------------------

There are a variety of ways to turn a 3D cube or portion thereof into a 2D image.
Most are accessed from the data-processing menu at the upper right. There
are also options for making linemaps in the specviz window at the bottom.

Continuum Subtraction
---------------------
There is a very basic continuum fitting option under `Operations` 
in the specviz window labeled as `Generate continuum model`.

It is often preferable to tailor your continuum to a specific region
of interest in building up a model of the spectrum. 
You can do this by accessing `New Model` from the specviz menu or from the
`Models` tab at the far right. Using the `+` sign at the bottom of
the menu, you can select different components for your fit (e.g. 
linear or polynomial). 

To apply this continuum fit spaxel by spaxel, select 
`Fit Spaxels` option from the `Cube Operations` menu. This will use
the parameters of the specviz result as the initial guess for fitting
each individual spaxel. The result will be a new 3D cube, where the 
spectrum in each spaxel is the model fit. This can then be subtracted
from the cube using the `Data Processing -> Arithmetic Operations` sub-menu
at the top right.

Measuring Emission lines
------------------------

Having subtracted continuum, 
you can get some useful statistics by selecting the `Continuum Subtracted`
option in the Statistics tab at the far right. The values there refer to the
portion of the spectrum under the selected ROI.

To measure the equivalent width, you should normalize by the continuum
rather than subtract. Having done that, you can select the `Continuum Normalized` option
in the Statistics tab and see the equivalent width at the bottom.

Fitting Spectral Lines
----------------------

You fit an analytical model to a region of a spectrum by selecting
a region of interest from the specviz top menu and then accessing
`New Model` from the specviz menu or from the
`Models` tab at the far right. Using the `+` sign at the bottom of
the menu, you can select different components for your fit (e.g. 
linear or polynomial). The initial guess will be plotted on the 
screen. If it is not reasonably close, it is best to adjust the parameters
by hand from the right-hand menu. See the 
`specviz <https://specviz.readthedocs.io/en/stable/>`__
documentation for more information on fitting and saving models.

Simple Line Maps 
----------------

A simple line map is just a sum over the spectral pixels selected by the specviz
ROI, for every spaxel in the cube. This allows you to isolate the wavelength region
of interest, but doesn't do anything more than that (i.e. it doesn't subtract
continuum). You can create a simple line map from the `Cube Operations` menu. 

Fitted Line Maps 
----------------

A fitted line map will apply a model to every spaxel in the image. 
Select the region of interest in specviz and then select your model 
components (e.g. Gaussian plus Linear) using the `+` icon in the modeling
tab. Fit it to get a good first guess for fitting every spaxel. Then
select fitted line map from the `Cube Operations` menu. This will fit the
model to every spaxel and then sum *the model* within the ROI.

It's important to note that this is not a continuum-subtracted line map
unless you have already subtracted continuum.  To subtract continuum, 
you should fit two separate models, one for line
and one for continuum using the `Fit Spaxels` option from the `Cube Operations`
menu. Then use cube arithmetic to subtract one from the other
from the `Data Processing -> Arithmetic Operations` sub-menu at the upper
right above the image windows. Then use `Data Processing -> Collapse Cube` 
to sum this residual cube along the spectral dimension.

Creating Moment Maps
--------------------

To create moment maps, select select `Data Processing -> Moment Maps`
menu from the upper right, above the image viewers. This uses the
`spectral-cube <https://spectral-cube.readthedocs.io/en/stable/>`__
library under the hood. The formulae for the moments are given there.

Mock long-slit Observations
---------------------------

To replicate a long-slit observation, typically one would want to place a rectangular
selection window of a specified size at a certain positional angle over the data
cube.  Cubeviz does not currently the ability to rotate the cube or rectangular selection
box to an arbitrary angle.
dimensions. 
