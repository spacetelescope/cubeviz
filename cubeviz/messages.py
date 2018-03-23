from glue.core.message import Message


def glue_subscribe(message):
    def decorator(function):
        self = args[0]
        self._hub.subscribe(self, message, handler=function)

    return decorator


class SliceIndexUpdateMessage(Message):

    def __init__(self, sender, index, data_set, slider_down=False, tag=None):
        super(SliceIndexUpdateMessage, self).__init__(sender, tag=tag)
        self.index = index
        self.data_set = data_set
        self.slider_down = slider_down
