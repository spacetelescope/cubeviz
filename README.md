# Cube Tools
Data analysis package for cubes.

## Installation
Cube Tools itself is pretty straight forward: simply clone or download and run the `setup.py` file. Cube Tools 
currently requires the development version of SpecView, along with Glue. 


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
You must copy the contents of the `glue_loader` directory into your `~/.glue` directory (if `~/.glue` doesn't exist, 
you can create it using `mkdir ~/.glue`).

With that finished, you can launch Glue by simply typing `glue` at the command line.



