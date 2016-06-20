"""
moteradio: Mote radio configuration.

Change mote radio channel.
"""

from setuptools import setup, find_packages

import moteradio

doclines = __doc__.split("\n")

setup(name='moteradio',
      version=moteradio.version,
      description='Mote radio configuration.',
      long_description='\n'.join(doclines[2:]),
      url='https://github.com/proactivity-lab/python-moteradio',
      author='Raido Pahtma',
      author_email='raido.pahtma@ttu.ee',
      license='MIT',
      platforms=["any"],
      packages=find_packages(),
      install_requires=['moteconnection'],
      test_suite='nose.collector',
      tests_require=['nose'],
      zip_safe=False)
