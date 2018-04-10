from glue.core.message import Message


def glue_subscribe(message):
    def decorator(function):
        self = args[0]
        self._hub.subscribe(self, message, handler=function)

    return decorator


class SliceIndexUpdateMessage(Message):

    # TODO: this should also track the originating layout tab so that if we
    # support multiple CubeViz tabs, the messages from different tabs don't
    # conflict
    def __init__(self, sender, index, data_set, slider_down=False, tag=None):
        super(SliceIndexUpdateMessage, self).__init__(sender, tag=tag)
        self.index = index
        self.data_set = data_set
        self.slider_down = slider_down


class WavelengthUpdateMessage(Message):

    def __init__(self, sender, wavelengths, tag=None):
        super(WavelengthUpdateMessage, self).__init__(sender, tag=tag)
        self.wavelengths = wavelengths


class WavelengthUnitUpdateMessage(Message):

    def __init__(self, sender, units, tag=None):
        super(WavelengthUnitUpdateMessage, self).__init__(sender, tag=tag)
        self.units = units


class RedshiftUpdateMessage(Message):

    def __init__(self, sender, redshift, label='', tag=None):
        super(RedshiftUpdateMessage, self).__init__(sender, tag=tag)
        self.redshift = redshift
        self.label = label


class FluxUnitsUpdateMessage(Message):

    def __init__(self, sender, flux_units, component_id, tag=None):
        super(FluxUnitsUpdateMessage, self).__init__(sender, tag=tag)
        self.flux_units = flux_units
        self.component_id = component_id
