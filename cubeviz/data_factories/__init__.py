# Licensed under a 3-clause BSD style license - see LICENSE.rst
from .jwst import read_jwst_data_cube
from .kmos import read_kmos_data_cube
from .manga import read_manga_data_cube

import yaml
import os
import glob
from astropy.io import fits
import pprint

class InstrumentFactoryConfiguration:

    def __init__(self, config_files_or_directory):
        """
        The IFC takes either a directory (that contains YAML files), a list of directories (each of which contain
        YAML files) or a list of YAML files.  Each YAML file defines requirements

        :param config_files_or_directory: Directory, list of directories, or list of files.
        """

        if os.path.isdir(config_files_or_directory):
            # Get all the yaml files in the directory
            self._config_files = glob.glob(os.path.join(config_files_or_directory, '*.yaml'))
        else:
            self._config_files = config_files_or_directory

            if not isinstance(self._config_files, list):
                self._config_files = [self._config_files]


    def process(self, filename):
        """
        Main call to which we pass in the file to see if it matches based
        on the criteria in the config file.

        :param filename:
        :return:
        """
        self._fits = fits.open(filename)

        config_weightings = {}
        for config_file in self._config_files:
            print('Checking {}'.format(config_file))

            with open(config_file, 'r') as ymlfile:
                cfg = yaml.load(ymlfile)

                name = cfg['name']
                type = cfg['type']
                weight = cfg.get('weight', 0)
                configuration = cfg['match']

                # Now call the internal processing.
                matches = self._process('all', configuration['all'])

                if matches:
                    print('File matches')
                    config_weightings[name] = weight
                else:
                    print('File does not match')
                    config_weightings[name] = 0

        pprint.pprint(config_weightings)

    def _process(self, key, conditional):
        """
        Internal processing. This will get called numerous times recursively.

        :param key: The type of check we want to do
        :param conditional: The thing we are checking
        :return:
        """

        if 'all' == key:
            return self._all(conditional)
        elif 'any' == key:
            return self._any(conditional)
        elif 'equal' == key:
            return self._equal(conditional)
        elif 'startswith' == key:
            return self._startswith(conditional)
        elif 'extension_name' == key:
            return self._exists(conditional)

    #
    # Branch processing
    #

    def _all(self, conditionals):
        """
        Check all the conditionals and they must all be true for this to return true.

        :param conditionals:
        :return:
        """
        for key, conditional in conditionals.items():
            print('Checking {}'.format(key))
            ret = self._process(key, conditional)
            print('    returned {}'.format(ret))
            if not ret:
                return False
        print('_all: GOOD')
        return True

    def _any(self, conditionals):
        """
        Check each conditional and return true for the first one that matches true. Else return False

        :param conditionals:
        :return:
        """

        for key, conditional in conditionals.items():
            # process conditional
            ret = self._process(key, conditional)
            if ret:
                return ret

        return False

    #
    # Leaf processing
    #

    def _equal(self, value):
        """
        This is to check if a header_key entry has the same value as what is passed in here.

        :param value:
        :return:
        """
        return self._fits[0].header.get(value['header_key'], False) == value['value']


    def _startswith(self, value):
        """
        This is to check if a header_key entry starts with the value as what is passed in here.

        :param value:
        :return:
        """
        return self._fits[0].header.get(value['header_key'], '').startswith(value['value'])

    def _extension_name(self, value):
        """
        This is to check if a header_key entry has the same value as what is passed in here.

        :param value:
        :return:
        """
        return value in self._fits

if __name__ == "__main__":
    #iml = InstrumentFactoryConfiguration('configs/kmos.yaml')
    iml = InstrumentFactoryConfiguration('configs/')
    iml.process('/astro/3/jwst_da_sprint_testdata/IFU_datacubes/KMOS_Mason/KLASS_KMOS_COMBINE_SCI_RECONSTRUCTED_S2A_1261.fits')
