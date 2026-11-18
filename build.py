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

CONDITIONS = [
    ("POTS", "pots-symptom-tracker/", "what-is-pots/",
     "Dizziness on standing, heart rate lying and standing, salt and fluids."),
    ("Endometriosis", "endometriosis-symptom-tracker/", "what-is-endometriosis/",
     "Pelvic and period pain, bleeding level, endo belly, cycle day."),
    ("Fibromyalgia", "fibromyalgia-symptom-tracker/", "what-is-fibromyalgia/",
     "Widespread pain, fibro fog, morning stiffness, sleep quality."),
    ("Lupus", "lupus-flare-tracker/", "what-is-lupus/",
     "Joint pain, rashes, fatigue, temperature, sun exposure."),
    ("ME/CFS", "me-cfs-symptom-tracker/", "what-is-me-cfs/",
     "PEM crashes, physical, mental and social exertion, morning energy."),
]

# The hero month: wellbeing 1-5 per day (None = not logged), "f" marks a flare day.
# September 2026 starts on a Tuesday. Mirrors the app's Calendar tab.
MONTH = "September"
MONTH_OFFSET = 2
DAYS = ["1f", "1f", "1f", "2", "3", "3", "3", None, "4", "4", "3", "3", "2f", "2f", "2f",
        "2f", "3", "3", "4", "3", "3", None, None, "3", "4", "4", "4", "3", "1f", "2f"]


def calendar() -> str:
    cells = ['<span class="cal-head">' + d + "</span>" for d in "SMTWTFS"]
    cells += ['<span class="cal-day cal-pad"></span>'] * MONTH_OFFSET
    for number, value in enumerate(DAYS, start=1):
        if value is None:
            cells.append(f'<span class="cal-day cal-empty" style="--i:{number}">{number}</span>')
            continue
        flare = " cal-flare" if value.endswith("f") else ""
        cells.append(f'<span class="cal-day w{value[0]}{flare}" style="--i:{number}">{number}</span>')
    logged = sum(1 for d in DAYS if d)
    flares = sum(1 for d in DAYS if d and d.endswith("f"))
    label = (f"Example month in Betony's calendar: {logged} of {len(DAYS)} days logged, "
             f"{flares} flare days, {len(DAYS) - logged} days left empty.")
    legend = ('<p class="cal-legend" aria-hidden="true"><span class="cal-ramp">'
              + "".join(f'<i class="w{i}"></i>' for i in range(1, 6))
              + '</span>Wellbeing 1–5 <span class="cal-flare-key"></span>Flare</p>')
    return (f'<figure class="cal" role="img" aria-label="{label}">\n'
            f'<p class="cal-month" aria-hidden="true">{MONTH}</p>\n'
            f'<div class="cal-grid" aria-hidden="true">{"".join(cells)}</div>\n{legend}\n'
            '<figcaption>Three days are empty. Betony leaves them empty: no streaks, no reminders about gaps.</figcaption>\n'
            '</figure>')


def shot(name: str, alt: str) -> str:
    return (f'<picture><source srcset="/img/{name}-dark.jpg" media="(prefers-color-scheme: dark)">'
            f'<img src="/img/{name}-light.jpg" width="640" height="1391" alt="{html.escape(alt)}" loading="lazy"></picture>')


def app_store_button(extra: str = "") -> str:
    return f'<a class="button{extra}" href="{APP_STORE_URL}">Download on the App Store</a>'


def home() -> str:
    rows = "\n".join(
        f'<li><h3>{name}</h3><p>{what}</p>'
        f'<p class="cond-links"><a href="/{guide}">{name} tracker</a><a href="/{article}">What is {name if name.isupper() or "/" in name else name.lower()}?</a></p></li>'
        for name, guide, article, what in CONDITIONS)
    return f"""<section class="hero">
<div class="hero-text">
<h1>A symptom diary built for flare days.</h1>
<p class="lede">Betony is a symptom tracker for chronic illness: POTS, endometriosis, fibromyalgia, lupus, ME/CFS. A full day takes under 30 seconds to log, with big buttons and no typing.</p>
<p class="hero-cta">{app_store_button()}<span class="small">Free on iPhone. Optional Pro upgrade.</span></p>
</div>
{calendar()}
</section>

<section class="promises" aria-label="How Betony works">
<div><h2>Under 30 seconds</h2><p>Tap a number for each symptom and you are done. Nothing has to be typed.</p></div>
<div><h2>Nothing is mandatory</h2><p>Skip any field. A symptom you leave alone counts as not logged, never as zero.</p></div>
<div><h2>Stays on your iPhone</h2><p>No account, no sign-up, no analytics. Export everything to CSV for free.</p></div>
</section>

<section class="shots" aria-labelledby="shots-title">
<h2 id="shots-title"><span>Log the day, see the month, take a report to your doctor</span></h2>
<div class="shots-row">
<figure>{shot("1-today", "Betony's Today screen: overall wellbeing from 1 to 5, a flare day toggle and a list of symptoms with severity")}<figcaption>Today: wellbeing, flare day, symptoms.</figcaption></figure>
<figure>{shot("3-trends-90d", "Betony's Trends screen: 90 days of dizziness with each day's real high and low")}<figcaption>Trends: real highs and lows, never averaged away.</figcaption></figure>
<figure>{shot("4-report-preview", "Betony's Report screen: a preview of a printable symptom report with charts per symptom")}<figcaption>Report: a summary your doctor can read in a minute. Pro.</figcaption></figure>
</div>
</section>

<section class="conditions" aria-labelledby="cond-title">
<h2 id="cond-title">Set up for your condition</h2>
<p>Pick a condition during setup and Betony fills in symptoms, numbers and triggers that people with it tend to track. Change any of it later.</p>
<ul class="cond-list">
{rows}
</ul>
</section>
"""


def cta(meta: dict) -> str:
    return f"""<aside class="cta" aria-label="Get Betony">
<img src="/img/icon.png" width="64" height="64" alt="">
<div>
<p class="cta-title">Betony: Symptom Tracker</p>
<p>Log a day in under 30 seconds. No account, data stays on your iPhone.</p>
{app_store_button(" button-small")}
</div>
</aside>"""


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
    is_home = meta["path"] == ""
    kind = meta.get("kind")
    url = SITE_URL + ("" if is_404 else meta["path"])
    if is_home:
        content = home()
    else:
        content = body(markdown)
        # The date line goes right under the page heading.
        content = re.sub(r"(</h1>\n)", lambda m: m.group(1) + dateline(meta), content, count=1)
        content = f'<article class="prose">\n{content}\n</article>'
        if kind:
            content += "\n" + cta(meta)
    nav = "\n".join(f'<li><a href="/{p}">{name}</a></li>' for name, p in NAV)
    seo = "" if is_404 else (
        f'<link rel="canonical" href="{url}">\n'
        f'<meta property="og:type" content="{"article" if kind else "website"}">\n'
        f'<meta property="og:site_name" content="{SITE_NAME}">\n'
        f'<meta property="og:title" content="{html.escape(meta["title"])}">\n'
        f'<meta property="og:description" content="{html.escape(meta["description"])}">\n'
        f'<meta property="og:url" content="{url}">\n'
        f'<meta property="og:image" content="{SITE_URL}img/1-today-light.jpg">\n'
        f'<meta name="apple-itunes-app" content="app-id=6813134795">\n'
        + structured_data(meta, url))
    robots = '<meta name="robots" content="noindex">\n' if is_404 else ""
    if is_home:
        # Google Search Console ownership; keep it, or the property stops being verified.
        robots += '<meta name="google-site-verification" content="K2qzudUGoRobqem0MvwjoKvL5TuLfc5GnV8nQp2NCn0">\n'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#FAF6F0" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#181611" media="(prefers-color-scheme: dark)">
<meta name="description" content="{html.escape(meta['description'])}">
{robots}<title>{html.escape(meta['title'])}</title>
{seo}<link rel="icon" href="/favicon.png" type="image/png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:wght@400;700;800&display=swap">
<link rel="stylesheet" href="/styles.css">
</head>
<body class="{'home' if is_home else 'inner'}">
<header class="site-header">
<a class="brand" href="/"><img src="/img/icon.png" width="36" height="36" alt="">Betony</a>
<nav aria-label="Main"><a href="/guides/">Guides</a><a class="button button-small" href="{APP_STORE_URL}">Get the app</a></nav>
</header>
<main>
{content}
</main>
<footer class="site-footer">
<nav aria-label="Site">
<ul>
{nav}
</ul>
</nav>
<p class="small">Betony records what you log. It is not a medical device and does not give medical advice.</p>
</footer>
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
