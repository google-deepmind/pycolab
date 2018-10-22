# Copyright 2017 the pycolab Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""pycolab PyPI package setup."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

try:
  import setuptools
except ImportError:
  from ez_setup import use_setuptools
  use_setuptools()
  import setuptools

# Warn user about how curses is required to play games yourself.
try:
  import curses
except ImportError:
  import warnings
  warnings.warn(
      'The human_ui module and all of the example games (when run as '
      'standalone programs) require the curses library. Without curses, you '
      'can still use pycolab as a library, but you won\'t be able to play '
      'pycolab games on the console.')

setuptools.setup(
    name='pycolab',
    version='1.2',
    description='An engine for small games for reinforcement learning agents.',
    long_description=(
        'A highly-customisable all-Python gridworld game engine with some '
        'batteries included. Make your own gridworld games to demonstrate '
        'reinforcement learning problems and test your agents!'),
    url='https://github.com/deepmind/pycolab/',
    author='The pycolab authors',
    author_email='pycolab@deepmind.com',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Environment :: Console :: Curses',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Games/Entertainment :: Arcade',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Testing',
    ],
    keywords=(
        'ai '
        'ascii art '
        'game engine '
        'gridworld '
        'reinforcement learning '
        'retro retrogaming'),

    install_requires=[
        'numpy>=1.9',
        'six',
    ],
    extras_require={
        'ndimage': ['scipy>=0.13.3'],
    },

    packages=setuptools.find_packages(),
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'aperture = pycolab.examples.aperture:main',
            'apprehend = pycolab.examples.apprehend:main',
            ('extraterrestrial_marauders = '
             'pycolab.examples.extraterrestrial_marauders:main'),
            'fluvial_natation = pycolab.examples.fluvial_natation:main',
            'hello_world = pycolab.examples.hello_world:main',
            'scrolly_maze = pycolab.examples.scrolly_maze:main',
            'shockwave = pycolab.examples.shockwave:main [ndimage]',
            'warehouse_manager = pycolab.examples.warehouse_manager:main',
            'chain_walk = pycolab.examples.classics.chain_walk:main',
            'cliff_walk = pycolab.examples.classics.cliff_walk:main',
            'four_rooms = pycolab.examples.classics.four_rooms:main',
        ],
    },

    test_suite='nose.collector',
    tests_require=['nose'],
)
