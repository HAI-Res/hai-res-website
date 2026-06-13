# Contributing to the HAI-RES website

Each profile, blog post, and music piece lives in **its own folder**. You write
content in **Markdown** (`index.md`), then open a pull request.

## Workflow

1. Clone the repo and create a branch: `git checkout -b my-update`
2. Copy the relevant `_template` folder:
   - Profile: `profiles/_template/` → `profiles/your_name/`
   - Blog: `blog_posts/_template/` → `blog_posts/my_post/`
   - Music: `music/_template/` → `music/piece_slug/`
3. Edit `index.md` and add files under `assets/`
4. Push and open a PR — Anna or Stephen will review and merge
5. CI builds the pages and deploys automatically

## Markdown front matter

Every `index.md` starts with a YAML front-matter block. The keys are:

```markdown
---
type: profile          # profile | blog | music
date: 2026-05-25
title: Your Name
subtitle: Role · tagline
thumbnail: ./assets/photo.svg
---

Markdown body goes here.
```

For **blog posts**, also add:

```markdown
excerpt: One-line summary for the blog listing.
thumbnail: ./assets/thumbnail.jpg
```

Blog posts **require** a thumbnail image at the path given in `thumbnail` (used
on the home page carousel and blog listing). Recommended size: roughly
1200×675 (16:9).

## Writing the body

- The Markdown body fills the page content area. The site header, navigation,
  and footer are generated for you — you don't copy any chrome.
- **Profiles:** each `## heading` (Research Topic, Contact, Bio, …) becomes its
  own section. The name, tagline, and photo come from the front matter.
- Standard Markdown works: headings, lists, tables, code blocks, links, images.
- Raw HTML is allowed inline (e.g. YouTube iframes, `<audio>`).
- For per-post styling, add `styles.css` (and `scripts.js`) next to `index.md`;
  the build links them automatically.

## Video (YouTube only)

Do **not** commit `.mp4` files — they are gitignored and exceed GitHub's file
size limits. Upload to **YouTube** and embed with a privacy-friendly iframe:

```html
<iframe
  src="https://www.youtube-nocookie.com/embed/VIDEO_ID"
  title="Short description"
  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
  referrerpolicy="strict-origin-when-cross-origin"
  allowfullscreen
  loading="lazy"></iframe>
```

## Local check

Install dependencies once, then run the build before opening a PR:

```bash
python3 -m pip install -r requirements.txt
python3 scripts/build_listings.py
```

This renders each `index.md` to an `index.html` (gitignored) and regenerates
the listing pages. Preview locally with `python3 -m http.server 8080`. Fix any
metadata errors the script reports.

## Authoring raw HTML (advanced)

Markdown is the default, but a folder may instead contain a hand-written
`index.html` (useful for highly custom pages). If both exist, `index.md` wins.
Hand-written HTML posts must include the full site chrome themselves — see
`templates/snippets/` and `blog_posts/live_music_diffusion_models/` for a rich
reference.

## Maintainer note: deployment

The site deploys via the **GitHub Pages artifact** flow so that
Markdown-generated `index.html` files (which are gitignored) are served. In the
repo settings, set **Settings → Pages → Build and deployment → Source** to
**GitHub Actions**. The `Build and deploy` workflow builds and publishes on
every push to `main`.
