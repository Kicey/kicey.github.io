#!/usr/bin/env python3
"""Validate the generated site's crawlability and search metadata."""

from __future__ import annotations

from collections import Counter
from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import urljoin
import xml.etree.ElementTree as ET


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.alternates: list[tuple[str, str]] = []
        self.canonical = ""
        self.h1_count = 0
        self.html_lang = ""
        self.json_ld: list[str] = []
        self.links: list[str] = []
        self.meta: dict[str, str] = {}
        self.title = ""
        self._in_json_ld = False
        self._in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if tag == "html":
            self.html_lang = values.get("lang", "")
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "meta":
            key = values.get("name") or values.get("property")
            if key:
                self.meta[key] = values.get("content", "")
        elif tag == "link":
            rel = values.get("rel", "")
            if rel == "canonical":
                self.canonical = values.get("href", "")
            elif rel == "alternate" and values.get("hreflang"):
                self.alternates.append(
                    (values["hreflang"], values.get("href", ""))
                )
        elif tag == "a" and values.get("href"):
            self.links.append(values["href"])
        elif tag == "script" and values.get("type") == "application/ld+json":
            self._in_json_ld = True
            self.json_ld.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_json_ld:
            self._in_json_ld = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_json_ld:
            self.json_ld[-1] += data


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    site_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "site").resolve()
    if not site_dir.is_dir():
        print(f"SEO check failed: site directory does not exist: {site_dir}")
        return 2

    errors: list[str] = []
    pages: dict[str, tuple[Path, PageParser]] = {}
    title_counts: Counter[str] = Counter()

    for html_file in site_dir.rglob("*.html"):
        parser = PageParser()
        parser.feed(html_file.read_text(encoding="utf-8"))
        if not parser.canonical:
            continue
        if parser.canonical in pages:
            fail(errors, f"duplicate canonical URL: {parser.canonical}")
            continue
        pages[parser.canonical] = (html_file, parser)
        title_counts[parser.title.strip()] += 1

    for canonical, (html_file, parser) in pages.items():
        label = html_file.relative_to(site_dir)
        if not parser.title.strip():
            fail(errors, f"{label}: missing title")
        if parser.h1_count != 1:
            fail(errors, f"{label}: expected one h1, found {parser.h1_count}")
        if not parser.html_lang:
            fail(errors, f"{label}: missing html lang")
        if not parser.meta.get("description"):
            fail(errors, f"{label}: missing meta description")
        for key in (
            "og:title",
            "og:description",
            "og:url",
            "og:image",
            "twitter:card",
            "twitter:title",
            "twitter:description",
            "twitter:image",
        ):
            if not parser.meta.get(key):
                fail(errors, f"{label}: missing {key}")
        if parser.meta.get("og:url") != canonical:
            fail(errors, f"{label}: og:url does not match canonical")

        structured_types: set[str] = set()
        for block in parser.json_ld:
            try:
                structured_data = json.loads(block)
                structured_type = structured_data.get("@type")
                if isinstance(structured_type, str):
                    structured_types.add(structured_type)
            except json.JSONDecodeError as error:
                fail(errors, f"{label}: invalid JSON-LD: {error}")
        if canonical == "https://kicey.github.io/":
            if "WebSite" not in structured_types:
                fail(errors, f"{label}: missing WebSite JSON-LD")
        else:
            if "BreadcrumbList" not in structured_types:
                fail(errors, f"{label}: missing BreadcrumbList JSON-LD")
        if parser.meta.get("og:type") == "article" and "BlogPosting" not in structured_types:
            fail(errors, f"{label}: missing BlogPosting JSON-LD")

    for title, count in title_counts.items():
        if title and count > 1:
            fail(errors, f"duplicate title on {count} pages: {title}")

    incoming: Counter[str] = Counter()
    for source, (_, parser) in pages.items():
        for href in parser.links:
            destination = urljoin(source, href).split("#", 1)[0].split("?", 1)[0]
            if destination in pages and destination != source:
                incoming[destination] += 1

    homepage = "https://kicey.github.io/"
    for canonical in sorted(pages):
        if canonical != homepage and incoming[canonical] == 0:
            fail(errors, f"page has no internal incoming link: {canonical}")

    for source, (_, parser) in pages.items():
        source_lang = parser.html_lang
        for alternate_lang, alternate_url in parser.alternates:
            if alternate_url not in pages:
                fail(errors, f"{source}: hreflang target is not canonical: {alternate_url}")
                continue
            target_parser = pages[alternate_url][1]
            reciprocal = (source_lang, source) in target_parser.alternates
            if not reciprocal:
                fail(errors, f"{source}: non-reciprocal hreflang target {alternate_url}")
            if target_parser.html_lang != alternate_lang:
                fail(errors, f"{source}: hreflang language does not match {alternate_url}")

    sitemap_path = site_dir / "sitemap.xml"
    if not sitemap_path.is_file():
        fail(errors, "missing sitemap.xml")
    else:
        namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        root = ET.parse(sitemap_path).getroot()
        sitemap_urls: set[str] = set()
        for url_node in root.findall("s:url", namespace):
            location_node = url_node.find("s:loc", namespace)
            if location_node is None or not location_node.text:
                fail(errors, "sitemap entry is missing loc")
                continue
            location = location_node.text.strip()
            sitemap_urls.add(location)
            lastmod_node = url_node.find("s:lastmod", namespace)
            if lastmod_node is not None and lastmod_node.text:
                try:
                    modified = date.fromisoformat(lastmod_node.text.strip()[:10])
                    if modified > date.today():
                        fail(errors, f"future sitemap lastmod: {location}")
                except ValueError:
                    fail(errors, f"invalid sitemap lastmod: {location}")

        missing = set(pages) - sitemap_urls
        extra = sitemap_urls - set(pages)
        for location in sorted(missing):
            fail(errors, f"canonical page missing from sitemap: {location}")
        for location in sorted(extra):
            fail(errors, f"non-canonical URL in sitemap: {location}")

    if errors:
        print(f"SEO check failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"SEO check passed: {len(pages)} canonical pages, "
        "complete metadata, crawlable internal links, and a consistent sitemap."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
