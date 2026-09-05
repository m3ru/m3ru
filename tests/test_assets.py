import contextlib
import io
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main as site


class AssetTests(unittest.TestCase):
    def test_asset_versions_match_their_contents(self):
        for path in ('links/main.css', 'links/theme.js'):
            with self.subTest(path=path):
                version = sha256((site.ASSET_ROOT / path).read_bytes()).hexdigest()[:12]
                self.assertEqual(site.versioned_asset(path), f'../{path}?v={version}')

    def test_changed_content_gets_a_new_url_only_for_that_asset(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(site, 'ASSET_ROOT', Path(directory)):
            assets = Path(directory) / 'links'
            assets.mkdir()
            css = assets / 'main.css'
            css.write_text('body { display: block; }')
            (assets / 'theme.js').write_text('/* theme */')
            old_css = site.versioned_asset('links/main.css')
            old_js = site.versioned_asset('links/theme.js')
            self.assertEqual(site.versioned_asset('links/main.css'), old_css)
            css.write_text('body { display: grid; }')
            self.assertNotEqual(site.versioned_asset('links/main.css'), old_css)
            self.assertEqual(site.versioned_asset('links/theme.js'), old_js)

    def test_every_generated_page_uses_versioned_css_and_js(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(site, 'DEST', directory), \
             patch.object(site, 'load_build_selection', return_value=[]), \
             contextlib.redirect_stdout(io.StringIO()):
            site.engine(offline=True)
            pages = list(Path(directory).glob('*.html'))
            self.assertGreater(len(pages), 1)
            for page in pages:
                with self.subTest(page=page.name):
                    html = page.read_text()
                    self.assertIn(f"href='{site.versioned_asset('links/main.css')}'", html)
                    self.assertIn(f"src='{site.versioned_asset('links/theme.js')}'", html)
                    self.assertNotIn("href='../links/main.css'", html)
                    self.assertNotIn("src='../links/theme.js'", html)


if __name__ == '__main__':
    unittest.main()
