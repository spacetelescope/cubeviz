# Cube Tools
Data analysis package for cubes.

## More info
For more information, such as demos and tutorials, see the [wiki](https://github.com/spacetelescope/cube-tools/wiki)

## Installation

Cube Tools itself is pretty straight forward: simply clone or download and run
the `setup.py` file. Cube Tools currently requires the development version of
SpecView, along with Glue.

* [Glue](http://www.glueviz.org/en/stable/installation.html)
* [SpecView](https://github.com/spacetelescope/specview)

### Installing SpecView
You can get this version using the git commands:

1. Clone the repository
    ```
    git clone https://github.com/spacetelescope/specview.git
    ```

2. Enter the cloned directory and switch to the development branch
    ```
    cd specview
    git checkout dev-0.1
    ```

3. Run the installation
    ```
    python setup.py install
    ```

### Setting up Glue

This plugin requires Glue 0.5.1 or later. Once the plugin is installed, it will
automatically be registered with Glue. If the plugin does not not appear in
Glue, you can start up glue with:

    glue --verbose
    
You should normally see:

    INFO:glue:Loading plugin cube_tools succeeded

but if there is an issue, you might see something like:

    INFO:glue:Loading plugin cube_tools failed (Exception: No module named models)

**Note:** if you installed this package by copying its contents to the
``~/.glue`` folder in the past, be sure to remove these files now.

### Customize the STcube Loader

How cubes are stored in FITS files varies greatly between data sets. A number of the more common formats have been included, but chances are more will need be added. If your particular dataset loads but is non-sensical, or, you get the "Wrong load method" dialog when using the STcube load method, you can try to define your own cube configuration.

Below is an example configuration. Add this code to the end of the ```~/.gluerc``` file. If the file does not exist, create it.

```
from cube_tools.core.fits_registry import fits_registry
fits_registry.update(
    {'MyNewCube': {
        'flux': {
            'ext': 0,
            'required': True,
            'wcs': True,
        },
        'error': {
            'ext': 1,
        },
        'mask': {
            'ext': 2,
        },
    }}
)
```
This defines a FITS file where the flux data is found in extension 0, the error data in extension 1, and the mask data in extension 2. Only the flux data is required and the wcs information is found in the flux data extension. Each configuration is identified by a name, in this case "MyNewCube". The only requirement is that the names be unique.

You can use extension numbers, or, if your data has named extensions, the extension names. The example below uses named extensions:

```
fits_registry.update(
    {'MyOtherNewCube': {
        'flux': {
            'ext': 'SCI',
            'required': True,
            'wcs': True,
        },
        'error': {
            'ext': 'IVAR',
        },
        'mask': {
            'ext': 'MASK',
        },
    }}
)
```
You can specify more than one configuration. Simply duplicate the code starting with ```fits_registry.update(```
