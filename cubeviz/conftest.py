# This file is used to configure the behavior of pytest when using the Astropy
# test infrastructure.

import sys

from astropy.version import version as astropy_version
if astropy_version < '3.0':
    # With older versions of Astropy, we actually need to import the pytest
    # plugins themselves in order to make them discoverable by pytest.
    from astropy.tests.pytest_plugins import *
else:
    # As of Astropy 3.0, the pytest plugins provided by Astropy are
    # automatically made available when Astropy is installed. This means it's
    # not necessary to import them here, but we still need to import global
    # variables that are used for configuration.
    from astropy.tests.plugins.display import PYTEST_HEADER_MODULES, TESTED_VERSIONS

from astropy.tests.helper import enable_deprecations_as_exceptions

## Uncomment the following line to treat all DeprecationWarnings as
## exceptions. For Astropy v2.0 or later, there are 2 additional keywords,
## as follow (although default should work for most cases).
## To ignore some packages that produce deprecation warnings on import
## (in addition to 'compiler', 'scipy', 'pygments', 'ipykernel', and
## 'setuptools'), add:
##     modules_to_ignore_on_import=['module_1', 'module_2']
## To ignore some specific deprecation warning messages for Python version
## MAJOR.MINOR or later, add:
##     warnings_to_ignore_by_pyver={(MAJOR, MINOR): ['Message to ignore']}
# enable_deprecations_as_exceptions()

## Uncomment and customize the following lines to add/remove entries from
## the list of packages for which version numbers are displayed when running
## the tests. Making it pass for KeyError is essential in some cases when
## the package uses other astropy affiliated packages.
try:
    PYTEST_HEADER_MODULES['Astropy'] = 'astropy'
    PYTEST_HEADER_MODULES['Glue'] = 'glue'
    PYTEST_HEADER_MODULES['Asdf'] = 'asdf'
    PYTEST_HEADER_MODULES['QtPy'] = 'qtpy'
    PYTEST_HEADER_MODULES['SpecViz'] = 'specviz'
except (NameError, KeyError):  # NameError is needed to support Astropy < 1.0
    pass

## Uncomment the following lines to display the version number of the
## package rather than the version number of Astropy in the top line when
## running the tests.
import os

# This is to figure out the package version, rather than
# using Astropy's
try:
    from .version import version
except ImportError:
    version = 'dev'

try:
    packagename = os.path.basename(os.path.dirname(__file__))
    TESTED_VERSIONS[packagename] = version
except NameError:   # Needed to support Astropy <= 1.0.0
    pass


import pytest
from .tests.helpers import (toggle_viewer, select_viewer, create_glue_app,
                            reset_app_state)

@pytest.fixture(scope='session')
def cubeviz_layout():
    app = create_glue_app()
    layout = app.tab(0)

    # Cheap workaround for Windows test environment
    if sys.platform.startswith('win'):
        layout._cubeviz_toolbar._toggle_sidebar()

    return app.tab(0)

@pytest.fixture(autouse=True)
def reset_state(qtbot, cubeviz_layout):
    # This yields the test itself
    yield

    # Make sure to return the application to this state between tests
    reset_app_state(qtbot, cubeviz_layout)
