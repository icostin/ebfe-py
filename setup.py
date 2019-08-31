from setuptools import setup

setup(name='ebfe',
      version='0.0',
      description='Exuberant Binary Formats Editor',
      url='https://gitlab.com/icostin/ebfe-py',
      author='Costin Ionescu',
      author_email='costin.ionescu@gmail.com',
      license='MIT',
      packages=['ebfe'],
      zip_safe=False,
      entry_points = {
          'console_scripts': ['ebfe=ebfe.cmd_line:main'],
      })
