# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

def get_package_data():  # pragma: no cover
    package_name = str(_ASTROPY_PACKAGE_NAME_ + '.misc')
    return { package_name: ['update_cubeviz_test_env_pip'] }
