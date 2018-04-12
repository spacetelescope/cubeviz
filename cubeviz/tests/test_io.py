import os

from glue.core.data_factories import find_factory

from ..data_factories import DataFactoryConfiguration, cubeviz_fits_exporter

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'data_cube.fits.gz')


def test_export_roundtrip(tmpdir):

    # TODO: generalize this to all example data files once we
    # have more than one format in the data directory.

    DataFactoryConfiguration(check_ifu_valid=False)

    # Make sure the right factory was identified
    factory = find_factory(TEST_DATA_PATH)
    assert factory.__self__.name == 'kmos'

    # Load in the data
    data = factory(TEST_DATA_PATH)

    # Generate temporary output filename
    filename = tmpdir.join('test.fits').strpath

    # Export the data
    cubeviz_fits_exporter(filename, data)

    # And check that we identify the file correctly again
    factory = find_factory(filename)
    assert factory.__self__.name == 'kmos'
