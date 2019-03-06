import numpy as np
from specutils import SpectralRegion, Spectrum1D
from specutils.analysis import centroid, equivalent_width, fwhm, line_flux
from specutils.manipulation import extract_region


def test_stat_box_full_spectrum(cubeviz_layout):
    # Pull out stats dictionary
    stats_dict = cubeviz_layout.specviz._widget.current_workspace._plugin_bars["Statistics"].stats

    # Generate truth comparisons
    spectrum = cubeviz_layout.specviz._widget.hub.plot_item._data_item.spectrum
    truth_dict = {'mean': spectrum.flux.mean(),
                  'median': np.median(spectrum.flux),
                  'stddev': spectrum.flux.std(),
                  'centroid': centroid(spectrum, region=None),
                  'snr': "N/A",
                  'fwhm': fwhm(spectrum),
                  'ew': equivalent_width(spectrum),
                  'total': line_flux(spectrum),
                  'maxval': spectrum.flux.max(),
                  'minval': spectrum.flux.min()}

    # Compare
    assert stats_dict == truth_dict

def test_stat_box_roi_spectrum(cubeviz_layout):
    cubeviz_layout.specviz._widget.current_workspace.current_plot_window.plot_widget._on_add_linear_region()

    spectrum = extract_region(cubeviz_layout.specviz._widget.hub.plot_item._data_item.spectrum,
                              SpectralRegion(*cubeviz_layout.specviz._widget.hub.selected_region_bounds))

    # Pull out stats dictionary
    stats_dict = cubeviz_layout.specviz._widget.current_workspace._plugin_bars["Statistics"].stats

    # Generate truth comparisons
    truth_dict = {'mean': spectrum.flux.mean(),
                  'median': np.median(spectrum.flux),
                  'stddev': spectrum.flux.std(),
                  'centroid': centroid(spectrum, region=None),
                  'snr': "N/A",
                  'fwhm': fwhm(spectrum),
                  'ew': equivalent_width(spectrum),
                  'total': line_flux(spectrum),
                  'maxval': spectrum.flux.max(),
                  'minval': spectrum.flux.min()}

    # compare!
    assert stats_dict == truth_dict

    cubeviz_layout.specviz._widget.current_workspace.current_plot_window.plot_widget._on_remove_linear_region()
