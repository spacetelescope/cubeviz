import sys
import traceback
import multiprocessing
from urllib.parse import urljoin

import pytest

from specviz.tests.test_load_data import (BOX_PREFIX, jwst_data_test,
                                          download_test_data,
                                          run_subprocess_test)

from cubeviz.cubeviz import create_app


JWST_DATA_FILES = [
    # det_image_ch1-short_s3d.fits
    'mhicn6ofnwpi4mzjm4yoppm95mdhmw42.fits',
    # det_image_ch1-short_s3d_ref.fits
    'k4kwyn1t5zcjw7wg4xv9ub3fgg07lwl7.fits',
    # det_image_ch2-short_s3d.fits
    'kpye05xrwcpllzlju0l96nw0lmtwom98.fits',
    # ditherunity_CLEAR_PRISM_M1_m1_noiseless_NRS1_modified_updatedHDR_fixintarget_s3d.fits
    'f3bozjgdgtv0n1fqdt002ufmf1z97qup.fits',
]

JWST_DATA_PATHS = [urljoin(BOX_PREFIX, name) for name in JWST_DATA_FILES]


def run_cubeviz_test(q, _, tmpdir, url, *args):
    app = None

    try:
        fname = download_test_data(tmpdir, url)
        app = create_app(interactive=False)
        app.load_data([fname])
        assert len(app.data_collection) == 1
        assert app.data_collection[0].label.startswith('jwst-fits-cube')
    except Exception:
        ex_type, ex_value, tb = sys.exc_info()
        error = ex_type, ex_value, ''.join(traceback.format_tb(tb))
    else:
        error = None
    finally:
        if app is not None:
            app.app.quit()

    q.put(error)


@jwst_data_test
@pytest.mark.parametrize('url', JWST_DATA_PATHS)
def test_load_jwst_data(tmpdir, url):
    multiprocessing.set_start_method('spawn', force=True)
    run_subprocess_test(None, tmpdir, url, callback=run_cubeviz_test)
