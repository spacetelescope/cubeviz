Installation
============

CubeViz is packaged in the Conda environment system and therefore requires Miniconda to be installed.  This makes it reasonably simple to install CubeViz along with all its dependencies. 

Installing Miniconda 
--------------------

Follow the Miniconda `installation instructions <https://conda.io/miniconda.html>`_ found on the Miniconda website. When asked whether miniconda should be appended to your system PATH, make sure to select yes.

Note that we have encountered issues with older versions of Miniconda, so if you already have it installed, it might be a good idea to update it.

CubeViz
-------

Once Miniconda is installed, you can install CubeViz by typing the command:

.. code-block:: console

    $ conda create -n <environment name> -c glueviz cubeviz

where the <environment name> is the name of the Conda environment you want to create for the new CubeViz installation.  For example:

.. code-block:: console

    $ conda create -n cubeviz02 -c glueviz cubeviz

Once you have created the environment, you will need to activate it with the command:

.. code-block:: console

    $ source activate <environment name>

and for the example above:

.. code-block:: console

    $ source activate cubeviz02
  
Once the Conda environment is activated you can start CubeViz with:

.. code-block:: console

    $ cubeviz
  

License
=======

This project is Copyright (c) JDADF Developers and licensed under the terms of the BSD 3-Clause license. See the licenses folder for more information.
