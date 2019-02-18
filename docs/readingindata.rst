Reading-in Data
===============

CubeViz will be able to read in NIRSpec and MIRI IFU data straight from the pipeline or archive.  It includes data loaders for many but not all ground-based IFUs.

CubeViz uses simple `yaml <https://learn.getgrav.org/advanced/yaml>`_ files to
specify the information needed to load the data files (e.g., `JWST FITS YAML
configuration file
<https://github.com/spacetelescope/cubeviz/blob/master/cubeviz/data_factories/configurations/jwst-fits.yaml>`_.
Examples are given below.  In short, the yaml file tells CubeViz which axes in
the cube are RA, DEC, and wavelength, and the units used, among other things.

If you have trouble loading your data cube into CubeViz, please either login to `Stars <https://stsci.service-now.com/stars>`_ or `create an issue <https://github.com/spacetelescope/cubeviz/issues/new>`_.  It would be helpful to include a link to your data cube is provided.

Reading in an Example Data Cube
===============================

An example data cube from the `MaNGA Survey <http://www.sdss.org/surveys/manga/>`_ can be found on the bottom of `this website <http://skyserver.sdss.org/dr13/en/tools/explore/summary.aspx?ra=205.4384&dec=27.004754>`_.  To download the data cube, click on "LIN Data Cube" or "LOG Data Cube" to dowload a data cube with a linear or log wavelength axis, respectively.

Start up CubeViz by typing "cubeviz" on the command line, following the
installation instructions (:ref:'installation.rst').  CubeViz should start
up and you will be shown the user interface.  Next, to load the cube, click
on the "Open Data" red folder in the upper left of CubeViz, and a dialog box
should appear.  In the dialog box, select the data cube you wish to load and
select the relevant data loader using the drop down menu on the bottom.
For the MaNGA cube, select "manga (*)."  The data cube should load.

Create an Data Cube
===================

CubeViz has several expectations on the format of the FITS file in order to
easily read in IFU data. At a bare minimum, the FITS file must contain an image
HDU that contains the three-dimensional science data. By convention this
extension is often named `'SCI'`.

CubeViz is able to display multiple components from a single data set. Some
files might wish to provide error and data quality information, for exaple.
If the FITS file provides these, each must be stored in a separate image HDU
These are often named `'ERR'` and `'DQ'` by convention. The data components of
these HDUs must match those of the HDU containing science data.

Each HDU header must contain several keywords with WCS information. The CTYPE1
keyword should be set to `RA---TAN`, CTYPE2 should be set to `DEC---TAN` and
CTYPE3 should be set to one of the valid spectral coordinate types
`SPECTRAL_COORD_TYPE_CODES` listed at the top of the `reader file
<https://github.com/spacetelescope/cubeviz/blob/master/cubeviz/data_factories/ifucube.py>`_.

The CUNIT1 and CUNIT2 keywords should be set to `'deg'` and CUNIT3 must be set
to a valid FITS compatible unit that represents wavelength (e.g., `m`, `um`, or
`AA`). You can check if a unit is FITS-compatible by using Astropy's Unit
class:

.. code-block:: console

   from astropy.units import Unit
   unit = Unit('m', format='fits')

This will crash for units not compatible with the FITS standard.

Reading in an Unsupported Data Cube
===================================

If your data cube does not automatically load with one of the
pre-existing data loaders in the "Open Data" dialog box, you can
create a yaml file to help load your cube.

An example yaml file for the MaNGA data cube above is here.
It was created as follows.

(Instructions on how to create a yaml file.)
