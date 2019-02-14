import os
import pytest
from glue.core.data_factories import load_data, find_factory
from glue.config import data_factory
from ...listener import CUBEVIZ_LAYOUT

DATA = os.path.join(os.path.dirname(__file__), 'data')


def factory_label(factory):
    # find_factory in glue just returns the factory function, so we have to
    # look at all data factories to figure out which one it is, to make sure
    # the label matches.
    for df in data_factory.members:
        if df.function is factory:
            return df.label


# IMPORTANT: do not include full resolution cubes in the data/ directory.
# Instead, downsample or replace the arrays with smaller arrays.

TEST_CASES = [('manga-7495-12704-LOGCUBE.fits', 'manga', (10, 10, 10)),
              ('SINFONI_CAS64_k_bjames.fits', 'sinfoni-cube', (10, 10, 10)),
              ('det_image_seq1_MIRIFUSHORT_12SHORTexp1_s3d.fits', 'jwst-fits-cube', (10, 10, 10))]


@pytest.mark.parametrize(('filename', 'factory_name', 'shape'), TEST_CASES)
def test_basic(filename, factory_name, shape):

    # This is a basic test to excercise the data factory infrastructure. Above
    # is a list containing (filename, factory, shape) where filename is
    # the name of a file inside the data/ directory, factory is the factory that
    # should be identified to be used for the file, and shape is the expected
    # shape of the data.

    filename = os.path.join(DATA, filename)
    factory = find_factory(filename)
    assert factory_label(factory) == factory_name
    data = load_data(filename)
    assert data.meta[CUBEVIZ_LAYOUT] == factory_name
    assert data.shape == shape
