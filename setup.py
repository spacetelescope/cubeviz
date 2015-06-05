from distutils.core import setup

setup(
    name='Cube Tools',
    version='0.0.1',
    packages=['build.lib.cube_tools', 'build.lib.cube_tools.qt',
              'build.lib.cube_tools.core', 'build.lib.cube_tools.clients',
              'cube_tools', 'cube_tools.qt', 'cube_tools.core',
              'cube_tools.clients'],
    url='https://github.com/spacetelescope/cube-tools',
    license='',
    author='STScI',
    author_email='nearl@stsci.edu',
    description='Data analysis package for cubes.'
)
