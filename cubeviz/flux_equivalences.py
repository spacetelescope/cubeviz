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

    def __call__(self, wave, factor=None):
        pixel_area = self.pixel_area
        if pixel_area is not None:
            if type(pixel_area) == Quantity:
                pixel_area = pixel_area.to("arcsec2 / pix").value  # Convert to Quantity
        default_spectral_density = self.default_spectral_density(wave, factor=None)
        equivalencies = default_spectral_density[:]
        added_area_units = []
        for u1, u2, f1, f2 in default_spectral_density:
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
