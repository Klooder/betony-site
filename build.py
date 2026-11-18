#!/usr/bin/env python3
"""Builds betonyapp.com: src/pages/*.md -> <path>/index.html, plus sitemap.xml and robots.txt.

    python3 build.py            # writes the site into the repo root
    python3 build.py --check    # fails if the built files are not up to date

Each page is a small Markdown file with a header block:

    title: POTS symptom tracker — Betony
    description: ...
    path: pots-symptom-tracker/
    kind: guide            # optional: guide | article (adds Article markup and a date line)
    updated: 2026-11-18    # optional, shown on guides and articles, used in the sitemap
    ---
    # Heading
    Paragraph with **bold** and [links](/privacy/).
    - list item

Only what the pages use is supported: #/## headings, paragraphs, "- " lists,
**bold**, [text](url). Everything else is escaped, never interpreted.
Links are root-relative: the site lives at the domain root.
"""
import datetime
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PAGES = ROOT / "src" / "pages"
SITE_NAME = "Betony"
SITE_URL = "https://betonyapp.com/"
APP_STORE_URL = "https://apps.apple.com/us/app/betony-symptom-tracker/id6813134795"

NAV = [("Home", ""), ("Guides", "guides/"), ("Privacy Policy", "privacy/"), ("Support", "support/")]


def inline(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                  lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>', escaped)


def body(markdown: str) -> str:
    out, paragraph, items = [], [], []

    def flush():
        if paragraph:
            out.append(f"<p>{inline(' '.join(paragraph))}</p>")
            paragraph.clear()
        if items:
            out.append("<ul>\n" + "\n".join(f"<li>{inline(i)}</li>" for i in items) + "\n</ul>")
            items.clear()

    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            flush()
        elif stripped.startswith("## "):
            flush(); out.append(f"<h2>{inline(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            flush(); out.append(f"<h1>{inline(stripped[2:])}</h1>")
        elif stripped.startswith("- "):
            if paragraph:
                flush()
            items.append(stripped[2:])
        else:
            if items:
                flush()
            paragraph.append(stripped)
    flush()
    return "\n".join(out)


def json_ld(data: dict) -> str:
    text = json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{text}\n</script>\n'


def structured_data(meta: dict, url: str) -> str:
    if meta["path"] == "":
        return json_ld({
            "@context": "https://schema.org", "@type": "MobileApplication",
            "name": "Betony: Symptom Tracker", "operatingSystem": "iOS",
            "applicationCategory": "HealthApplication", "url": SITE_URL,
            "downloadUrl": APP_STORE_URL, "description": meta["description"],
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        })
    if meta.get("kind") in ("guide", "article"):
        return json_ld({
            "@context": "https://schema.org", "@type": "Article",
            "headline": meta["heading"], "description": meta["description"],
            "mainEntityOfPage": url, "dateModified": meta["updated"],
            "author": {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL},
            "publisher": {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL},
        })
    return ""


def dateline(meta: dict) -> str:
    if meta.get("kind") not in ("guide", "article"):
        return ""
    day = datetime.date.fromisoformat(meta["updated"])
    return f'<p class="small">Updated <time datetime="{day.isoformat()}">{day:%B} {day.day}, {day.year}</time></p>\n'


def page(meta: dict, markdown: str) -> str:
    is_404 = meta["path"] == "404"
    url = SITE_URL + ("" if is_404 else meta["path"])
    content = body(markdown)
    # The date line goes right under the page heading.
    content = re.sub(r"(</h1>\n)", lambda m: m.group(1) + dateline(meta), content, count=1)
    nav = "\n".join(f'<li><a href="/{p}">{name}</a></li>' for name, p in NAV)
    seo = "" if is_404 else (
        f'<link rel="canonical" href="{url}">\n'
        f'<meta property="og:type" content="{"article" if meta.get("kind") else "website"}">\n'
        f'<meta property="og:site_name" content="{SITE_NAME}">\n'
        f'<meta property="og:title" content="{html.escape(meta["title"])}">\n'
        f'<meta property="og:description" content="{html.escape(meta["description"])}">\n'
        f'<meta property="og:url" content="{url}">\n'
        f'<meta name="apple-itunes-app" content="app-id=6813134795">\n'
        + structured_data(meta, url))
    robots = '<meta name="robots" content="noindex">\n' if is_404 else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="description" content="{html.escape(meta['description'])}">
{robots}<title>{html.escape(meta['title'])}</title>
{seo}<link rel="stylesheet" href="/styles.css">
</head>
<body>
<div class="page">
<header>
<a class="site-name" href="/">{SITE_NAME}</a>
</header>
<main>
{content}
</main>
<footer>
<nav aria-label="Site">
<ul>
{nav}
</ul>
</nav>
<p class="small">Betony records what you log. It is not a medical device and does not give medical advice.</p>
</footer>
</div>
</body>
</html>
"""


def read_pages() -> list[dict]:
    pages = []
    for source in sorted(PAGES.glob("*.md")):
        header, _, markdown = source.read_text(encoding="utf-8").partition("\n---\n")
        meta = {key.strip(): value.strip() for key, _, value in
                (line.partition(":") for line in header.strip().splitlines())}
        heading = next((l.strip()[2:] for l in markdown.splitlines() if l.strip().startswith("# ")), meta["title"])
        meta["heading"] = heading
        meta["markdown"] = markdown
        pages.append(meta)
    return pages


def sitemap(pages: list[dict]) -> str:
    rows = []
    for meta in sorted(pages, key=lambda m: m["path"]):
        if meta["path"] == "404":
            continue
        lastmod = f"<lastmod>{meta['updated']}</lastmod>" if "updated" in meta else ""
        rows.append(f"<url><loc>{SITE_URL}{meta['path']}</loc>{lastmod}</url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(rows) + "\n</urlset>\n")


def build() -> dict[pathlib.Path, str]:
    pages = read_pages()
    files = {}
    for meta in pages:
        target = ROOT / "404.html" if meta["path"] == "404" else ROOT / meta["path"] / "index.html"
        files[target] = page(meta, meta["markdown"])
    files[ROOT / "sitemap.xml"] = sitemap(pages)
    files[ROOT / "robots.txt"] = f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}sitemap.xml\n"
    return files


def main() -> int:
    files = build()
    if "--check" in sys.argv:
        stale = [str(p.relative_to(ROOT)) for p, text in files.items()
                 if not p.exists() or p.read_text(encoding="utf-8") != text]
        print("stale: " + ", ".join(stale) if stale else "up to date")
        return 1 if stale else 0
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
