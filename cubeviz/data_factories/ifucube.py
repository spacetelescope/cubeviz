import os
import logging
from collections import defaultdict

from astropy.io import fits
from astropy import units as u

logging.basicConfig(level=logging.DEBUG, format="%(filename)s: %(levelname)8s %(message)s")
log = logging.getLogger('ifcube')
log.setLevel(logging.WARNING)


class IFUCube(object):
    """
    Check and correct the IFUCube
    """

    def __init__(self):
        self._fits = None
        self._filename = None
        self._good = True
        self._log_text = defaultdict(lambda: dict())

        self._units = [u.m, u.cm, u.mm, u.um, u.nm, u.AA]
        self._units_titles = list(x.name for x in self._units)

    def open(self, filename, fix=False):
        """
        Check all checkers
        """
        self._filename = filename

        log.debug('In check with filename {} and fix {}'.format(filename, fix))

        # Check existence of the file
        if not os.path.isfile(filename):
            log.warning('File {} does not exist'.format(filename))
            return
        else:
            log.info('File {} exists'.format(filename))

        # Open the file
        try:
            self._fits = fits.open(filename)
        except:
            log.warning('Could not open {} '.format(filename))
            return

        self.check(fix)

        return self._fits

    def check(self, fix=False):
        """
        Check all checkers
        """
        log.debug('In check with filename {} and fix {}'.format(self._filename, fix))
        self._log_text['>front'] = 'Checking filename {}\n'.format(self._filename)

        self.check_data(fix)

        self.check_ctype1(fix)

        self.check_ctype2(fix)

        self.check_ctype3(fix)

        self.check_cunit1(fix)

        self.check_cunit2(fix)

        self.check_cunit3(fix)

        return self._fits

    def check_data(self, fix=False):
        """
        Check CTYPE and make sure it is the correct value

        :param: fits_file: The open fits file
        :param: fix: boolean whether to fix it or not
        :return: boolean whether it is good or not
        """
        log.debug('In check_data')
        good = False
        data_shape = []

        for ii, hdu in enumerate(self._fits):

            # Check the EXTNAME field for this HDU
            if not 'EXTNAME' in hdu.header:
                log.warning(' HDU {} has no EXTNAME field'.format(ii))

                if fix:
                    self._fits[ii].header['EXTNAME'] = '{}_{}'.format(self._filename, ii)
                    log.info(' Setting HDU {} EXTNAME field to {}'.format(ii, self._fits[ii].header['EXTNAME']))
                    self._log_text[hdu.name]['data'] = 'Setting HDU {} EXTNAME field to {}\n'.format(ii, self._fits[ii].header['EXTNAME'])

            if hasattr(hdu, 'data') and hdu.data is not None and len(hdu.data.shape) == 3:
                good = True
                self.good_check(good)
                extname = self._fits[ii].header['EXTNAME']

                log.info('  data exists in HDU ({}, {}) and is of shape {}'.format(
                    ii, extname, hdu.data.shape))

                # Check to see if the same size as the others
                if data_shape and not data_shape == hdu.data.shape:
                    log.warning('  Data are of different shapes (previous was {} and this is {})'.format(data_shape,
                                                                                                         hdu.data.shape))

                data_shape = hdu.data.shape

        if not good:
            self.good_check(False)
            log.error('  Can\'t fix lack of data')
            return False

        return good

    def check_ctype1(self, fix=False):
        self._check_ctype(key='CTYPE1', correct='RA---TAN', fix=fix)

    def check_ctype2(self, fix=False):
        self._check_ctype(key='CTYPE2', correct='DEC--TAN', fix=fix)

    def check_ctype3(self, fix=False):
        self._check_ctype(key='CTYPE3', correct='WAVE', fix=fix)

    def check_cunit1(self, fix=False):
        self._check_ctype(key='CUNIT1', correct='deg', fix=fix)

    def check_cunit2(self, fix=False):
        self._check_ctype(key='CUNIT2', correct='deg', fix=fix)

    def check_cunit3(self, fix=False):
        self._check_ctype(key='CUNIT3', correct=self._units_titles, fix=fix)

    def _check_ctype(self, key, correct, fix=False):
        """
        Check the header key and make sure it is the correct value

        :param: fits_file: The open fits file
        :param: fix: boolean whether to fix it or not
        :return: boolean whether it is good or not
        """
        log.debug('In check for {}'.format(key))

        for ii, hdu in enumerate(self._fits):
            if ii == 0 or (hasattr(hdu, 'data') and hdu.data is not None and len(hdu.data.shape) == 3):
                if key not in hdu.header:
                    hdu.header[key] = "NONE"
                    self.good_and_fix(hdu, key, correct, fix, ii)
                else:
                    self.good_and_fix(hdu, key, correct, fix, ii)

    def good_and_fix(self, hdu, key, correct, fix, ii):
        """
        Does as the name implies, checks to see if the hdu.header[key] equals the correct value, if it does not
        and fix is True, the correct value is inserted and passed back to CubeViz
        :param hdu: One of the headers from the original FITS file
        :param key: The header keyword to be checked
        :param correct: The correct value of the header keyword
        :param fix: Whether or not to fix the header to the correct value
        :param ii: The index of the hdu within the FITS file
        :return:
        """
        # (i.e. Angstroms instead of Angstrom will be corrected and added)
        if hdu.header[key] not in correct and len(hdu.header[key]) > 0 and hdu.header[key][:-1] in correct:
            self.good_check(False)
            self._log_text[hdu.name][key] = "{} is {}, setting to {}\n".format(key, hdu.header[key], hdu.header[key][:-1])
            log.info("{} is {}, setting to {} in header[{}]".format(key, hdu.header[key], hdu.header[key][:-1], ii))
            hdu.header[key] = hdu.header[key][:-1]

        elif not hdu.header[key] in correct and fix:
            self.good_check(False)
            if isinstance(correct, list):
                self._log_text[hdu.name][key] = "{} is {}, setting to {}\n".format(key, hdu.header[key], correct[0])
                log.info("{} is {}, setting to {} in header[{}]".format(key, hdu.header[key], correct[0], ii))
                hdu.header[key] = correct[0]
            else:
                self._log_text[hdu.name][key] = "{} is {}, setting to {}\n".format(key, hdu.header[key], correct)
                log.info("{} is {}, setting to {} in header[{}]".format(key, hdu.header[key], correct, ii))
                hdu.header[key] = correct

        elif not hdu.header[key] in correct and not fix:
            self.good_check(False)
            log.info("{} is {}, should equal {} in header[{}]".format(key, hdu.header[key], correct[0], ii))
            self._log_text[hdu.name][key] = "{} is {}, should equal {}".format(key, hdu.header[key], correct[0])

    def get_log_output(self):

        output = self._log_text['>front'] + '\n'

        for log_key, log_value in sorted(self._log_text.items()):
            if log_key == '>front':
                continue

            output += 'HDU {}\n'.format(log_key)

            if isinstance(log_value, str):
                output += '    {}'.format(log_value)
                continue

            for _, log_line in sorted(log_value.items()):
                output += '    {}'.format(log_line)

            output += '\n'

        return output

    def good_check(self, good):
        if good and self._good:
            self._good = True
        if not good:
            self._good = False

    def get_good(self):
        return self._good
