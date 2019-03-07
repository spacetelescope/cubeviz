import sys
import traceback
import multiprocessing
from urllib.parse import urljoin

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
]

JWST_DATA_PATHS = [urljoin(BOX_PREFIX, name) for name in JWST_DATA_FILES]


def run_cubeviz_test(q, _, tmpdir, *args):
    print('in callback')
    app = None

    try:
        fname = download_test_data(tmpdir, JWST_DATA_PATHS[0])
        app = create_app(interactive=False)
        print('created app')
        app.load_data([fname])
        print('loaded data')
    except Exception:
        print('there was an error')
        ex_type, ex_value, tb = sys.exc_info()
        error = ex_type, ex_value, ''.join(traceback.format_tb(tb))
    else:
        error = None
    finally:
        if app is not None:
            app.app.quit()
            print('quit app')

    print('putting on the queue')
    q.put(error)
    print('done')


@jwst_data_test
def test_load_jwst_data(tmpdir):
    multiprocessing.set_start_method('spawn')
    run_subprocess_test(None, tmpdir, callback=run_cubeviz_test)
