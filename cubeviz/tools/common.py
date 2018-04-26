from __future__ import absolute_import, division, print_function

from qtpy.QtWidgets import QMessageBox

from glue.core import Data
from glue.core.link_helpers import LinkSame
from glue.core.coordinates import WCSCoordinates


def add_to_2d_container(cubeviz_layout, data, component_data, label):
    """
    Given the cubeviz layout, a data object, a new 2D layer and a label, add
    the 2D layer to the data object and update the cubeviz layout accordingly.
    This creates the 2D container dataset if needed.
    """

    # If the 2D container doesn't exist, we create it here. This container is
    # basically just a Data object but we keep it in an attribute
    # ``container_2d`` on its parent dataset.
    if getattr(data, 'container_2d', None) is None:

        # For now, we assume that the 2D maps are always computed along the
        # spectral axis, so that the resulting WCS is always celestial
        coords = WCSCoordinates(wcs=data.coords.wcs.celestial)
        data.container_2d = Data(label=data.label + " [2d]", coords=coords)

        data.container_2d.add_component(component_data, label)

        cubeviz_layout.session.data_collection.append(data.container_2d)

        # NOTE: the following is disabled for now but can be uncommented once
        # we are ready to use the glue overlay infrastructure.
        # Set up pixel links so that selections in the image plane propagate
        # between 1D and 2D views. Again this assumes as above that the
        # moments are computed along the spectral axis
        # link1 = LinkSame(data.pixel_component_ids[2],
        #                  data.container_2d.pixel_component_ids[1])
        # link2 = LinkSame(data.pixel_component_ids[1],
        #                  data.container_2d.pixel_component_ids[0])
        # cubeviz_layout.session.data_collection.add_link(link1)
        # cubeviz_layout.session.data_collection.add_link(link2)

        for helper in cubeviz_layout._viewer_combo_helpers:
            helper.append_data(data.container_2d)

        for viewer in cubeviz_layout.cube_views:
            viewer._widget.add_data(data.container_2d)

    else:
        # Make sure we don't add duplicate data components
        if label in data.container_2d.component_ids():
            raise ValueError("Data component with label '{}' already exists, "
                             "and cannot be created again".format(label))

        data.container_2d.add_component(component_data, label)

def show_error_message(message, title, parent=None):

    box = QMessageBox(parent=parent)
    box.setIcon(QMessageBox.Warning)
    box.setText(message)
    box.setWindowTitle(title)
    box.setStandardButtons(QMessageBox.Ok)
    box.exec_()
