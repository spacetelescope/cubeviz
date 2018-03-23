from glue.core.message import Message


class SliceIndexUpdateMessage(Message):

    def __init__(self, sender, index, data_set, slider_down=False, tag=None):
        super(SliceIndexUpdateMessage, self).__init__(sender, tag=tag)
        self.index = index
        self.data_set = data_set
        self.slider_down = slider_down
        print("SliceIndexUpdateMessage, index=", index)
