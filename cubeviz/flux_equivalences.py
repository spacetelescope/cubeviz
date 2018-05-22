from astropy import units as u
from astropy.units.quantity import Quantity


class CustomFluxEquivalences:
    """
    This class is intended to behave as a function.
    It will replace astropy.units.equivalencies.spectral_density.
    It saves the original spectral_destiny function and adds
    flux units that are over pixels or arcsec**2. The class also
    stores pixel_area information that is used to convert b/w the
    pixels and arcsec**2.
    """
    def __init__(self, spectral_density):
        self.pixel_area = None
        self.default_spectral_density = spectral_density
        self.suppress_pixel_area = False

    def __call__(self, wave, factor=None):
        if self.suppress_pixel_area:
            pixel_area = None
        else:
            pixel_area = self.pixel_area
        if pixel_area is not None:
            if type(pixel_area) == Quantity:
                pixel_area = pixel_area.to("arcsec2 / pix").value  # Convert to Quantity
        default_spectral_density = self.default_spectral_density(wave, factor)

        # equivalencies = [[unit1, unit2, function_1_to_2, function_2_to_1]...]
        equivalencies = default_spectral_density[:]

        added_area_units = []
        for u1, u2, f1, f2 in default_spectral_density:
            """
            In this for loop, go through all the
            equivalency relationships and divide them with
            pixel and arcsec**2. Then construct functions
            that convert b/w all the pixel units only and
            the area units only. Then, if pixel_area is provided
            make functions that convert b/w the pixel units
            and area units. Note there should not be a function
            to convert b/w the original units and the (pixel
            and area) units.
            """
            u1_pix = u1 / u.pix
            u2_pix = u2 / u.pix

            u1_area = u1 / (u.arcsec ** 2)
            u2_area = u2 / (u.arcsec ** 2)

            equivalencies.append((u1_pix, u2_pix, f1, f2))
            equivalencies.append((u1_area, u2_area, f1, f2))

            if pixel_area is not None:
                equivalencies.append((u1_pix,
                                      u2_area,
                                      lambda x: f1(x) / pixel_area,
                                      lambda x: f2(x) * pixel_area))
                equivalencies.append((u1_area,
                                      u2_pix,
                                      lambda x: f1(x) * pixel_area,
                                      lambda x: f2(x) / pixel_area))
                if u1_area not in added_area_units:
                    equivalencies.append((u1_area,
                                          u1_pix,
                                          lambda x: x * pixel_area,
                                          lambda x: x / pixel_area))
                    added_area_units.append(u1_area)

                if u2_area not in added_area_units:
                    equivalencies.append((u2_area,
                                          u2_pix,
                                          lambda x: x * pixel_area,
                                          lambda x: x / pixel_area))
                    added_area_units.append(u2_area)

        return equivalencies

    def get_basic_relations(self, wave, factor=None):
        """
        Returns an equivalency list that does not include
        relationships b/w pixels and solid angles. This
        is useful when using equivalencies to compare if
        a unit is of flux vs flux/pixel vs flux/sold_angle
        """
        self.suppress_pixel_area = True
        equivalencies = self.__call__(wave, factor)
        self.suppress_pixel_area = False
        return equivalencies
