from setuptools import setup
import sys
import os

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import ebfe

setup(name=ebfe.NAME,
      version=ebfe.VER_STR,
      description='EBFE Binary File Editor',
      url='https://gitlab.com/icostin/ebfe-py',
      author='Costin Ionescu, Dumitru Stama',
      author_email='costin.ionescu@gmail.com, dumitru.stama@gmail.com',
      license='MIT',
      packages=['ebfe'],
      zip_safe=False,
      install_requires=[
          'zlx >= 0.0.12',
          'configparser',
      ],
      entry_points = {
          'console_scripts': ['ebfe=ebfe.cmd_line:main'],
      })
