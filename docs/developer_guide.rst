.. _developer_guide:

Developer Guide
===============

Testing
-------

Test Dependencies
^^^^^^^^^^^^^^^^^

The following dependencies are required for running the tests:

* `pytest <https://pytest.readthedocs.io>`_
* `pytest-astropy <https://github.com/astropy/pytest-astropy>`_

Optionally, these dependencies are required to run the tests using `tox
<https://tox.readthedocs.io>`_:

* `tox <https://tox.readthedocs.io>`_
* `tox-conda <https://github.com/tox-dev/tox-conda>`_

All of the above dependencies can be installed using `pip`.

Running the Tests
^^^^^^^^^^^^^^^^^

The test suite can be run using the following command:

.. code-block:: shell

   $ pytest

By default, the tests of the JWST data loader do not run since they require
network resources (to download the test data) and run in a subprocess. To run
those tests, use the following command:

.. code-block:: shell

   $ JWST_DATA_TEST=1 pytest cubeviz/tests/test_load_data.py

.. warning::
   When running the test suite, the ``cubeviz`` window must remain active and
   be the top window on your desktop, or else test failures will occur.

Using Tox
^^^^^^^^^

It is also possible to run the tests using `tox`. The benefit of this is that
`tox` automatically creates an isolated test environment in which the tests are
run. This means it is easy to test against various versions of dependencies,
and even against different versions of Python, without having to change
anything in your development environment.

We use `tox` to run our tests on CI servers. This means that developers can
rerun `tox` locally to reproduce the same test environments that run on CI.

The following is an example of how to run the test suite using `tox` in a
Python 3.7 environment:

.. code-block:: shell

   $ tox -e py37-test

The ``-e`` flag indicates the environment to be used. The possible environments
are defined in the ``tox.ini`` file found at the top of the package.

To run the JWST data tests using `tox`, use the following command:

.. code-block:: shell

   $ JWST_DATA_TEST=1 tox -e py37-test cubeviz/tests/test_load_data.py

Building Documentation
----------------------

The following dependencies are necessary for building the documentation:

* `sphinx <http://www.sphinx-doc.org/en/master>`_
* `sphinx-astropy <https://github.com/astropy/sphinx-astropy>`_
* `sphinx_rtd_theme <https://sphinx-rtd-theme.readthedocs.io/en/stable>`_

Each of these dependencies can be installed using `pip`.

To build the HTML documentation, first move into the ``docs`` directory, and
then run the build command:

.. code-block:: shell

   $ cd docs
   $ make html

The built documentation can be found under ``docs/_build/html``. To view the
local copy of the documentation, use a link like the following:

.. code-block:: shell

   file:///path/to/cubeviz/docs/_build/html/index.html
