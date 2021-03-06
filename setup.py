#!/usr/bin/env python

__author__ = "Katarina Brlec"
__copyright__ = "Copyright Katarina Brlec, Daniel W. Davies (2020)"
__version__ = "0.1"
__maintainer__ = "Katarina Brlec"
__email__ = "katarina.brlec.15@ucl.ac.uk"
__date__ = "July 12 2020"

from setuptools import setup, Extension
import os
import unittest

module_dir = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    setup(
      name='surfaxe',
      version='0.1',
      description='Dealing with slabs for first principles calculations of surfaces',
      long_description=open(os.path.join(module_dir, 'README.md')).read(),
      long_description_content_type='text/markdown',
      url='https://github.com/SMTG-group/',
      author='Katarina Brlec',
      author_email='katarina.brlec.15@ucl.ac.uk',
      license='MIT',
      packages=['surfaxe'],
      zip_safe=False,
      install_requires=['scipy', 'numpy', 'spglib', 'pymatgen','pandas'],
      classifiers=[
        'Programming Language :: Python',
        'Development Status :: Development',
        'Intended Audience :: Science/Research',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering'
      ]
    )
