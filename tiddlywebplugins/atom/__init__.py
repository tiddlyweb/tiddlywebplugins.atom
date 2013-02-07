"""
A TiddlyWeb plugin that automates the process
of configuring TiddlyWeb to use serializers that
provide Atom feeds of one or more tiddlers, and
links in HTML presentations to those feeds.

To use add 'tiddlywebplugins.atom' to system_plugins
in tiddlywebconfig.py.
"""

EXTENSION_TYPES = {
        'atom': 'application/atom+xml'
}
SERIALIZERS = {
        'application/atom+xml': ['tiddlywebplugins.atom.feed',
            'application/atom+xml; charset=UTF-8'],
        'text/html': ['tiddlywebplugins.atom.htmllinks',
            'text/html; charset=UTF-8'],
}


def init(config):
    """
    Update serialization info to include atom.
    """
    config['extension_types'].update(EXTENSION_TYPES)
    config['serializers'].update(SERIALIZERS)
