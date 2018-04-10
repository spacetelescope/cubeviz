import os
import logging

from astropy.io import fits

logging.basicConfig(level=logging.DEBUG, format="%(filename)s: %(levelname)8s %(message)s")
log = logging.getLogger('ifcube')
log.setLevel(logging.DEBUG)


class IFUCube(object):
    """
    Check and correct the IFUCube
    """

    def __init__(self):
        self._fits = None
        self._filename = None
        self._good = True

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
                    self._fits[ii].header['EXTNAME'] = 'Extension {}'.format(ii)
                    log.info(' Setting HDU {} EXTNAME field to {}'.format(ii, self._fits[ii].header['EXTNAME']))

            if hasattr(hdu, 'data') and hdu.data is not None and len(hdu.data.shape) == 3:
                good = True
                self.good_check(good)
                extname = self._fits[ii].header['EXTNAME']

                log.info('  data exists in HDU ({}, {}) and is of shape {}'.format(
                    ii, extname, hdu.data.shape))

                # Check to see if the same size as the others
                if data_shape and not data_shape == hdu.data.shape:
                    log.warning('  Data are of different shapes (previous was {} and this is {})'.format(data_shape, hdu.data.shape))

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
        self._check_ctype(key='CUNIT3', correct='Angstrom', fix=fix)

    def _check_ctype(self, key, correct, fix=False):
        """
        Check the header key and make sure it is the correct value

        :param: fits_file: The open fits file
        :param: fix: boolean whether to fix it or not
        :return: boolean whether it is good or not
        """
        log.debug('In check for {}'.format(key))
        good = True

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
        if not hdu.header[key] == correct and fix:
            log.info("{} is {}, setting to {} in header[{}]".format(key, hdu.header[key], correct, ii))
            self.good_check(False)
            hdu.header[key] = correct
        elif not hdu.header[key] == correct and not fix:
            self.good_check(False)
            log.info("{} is {}, should equal {} in header[{}]".format(key, hdu.header[key], correct, ii))

    def get_log_output(self):
        return "Here we will have specific locations of faulty values"

    def good_check(self, good):
        if good and self._good:
            self._good = True
        if not good:
            self._good = False

    def get_good(self):
        return self._good
