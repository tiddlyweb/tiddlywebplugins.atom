
import mangler

config = {
        'system_plugins': ['tiddlywebplugins.atom'],
        'log_level': 'DEBUG',
        'wikitext.type_render_map' :{
            'text/x-markdown': 'tiddlywebplugins.markdown',
            },
        'atom.default_filter': 'select=tag:!excludeLists;sort=-modified;limit=20',
        }
