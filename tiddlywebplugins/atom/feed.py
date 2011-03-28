"""
Atom feeds for tiddlyweb tiddlers.

By default the feed given is all the tiddlers in the collection represented
by the given URI, in no particular order. This is not always the best
default. If you want a different default you can set 'atom.default_filter'
in tiddlywebconfig.py to a string that represents a TiddlyWeb filter.
For example:

    'atom.default_filter': 'select=tag:!excludeLists;sort=-modified;limit=20',
         
would give the 20 most recently modified tiddlers which are not tagged
'excludeLists'.

The atom feed will include author elements for each tiddler. If all
the tiddlers have the same modifier, then there will also be a feed
level author element. 

If 'atom.author_uri_map' is set in config then its value will be used
as the format string for created a uri element within the author element.
For example:

    'atom.author_uri_map': '/profiles/%s'

will result in a uri element value for the user cdent on server_host
0.0.0.0:8080 (with no server_prefix) of "http://0.0.0.0/profiles/cdent".
"""

import time
import datetime
import logging

from feedgenerator import Atom1Feed, rfc3339_date

from tiddlyweb.filters import parse_for_filters, recursive_filter
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.serializations import SerializationInterface
from tiddlyweb.util import binary_tiddler, pseudo_binary
from tiddlyweb.wikitext import render_wikitext
from tiddlyweb.web.util import server_base_url, server_host_url, tiddler_url


class Serialization(SerializationInterface):

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

        authors = set()
        try:
            from tiddlyweb.model.collections import Tiddlers
            config = self.environ['tiddlyweb.config']
            default_filter = config['atom.default_filter']
            filters, _ = parse_for_filters(default_filter, self.environ)
            new_tiddlers = Tiddlers()
            for tiddler in recursive_filter(filters, tiddlers):
                new_tiddlers.add(tiddler)
                authors.add(tiddler.modifier)
            new_tiddlers.title = tiddlers.title
            new_tiddlers.is_search = tiddlers.is_search
            new_tiddlers.is_revisions = tiddlers.is_revisions
            tiddlers = new_tiddlers
        except (KeyError, ImportError):
            pass

        author_name = None
        author_link = None
        if len(authors) == 1:
            author_name = authors.pop()
            author_link = self._get_author_link(author_name)

        current_url = self._current_url()
        link = u'%s%s' % (self._host_url(), current_url)
        feed = AtomFeed(link=link,
            language=u'en',
            author_name=author_name,
            author_link=author_link,
            title=tiddlers.title,
            description=tiddlers.title)

        for tiddler in tiddlers:
            self._add_tiddler_to_feed(feed, tiddler)

        # can we avoid sending utf-8 and let the wrapper handle it?
        return feed.writeString('utf-8')

    def tiddler_as(self, tiddler):
        feed = AtomFeed(
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
                    description = ('\n<img src="%s" />\n'
                            % tiddler_url(self.environ, tiddler))
                else:
                    description = ('\n<a href="%s">%s</a>\n'
                            % (tiddler_url(self.environ, tiddler),
                                tiddler.title))
            elif (tiddler.type and (
                tiddler.type not in
                self.environ['tiddlyweb.config']['wikitext.type_render_map'])
                and pseudo_binary(tiddler.type)):
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

    def _get_author_link(self, author_name):
        author_link = None
        author_uri_map = self.environ.get(
                'tiddlyweb.config', {}).get(
                        'atom.author_uri_map', None)
        if author_uri_map:
            author_link = (server_base_url(self.environ) +
                    author_uri_map % author_name)
        return author_link

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
        logging.debug('adding %s', title)
        author_link = self._get_author_link(tiddler.modifier)
        feed.add_item(title=title,
                unique_id=self._tiddler_id(tiddler),
                link=link,
                categories=tiddler.tags,
                description=description,
                author_name=tiddler.modifier,
                author_link=author_link,
                pubdate=self._tiddler_datetime(tiddler.created),
                updated=self._tiddler_datetime(tiddler.modified))

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


class AtomFeed(Atom1Feed):
    """
    Override the default Atom1Feed to improve the output.
    Use content instead of summary in each entry for the "description".
    Later we'll add hub and top level author information.
    """

    def add_item(self, title, link, description,
            author_email=None, author_name=None, author_link=None,
            pubdate=None, updated=None, unique_id=None,
            enclosure=None, categories=(), item_copyright=None,
            **kwargs):
        """
        Adds an item to the feed. All args are expected to be Python Unicode
        objects except pubdate, which is a datetime.datetime object, and
        enclosure, which is an instance of the Enclosure class.
        """
        item = {
            'title': title,
            'link': link,
            'description': description,
            'author_email': author_email,
            'author_name': author_name,
            'author_link': author_link,
            'pubdate': pubdate,
            'updated': updated,
            'unique_id': unique_id,
            'enclosure': enclosure,
            'categories': categories or (),
            'item_copyright': item_copyright,
        }
        item.update(kwargs)
        self.items.append(item)

    def add_item_elements(self, handler, item):
        """
        We override this entire method to handle
        pubdate -> published
        updated -> updated
        description -> content (instead of summary)
        """
        handler.addQuickElement(u"title", item['title'])
        handler.addQuickElement(u"link", u"",
                {u"href": item['link'], u"rel": u"alternate"})
        if item['updated'] is not None:
            handler.addQuickElement(u"updated",
                    rfc3339_date(item['updated']).decode('utf-8'))
        if item['pubdate'] is not None:
            handler.addQuickElement(u"published",
                    rfc3339_date(item['pubdate']).decode('utf-8'))

        # Author information.
        if item['author_name'] is not None:
            handler.startElement(u"author", {})
            handler.addQuickElement(u"name", item['author_name'])
            if item['author_email'] is not None:
                handler.addQuickElement(u"email", item['author_email'])
            if item['author_link'] is not None:
                handler.addQuickElement(u"uri", item['author_link'])
            handler.endElement(u"author")

        # Unique ID.
        handler.addQuickElement(u"id", item['unique_id'])

        # Content.
        item_type = item.get('type', u'html')
        if item['description'] is not None:
            handler.addQuickElement(u"content", item['description'],
                    {u"type": item_type})

        # Enclosure.
        if item['enclosure'] is not None:
            handler.addQuickElement(u"link", '',
                {u"rel": u"enclosure",
                 u"href": item['enclosure'].url,
                 u"length": item['enclosure'].length,
                 u"type": item['enclosure'].mime_type})

        # Categories.
        for cat in item['categories']:
            handler.addQuickElement(u"category", u"", {u"term": cat})

        # Rights.
        if item['item_copyright'] is not None:
            handler.addQuickElement(u"rights", item['item_copyright'])
