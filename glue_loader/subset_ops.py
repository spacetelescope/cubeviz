"""Definte cube subset operations"""
import numpy as np

from glue.config import single_subset_action
from glue.core import Data

def collapse_to_1d(subset, data_collection):
    mask = subset.to_mask()
    md = np.ma.masked_array(subset.data['FLUX'], mask=mask)
    mdd = md.reshape((-1, md.shape[1] * md.shape[2]))
    spec = np.sum(mdd, axis=1)
    spec_data = Data(flux=spec, label=':'.join((subset.label,
                                                subset.data.label,
                                                'collapsed')))
    wave_component = subset.data['Wave'][:, md.shape[1] / 2, md.shape[2] / 2]
    spec_data.add_component(component=wave_component, label='Wave')
    spec_data.add_component(component=spec, label='FLUX')
    data_collection.append(spec_data)


# Register operations
single_subset_action('Collapse to 1D', collapse_to_1d)
