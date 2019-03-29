# CubeViz

![](http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat)
[![Coverage Status](https://codecov.io/gh/spacetelescope/cubeviz/branch/master/graph/badge.svg)](https://codecov.io/gh/spacetelescope/cubeviz)
[![DOI](https://zenodo.org/badge/36305330.svg)](https://zenodo.org/badge/latestdoi/36305330)

For documentation see http://cubeviz.readthedocs.io/en/latest/

## Release 0.3

We are pleased to announce the release of CubeViz, a visualization and analysis tool for data cubes from integral field units (IFUs). This is an early release (v0.3) and we would appreciate your feedback.  It is built on top of the "glue" visualization tool.

To install:
  * Install [Minconda3](https://conda.io/miniconda.html) if it is not on your system (**)
  * To install, type: `$ conda create -n cubeviz030 python=3.6`, activate the environment `$ conda activate cubeviz030` and pip install cubeviz `$ pip install cubeviz`.

To run:
  * Activate the environment: `$ source activate cubeviz030`
  * Run cubeviz: `$ cubeviz`
  * Once done, deactivate the environment: `source deactivate`

More installation instructions will be on the RTD page (currently incorrectly displaying the wrong docs and appears to be an RTD bug).

Read the Docs: http://cubeviz.readthedocs.io/en/latest/

More info on glue: http://glueviz.org

If you run into any issues or have suggestions for new features, we encourage you to create issues on GitHub.

This release requires Python 3.6.

** Note: There have been some issues with Miniconda3 with conda version less than 4.5.  If you see any problems with installation or running cubeviz and your conda version is less than 4.5 it is best to update to 4.5.  See [upgrade instructions](https://conda.io/miniconda.html) for more information.

![](/docs/images/CubeViz_splitviewer.png)


# License

This project is Copyright (c) JDADF Developers and licensed under the terms of the BSD 3-Clause license. See the licenses folder for more information.
