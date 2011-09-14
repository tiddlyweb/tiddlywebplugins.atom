"""
Test that base hrefs are added to each entry.
"""

from tiddlyweb.serializer import Serializer
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.config import config
import tiddlywebwiki

def setup_module(module):
    tiddlywebwiki.init(config)
    module.serializer = Serializer('tiddlywebplugins.atom.feed',
            environ={'tiddlyweb.config': config})

TEXT="""\
!Hi

* list one
* list two

[[link one]] [[link two]]
"""

def test_base_output():
    tiddler = Tiddler('link thing', 'fake')
    tiddler.text = TEXT

    serializer.object = tiddler
    output = serializer.to_string()

    assert 'xml:base="http://0.0.0.0:8080/bags/fake/tiddlers/"' in output

    tiddler.recipe = 'carnage'

    serializer.object = tiddler
    output = serializer.to_string()

    assert 'xml:base="http://0.0.0.0:8080/recipes/carnage/tiddlers/"' in output
