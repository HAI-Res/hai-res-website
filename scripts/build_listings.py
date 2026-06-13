#!/usr/bin/env python3
"""Scan profiles/, blog_posts/, and music/ for metadata and generate listing pages."""

from __future__ import annotations

import html
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover - optional until a .md source exists
    _yaml = None

try:
    import markdown as _markdown
except ImportError:  # pragma: no cover - optional until a .md source exists
    _markdown = None

MARKDOWN_EXTENSIONS = ("fenced_code", "tables", "attr_list", "md_in_html", "sane_lists")

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_META = ("type", "date", "title", "subtitle")
BLOG_REQUIRED_META = ("excerpt", "thumbnail")

NAV = """
<nav class="site-nav" aria-label="Main">
  <ul>
    <li><a href="./index.html">Home</a></li>
    <li><a href="./about.html">About</a></li>
    <li><a href="./people.html">People</a></li>
    <li><a href="./blog.html">Blog</a></li>
    <li><a href="./publications.html">Publications</a></li>
    <li><a href="./music.html">Music</a></li>
    <li><a href="./join.html">Join</a></li>
  </ul>
</nav>
"""

SITE_BRAND = """<a class="site-brand" href="./index.html"><img src="./assets/images/logo.png" alt="Human-AI Resonance" class="site-brand__logo"></a>"""


@dataclass
class Entry:
    slug: str
    folder: str
    meta: dict[str, str]
    url: str
    source: Path = field(default=Path())
    body_md: str | None = None  # set only for Markdown-sourced entries


def parse_meta(html_path: Path) -> dict[str, str]:
    text = html_path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    for match in re.finditer(
        r'<meta\s+name="hai-res:([^"]+)"\s+content=(["\'])(.*?)\2\s*/?>',
        text,
        re.IGNORECASE | re.DOTALL,
    ):
        meta[match.group(1)] = html.unescape(match.group(3))
    return meta


FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def parse_front_matter(md_path: Path) -> tuple[dict[str, str], str]:
    """Read YAML front matter + Markdown body from an index.md source."""
    if _yaml is None or _markdown is None:
        print(
            f"{md_path.relative_to(ROOT)}: Markdown sources need the 'markdown' and "
            "'PyYAML' packages. Install them with:\n"
            "  python3 -m pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)
    text = md_path.read_text(encoding="utf-8")
    match = FRONT_MATTER_RE.match(text)
    if not match:
        print(
            f"{md_path.relative_to(ROOT)}: missing or malformed YAML front matter "
            "(expected a '---' delimited block at the top of the file).",
            file=sys.stderr,
        )
        sys.exit(1)
    raw_meta = _yaml.safe_load(match.group(1)) or {}
    if not isinstance(raw_meta, dict):
        print(
            f"{md_path.relative_to(ROOT)}: front matter must be a mapping of key: value pairs.",
            file=sys.stderr,
        )
        sys.exit(1)
    meta = {str(k): str(v) for k, v in raw_meta.items()}
    return meta, match.group(2)


def render_markdown(text: str) -> str:
    return _markdown.markdown(text, extensions=list(MARKDOWN_EXTENSIONS))


def wrap_profile_sections(body_html: str) -> str:
    """Wrap each <h2>..</h2> block (and its content) in a .profile-section."""
    chunks = re.split(r"(?=<h2)", body_html)
    out: list[str] = []
    for chunk in chunks:
        stripped = chunk.strip()
        if not stripped:
            continue
        if stripped.startswith("<h2"):
            out.append(f'<section class="profile-section">\n{stripped}\n</section>')
        else:
            out.append(stripped)
    return "\n".join(out)


def resolve_thumbnail(entry: Entry) -> str:
    thumb = entry.meta.get("thumbnail", "./assets/images/placeholder.svg")
    rel = thumb.lstrip("./")
    url = f"./{entry.folder}/{rel}"
    thumb_path = ROOT / entry.folder / rel
    if thumb_path.is_file():
        url = f"{url}?v={int(thumb_path.stat().st_mtime)}"
    return url


def validate_blog_thumbnail(index: Path, child: Path, meta: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if "thumbnail" not in meta:
        errors.append(
            f"{index.relative_to(ROOT)}: blog posts require meta hai-res:thumbnail"
        )
        return errors
    thumb_path = child / meta["thumbnail"].lstrip("./")
    if not thumb_path.is_file():
        errors.append(
            f"{index.relative_to(ROOT)}: thumbnail not found at {thumb_path.relative_to(ROOT)}"
        )
    return errors


BLOG_CHROME_MARKERS = (
    'class="site-header"',
    'href="../../blog.html"',
    'href="../../index.html"',
)


def validate_blog_chrome(index: Path, html_text: str) -> list[str]:
    missing = [m for m in BLOG_CHROME_MARKERS if m not in html_text]
    if not missing:
        return []
    return [
        f"{index.relative_to(ROOT)}: blog posts must keep site navigation "
        f"(missing: {', '.join(missing)}). See templates/snippets/blog_site_header.html"
    ]


def scan_directory(base: Path, url_prefix: str) -> list[Entry]:
    entries: list[Entry] = []
    errors: list[str] = []

    if not base.exists():
        return entries

    for child in sorted(base.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue
        md_source = child / "index.md"
        html_source = child / "index.html"

        body_md: str | None = None
        if md_source.exists():
            source = md_source
            meta, body_md = parse_front_matter(md_source)
            label = ""  # front matter keys are bare (no hai-res: prefix)
        elif html_source.exists():
            source = html_source
            meta = parse_meta(html_source)
            label = "hai-res:"
        else:
            errors.append(f"{child.relative_to(ROOT)}: missing index.md or index.html")
            continue

        missing = [k for k in REQUIRED_META if k not in meta]
        if missing:
            errors.append(
                f"{source.relative_to(ROOT)}: missing {label}{(', ' + label).join(missing)}"
            )
            continue

        if meta.get("type") == "blog":
            missing_blog = [k for k in BLOG_REQUIRED_META if k not in meta]
            if missing_blog:
                errors.append(
                    f"{source.relative_to(ROOT)}: missing {label}{(', ' + label).join(missing_blog)}"
                )
                continue
            errors.extend(validate_blog_thumbnail(source, child, meta))
            # HTML posts must hand-author the site chrome; Markdown posts get it generated.
            if body_md is None:
                chrome_errors = validate_blog_chrome(source, html_source.read_text(encoding="utf-8"))
                if chrome_errors:
                    errors.extend(chrome_errors)
                    continue

        entries.append(
            Entry(
                slug=child.name,
                folder=str(child.relative_to(ROOT)),
                meta=meta,
                url=f"./{url_prefix}/{child.name}/index.html",
                source=source,
                body_md=body_md,
            )
        )

    if errors:
        print("Metadata errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    return entries


def build_blog_payload(blogs: list[Entry]) -> list[dict]:
    entries = sorted(blogs, key=lambda e: e.meta["date"], reverse=True)
    payload = []
    for entry in entries:
        payload.append(
            {
                "slug": entry.slug,
                "url": entry.url,
                "date": entry.meta["date"],
                "title": entry.meta["title"],
                "subtitle": entry.meta["subtitle"],
                "excerpt": entry.meta.get("excerpt", entry.meta["subtitle"]),
                "thumbnail": resolve_thumbnail(entry),
            }
        )
    return payload


def export_blog_json(payload: list[dict]) -> None:
    out_path = ROOT / "data" / "blog.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path.relative_to(ROOT)}")


def sync_home_carousel(payload: list[dict]) -> None:
    index_path = ROOT / "index.html"
    text = index_path.read_text(encoding="utf-8")
    json_str = json.dumps(payload, ensure_ascii=False)
    replacement = f'<script type="application/json" id="blog-carousel-data">{json_str}</script>'
    pattern = r'<script type="application/json" id="blog-carousel-data">.*?</script>'
    if re.search(pattern, text, re.DOTALL):
        text = re.sub(pattern, replacement, text, count=1, flags=re.DOTALL)
    else:
        text = text.replace(
            '  <script src="./assets/js/home-carousel.js"></script>',
            f"  {replacement}\n  <script src=\"./assets/js/home-carousel.js?v=3\"></script>",
        )
    index_path.write_text(text, encoding="utf-8")
    print(f"Wrote {index_path.relative_to(ROOT)} carousel data")


def render_site_footer(
    prefix: str,
    blogs: list[Entry],
    profiles: list[Entry],
    music: list[Entry],
) -> str:
    def href(path: str) -> str:
        if path.startswith("./"):
            return prefix + path[2:]
        return path

    def link_list(entries: list[Entry], label_key: str = "title") -> str:
        if not entries:
            return '<li class="site-footer__empty">Coming soon</li>'
        items = []
        for entry in sorted(entries, key=lambda e: e.meta[label_key].lower()):
            items.append(
                f'<li><a href="{html.escape(href(entry.url))}">'
                f"{html.escape(entry.meta['title'])}</a></li>"
            )
        return "\n        ".join(items)

    blog_entries = sorted(blogs, key=lambda e: e.meta["date"], reverse=True)
    blog_links = link_list(blog_entries) if blog_entries else '<li class="site-footer__empty">Coming soon</li>'

    return f"""<footer class="site-footer">
  <div class="site-footer__inner">
    <div class="site-footer__row site-footer__row--nav">
      <div class="site-footer__col">
        <h3>About Us</h3>
        <ul>
          <li><a href="{href('./about.html')}">About the lab</a></li>
          <li><a href="{href('./join.html')}">Join</a></li>
          <li><a href="{href('./publications.html')}">Publications</a></li>
        </ul>
      </div>
      <div class="site-footer__col">
        <h3>People</h3>
        <ul>
          <li><a href="{href('./people.html')}">All people</a></li>
          {link_list(profiles)}
        </ul>
      </div>
      <div class="site-footer__col">
        <h3>Music</h3>
        <ul>
          <li class="site-footer__empty">Coming soon</li>
        </ul>
      </div>
      <div class="site-footer__col">
        <h3>Concerts</h3>
        <ul>
          <li class="site-footer__empty">Coming soon</li>
        </ul>
      </div>
      <div class="site-footer__col">
        <h3>Blog Posts</h3>
        <ul>
          <li><a href="{href('./blog.html')}">All posts</a></li>
          {blog_links}
        </ul>
      </div>
    </div>
    <div class="site-footer__row site-footer__row--brand">
      <p class="site-footer__wordmark">Human-AI<br>Resonance</p>
    </div>
    <div class="site-footer__row site-footer__row--meta">
      <div class="site-footer__meta">
        <p class="site-footer__mit">MIT</p>
        <p class="site-footer__address">32 Vassar St<br>Cambridge, MA 02139</p>
        <p class="site-footer__contact"><a href="mailto:huangcza@mit.edu">huangcza@mit.edu</a></p>
      </div>
      <a class="site-footer__cta" href="{href('./join.html')}">Join the lab →</a>
    </div>
  </div>
</footer>"""


FOOTER_PATTERN = re.compile(r"<footer class=\"site-footer\">.*?</footer>", re.DOTALL)


def sync_footers(footer_root: str, footer_nested: str) -> None:
    root_pages = [
        ROOT / "index.html",
        ROOT / "about.html",
        ROOT / "join.html",
        ROOT / "publications.html",
    ]
    for path in root_pages:
        if not path.exists():
            continue
        text = FOOTER_PATTERN.sub(footer_root, path.read_text(encoding="utf-8"), count=1)
        path.write_text(text, encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)} footer")

    for base in (ROOT / "profiles", ROOT / "music", ROOT / "blog_posts"):
        if not base.exists():
            continue
        for child in base.iterdir():
            if not child.is_dir() or child.name.startswith("_"):
                continue
            index = child / "index.html"
            if index.exists():
                text = FOOTER_PATTERN.sub(footer_nested, index.read_text(encoding="utf-8"), count=1)
                index.write_text(text, encoding="utf-8")

    snippets = ROOT / "templates" / "snippets"
    snippets.mkdir(parents=True, exist_ok=True)
    (snippets / "site_footer.html").write_text(footer_root + "\n", encoding="utf-8")
    (snippets / "site_footer_nested.html").write_text(footer_nested + "\n", encoding="utf-8")


def page_shell(title: str, active: str, body: str, footer: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <title>{html.escape(title)} · Human-AI Resonance</title>
  <link rel="stylesheet" href="./assets/css/site.css">
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="site-header__inner">
      {SITE_BRAND}
      {NAV}
    </div>
  </header>
  <main id="main">
    {body}
  </main>
  {footer}
  <script src="./assets/js/site.js"></script>
</body>
</html>
"""


NESTED_HEADER = """  <header class="site-header">
    <div class="site-header__inner">
      <a class="site-brand" href="../../index.html"><img src="../../assets/images/logo.png" alt="Human-AI Resonance" class="site-brand__logo"></a>
      <nav class="site-nav" aria-label="Main">
        <ul>
          <li><a href="../../index.html">Home</a></li>
          <li><a href="../../about.html">About</a></li>
          <li><a href="../../people.html">People</a></li>
          <li><a href="../../blog.html">Blog</a></li>
          <li><a href="../../publications.html">Publications</a></li>
          <li><a href="../../music.html">Music</a></li>
          <li><a href="../../join.html">Join</a></li>
        </ul>
      </nav>
    </div>
  </header>"""


def nested_page_shell(
    title: str,
    main_html: str,
    footer: str,
    extra_head: str = "",
    extra_body: str = "",
) -> str:
    head_extra = f"\n  {extra_head}" if extra_head else ""
    body_extra = f"\n  {extra_body}" if extra_body else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} · Human-AI Resonance</title>
  <link rel="stylesheet" href="../../assets/css/site.css">{head_extra}
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
{NESTED_HEADER}
{main_html}
  {footer}
  <script src="../../assets/js/site.js"></script>{body_extra}
</body>
</html>
"""


def render_content_page(entry: Entry, body_html: str, footer: str) -> str:
    title = entry.meta["title"]
    subtitle = entry.meta.get("subtitle", "")
    content_type = entry.meta.get("type")
    folder = ROOT / entry.folder

    extra_head = ""
    if (folder / "styles.css").is_file():
        extra_head = '<link rel="stylesheet" href="styles.css">'
    extra_body = ""
    if (folder / "scripts.js").is_file():
        extra_body = '<script src="scripts.js"></script>'

    if content_type == "profile":
        thumb = html.escape(entry.meta.get("thumbnail", "./assets/photo.svg"))
        website = entry.meta.get("website", "").strip()
        website_html = ""
        if website:
            href = website if "://" in website else f"https://{website}"
            label = re.sub(r"^https?://", "", website).rstrip("/")
            website_html = (
                f'\n        <p class="profile-website">'
                f'<a href="{html.escape(href)}" target="_blank" rel="noopener">'
                f"{html.escape(label)}</a></p>"
            )
        hero = f"""    <a class="profile-back" href="../../people.html">← People</a>

    <div class="hero-bio">
      <div class="hero-bio__photo">
        <img src="{thumb}" alt="{html.escape(title)}">
      </div>
      <div class="profile-hero">
        <h1>{html.escape(title)}</h1>
        <p class="profile-tagline">{html.escape(subtitle)}</p>{website_html}
      </div>
    </div>"""
        main_html = (
            '  <main id="main" class="profile-page">\n'
            f"{hero}\n\n"
            f"{wrap_profile_sections(body_html)}\n"
            "  </main>"
        )
    elif content_type == "music":
        main_html = (
            '  <main id="main" class="profile-page">\n'
            '    <a class="profile-back" href="../../music.html">← Music</a>\n'
            f"    <h1>{html.escape(title)}</h1>\n"
            f'    <p class="profile-tagline">{html.escape(subtitle)}</p>\n'
            f"{body_html}\n"
            "  </main>"
        )
    else:  # blog
        main_html = (
            '  <main id="main">\n'
            '    <a class="profile-back" href="../../blog.html">← Blog</a>\n'
            f"    <h1>{html.escape(title)}</h1>\n"
            f"{body_html}\n"
            "  </main>"
        )

    return nested_page_shell(title, main_html, footer, extra_head, extra_body)


GITIGNORE_START = "# >>> generated from index.md (managed by scripts/build_listings.py)"
GITIGNORE_END = "# <<< generated from index.md"


def update_gitignore(generated: list[str]) -> None:
    path = ROOT / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    block_lines = [GITIGNORE_START, *sorted(generated), GITIGNORE_END]
    block = "\n".join(block_lines) + "\n"

    pattern = re.compile(
        re.escape(GITIGNORE_START) + r".*?" + re.escape(GITIGNORE_END) + r"\n?",
        re.DOTALL,
    )
    if pattern.search(text):
        text = pattern.sub(block if generated else "", text)
    elif generated:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\n" + block
    path.write_text(text, encoding="utf-8")
    if generated:
        print(f"Updated {path.relative_to(ROOT)} ({len(generated)} generated page(s))")


def generate_markdown_pages(entries: list[Entry], footer_nested: str) -> None:
    generated: list[str] = []
    for entry in entries:
        if entry.body_md is None:
            continue
        body_html = render_markdown(entry.body_md)
        page = render_content_page(entry, body_html, footer_nested)
        out_path = ROOT / entry.folder / "index.html"
        out_path.write_text(page, encoding="utf-8")
        generated.append(f"{entry.folder}/index.html")
        print(f"Wrote {out_path.relative_to(ROOT)} (from index.md)")
    update_gitignore(generated)


def render_people(entries: list[Entry], footer: str) -> str:
    entries = sorted(entries, key=lambda e: e.meta["title"].lower())
    cards = []
    for entry in entries:
        thumb_src = resolve_thumbnail(entry)
        cards.append(
            f"""<a class="person-card" href="{html.escape(entry.url)}">
  <div class="person-card__photo">
    <img src="{html.escape(thumb_src)}" alt="">
  </div>
  <h4>{html.escape(entry.meta['title'])}</h4>
  <h5>{html.escape(entry.meta['subtitle'])}</h5>
</a>"""
        )
    grid = "\n".join(cards) if cards else "<p>No profiles yet.</p>"
    body = f"""<p class="section-label">Community</p>
<h1>People</h1>
<p class="page-lede">Researchers, students, and collaborators in the Human-AI Resonance lab.</p>
<div class="card-grid">
{grid}
</div>"""
    return page_shell("People", "people", body, footer)


def render_blog(entries: list[Entry], footer: str) -> str:
    entries = sorted(entries, key=lambda e: e.meta["date"], reverse=True)
    items = []
    for entry in entries:
        excerpt = entry.meta.get("excerpt", entry.meta["subtitle"])
        thumb_src = resolve_thumbnail(entry)
        items.append(
            f"""<li class="blog-list__item">
  <a href="{html.escape(entry.url)}" class="blog-list__link">
    <div class="blog-list__thumb">
      <img src="{html.escape(thumb_src)}" alt="">
    </div>
    <div class="blog-list__text">
      <div class="blog-list__date">{html.escape(entry.meta['date'])}</div>
      <h3>{html.escape(entry.meta['title'])}</h3>
      <p>{html.escape(excerpt)}</p>
    </div>
  </a>
</li>"""
        )
    listing = "\n".join(items) if items else "<li>No blog posts yet.</li>"
    body = f"""<p class="section-label">News &amp; writing</p>
<h1>Blog</h1>
<p class="page-lede">Practice-based accounts, project notes, and lab updates.</p>
<ul class="blog-list">
{listing}
</ul>"""
    return page_shell("Blog", "blog", body, footer)


def render_music(entries: list[Entry], footer: str) -> str:
    body = """<p class="section-label">Compositions</p>
<h1>Music</h1>
<p class="page-lede">Coming soon.</p>"""
    return page_shell("Music", "music", body, footer)


def main() -> None:
    profiles = scan_directory(ROOT / "profiles", "profiles")
    blogs = scan_directory(ROOT / "blog_posts", "blog_posts")
    music = scan_directory(ROOT / "music", "music")

    blog_payload = build_blog_payload(blogs)
    export_blog_json(blog_payload)
    sync_home_carousel(blog_payload)

    footer_root = render_site_footer("./", blogs, profiles, music)
    footer_nested = render_site_footer("../../", blogs, profiles, music)

    generate_markdown_pages(profiles + blogs + music, footer_nested)

    sync_footers(footer_root, footer_nested)

    outputs = {
        ROOT / "people.html": render_people(profiles, footer_root),
        ROOT / "blog.html": render_blog(blogs, footer_root),
        ROOT / "music.html": render_music(music, footer_root),
    }

    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
