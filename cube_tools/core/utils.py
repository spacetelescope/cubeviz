import numpy as np

from glue.plugins.tools.spectrum_tool import Extractor
import time
from glue.core import message as msg


class MaskExtractor(Extractor):
    def __init__(self, *args, **kwargs):
        super(MaskExtractor, self).__init__(*args, **kwargs)

    @staticmethod
    def subset_mask(subset, attribute, slc, zaxis):
        """
        Extract a mask from a subset.
        """
        data = subset.data
        # x = Extractor.abcissa(data, zaxis)

        view = [slice(s, s + 1)
                if s not in ['x', 'y'] else slice(None)
                for s in slc]

        t1 = time.time()
        full_mask = subset.to_mask(view)
        print("Mask time: {}".format(time.time() - t1))
        t1 = time.time()
        full_mask = np.tile(full_mask, (data.shape[0], 1, 1))
        print("Full mask time: {}".format(time.time() - t1))

        return full_mask


class SubsetParsedMessage(msg.Message):
    def __init__(self, sender, tag=None):
        super(SubsetParsedMessage, self).__init__(sender, tag)