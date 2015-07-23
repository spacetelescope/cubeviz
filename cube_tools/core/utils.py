import numpy as np

from glue.plugins.tools.spectrum_tool import Extractor


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

        mask = np.squeeze(subset.to_mask(view))
        if slc.index('x') < slc.index('y'):
            mask = mask.T

        print(mask.shape)

        w = np.where(mask)
        view[slc.index('x')] = w[1]
        view[slc.index('y')] = w[0]

        print(view)
        print(view[0])

        # result = np.empty(x.size)

        # # treat each channel separately, to reduce memory storage
        # for i in xrange(data.shape[zaxis]):
        #     view[zaxis] = i
        #     val = data[attribute, view]
        #     result[i] = np.nansum(val) / np.isfinite(val).sum()
        #
        # y = result

        return mask