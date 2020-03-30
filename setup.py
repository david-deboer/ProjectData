#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 David DeBoer
# Licensed under the 2-clause BSD license.

"""ProjectData setup."""
from setuptools import setup
import glob

setup_args = {
    'name': "project_data",
    'description': "ProjectData:  milestone/schedule tracker.",
    'license': "BSD",
    'author': "David DeBoer",
    'author_email': "david.r.deboer@gmail.edu",
    'version': '0.1',
    'packages': ['project_data'],
    'scripts': glob.glob('scripts/*'),
    'include_package_data': True,
    'install_requires': []
}

if __name__ == '__main__':
    setup(**setup_args)
