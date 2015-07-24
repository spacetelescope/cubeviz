# Cube Tools
Data analysis package for cubes.

## More info
For more information, such as demos and tutorials, see the [wiki](https://github.com/spacetelescope/cube-tools/wiki)

## Installation

Cube Tools itself is pretty straight forward: simply clone or download and run
the `setup.py` file. Cube Tools currently requires the development version of
SpecView, along with Glue.

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
