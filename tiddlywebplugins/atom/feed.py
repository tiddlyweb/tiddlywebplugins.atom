"""
Atom feeds for tiddlyweb.

The Atom code is borrowed from Django's django/utils/feedgenerator.py

  http://www.djangoproject.com/documentation/syndication_feeds/
  http://code.djangoproject.com/browser/django/trunk/django/utils/feedgenerator.py

Which appears to be licensed with

PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2

Thanks to those guys for making a feed library that hides the
nasty XML details.

"""

import time
import types
import urllib
import datetime
import re
import email.Utils
import logging

from xml.sax.saxutils import XMLGenerator


from tiddlyweb.filters import parse_for_filters, recursive_filter
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.serializations import SerializationInterface
from tiddlyweb.wikitext import render_wikitext
from tiddlyweb.web.util import server_base_url, server_host_url

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

    def list_tiddlers(self, bag):
        """
        Turn the contents of a bag into an Atom Feed.
        """
        try:
            tiddlers = bag.gen_tiddlers()
        except AttributeError:
            tiddlers = bag

        try:
            from tiddlyweb.model.collections import Tiddlers
            store = self.environ['tiddlyweb.store']
            config = self.environ['tiddlyweb.config']
            default_filter = config['atom.default_filter']
            filters, _ = parse_for_filters(default_filter, self.environ)
            new_tiddlers = Tiddlers()
            for tiddler in recursive_filter(filters, tiddlers):
                new_tiddlers.add(tiddler)
            tiddlers = new_tiddlers
        except KeyError, ImportError:
            pass

        current_url = self._current_url()
        link=u'%s%s' % (self._host_url(), current_url)
        feed = Atom1Feed(link=link,
            language=u'en',
            title='Empty Tiddler List',
            description=u'Empty Tiddler List')

        for tiddler in tiddlers:
            if tiddler.recipe:
                feed.title = u'Tiddlers in Recipe %s' % tiddler.recipe
                feed.description = u'the tiddlers of recipe %s' % tiddler.recipe
            else:
                feed.title = u'Tiddlers in Bag %s' % tiddler.bag
                feed.description = u'the tiddlers of recipe %s' % tiddler.bag
            
            self._add_tiddler_to_feed(feed, tiddler)

        # can we avoid sending utf-8 and let the wrapper handle it?
        return feed.writeString('utf-8')

    def tiddler_as(self, tiddler):
        if tiddler.recipe:
            link = u'%s/recipes/%s/tiddlers/%s' % \
                    (self._server_url(), iri_to_uri(tiddler.recipe),
                            iri_to_uri(urllib.quote(tiddler.title.encode('utf-8'), safe='')))
        else:
            link = u'%s/bags/%s/tiddlers/%s' % \
                    (self._server_url(), iri_to_uri(tiddler.bag),
                            iri_to_uri(urllib.quote(tiddler.title.encode('utf-8'), safe='')))
        feed = Atom1Feed(
                title=u'%s' % tiddler.title,
                link=link,
                language=u'en',
                description=u'tiddler %s' % tiddler.title
                )
        self._add_tiddler_to_feed(feed, tiddler)
        return feed.writeString('utf-8')

    def _add_tiddler_to_feed(self, feed, tiddler):
        if tiddler.recipe:
            tiddler_link = 'recipes/%s/tiddlers' % tiddler.recipe
            link = u'%s/recipes/%s/tiddlers/%s' % \
                    (self._server_url(), iri_to_uri(tiddler.recipe),
                            iri_to_uri(urllib.quote(tiddler.title.encode('utf-8'), safe='')))
        else:
            tiddler_link = 'bags/%s/tiddlers' % tiddler.bag
            link = u'%s/bags/%s/tiddlers/%s' % \
                    (self._server_url(), iri_to_uri(tiddler.bag),
                            iri_to_uri(urllib.quote(tiddler.title.encode('utf-8'), safe='')))

        do_revisions = self.environ.get('tiddlyweb.query', {}).get(
                'depth', [None])[0]

        if not do_revisions:
            if tiddler.type and tiddler.type != 'None' and not tiddler.type.startswith('text/'):
                description = 'Binary Content'
            else:
                try:
                    description = render_wikitext(tiddler, self.environ)
                except KeyError:
                    description = 'Tiddler cannot be rendered.'

            self._add_item(feed, tiddler, link, tiddler.title, description)
        else:
            self._process_tiddler_revisions(feed, tiddler, link, do_revisions)

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
            if tiddler.type and tiddler.type != 'None' and not tiddler.type.startswith('text/'):
                self._add_item(feed, tiddler, link, tiddler.title, 'Binary Content')
            else:
                title = '%s comparing version %s to %s' % (tiddler.title,
                        rev_older.revision, rev_current.revision)
                self._add_item(feed, rev_current, link, title,
                        '<pre>' + compare_tiddlers(rev_older, rev_current) + '</pre>')
            depth -= 1

    def _add_item(self, feed, tiddler, link, title, description):
        logging.debug('adding %s' % title)
        feed.add_item(title=title,
                unique_id=self._tiddler_id(tiddler),
                link=link,
                categories=tiddler.tags,
                description=description,
                author_name=tiddler.modifier,
                pubdate=self._tiddler_datetime(tiddler.modified)
                )

    def _tiddler_id(self, tiddler):
        return '%s/%s/%s' % (tiddler.title, tiddler.bag, tiddler.revision)

    def _tiddler_datetime(self, date_string):
        return datetime.datetime(*(time.strptime(date_string, '%Y%m%d%H%M%S')[0:6]))

    def _host_url(self):
        return server_host_url(self.environ)

    def _server_url(self):
        return server_base_url(self.environ)


"""
Atom feed generation from django.
"""
class SimplerXMLGenerator(XMLGenerator):
    def addQuickElement(self, name, contents=None, attrs=None):
        "Convenience method for adding an element with no children"
        if attrs is None: attrs = {}
        self.startElement(name, attrs)
        if contents is not None:
            self.characters(contents)
        self.endElement(name)

def force_unicode(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Similar to smart_unicode, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int, long, datetime.datetime, datetime.date, datetime.time, float)):
        return s
    if not isinstance(s, basestring,):
        if hasattr(s, '__unicode__'):
            s = unicode(s)
        else:
            s = unicode(str(s), encoding, errors)
    elif not isinstance(s, unicode):
        # Note: We use .decode() here, instead of unicode(s, encoding,
        # errors), so that if s is a SafeString, it ends up being a
        # SafeUnicode at the end.
        s = s.decode(encoding, errors)
    return s

def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
    elif not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s

def iri_to_uri(iri):
    """
    Convert an Internationalized Resource Identifier (IRI) portion to a URI
    portion that is suitable for inclusion in a URL.

    This is the algorithm from section 3.1 of RFC 3987.  However, since we are
    assuming input is either UTF-8 or unicode already, we can simplify things a
    little from the full method.

    Returns an ASCII string containing the encoded result.
    """
    # The list of safe characters here is constructed from the printable ASCII
    # characters that are not explicitly excluded by the list at the end of
    # section 3.1 of RFC 3987.
    if iri is None:
        return iri
    return urllib.quote(smart_str(iri), safe='/#%[]=:;$&()+,!*')


"""
Syndication feed generation library -- used for generating RSS, etc.

Sample usage:

>>> from django.utils import feedgenerator
>>> feed = feedgenerator.Rss201rev2Feed(
...     title=u"Poynter E-Media Tidbits",
...     link=u"http://www.poynter.org/column.asp?id=31",
...     description=u"A group weblog by the sharpest minds in online media/journalism/publishing.",
...     language=u"en",
... )
>>> feed.add_item(title="Hello", link=u"http://www.holovaty.com/test/", description="Testing.")
>>> fp = open('test.rss', 'w')
>>> feed.write(fp, 'utf-8')
>>> fp.close()
"""

def rfc2822_date(date):
    return email.Utils.formatdate(time.mktime(date.timetuple()))

def rfc3339_date(date):
    if date.tzinfo:
        return date.strftime('%Y-%m-%dT%H:%M:%S%z')
    else:
        return date.strftime('%Y-%m-%dT%H:%M:%SZ')

def get_tag_uri(url, date):
    "Creates a TagURI. See http://diveintomark.org/archives/2004/05/28/howto-atom-id"
    tag = re.sub('^http://', '', url)
    if date is not None:
        tag = re.sub('/', ',%s:/' % date.strftime('%Y-%m-%d'), tag, 1)
    tag = re.sub('#', '/', tag)
    return u'tag:' + tag

class SyndicationFeed(object):
    "Base class for all syndication feeds. Subclasses should provide write()"
    def __init__(self, title, link, description, language=None, author_email=None,
            author_name=None, author_link=None, subtitle=None, categories=None,
            feed_url=None, feed_copyright=None, feed_guid=None, ttl=None):
        to_unicode = lambda s: force_unicode(s, strings_only=True)
        if categories:
            categories = [force_unicode(c) for c in categories]
        self.feed = {
            'title': to_unicode(title),
            'link': iri_to_uri(link),
            'description': to_unicode(description),
            'language': to_unicode(language),
            'author_email': to_unicode(author_email),
            'author_name': to_unicode(author_name),
            'author_link': iri_to_uri(author_link),
            'subtitle': to_unicode(subtitle),
            'categories': categories or (),
            'feed_url': iri_to_uri(feed_url),
            'feed_copyright': to_unicode(feed_copyright),
            'id': feed_guid or link,
            'ttl': ttl,
        }
        self.items = []

    def add_item(self, title, link, description, author_email=None,
        author_name=None, author_link=None, pubdate=None, comments=None,
        unique_id=None, enclosure=None, categories=(), item_copyright=None, ttl=None):
        """
        Adds an item to the feed. All args are expected to be Python Unicode
        objects except pubdate, which is a datetime.datetime object, and
        enclosure, which is an instance of the Enclosure class.
        """
        to_unicode = lambda s: force_unicode(s, strings_only=True)
        if categories:
            categories = [to_unicode(c) for c in categories]
        self.items.append({
            'title': to_unicode(title),
            'link': iri_to_uri(link),
            'description': to_unicode(description),
            'author_email': to_unicode(author_email),
            'author_name': to_unicode(author_name),
            'author_link': iri_to_uri(author_link),
            'pubdate': pubdate,
            'comments': to_unicode(comments),
            'unique_id': to_unicode(unique_id),
            'enclosure': enclosure,
            'categories': categories or (),
            'item_copyright': to_unicode(item_copyright),
            'ttl': ttl,
        })

    def num_items(self):
        return len(self.items)

    def write(self, outfile, encoding):
        """
        Outputs the feed in the given encoding to outfile, which is a file-like
        object. Subclasses should override this.
        """
        raise NotImplementedError

    def writeString(self, encoding):
        """
        Returns the feed in the given encoding as a string.
        """
        from StringIO import StringIO
        s = StringIO()
        self.write(s, encoding)
        return s.getvalue()

    def latest_post_date(self):
        """
        Returns the latest item's pubdate. If none of them have a pubdate,
        this returns the current date/time.
        """
        updates = [i['pubdate'] for i in self.items if i['pubdate'] is not None]
        if len(updates) > 0:
            updates.sort()
            return updates[-1]
        else:
            return datetime.datetime.now()

class Enclosure(object):
    "Represents an RSS enclosure"
    def __init__(self, url, length, mime_type):
        "All args are expected to be Python Unicode objects"
        self.length, self.mime_type = length, mime_type
        self.url = iri_to_uri(url)

class Atom1Feed(SyndicationFeed):
    # Spec: http://atompub.org/2005/07/11/draft-ietf-atompub-format-10.html
    mime_type = 'application/atom+xml'
    ns = u"http://www.w3.org/2005/Atom"
    def write(self, outfile, encoding):
        handler = SimplerXMLGenerator(outfile, encoding)
        handler.startDocument()
        if self.feed['language'] is not None:
            handler.startElement(u"feed", {u"xmlns": self.ns, u"xml:lang": self.feed['language']})
        else:
            handler.startElement(u"feed", {u"xmlns": self.ns})
        handler.addQuickElement(u"title", self.feed['title'])
        handler.addQuickElement(u"link", "", {u"rel": u"alternate", u"href": self.feed['link']})
        if self.feed['feed_url'] is not None:
            handler.addQuickElement(u"link", "", {u"rel": u"self", u"href": self.feed['feed_url']})
        handler.addQuickElement(u"id", self.feed['id'])
        handler.addQuickElement(u"updated", rfc3339_date(self.latest_post_date()).decode('ascii'))
        if self.feed['author_name'] is not None:
            handler.startElement(u"author", {})
            handler.addQuickElement(u"name", self.feed['author_name'])
            if self.feed['author_email'] is not None:
                handler.addQuickElement(u"email", self.feed['author_email'])
            if self.feed['author_link'] is not None:
                handler.addQuickElement(u"uri", self.feed['author_link'])
            handler.endElement(u"author")
        if self.feed['subtitle'] is not None:
            handler.addQuickElement(u"subtitle", self.feed['subtitle'])
        for cat in self.feed['categories']:
            handler.addQuickElement(u"category", "", {u"term": cat})
        if self.feed['feed_copyright'] is not None:
            handler.addQuickElement(u"rights", self.feed['feed_copyright'])
        self.write_items(handler)
        handler.endElement(u"feed")

    def write_items(self, handler):
        for item in self.items:
            handler.startElement(u"entry", {})
            handler.addQuickElement(u"title", item['title'])
            handler.addQuickElement(u"link", u"", {u"href": item['link'], u"rel": u"alternate"})
            if item['pubdate'] is not None:
                handler.addQuickElement(u"updated", rfc3339_date(item['pubdate']).decode('ascii'))

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
            if item['unique_id'] is not None:
                unique_id = item['unique_id']
            else:
                unique_id = get_tag_uri(item['link'], item['pubdate'])
            handler.addQuickElement(u"id", unique_id)

            # Summary.
            if item['description'] is not None:
                handler.addQuickElement(u"summary", item['description'], {u"type": u"html"})

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

            handler.endElement(u"entry")
