from glue.core.client import Client


class SpectraClient(Client):
    def __init__(self, data=None):
        pass

    def unregister(self, hub):
        super(SpectraClient, self).unregister(hub)

    def notify(self, message):
        pass

    def _remove_data(self, message):
        pass

    def _update_data(self, message):
        pass

    def _update_subset(self, message):
        pass

    def register_to_hub(self, hub):
        super(SpectraClient, self).register_to_hub(hub)

    def data(self):
        return super(SpectraClient, self).data()

    def add_data(self, data):
        pass

    def _add_subset(self, message):
        pass

    def _numerical_data_changed(self, message):
        pass

    def apply_roi(self, roi):
        pass

    def _remove_subset(self, message):
        pass
