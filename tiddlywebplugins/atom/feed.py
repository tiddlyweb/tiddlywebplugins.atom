"""
Atom feeds for tiddlyweb tiddlers.
"""

import time
import datetime
import logging

from feedgenerator import Atom1Feed

from tiddlyweb.filters import parse_for_filters, recursive_filter
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.serializations import SerializationInterface
from tiddlyweb.util import binary_tiddler, pseudo_binary
from tiddlyweb.wikitext import render_wikitext
from tiddlyweb.web.util import server_host_url, tiddler_url


class Serialization(SerializationInterface):

    def __init__(self, environ={}):
        self.environ = environ

    def _current_url(self):
        script_name = self.environ.get('SCRIPT_NAME', '')
        query_string = self.environ.get('QUERY_STRING', None)
        url = script_name
        if query_string:
            url += '?%s' % query_string
        return url

    def list_tiddlers(self, tiddlers):
        """
        Turn the contents of a Tiddlers into an Atom Feed.
        """

        try:
            from tiddlyweb.model.collections import Tiddlers
            store = self.environ['tiddlyweb.store']
            config = self.environ['tiddlyweb.config']
            default_filter = config['atom.default_filter']
            filters, _ = parse_for_filters(default_filter, self.environ)
            new_tiddlers = Tiddlers()
            for tiddler in recursive_filter(filters, tiddlers):
                new_tiddlers.add(tiddler)
            new_tiddlers.title = tiddlers.title
            new_tiddlers.is_search = tiddlers.is_search
            new_tiddlers.is_revisions = tiddlers.is_revisions
            tiddlers = new_tiddlers
        except KeyError, ImportError:
            pass

        current_url = self._current_url()
        link = u'%s%s' % (self._host_url(), current_url)
        feed = Atom1Feed(link=link,
            language=u'en',
            title=tiddlers.title,
            description=tiddlers.title)

        for tiddler in tiddlers:
            self._add_tiddler_to_feed(feed, tiddler)

        # can we avoid sending utf-8 and let the wrapper handle it?
        return feed.writeString('utf-8')

    def tiddler_as(self, tiddler):
        feed = Atom1Feed(
                title=u'%s' % tiddler.title,
                link=tiddler_url(self.environ, tiddler),
                language=u'en',
                description=u'tiddler %s' % tiddler.title)
        self._add_tiddler_to_feed(feed, tiddler)
        return feed.writeString('utf-8')

    def _add_tiddler_to_feed(self, feed, tiddler):
        do_revisions = self.environ.get('tiddlyweb.query', {}).get(
                'depth', [None])[0]

        if not do_revisions:
            if binary_tiddler(tiddler):
                if tiddler.type.startswith('image/'):
                    description = ('\n<html><img src="%s" /></html>\n'
                            % tiddler_url(self.environ, tiddler))
                else:
                    description = ('\n<html><a href="%s">%s</a></html>\n'
                            % (tiddler_url(self.environ, tiddler),
                                tiddler.title))
            elif tiddler.type and pseudo_binary(tiddler.type):
                description = '<pre>' + tiddler.text + '</pre>'
            else:
                try:
                    description = render_wikitext(tiddler, self.environ)
                except KeyError:
                    description = 'Tiddler cannot be rendered.'

            self._add_item(feed, tiddler, tiddler_url(self.environ, tiddler),
                    tiddler.title, description)
        else:
            self._process_tiddler_revisions(feed, tiddler,
                    tiddler_url(self.environ, tiddler), do_revisions)

    def _process_tiddler_revisions(self, feed, tiddler, link, do_revisions):
        try:
            from tiddlywebplugins.differ import compare_tiddlers
        except ImportError:
            self._add_item(feed, tiddler, link, tiddler.title,
                    'unable to diff without tiddlywebplugins.differ')
        try:
            depth = int(do_revisions)
        except ValueError:
            depth = 1
        store = self.environ['tiddlyweb.store']
        revision_ids = store.list_tiddler_revisions(tiddler)
        while depth >= 0:
            try:
                rev_older = Tiddler(tiddler.title, tiddler.bag)
                rev_older.revision = revision_ids[depth + 1]
                rev_older = store.get(rev_older)
            except IndexError:
                depth -= 1
                continue
            rev_current = Tiddler(tiddler.title, tiddler.bag)
            rev_current.revision = revision_ids[depth]
            rev_current = store.get(rev_current)
            if binary_tiddler(tiddler):
                self._add_item(feed, tiddler, link, tiddler.title,
                        'Binary Content')
            else:
                title = '%s comparing version %s to %s' % (tiddler.title,
                        rev_older.revision, rev_current.revision)
                self._add_item(feed, rev_current, link, title,
                        '<pre>' + compare_tiddlers(rev_older, rev_current)
                        + '</pre>')
            depth -= 1

    def _add_item(self, feed, tiddler, link, title, description):
        logging.debug('adding %s' % title)
        feed.add_item(title=title,
                unique_id=self._tiddler_id(tiddler),
                link=link,
                categories=tiddler.tags,
                description=description,
                author_name=tiddler.modifier,
                pubdate=self._tiddler_datetime(tiddler.modified))

    def _tiddler_id(self, tiddler):
        return '%s/%s/%s' % (tiddler.title, tiddler.bag, tiddler.revision)

    def _tiddler_datetime(self, date_string):
        try:
            return datetime.datetime(*(time.strptime(
                date_string, '%Y%m%d%H%M%S')[0:6]))
        except ValueError:  # bad format in timestring
            return datetime.datetime.utcnow()

    def _host_url(self):
        return server_host_url(self.environ)
