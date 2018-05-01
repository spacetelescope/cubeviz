CubeViz
--------------------------------

.. image:: http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat
    :target: http://www.astropy.org
    :alt: Powered by Astropy Badge


Release 0.2.0
-------------

We are pleased to announce the release of CubeViz, a visualization and analysis tool for data cubes from integral field units (IFUs). This is an early release (v0.2.0) and we would appreciate your feedback.  It is built on top of the “glue” visualization tool.

Read the Docs: http://cubeviz.readthedocs.io/en/latest/
More info on glue: http://glueviz.org

If you run into any issues or have suggestions for new features, we encourage you to create issues on GitHub or send comments via email: kassin@stsci.edu

This release requires Python 3.5 or 3.6.

Installation
------------

Cubeviz is packaged in the conda environment system and therefore requires Miniconda to be installed.  This makes it reasonably simple to install cubeviz along with all the dependencies. 

Miniconda 
^^^^^^^^^

Follow the Miniconda `installation instructions <https://conda.io/miniconda.html>`_ found on the Miniconda website. When asked whether miniconda should be appended to your system PATH, make sure to select yes.

Note that we have encountered issues with older versions of miniconda, so if you already have it installed, it might be a good idea to update.

Cubeviz
^^^^^^^

Once Miniconda is installed you can install cubeviz by typing the command:

.. code-block:: sh

  $ conda create -n <environment name> -c glueviz cubeviz

where the <environment name> is the name of the Conda environment you want to create for the new cubeviz installation.  For example:

.. code-block:: sh

  $ conda create -n cubeviz02 -c glueviz cubeviz

Then once you have created the environment, you will need to activate it by doing:

.. code-block:: sh

  $ source activate <environment name>

and for the example above:

.. code-block:: sh

  $ source activate cubeviz02
  
Then once the conda environment is activated you can start cubeviz with:

.. code-block:: sh

  $ cubeviz
  

License
-------

This project is Copyright (c) JDADF Developers and licensed under the terms of the BSD 3-Clause license. See the licenses folder for more information.
