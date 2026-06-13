# Human-AI Resonance Lab Website

Static GitHub Pages site for the Human-AI Resonance (HAI-RES) lab at MIT.

## Structure

- **Maintainer pages**: `index.html`, `join.html`
- **Generated listings**: `people.html`, `blog.html`, `music.html`, `publications.html`
- **Modular content**: `profiles/`, `blog_posts/`, `music/` — one folder per person/post/piece

## Local preview

```bash
# 1. One-time setup: create a venv and install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Build: renders each index.md → index.html and regenerates listings/footers/carousel
.venv/bin/python scripts/build_listings.py

# 3. Serve the site
.venv/bin/python -m http.server 8080
```

Open http://localhost:8080

Edit loop: change an `index.md` (or any metadata), re-run step 2, then refresh the
browser. The server keeps running — editing `.md` alone won't change what you see
until you rebuild. Stop the server with `Ctrl+C`.

> Note: running the build re-stamps `?v=<timestamp>` cache-busting URLs, so
> `git status` may show small diffs in `index.html`/`blog.html`/`people.html`/`data/blog.json`.
> That's just local noise — `git checkout --` them before committing; CI regenerates them anyway.

## Regenerate listings

`scripts/build_listings.py` scans `profiles/`, `blog_posts/`, and `music/`, renders any
Markdown content (`index.md`), and regenerates the listing pages, footers, and home carousel.

```bash
.venv/bin/python scripts/build_listings.py
.venv/bin/python scripts/sync_scholar.py   # pulls publications from Google Scholar
```

## GitHub Pages

The site is built and deployed by GitHub Actions (the `Build and deploy` workflow) on every
push to `main`. The build renders Markdown to HTML and publishes the result as a Pages
artifact, so generated `index.html` files (which are git-ignored) still go live.

1. Push to GitHub
2. **Settings → Pages → Build and deployment → Source → GitHub Actions**
3. Optional: set repository variable `GOOGLE_SCHOLAR_ID` to `NRz_EVgAAAAJ` for Scholar sync

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
