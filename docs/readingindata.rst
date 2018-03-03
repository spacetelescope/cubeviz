***************
Reading-in Data
***************

CubeViz will be able to read in NIRSpec and MIRI IFU data straight from the pipeline or archive.  It includes data loaders for many but not all ground-based IFUs.

CubeViz uses simple _`yaml <https://learn.getgrav.org/advanced/yaml>`_ files as data loaders.  Examples are given below.  In short, the yaml file tells CubeViz which axes in the cube are RA, DEC, and wavelength, and the units used, among other things.

If you have trouble loading your data cube into CubeViz, please email _`Susan Kassin <https://www.susankassin.com/contact/>`_.  It would be helpfu a link to your data cube is provided.

+++++++++++++++++++++++++++++++++++++++++++++++++++++
Reading in an Example Data Cube
+++++++++++++++++++++++++++++++++++++++++++++++++++++

An example data cube from the _`MaNGA Survey <http://www.sdss.org/surveys/manga/>`_ can be found on the bottom of _`this website <http://skyserver.sdss.org/dr13/en/tools/explore/summary.aspx?ra=205.4384&dec=27.004754>`_.  To download the data cube, click on "LIN Data Cube" or "LOG Data Cube" to dowload a data cube with a linear or log wavelength axis, respectively.

Start up CubeViz by typing "cubeviz" on the command line, following the
installation instructions (:ref:'installation.rst').  CubeViz should start
up and you will be shown the user interface.  Next, to load the cube, click
on the "Open Data" red folder in the upper left of CubeViz, and a dialog box
should appear.  In the dialog box, select the data cube you wish to load and
select the relevant data loader using the drop down menu on the bottom.
For the MaNGA cube, select "manga (*)."  The data cube should load.

+++++++++++++++++++++++++++++++++++++++++++++++++++++
Reading in an Unsupported Data Cube
+++++++++++++++++++++++++++++++++++++++++++++++++++++

If your data cube does not automatically load with one of the
pre-existing data loaders in the "Open Data" dialog box, you can
create a yaml file to help load your cube.

An example yaml file for the MaNGA data cube above is here.
It was created as follows.

(Instructions on how to create a yaml file.)
