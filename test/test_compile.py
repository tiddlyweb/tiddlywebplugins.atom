


def test_compile():
    try:
        import tiddlywebplugins.atom
        assert True
    except ImportError, exc:
        assert False, exc
    try:
        import tiddlywebplugins.atom.feed
        assert True
    except ImportError, exc:
        assert False, exc
    try:
        import tiddlywebplugins.atom.htmllinks
        assert True
    except ImportError, exc:
        assert False, exc
