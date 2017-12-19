# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os

import pytest

from glue.app.qt import GlueApplication


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


@pytest.fixture(scope='module')
def cubeviz_layout():
    filename = os.path.join(TEST_DATA_PATH, 'data_cube.fits.gz')

    app = GlueApplication()
    app.run_startup_action('cubeviz')
    app.load_data(filename)

    return app.tab(0)


def test_starting_state(cubeviz_layout):

    assert cubeviz_layout._active_view is cubeviz_layout.left_view
