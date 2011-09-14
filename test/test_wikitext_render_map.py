"""
Test that the wikitext render map is seen and used.
"""

from tiddlyweb.serializer import Serializer
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.config import config
import tiddlywebwiki

def setup_module(module):
    tiddlywebwiki.init(config)
    module.serializer = Serializer('tiddlywebplugins.atom.feed',
            environ={'tiddlyweb.config': config})

MARKDOWN="""
= Hi

* list one
* list two
"""

def test_svg_output():
    tiddler = Tiddler('markdown thing', 'fake')
    tiddler.text = MARKDOWN
    tiddler.type = 'text/x-markdown'

    serializer.object = tiddler
    output = serializer.to_string()
    assert '* list one' not in output
    assert '&lt;li&gt;list one' in output
