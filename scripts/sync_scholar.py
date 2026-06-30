#!/usr/bin/env python3
"""Fetch Google Scholar publications and generate publications.html."""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
YEAR_RE = re.compile(r"\d{4}")
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
THUMB_META_RE = re.compile(
    r'<meta\s+name="hai-res:thumbnail"\s+content=(["\'])(.*?)\1\s*/?>',
    re.IGNORECASE | re.DOTALL,
)
CONFIG_PATH = ROOT / "data" / "scholar_config.json"
PUBLICATIONS_PATH = ROOT / "data" / "publications.json"
OVERRIDES_PATH = ROOT / "data" / "publications_overrides.json"
OUTPUT_PATH = ROOT / "publications.html"

SITE_BRAND = """<a class="site-brand" href="./index.html"><img src="./assets/images/logo.png" alt="Human-AI Resonance" class="site-brand__logo"></a>"""

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


def load_json(path: Path) -> dict | list:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def format_authors(authors: str) -> str:
    if not authors:
        return ""
    return authors.replace(" and ", ", ")


def scholar_citations_url(scholar_id: str) -> str:
    if not scholar_id:
        return ""
    return f"https://scholar.google.com/scholar?oi=bibs&hl=en&cites={scholar_id}"


ARXIV_ID_RE = re.compile(r"arxiv[:\s]*(\d{4}\.\d{4,5})", re.IGNORECASE)


def paper_url_from_bib(bib: dict) -> str:
    for key in ("url", "link", "ee", "eprint"):
        value = str(bib.get(key, "")).strip()
        if value.startswith("http"):
            return value
    haystack = " ".join(str(bib.get(field, "")) for field in ("journal", "citation", "venue"))
    match = ARXIV_ID_RE.search(haystack)
    if match:
        return f"https://arxiv.org/abs/{match.group(1)}"
    return ""


def attach_paper_url(pub: dict, overrides: dict) -> dict:
    if pub.get("scholar_url") or pub.get("paper_url"):
        return pub
    paper_map = overrides.get("paper", {})
    scholar_id = pub.get("scholar_id", "")
    title = pub.get("title", "")
    paper_url = paper_map.get(scholar_id) or paper_map.get(title) or ""
    if paper_url:
        return {**pub, "scholar_url": paper_url}
    return pub


def fetch_scholar(user_id: str) -> list[dict] | None:
    try:
        from scholarly import scholarly  # type: ignore
    except ImportError:
        print("scholarly not installed; using existing publications.json", file=sys.stderr)
        return None

    try:
        author = scholarly.search_author_id(user_id)
        author = scholarly.fill(author, sections=["publications"])
        publications = []
        for pub in author.get("publications", []):
            filled = scholarly.fill(pub)
            bib = filled.get("bib", {})
            venue = (
                bib.get("venue")
                or bib.get("journal")
                or bib.get("booktitle")
                or bib.get("publisher")
                or ""
            )
            scholar_url = (
                filled.get("pub_url")
                or filled.get("eprint_url")
                or paper_url_from_bib(bib)
                or ""
            )
            publications.append(
                {
                    "title": bib.get("title", "Untitled"),
                    "authors": bib.get("author", ""),
                    "venue": venue,
                    "year": str(bib.get("pub_year", "")),
                    "citations": filled.get("num_citations", 0),
                    "scholar_url": scholar_url,
                    "scholar_id": filled.get("author_pub_id", ""),
                    "citations_url": scholar_citations_url(filled.get("author_pub_id", "")),
                }
            )
        return publications
    except Exception as exc:  # noqa: BLE001
        print(f"Scholar fetch failed: {exc}", file=sys.stderr)
        return None


def seed_publications() -> list[dict]:
    return [
        {"title": "Music Transformer", "authors": "Cheng-Zhi Anna Huang, Ashish Vaswani, Jakob Uszkoreit, Ian Simon, Curtis Hawthorne, Noam Shazeer, Andrew M Dai, Matthew D Hoffman, Monica Dinculescu, Douglas Eck", "venue": "ICLR, 2019", "year": "2019", "citations": 0, "scholar_url": ""},
        {"title": "The Bach Doodle: Approachable Music Composition with Machine Learning at Scale", "authors": "Cheng-Zhi Anna Huang, Curtis Hawthorne, Adam Roberts, Monica Dinculescu, James Wexler, Leon Hong, Jacob Howcroft", "venue": "ISMIR, 2019", "year": "2019", "citations": 0, "scholar_url": ""},
        {"title": "Coconet: Counterpoint by Convolution", "authors": "Cheng-Zhi Anna Huang, Tim Cooijmans, Adam Roberts, Aaron Courville, Douglas Eck", "venue": "ISMIR, 2017", "year": "2017", "citations": 0, "scholar_url": ""},
        {"title": "AI Song Contest: Human-AI Co-Creation in Songwriting", "authors": "Cheng-Zhi Anna Huang, Hendrik Vincent Koops, Ed Newton-Rex, Monica Dinculescu, Carrie J Cai", "venue": "ISMIR, 2020", "year": "2020", "citations": 0, "scholar_url": ""},
        {"title": "MIDI-DDSP: Detailed Control of Musical Performance via Hierarchical Modeling", "authors": "Yusong Wu, Ethan Manilow, Yi Deng, Rigel Swavely, Kyle Kastner, Tim Cooijmans, Aaron Courville, Cheng-Zhi Anna Huang, Jesse Engel", "venue": "ICLR, 2022", "year": "2022", "citations": 0, "scholar_url": ""},
        {"title": "Expressive Communication: A Common Framework for Evaluating Developments in Generative Models and Steering Interfaces", "authors": "Ryan Louie, Jesse Engel, Cheng-Zhi Anna Huang", "venue": "IUI, 2022", "year": "2022", "citations": 0, "scholar_url": ""},
        {"title": "Editorial for TISMIR Special Collection: AI and Musical Creativity", "authors": "Bob LT Sturm, Alexandra L Uitdenbogerd, Hendrik Vincent Koops, Cheng-Zhi Anna Huang", "venue": "TISMIR, 2021", "year": "2021", "citations": 0, "scholar_url": ""},
        {"title": "Compositional Steering of Music Transformers", "authors": "Halley Young, Vincent Dumoulin, Pablo S Castro, Jesse Engel, Cheng-Zhi Anna Huang", "venue": "HAI-GEN Workshop @ IUI, 2021", "year": "2021", "citations": 0, "scholar_url": ""},
        {"title": "Improving Source Separation by Explicitly Modeling Dependencies Between Sources", "authors": "Ethan Manilow, Curtis Hawthorne, Cheng-Zhi Anna Huang, Bryan Pardo, Jesse Engel", "venue": "ICASSP, 2021", "year": "2021", "citations": 0, "scholar_url": ""},
        {"title": "Cococo: Novice-AI Music Co-Creation via AI-Steering Tools for Deep Generative Models", "authors": "Ryan Louie, Andy Coenen, Cheng-Zhi Anna Huang, Michael Terry, Carrie J Cai", "venue": "CHI, 2020", "year": "2020", "citations": 0, "scholar_url": ""},
        {"title": "Wave2Midi2Wave: Enabling Factorized Piano Music Modeling and Generation with the MAESTRO Dataset", "authors": "Curtis Hawthorne, Andriy Stasyuk, Adam Roberts, Ian Simon, Cheng-Zhi Anna Huang, Sander Dieleman, Erich Elsen, Jesse Engel, Douglas Eck", "venue": "ICLR, 2019", "year": "2019", "citations": 0, "scholar_url": ""},
        {"title": "Infilling Piano Performances", "authors": "Daphne Ippolito, Cheng-Zhi Anna Huang, Curtis Hawthorne, Douglas Eck", "venue": "NeurIPS Workshop on Machine Learning for Creativity and Design, 2018", "year": "2018", "citations": 0, "scholar_url": ""},
        {"title": "Transformer-NADE for Piano Performances", "authors": "Curtis Hawthorne, Cheng-Zhi Anna Huang, Daphne Ippolito, Douglas Eck", "venue": "NeurIPS Workshop on Machine Learning for Creativity and Design, 2018", "year": "2018", "citations": 0, "scholar_url": ""},
        {"title": "Chordripple: Recommending Chords to Help Novice Composers Go Beyond the Ordinary", "authors": "Cheng-Zhi Anna Huang, David Duvenaud, Krzysztof Z Gajos", "venue": "IUI, 2016", "year": "2016", "citations": 0, "scholar_url": ""},
        {"title": "Active Learning of Intuitive Control Knobs for Synthesizers using Gaussian Processes", "authors": "Cheng-Zhi Anna Huang, David Duvenaud, Kenneth C Arnold, Brenton Partridge, Josiah W Oberholtzer, Krzysztof Z Gajos", "venue": "IUI, 2014", "year": "2014", "citations": 0, "scholar_url": ""},
        {"title": "Melodic Variations: Toward Cross-Cultural Transformation", "authors": "Cheng-Zhi Anna Huang", "venue": "Master's Thesis, MIT Media Lab, 2008", "year": "2008", "citations": 0, "scholar_url": ""},
        {"title": "Palestrina Pal: a Grammar Checker for Music Compositions in the Style of Palestrina", "authors": "Cheng-Zhi Anna Huang, Elaine Chew", "venue": "Conference on Understanding and Creating Music, 2005", "year": "2005", "citations": 0, "scholar_url": ""},
    ]


def publication_year(pub: dict) -> int:
    for field in ("year", "venue"):
        value = str(pub.get(field, ""))
        match = YEAR_RE.search(value)
        if match:
            return int(match.group())
    return 0


def is_valid_publication_year(year: int) -> bool:
    if not year:
        return True
    current_year = datetime.now(timezone.utc).year
    return 1970 <= year <= current_year + 1


def thumbnail_from_spotlight(spotlight_url: str) -> str:
    match = re.search(r"blog_posts/([^/]+)", spotlight_url)
    if not match:
        return ""
    slug = match.group(1)
    folder = ROOT / "blog_posts" / slug
    thumb = ""
    md_path = folder / "index.md"
    html_path = folder / "index.html"
    if md_path.is_file():
        text = md_path.read_text(encoding="utf-8")
        front_matter = FRONT_MATTER_RE.match(text)
        if front_matter:
            for line in front_matter.group(1).splitlines():
                if line.strip().startswith("thumbnail:"):
                    thumb = line.split(":", 1)[1].strip().strip("'\"")
                    break
    elif html_path.is_file():
        meta_match = THUMB_META_RE.search(html_path.read_text(encoding="utf-8"))
        if meta_match:
            thumb = html.unescape(meta_match.group(2))
    if not thumb:
        return ""
    rel = thumb.lstrip("./")
    asset_path = folder / rel
    url = f"./blog_posts/{slug}/{rel}"
    if asset_path.is_file():
        url = f"{url}?v={int(asset_path.stat().st_mtime)}"
    return url


def attach_thumbnail(pub: dict, overrides: dict) -> dict:
    title = pub.get("title", "")
    thumb_map = overrides.get("thumbnail", {})
    if pub.get("thumbnail"):
        return pub
    if title in thumb_map:
        return {**pub, "thumbnail": thumb_map[title]}
    spotlight = pub.get("spotlight_url") or ""
    if spotlight:
        auto_thumb = thumbnail_from_spotlight(spotlight)
        if auto_thumb:
            return {**pub, "thumbnail": auto_thumb}
    return pub


def apply_overrides(publications: list[dict], overrides: dict) -> list[dict]:
    hide = set(overrides.get("hide", []))
    links = overrides.get("link", {})
    fix_venue = overrides.get("fix_venue", {})
    featured = set(overrides.get("featured", []))

    filtered = []
    for pub in publications:
        pub_id = pub.get("scholar_id") or pub.get("title", "")
        if pub_id in hide or pub.get("title") in hide:
            continue
        year = publication_year(pub)
        if year and not is_valid_publication_year(year):
            continue
        if pub.get("title") in fix_venue:
            pub = {**pub, "venue": fix_venue[pub["title"]]}
        if pub.get("title") in links:
            pub = {**pub, "spotlight_url": links[pub["title"]]}
        if pub.get("title") in featured:
            pub = {**pub, "featured": True}
        pub = attach_paper_url(pub, overrides)
        filtered.append(attach_thumbnail(pub, overrides))

    for extra in overrides.get("add", []):
        if extra.get("title") in featured:
            extra = {**extra, "featured": True}
        extra = attach_paper_url(extra, overrides)
        filtered.append(attach_thumbnail(extra, overrides))

    filtered.sort(key=lambda p: (-publication_year(p), p.get("title", "").lower()))
    return deduplicate_publications(filtered)


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.lower().strip())


def publication_quality_score(pub: dict) -> tuple:
    venue = pub.get("venue", "").strip()
    url = primary_paper_url(pub)
    return (
        bool(venue),
        pub.get("citations", 0),
        "arxiv.org" in url,
        bool(url),
    )


def deduplicate_publications(publications: list[dict]) -> list[dict]:
    by_title: dict[str, dict] = {}
    order: list[str] = []
    for pub in publications:
        key = normalize_title(pub.get("title", ""))
        if not key:
            order.append(f"__empty__{len(order)}")
            by_title[order[-1]] = pub
            continue
        existing = by_title.get(key)
        if existing is None:
            by_title[key] = pub
            order.append(key)
        elif publication_quality_score(pub) > publication_quality_score(existing):
            by_title[key] = pub
    return [by_title[key] for key in order]


def group_publications_by_year(publications: list[dict]) -> list[tuple[int, list[dict]]]:
    groups: dict[int, list[dict]] = {}
    for pub in publications:
        year = publication_year(pub)
        groups.setdefault(year, []).append(pub)
    return sorted(groups.items(), key=lambda item: -item[0])


def primary_paper_url(pub: dict) -> str:
    return pub.get("paper_url") or pub.get("scholar_url") or pub.get("pdf_url") or ""


def is_blog_url(url: str) -> bool:
    return "blog_posts/" in url


def render_pub_paper_links(pub: dict) -> str:
    links: list[str] = []
    paper_url = primary_paper_url(pub)
    pdf_url = pub.get("pdf_url") or ""

    if paper_url and paper_url != pdf_url:
        links.append(
            f'<a class="pub-card__link" href="{html.escape(paper_url)}">Paper</a>'
        )

    if pdf_url and pdf_url != paper_url:
        links.append(f'<a class="pub-card__link" href="{html.escape(pdf_url)}">PDF</a>')

    spotlight_url = pub.get("spotlight_url") or ""
    if spotlight_url and is_blog_url(spotlight_url):
        links.append(
            f'<a class="pub-card__link" href="{html.escape(spotlight_url)}">Blog</a>'
        )
    elif spotlight_url:
        links.append(
            f'<a class="pub-card__link" href="{html.escape(spotlight_url)}">Project</a>'
        )

    if not links:
        return ""
    return f'<div class="pub-card__links">{" · ".join(links)}</div>'


def render_pub_card(pub: dict) -> str:
    title = pub.get("title", "")
    title_text = html.escape(title)
    paper_url = primary_paper_url(pub)
    spotlight_url = pub.get("spotlight_url") or ""
    title_href = paper_url or spotlight_url
    if title_href:
        title_html = f'<a href="{html.escape(title_href)}">{title_text}</a>'
    else:
        title_html = title_text

    featured = pub.get("featured")
    featured_html = '<span class="pub-card__featured" aria-hidden="true">★</span> ' if featured else ""

    authors = html.escape(format_authors(pub.get("authors", "")))
    authors_html = f'<p class="pub-card__authors">{authors}</p>' if authors else ""

    venue = html.escape(pub.get("venue", ""))
    venue_html = f'<p class="pub-card__venue"><em>{venue}</em></p>' if venue else ""

    links_html = render_pub_paper_links(pub)

    abstract = pub.get("abstract", "").strip()
    abstract_html = ""
    if abstract:
        abstract_html = f"""<details class="pub-card__abstract">
  <summary>Abstract</summary>
  <p>{html.escape(abstract)}</p>
</details>"""

    return f"""    <li class="pub-card">
      <article>
        <h3 class="pub-card__title">{featured_html}{title_html}</h3>
        {authors_html}
        {venue_html}
        {links_html}
        {abstract_html}
      </article>
    </li>"""


def render_publications(
    publications: list[dict],
    updated_at: str,
    scholar_user_id: str = "",
) -> str:
    year_sections = []
    for year, pubs in group_publications_by_year(publications):
        cards = "\n".join(render_pub_card(pub) for pub in pubs)
        year_label = str(year) if year else "Undated"
        year_id = f"pub-{year_label.lower()}"
        year_sections.append(
            f"""    <section class="pub-year" id="{html.escape(year_id)}" aria-labelledby="{html.escape(year_id)}-heading">
      <h2 class="pub-year__heading" id="{html.escape(year_id)}-heading">{html.escape(year_label)}</h2>
      <ol class="pub-list">
{cards}
      </ol>
    </section>"""
        )

    body_sections = "\n\n".join(year_sections)
    scholar_link = ""
    if scholar_user_id:
        profile_url = f"https://scholar.google.com/citations?user={html.escape(scholar_user_id)}"
        scholar_link = (
            f'<p class="pub-scholar-link">'
            f'<a href="{profile_url}">View full profile on Google Scholar</a></p>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Publications · Human-AI Resonance</title>
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
    <p class="section-label">Research</p>
    <h1>Publications</h1>
    <p class="page-lede">Selected papers from the Human-AI Resonance lab and collaborators.</p>
    {scholar_link}
    <div class="pub-index">
{body_sections}
    </div>
    <p class="pub-updated">Last updated: {html.escape(updated_at)}</p>
  </main>
  <script src="./assets/js/site.js"></script>
</body>
</html>
"""


def main() -> None:
    config = load_json(CONFIG_PATH)
    overrides = load_json(OVERRIDES_PATH)
    user_id = config.get("scholar_user_id", "")

    fetched = fetch_scholar(user_id) if user_id else None
    if fetched:
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "source": "google_scholar",
            "publications": fetched,
        }
        save_json(PUBLICATIONS_PATH, payload)
        print(f"Fetched {len(fetched)} publications from Scholar")
    elif PUBLICATIONS_PATH.exists():
        payload = load_json(PUBLICATIONS_PATH)
        if payload.get("source") == "seed":
            print("Warning: using seed data; install scholarly and re-run to fetch live publications", file=sys.stderr)
        else:
            print("Using existing publications.json (Scholar fetch unavailable)")
    else:
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "source": "seed",
            "publications": seed_publications(),
        }
        save_json(PUBLICATIONS_PATH, payload)
        print(f"Seeded {len(payload['publications'])} publications")

    publications = apply_overrides(payload.get("publications", []), overrides)
    updated_at = payload.get("updated_at", datetime.now(timezone.utc).isoformat())

    sys.path.insert(0, str(ROOT / "scripts"))

    OUTPUT_PATH.write_text(
        render_publications(publications, updated_at, user_id),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
