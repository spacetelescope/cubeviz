CubeViz: Visualization & Analysis Tool for Data Cubes from Integral Field Units (IFUs)
======================================================================================

CubeViz is an visualization and analysis toolbox for data cubes from _`integral field units (IFUs) <https://jwst-docs.stsci.edu/display/JPP/Introduction+to+IFU+Spectroscopy>`_.  It is built as part of the `glue visualiztion tool <http://glueviz.org>`.  CubeViz is designed to work with data cubes from the _`NIRSpec <https://jwst-docs.stsci.edu/display/JTI/NIRSpec+IFU+Spectroscopy>`_ and _`MIRI <https://jwst-docs.stsci.edu/display/JTI/MIRI+Medium-Resolution+Spectroscopy>`_ instruments on _`JWST <https://jwst-docs.stsci.edu/display/HOM/JWST+User+Documentation+Home>`_, and will work with data cubes from any IFU.  It uses the _`specutils <https://specutils.readthedocs.io/en/latest/>`_ package from _`Astropy <http://www.astropy.org>`_.

The core functionality of CubeViz currently includes the ability to:

* view the wavelength slices (RA, DEC) in a data cube,

* view flux, error, and data quality slices simultaneously,

* view spectra from selected spatial (RA, DEC) regions,

* smooth cubes spactially (RA, DEC) and spectrally (wavelength), and

* create and display contour maps.

Future functionality will include the ability to:

* collapse cubes over selected wavelength regions,

* fit spectral lines,

* create moment maps,

* create kinematic maps (rotation velocity and velocity dispersion),

* create RGB images from regions collapsed in wavelength space (i.e., linemaps),

* perform continuum subtraction,  
  
* overlay spectral line lists,

* save edited cubes,

* create publication quality figures,

* output astropy commands,

* match spatial resolution among selected data cubes,

* bin data into constant signal-to-noise regions,

* mock slit observations

* accurate spectro-photometry

Reference/API
=============

.. toctree::
   :maxdepth: 2

   installation
   functionality
   readingindata
