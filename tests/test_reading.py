import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
from xml.etree import ElementTree

import main as site
import reading


ARTICLE = {"title": 'An article & <thoughts>', "url": 'https://www.lesswrong.com/posts/abc/title?a=1&b=2'}
RSS = b'''<rss version="2.0"><channel><item>
<title>An article &amp; &lt;thoughts&gt;</title>
<link>https://www.lesswrong.com/posts/abc/title?a=1&amp;b=2</link>
<description>PRIVATE NOTE MUST NEVER APPEAR</description>
</item></channel></rss>'''
NOTE = b'''<html><body>
<a href="https://histre.com/notes/user/example/?accesscode=DO-NOT-PUBLISH">Share</a>
<div class="note-card"><a class="note-title text-truncate"
href="https://www.lesswrong.com/posts/abc/title?a=1&amp;b=2">
An article &amp; &lt;thoughts&gt;</a>
<div class="note-body">PRIVATE NOTE MUST NEVER APPEAR</div></div>
</body></html>'''
LATEST_RSS = b'''<rss><channel>
<item><title>The Void</title><link>https://example.org/void</link><pubDate>Sat, 05 Sep 2026 18:02:40 +0000</pubDate></item>
<item><title>Collections | histre</title><link>https://histre.com/collections/</link></item>
<item><title>Duplicate</title><link>https://example.org/void</link></item>
<item><title>Philosophy</title><link>https://example.org/book</link><pubDate>Sat, 05 Sep 2026 18:13:00 +0000</pubDate></item>
<item><title>AGI</title><link>https://example.org/agi</link></item>
</channel></rss>'''
LATEST = [{"title": "The Void", "url": "https://example.org/void"},
          {"title": "Philosophy", "url": "https://example.org/book"}]


class ReadingTests(unittest.TestCase):
    @contextlib.contextmanager
    def configured_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / 'currently-reading.json'
            config = Path(directory) / 'reading-feed.json'
            snapshot.write_text(json.dumps([ARTICLE]), encoding='utf-8')
            config.write_text(json.dumps({'url': 'https://histre.com/example/rss/'}), encoding='utf-8')
            with patch.object(reading, 'SELECTION_PATH', snapshot), \
                 patch.object(reading, 'FEED_CONFIG_PATH', config):
                yield snapshot

    def test_empty_selection_has_no_heading(self):
        self.assertEqual(reading.render_selection([]), "")

    def test_render_escapes_titles_and_attributes(self):
        html = reading.render_selection([ARTICLE])
        self.assertIn('Currently reading</h3>', html)
        self.assertIn('An article &amp; &lt;thoughts&gt;', html)
        self.assertIn('?a=1&amp;b=2', html)

    def test_invalid_selections_are_rejected(self):
        for items in ({}, [ARTICLE] * 3, [ARTICLE] * 2,
                      [{"title": "", "url": "https://example.org"}],
                      [{"title": "Bad", "url": "javascript:alert(1)"}],
                      [{"title": "Bad", "url": "https://user:secret@example.org"}],
                      [{"title": "Bad", "url": "https://exa\nmple.org"}]):
            with self.subTest(items=items), self.assertRaises(ValueError):
                reading.validate_selection(items)

    def test_feed_imports_only_selected_titles_and_urls(self):
        self.assertEqual(reading.parse_feed(RSS), [ARTICLE])
        self.assertEqual(reading.parse_feed(b'<rss><channel/></rss>'), [])
        for content in (b'<html>Log in</html>',
                        RSS.replace(b'</channel>', b'<item><title>X</title></item></channel>'),
                        RSS.replace(b'www.lesswrong.com', b'histre.com')):
            with self.subTest(content=content), self.assertRaises(ValueError):
                reading.parse_feed(content)

    def test_atom_alternate_link(self):
        feed = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
        <title>Two</title><link rel="self" href="https://histre.com/note"/>
        <link rel="alternate" href="https://www.alignmentforum.org/posts/def/title"/>
        </entry></feed>'''
        self.assertEqual(reading.parse_feed(feed), [{"title": "Two", "url": "https://www.alignmentforum.org/posts/def/title"}])

    def test_latest_uses_feed_order_skips_histre_and_deduplicates(self):
        self.assertEqual(reading.parse_feed(LATEST_RSS, latest=True), LATEST)
        with self.assertRaises(ValueError):
            reading.parse_feed(LATEST_RSS)
        with self.assertRaises(ValueError):
            reading.parse_feed(LATEST_RSS.replace(b'https://example.org/book', b'javascript:alert(1)'), latest=True)
        self.assertEqual(reading.parse_feed(b'<rss><channel/></rss>', latest=True), [])

    def test_latest_atom_also_limits_to_two_original_links(self):
        feed = b'''<feed xmlns="http://www.w3.org/2005/Atom">
        <entry><title>Histre</title><link href="https://histre.com/collections/"/></entry>
        <entry><title>The Void</title><link href="https://example.org/void"/></entry>
        <entry><title>Philosophy</title><link href="https://example.org/book"/></entry>
        <entry><title>AGI</title><link href="https://example.org/agi"/></entry>
        </feed>'''
        self.assertEqual(reading.parse_feed(feed, latest=True), LATEST)

    def test_build_refreshes_and_saves_only_selected_links(self):
        with self.configured_snapshot() as snapshot, \
             patch.object(reading, 'fetch_selection', return_value=LATEST) as fetch, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(reading.load_build_selection(), LATEST)
            fetch.assert_called_once_with('https://histre.com/example/rss/', latest=True)
            self.assertEqual(reading.load_selection(snapshot), LATEST)

    def test_failed_build_refresh_preserves_snapshot(self):
        for error in (URLError('offline'), ValueError('bad feed'), ElementTree.ParseError('bad XML')):
            with self.subTest(error=type(error).__name__), self.configured_snapshot() as snapshot, \
                 patch.object(reading, 'fetch_selection', side_effect=error), \
                 contextlib.redirect_stderr(io.StringIO()) as errors:
                before = snapshot.read_bytes()
                self.assertEqual(reading.load_build_selection(), [ARTICLE])
                self.assertEqual(snapshot.read_bytes(), before)
                self.assertIn('using the saved selection', errors.getvalue())

    def test_build_uses_clean_title_overrides_without_pinning_old_articles(self):
        with self.configured_snapshot() as snapshot, \
             patch.object(reading, 'fetch_selection', return_value=LATEST), \
             contextlib.redirect_stdout(io.StringIO()):
            reading.FEED_CONFIG_PATH.write_text(json.dumps({
                'url': 'https://histre.com/example/rss/',
                'titles': {'https://example.org/book': 'A shorter book title',
                           'https://example.org/absent': 'Do not pin this article'}
            }), encoding='utf-8')
            selected = reading.load_build_selection()
            self.assertEqual([item['url'] for item in selected], [item['url'] for item in LATEST])
            self.assertEqual(selected[1]['title'], 'A shorter book title')
            self.assertEqual(reading.load_selection(snapshot), selected)

    def test_offline_build_does_not_fetch_or_change_snapshot(self):
        with self.configured_snapshot() as snapshot, patch.object(reading, 'fetch_selection') as fetch:
            before = snapshot.read_bytes()
            self.assertEqual(reading.load_build_selection(offline=True), [ARTICLE])
            fetch.assert_not_called()
            self.assertEqual(snapshot.read_bytes(), before)

    def test_intentionally_empty_feed_clears_reading_section(self):
        with self.configured_snapshot() as snapshot, \
             patch.object(reading, 'fetch_selection', return_value=[]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(reading.load_build_selection(), [])
            self.assertEqual(reading.load_selection(snapshot), [])

    def test_latest_cli_can_import_downloaded_feed(self):
        with self.configured_snapshot() as snapshot:
            feed = snapshot.parent / 'collection.rss'
            feed.write_bytes(LATEST_RSS)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(reading.main(['--feed-file', str(feed), '--latest', '--write']), 0)
            self.assertEqual(reading.load_selection(snapshot), LATEST)

    def test_shared_note_imports_only_original_title_and_url(self):
        self.assertEqual(reading.parse_note(NOTE), [ARTICLE])
        html = reading.render_selection(reading.parse_note(NOTE))
        self.assertNotIn('PRIVATE NOTE', html)
        self.assertNotIn('accesscode', html)
        self.assertNotIn('histre.com', html)

    def test_invalid_shared_notes_are_rejected(self):
        for content in (b'<html>Log in</html>', NOTE + NOTE,
                        NOTE.replace(b'www.lesswrong.com', b'histre.com'),
                        NOTE.replace(b'https://www.lesswrong.com', b'javascript:'),
                        NOTE[:NOTE.index(b'An article')],
                        b'x' * (reading.MAX_FEED_BYTES + 1)):
            with self.subTest(content=content[:80]), self.assertRaises(ValueError):
                reading.parse_note(content)

    def test_note_fetch_uses_only_the_supplied_share_page(self):
        url = 'https://histre.com/notes/user/example/?accesscode=DO-NOT-PUBLISH'
        with patch.object(reading, 'fetch_content', return_value=NOTE) as fetch:
            self.assertEqual(reading.fetch_note(url), [ARTICLE])
            fetch.assert_called_once_with(url, 'text/html')
        for url in ('https://example.org/notes/user/example/', 'https://histre.com/@user/',
                    'https://histre.com/collections/user/example/'):
            with self.subTest(url=url), patch.object(reading, 'fetch_content') as fetch, \
                 self.assertRaises(ValueError):
                reading.fetch_note(url)
            fetch.assert_not_called()

    def test_note_import_saves_no_share_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / 'currently-reading.json'
            with patch.object(reading, 'SELECTION_PATH', snapshot), \
                 patch.object(reading, 'fetch_note', return_value=reading.parse_note(NOTE)), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(reading.main([
                    '--histre-note', 'https://histre.com/notes/user/example/?accesscode=DO-NOT-PUBLISH',
                    '--write']), 0)
            self.assertEqual(reading.load_selection(snapshot), [ARTICLE])
            self.assertNotIn('DO-NOT-PUBLISH', snapshot.read_text())

    def test_two_notes_are_atomic_and_limited(self):
        second = {"title": "Second", "url": "https://www.alignmentforum.org/posts/def/title"}
        urls = ['--histre-note', 'https://histre.com/notes/user/one/',
                '--histre-note', 'https://histre.com/notes/user/two/']
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / 'currently-reading.json'
            snapshot.write_text(json.dumps([ARTICLE]), encoding='utf-8')
            before = snapshot.read_bytes()
            with patch.object(reading, 'SELECTION_PATH', snapshot), \
                 patch.object(reading, 'fetch_note', side_effect=[[ARTICLE], URLError('offline')]), \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(reading.main(urls + ['--write']), 1)
            self.assertEqual(snapshot.read_bytes(), before)
            with patch.object(reading, 'SELECTION_PATH', snapshot), \
                 patch.object(reading, 'fetch_note', side_effect=[[ARTICLE], [second]]), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(reading.main(urls + ['--write']), 0)
            self.assertEqual(reading.load_selection(snapshot), [ARTICLE, second])
            before = snapshot.read_bytes()
            with patch.object(reading, 'SELECTION_PATH', snapshot), \
                 patch.object(reading, 'fetch_note') as fetch, \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(reading.main(urls + urls[:2] + ['--write']), 1)
                fetch.assert_not_called()
            self.assertEqual(snapshot.read_bytes(), before)

    def test_feed_host_and_redirects_are_restricted(self):
        reading.check_feed_url('https://histre.com/collection/feed/')
        for url in ('http://histre.com/feed', 'https://example.org/feed',
                    'https://histre.com@evil.example/feed', 'https://histre.com:444/feed'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                reading.check_feed_url(url)

    def test_failed_refresh_retains_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / 'currently-reading.json'
            snapshot.write_text(json.dumps([ARTICLE]), encoding='utf-8')
            before = snapshot.read_bytes()
            with patch.object(reading, 'SELECTION_PATH', snapshot), \
                 patch.object(reading, 'fetch_selection', side_effect=URLError('offline')), \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(reading.main(['--histre-feed', 'https://histre.com/feed', '--write']), 1)
            self.assertEqual(snapshot.read_bytes(), before)

    def test_successful_refresh_writes_only_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / 'currently-reading.json'
            with patch.object(reading, 'SELECTION_PATH', snapshot), \
                 patch.object(reading, 'fetch_selection', return_value=reading.parse_feed(RSS)), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(reading.main(['--histre-feed', 'https://histre.com/feed', '--write']), 0)
            self.assertEqual(reading.load_selection(snapshot), [ARTICLE])
            self.assertNotIn('PRIVATE NOTE', snapshot.read_text())

    def test_site_build_renders_the_selected_links(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(site, 'DEST', directory), \
             patch.object(site, 'load_build_selection', return_value=[ARTICLE]), \
             contextlib.redirect_stdout(io.StringIO()):
            site.engine()
            html = (Path(directory) / 'home.html').read_text()
            self.assertIn('Currently reading</h3>', html)
            self.assertIn('An article &amp; &lt;thoughts&gt;', html)
            self.assertNotIn('CURRENTLY_READING', html)
            self.assertNotIn('PRIVATE NOTE', html)


if __name__ == '__main__':
    unittest.main()
