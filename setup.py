
import os
from setuptools import setup, find_packages

VERSION = '1.4.6'


setup(
        namespace_packages = ['tiddlywebplugins'],
        name = 'tiddlywebplugins.atom',
        version = VERSION,
        description = 'A TiddlyWeb plugin that provides an Atom feed of tiddler collections.',
        long_description=open(os.path.join(os.path.dirname(__file__), 'README')).read(),
        author = 'Chris Dent',
        url = 'http://pypi.python.org/pypi/tiddlywebplugins.atom',
        packages = find_packages(exclude=['test']),
        author_email = 'cdent@peermore.com',
        platforms = 'Posix; MacOS X; Windows',
        install_requires = ['setuptools',
            'tiddlyweb>=1.4.2',
            'feedgenerator'],
        extras_require = {
            'testing': ['tiddlywebwiki', 'tiddlywebplugins.markdown']
        },
        zip_safe = False,
        license = 'BSD',
)
