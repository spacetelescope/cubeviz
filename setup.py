from setuptools import setup

entry_points = """
[glue.plugins]
cube_tools=cube_tools:setup
"""

setup(
    name='Cube Tools',
    version='0.0.1',
    packages=['cube_tools', 'cube_tools.qt', 'cube_tools.core',
              'cube_tools.clients'],
    url='https://github.com/spacetelescope/cube-tools',
    license='',
    author='STScI',
    author_email='nearl@stsci.edu',
    description='Data analysis package for cubes.',
    entry_points=entry_points
)
