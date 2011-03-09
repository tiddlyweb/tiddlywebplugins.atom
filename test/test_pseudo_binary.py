"""
Test that psuedo-binaries like image/svg+xml get treated
fairly and not wikified.
"""

from tiddlyweb.serializer import Serializer
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.config import config
import tiddlywebwiki

def setup_module(module):
    tiddlywebwiki.init(config)
    module.serializer = Serializer('tiddlywebplugins.atom.feed',
            environ={'tiddlyweb.config': config})

SVG="""
<?xml version="1.0" encoding="utf-8"?>
<!-- Generator: Adobe Illustrator 14.0.0, SVG Export Plug-In . SVG Version: 6.00 Build 43363)  -->
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
width="76.441px" height="100px" viewBox="0 0 76.441 100" enable-background="new 0 0 76.441 100" xml:space="preserve">
<path d="M25.848,21.016c5.804-0.019,10.501-4.716,10.506-10.507C36.349,4.711,31.652,0.014,25.848,0
c-5.786,0.014-10.483,4.711-10.507,10.509C15.365,16.3,20.062,20.997,25.848,21.016L25.848,21.016z"/>
<path d="M25.848,10.509"/>
<path d="M17.877,33.748c-1.878-12.064,15.536-15.73,18.323-3.363l4.762,23.653h17.701c5.168,0.017,7.854,4.151,7.869,7.974v32.143
c-0.015,7.832-11.135,7.794-11.131-0.104c-0.004-7.354,0-25.055,0-25.055H32.784c-5.265,0.011-8.572-3.607-9.42-7.764L17.877,33.748
L17.877,33.748z"/>
<path d="M47.123,71.119c5.859,0,5.832,8.688,0.051,8.697H30.972c-7.91-0.01-15.782-5.939-17.857-15.116L8.094,40.114
c-1.047-5.572,6.989-7.43,8.178-1.707l4.814,23.498c1.322,6.012,5.768,9.214,11.129,9.214H47.123L47.123,71.119z"/>
<path d="M69.121,15.789"/>
<path d="M69.121,15.789"/>
</svg>
"""

def test_svg_output():
    tiddler = Tiddler('svg thing', 'fake')
    tiddler.text = SVG
    tiddler.type = 'image/svg+xml'

    serializer.object = tiddler
    output = serializer.to_string()
    assert 'wikkly-error-head' not in output

def test_normal_output():
    tiddler = Tiddler('not svg thing', 'fake')
    tiddler.text = '!Hi'

    serializer.object = tiddler
    output = serializer.to_string()
    assert 'h1 class="w' in output
