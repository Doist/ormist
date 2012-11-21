# -*- coding: utf-8 -*-
import os
from setuptools import setup

def read(fname):
    try:
        return open(os.path.join(os.path.dirname(__file__), fname)).read()
    except IOError:
        return ''

setup(
    name = 'ormist',
    version = '0.1',
    author = 'Roman Imankulov',
    author_email = 'roman.imankulkov@gmail.com',
    description = ('Object-to-Redis mapper. '),
    license = 'BSD',
    keywords = 'library framework orm redis',
    url = 'http://github.com/doist/ormist',
    packages = ['ormist', ],
    long_description = read('README.rst'),
    install_requires = ['redis', ],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: BSD License',
    ],
)
