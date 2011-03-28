"""
Test that author elements are properly entered.
"""

from tiddlyweb.serializer import Serializer
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.model.collections import Tiddlers
from tiddlyweb.config import config
import tiddlywebwiki

def setup_module(module):
    tiddlywebwiki.init(config)
    module.serializer = Serializer('tiddlywebplugins.atom.feed',
            environ={'tiddlyweb.config': config})
    config['atom.author_uri_map'] = '/profiles/%s'
    config['atom.hub'] = 'http://pubsubhubbub.appspot.com/'

def test_collection():
    tiddlers = Tiddlers()
    tiddler = Tiddler('foo', 'null')
    tiddler.text = 'bam'
    tiddler.modifier = 'cdent'
    tiddlers.add(tiddler)
    tiddler = Tiddler('bar', 'null')
    tiddler.text = 'zoom'
    tiddler.modifier = 'cdent'
    tiddlers.add(tiddler)

    output = serializer.list_tiddlers(tiddlers)

    assert '<name>cdent</name>' in output
    assert '<uri>http://0.0.0.0:8080/profiles/cdent</uri>' in output
    assert '<link href="http://pubsubhubbub.appspot.com/" rel="hub">' in output
