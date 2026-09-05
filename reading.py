"""Render an explicit reading selection; import Histre shared notes or collection feeds."""

import argparse
import json
import sys
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree


SELECTION_PATH = Path(__file__).resolve().parent / "data/currently-reading.json"
FEED_CONFIG_PATH = Path(__file__).resolve().parent / "data/reading-feed.json"
MAX_FEED_BYTES = 1024 * 1024


def validate_selection(items):
    """Keep only title/URL pairs. Every item must have been explicitly selected."""
    if not isinstance(items, list) or len(items) > 2:
        raise ValueError("Currently reading must contain a list of at most two links.")
    selected = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each reading selection needs a title and URL.")
        title, url = item.get("title"), item.get("url")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Each reading selection needs a nonempty title.")
        if not isinstance(url, str) or any(c.isspace() or ord(c) < 32 for c in url):
            raise ValueError("Each reading URL must be an absolute HTTP(S) URL.")
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Each reading URL must be an absolute HTTP(S) URL without credentials.")
        if url in seen:
            raise ValueError("Choose distinct reading links.")
        selected.append({"title": title.strip(), "url": url})
        seen.add(url)
    return selected


def load_selection(path=SELECTION_PATH):
    return validate_selection(json.loads(Path(path).read_text(encoding="utf-8")))


def save_selection(items):
    output = json.dumps(validate_selection(items), ensure_ascii=False, indent=2) + "\n"
    temporary = SELECTION_PATH.with_suffix(".json.tmp")
    temporary.write_text(output, encoding="utf-8")
    temporary.replace(SELECTION_PATH)


def load_build_selection(offline=False):
    """Refresh the configured public collection at build time; keep a local fallback."""
    if offline or not FEED_CONFIG_PATH.exists():
        return load_selection(SELECTION_PATH)
    try:
        config = json.loads(FEED_CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(config, dict) or not isinstance(config.get("url"), str):
            raise ValueError("Reading feed configuration needs a URL.")
        titles = config.get("titles", {})
        if (not isinstance(titles, dict)
                or any(not isinstance(title, str) or not title.strip() for title in titles.values())):
            raise ValueError("Reading title overrides must be nonempty strings.")
        selected = fetch_selection(config["url"], latest=True)
        selected = validate_selection([
            {"title": titles.get(item["url"], item["title"]), "url": item["url"]}
            for item in selected
        ])
        save_selection(selected)
        print(f"Currently reading: refreshed {len(selected)} links from Histre.")
        return selected
    except (OSError, URLError, ValueError, ElementTree.ParseError) as error:
        # Never turn an unavailable or malformed feed into an empty reading list.
        print(f"Reading feed refresh failed ({type(error).__name__}); using the saved selection.",
              file=sys.stderr)
        return load_selection(SELECTION_PATH)


def render_selection(items):
    items = validate_selection(items)
    if not items:
        return ""
    links = "\n".join(
        f'      <li><a href="{escape(item["url"], quote=True)}">{escape(item["title"])}</a></li>'
        for item in items
    )
    return (
        '<section class="currently-reading" aria-labelledby="currently-reading-title">\n'
        '    <h3 id="currently-reading-title">Currently reading</h3>\n'
        '    <ul class="nobull">\n'
        f'{links}\n'
        '    </ul>\n'
        '  </section>'
    )


def parse_feed(content, latest=False):
    """Read RSS 2.0 or Atom; never import descriptions, notes, or reading history."""
    if len(content) > MAX_FEED_BYTES:
        raise ValueError("Reading feed exceeds the 1 MiB limit.")
    root = ElementTree.fromstring(content)
    if root.tag == "rss" and root.find("channel") is not None:
        items = [
            {"title": item.findtext("title", ""), "url": item.findtext("link", "").strip()}
            for item in root.findall("./channel/item")
        ]
    elif root.tag == "{http://www.w3.org/2005/Atom}feed":
        ns = {"a": "http://www.w3.org/2005/Atom"}
        items = []
        for entry in root.findall("a:entry", ns):
            link = next((link for link in entry.findall("a:link", ns)
                         if link.get("rel", "alternate") == "alternate"), None)
            items.append({"title": entry.findtext("a:title", "", ns),
                          "url": link.get("href", "").strip() if link is not None else ""})
    else:
        raise ValueError("Expected an RSS or Atom feed, not a collection page or login screen.")
    if latest:
        # Preserve Histre's collection order: pubDate did not match this order
        # in the verified live feed, so sorting by it would show different links.
        selected, seen = [], set()
        for item in items:
            item = validate_selection([item])[0]
            if urlsplit(item["url"]).hostname in ("histre.com", "www.histre.com"):
                continue
            if item["url"] not in seen:
                selected.append(item)
                seen.add(item["url"])
        return validate_article_selection(selected[:2])
    return validate_article_selection(items)


def validate_article_selection(items):
    # Do not silently choose among a larger collection or publish Histre note links.
    selected = validate_selection(items)
    if any(urlsplit(item["url"]).hostname in ("histre.com", "www.histre.com") for item in selected):
        raise ValueError("Imported links point to Histre. Use the original article URLs in data/currently-reading.json.")
    return selected


class HistreNoteParser(HTMLParser):
    """Extract only Histre's original-article title link, never note contents."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "note-title" in (attrs.get("class") or "").split():
            if self.current is not None:
                raise ValueError("Malformed Histre article link.")
            self.current = {"title": "", "url": (attrs.get("href") or "").strip()}

    def handle_data(self, data):
        if self.current is not None:
            self.current["title"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            self.current["title"] = " ".join(self.current["title"].split())
            self.items.append(self.current)
            self.current = None


def parse_note(content):
    if len(content) > MAX_FEED_BYTES:
        raise ValueError("Shared note exceeds the 1 MiB limit.")
    parser = HistreNoteParser()
    parser.feed(content.decode("utf-8"))
    parser.close()
    if parser.current is not None or len(parser.items) != 1:
        raise ValueError("Expected one accessible shared Histre note with an original article link.")
    return validate_article_selection(parser.items)


def check_feed_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != "histre.com"
            or parsed.port not in (None, 443) or parsed.username or parsed.password):
        raise ValueError("Use an HTTPS link on histre.com without account credentials.")


class HistreRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_feed_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_content(url, accept):
    check_feed_url(url)
    request = Request(url, headers={"User-Agent": "m3ru-currently-reading/1.0",
                                   "Accept": accept})
    with build_opener(HistreRedirects()).open(request, timeout=15) as response:
        return response.read(MAX_FEED_BYTES + 1)


def fetch_selection(url, latest=False):
    return parse_feed(fetch_content(url, "application/rss+xml, application/atom+xml"), latest=latest)


def fetch_note(url):
    check_feed_url(url)
    parts = urlsplit(url).path.strip("/").split("/")
    if len(parts) != 3 or parts[0] != "notes" or not all(parts):
        raise ValueError("Use the share link for a single Histre note, not an account or collection page.")
    return parse_note(fetch_content(url, "text/html"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--histre-feed", metavar="URL", help="RSS URL of the deliberately selected public collection")
    source.add_argument("--histre-note", metavar="URL", action="append",
                        help="shared Histre note URL; repeat for a second selection (replaces the snapshot)")
    source.add_argument("--feed-file", type=Path, help="preview or import a saved RSS/Atom feed")
    parser.add_argument("--latest", action="store_true",
                        help="take the first two distinct non-Histre article links in feed order")
    parser.add_argument("--write", action="store_true", help="replace data/currently-reading.json after validation")
    args = parser.parse_args(argv)
    if args.latest and args.histre_note:
        parser.error("--latest applies to a feed, not individual shared notes")
    try:
        if args.histre_feed:
            selected = fetch_selection(args.histre_feed, latest=args.latest)
        elif args.histre_note:
            if len(args.histre_note) > 2:
                raise ValueError("Choose at most two shared Histre notes.")
            selected = validate_selection([
                item for url in args.histre_note for item in fetch_note(url)
            ])
        else:
            with args.feed_file.open("rb") as source_file:
                selected = parse_feed(source_file.read(MAX_FEED_BYTES + 1), latest=args.latest)
        output = json.dumps(selected, ensure_ascii=False, indent=2) + "\n"
        if args.write:
            # A failed fetch/parse cannot overwrite the last successful selection.
            save_selection(selected)
            print(f"Saved {len(selected)} selected links. Run python main.py to rebuild.")
        else:
            print(output, end="")
    except (OSError, URLError, ValueError, ElementTree.ParseError) as error:
        print(f"Reading selection was not updated: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
