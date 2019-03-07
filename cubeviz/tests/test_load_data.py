import multiprocessing

from qtpy import QtWidgets
from specviz.tests.test_load_data import (BOX_PREFIX, jwst_data_test,
                                          run_subprocess_test)

from cubeviz.cubeviz import create_app


def run_cubeviz_test(q, *args):
    print('in callback')
    try:
        app = create_app(interactive=False)
        print('created app')
    except Exception:
        print('there was an error')
        ex_type, ex_value, tb = sys.exc_info()
        error = ex_type, ex_value, ''.join(traceback.format_tb(tb))
    else:
        error = None
    finally:
        app.app.quit()
        print('quit app')

    print('putting on the queue')
    q.put(error)
    print('done')


@jwst_data_test
def test_load_jwst_data():
    multiprocessing.set_start_method('spawn')
    run_subprocess_test(None, callback=run_cubeviz_test)
