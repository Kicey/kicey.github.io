"""Build-time SEO metadata for the MkDocs site.

The hook keeps metadata close to the content while avoiding repetitive front
matter on older notes. Explicit front matter always wins over derived values.
"""

from __future__ import annotations

from html import unescape
from pathlib import Path
import re
import subprocess
from urllib.parse import urljoin


_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_IMAGE_RE = re.compile(r"!\[[^]]*]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^]]+)]\([^)]*\)")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MARKUP_RE = re.compile(r"(?:^|\s)[#>*_`~]+|[*_`~]+(?:$|\s)")


def _absolute_url(site_url: str, path: str) -> str:
    return urljoin(site_url.rstrip("/") + "/", path)


def _plain_text(value: object) -> str:
    text = unescape(str(value or ""))
    text = _IMAGE_RE.sub("", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _HTML_TAG_RE.sub("", text)
    text = _MARKUP_RE.sub(" ", text)
    return " ".join(text.split())


def _truncate(text: str, limit: int = 160) -> str:
    if len(text) <= limit:
        return text
    shortened = text[: limit + 1].rsplit(" ", 1)[0]
    if len(shortened) < limit // 2:
        shortened = text[:limit]
    return shortened.rstrip(" ,.;:，。；：") + "…"


def _first_paragraph(markdown: str) -> str:
    markdown = _HTML_COMMENT_RE.sub("", markdown)
    paragraphs: list[str] = []
    current: list[str] = []
    in_fence = False

    for line in markdown.splitlines():
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if stripped.startswith(("#", "|", "!!!", "???", "{")):
            continue
        if re.match(r"^[-+*]\s+", stripped) or re.match(r"^\d+[.)]\s+", stripped):
            continue
        current.append(stripped)

    if current:
        paragraphs.append(" ".join(current))

    for paragraph in paragraphs:
        plain = _plain_text(paragraph)
        if len(plain) >= 24:
            return plain
    return ""


def _detect_language(markdown: str) -> str:
    sample = _plain_text(markdown[:8000])
    cjk_count = len(_CJK_RE.findall(sample))
    latin_count = len(re.findall(r"[A-Za-z]", sample))
    return "zh-Hans" if cjk_count >= 12 and cjk_count * 2 >= latin_count else "en"


def _git_updated(config, page) -> str | None:
    src_uri = page.file.src_uri
    src_path = Path(config.docs_dir, src_uri)
    if not src_path.is_file():
        return None

    repository = Path(config.config_file_path).resolve().parent
    relative_path = src_path.resolve().relative_to(repository)
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", str(relative_path)],
        cwd=repository,
        capture_output=True,
        check=False,
        text=True,
    )
    updated = result.stdout.strip()
    return updated or None


def _translation_alternates(page, files, config) -> list[dict[str, str]]:
    src_uri = page.file.src_uri
    prefix = "blog/posts/"
    zh_prefix = f"{prefix}zh/"

    if src_uri.startswith(zh_prefix):
        counterpart_uri = prefix + src_uri.removeprefix(zh_prefix)
        own_lang, counterpart_lang = "zh-Hans", "en"
    elif src_uri.startswith(prefix) and "/" not in src_uri.removeprefix(prefix):
        counterpart_uri = zh_prefix + src_uri.removeprefix(prefix)
        own_lang, counterpart_lang = "en", "zh-Hans"
    else:
        return []

    counterpart = next(
        (candidate for candidate in files if candidate.src_uri == counterpart_uri),
        None,
    )
    if counterpart is None:
        return []

    return [
        {"lang": own_lang, "href": _absolute_url(config.site_url, page.url)},
        {
            "lang": counterpart_lang,
            "href": _absolute_url(config.site_url, counterpart.url),
        },
    ]


def on_page_markdown(markdown, page, config, files):
    """Derive only metadata that the page author did not specify."""

    inferred_language = (
        "zh-Hans"
        if page.file.src_uri.startswith("blog/posts/zh/")
        else _detect_language(markdown)
    )
    language = page.meta.setdefault("lang", inferred_language)

    if not page.meta.get("description"):
        summary = _plain_text(page.meta.get("summary"))
        paragraph = _first_paragraph(markdown)
        is_homepage = page.file.src_uri == "index.md" or page.url in ("", "index.html")
        if is_homepage:
            description = config.site_description
        else:
            description = summary or paragraph
        if not description:
            suffix = "kicey 的技术笔记" if language.startswith("zh") else "Technical notes from kicey's blog"
            description = f"{page.title}: {suffix}."
        page.meta["description"] = _truncate(description)

    if not page.meta.get("updated"):
        updated = _git_updated(config, page)
        if updated:
            page.meta["updated"] = updated

    alternates = _translation_alternates(page, files, config)
    if alternates:
        page.meta.setdefault("alternates", alternates)

    return markdown


def on_post_page(output, page, config):
    """Material has a global UI language; correct the document language per page."""

    language = page.meta.get("lang", "en") if page.meta else "en"
    return re.sub(
        r'(<html\s+lang=")[^"]+("[^>]*>)',
        rf"\g<1>{language}\g<2>",
        output,
        count=1,
    )
