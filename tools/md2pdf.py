#!/usr/bin/env python3
"""Convert the festivals markdown into a print-quality PDF via Chromium."""
import re, sys, pathlib
import markdown

SRC = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2])
HTML_OUT = OUT.with_suffix(".html")

raw = SRC.read_text(encoding="utf-8")

# ── split front matter (title block) from body at the first horizontal rule ──
parts = re.split(r"\n---\n", raw, maxsplit=1)
front, body_md = (parts[0], parts[1]) if len(parts) == 2 else ("", raw)

title_m = re.search(r"^#\s+(.*)$", front, re.M)
doc_title = title_m.group(1).strip() if title_m else SRC.stem
front_rest = re.sub(r"^#\s+.*$", "", front, count=1, flags=re.M).strip()

md = markdown.Markdown(
    extensions=["tables", "attr_list", "sane_lists", "toc", "md_in_html"],
    extension_configs={"toc": {"toc_depth": "1-2", "permalink": False}},
)
body_html = md.convert(body_md)
toc_html = md.toc

# cover blurb
cover_md = markdown.Markdown(extensions=["tables", "nl2br"])
cover_html = cover_md.convert(front_rest)

# de-link references to sibling .md files (dead in a PDF) -> keep the text
body_html = re.sub(r'<a href="[^"]*\.md">(.*?)</a>', r"<strong>\1</strong>", body_html)
cover_html = re.sub(r'<a href="[^"]*\.md">(.*?)</a>', r"<strong>\1</strong>", cover_html)

# strip the emoji + code-ish wrapper markers left in the cover text
cover_html = cover_html.replace("<code>", "<strong>").replace("</code>", "</strong>")

CSS = """
@page { size: A4 portrait; margin: 13mm 11mm 15mm 11mm; }
@page :first { margin: 0; }

* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  font-family: "DejaVu Sans", "Liberation Sans", sans-serif, "Noto Color Emoji";
  font-size: 9.1pt; line-height: 1.45; color: #1d2127; margin: 0;
}
:root {
  --ink:#1d2127; --muted:#6a7280; --rule:#dfe3e8;
  --accent:#7c2d12; --accent2:#9a3412; --band:#faf6f2; --zebra:#f7f8fa;
}

/* ───────── cover ───────── */
/* content box on A4 with our margins = 188mm x 269mm; stay safely inside it */
.cover {
  height: 264mm; width: 100%; padding: 26mm 20mm 16mm 20mm;
  break-after: page; break-inside: avoid; overflow: hidden;
  background-color: #5b2c17;
  background-image: linear-gradient(160deg,#2b1810 0%,#5b2c17 55%,#7c2d12 100%);
  color: #fdf6ef; display: flex; flex-direction: column; border-radius: 2mm;
}
.cover .crest { font-size: 34pt; line-height: 1; margin-bottom: 12mm; }
.cover h1 { font-size: 27pt; line-height: 1.18; margin: 0 0 6mm 0; color: #ffffff;
            font-weight: 700; letter-spacing: -.4pt; border: 0; padding: 0;
            break-before: avoid; }
.cover .rule { width: 44mm; height: 3px; background: #e8b57a; margin: 0 0 8mm 0; }
.cover .blurb { font-size: 10pt; line-height: 1.65; color: #f0ddca; max-width: 132mm; }
.cover .blurb p { margin: 0 0 3.2mm 0; }
.cover .blurb strong { color: #e8b57a; font-weight: 700; }
.cover .blurb a { color: #f0ddca; }
.cover .foot { margin-top: auto; font-size: 8.5pt; line-height: 1.55; color: #cbab8d; }

.cover .foot { border-top: 1px solid rgba(232,181,122,.4); padding-top: 5mm; }

/* ───────── contents ───────── */
.toc-page { break-after: page; }
.toc-page > h2 { margin-top: 0; }
.toc { column-count: 2; column-gap: 10mm; column-fill: balance; font-size: 8.4pt; }
.toc ul { list-style: none; margin: 0; padding: 0; }
.toc > ul > li { break-inside: avoid; margin: 0 0 1.6mm 0; }
.toc > ul > li > a { font-weight: 700; color: var(--accent); text-decoration: none; }
.toc ul ul { margin: .6mm 0 2.4mm 0; padding-left: 3.5mm; }
.toc ul ul li { margin: 0 0 .5mm 0; }
.toc ul ul a { color: #40474f; text-decoration: none; }

/* ───────── headings ───────── */
h1 {
  break-before: page; font-size: 17pt; margin: 0 0 5mm 0; padding: 0 0 2.5mm 0;
  color: var(--accent); border-bottom: 2.5px solid var(--accent);
  letter-spacing: -.2pt; break-after: avoid;
}
h2 {
  font-size: 12.4pt; margin: 7mm 0 2.6mm 0; padding: 0 0 1.4mm 0;
  color: var(--accent2); border-bottom: 1px solid var(--rule); break-after: avoid;
}
h3 { font-size: 10.4pt; margin: 5mm 0 2mm 0; color: #33383f; break-after: avoid; }
h4 { font-size: 9.4pt; margin: 4mm 0 1.5mm 0; color: #4a5058; break-after: avoid; }
h1 + h2, h1 + p { margin-top: 0; }

p { margin: 0 0 2.6mm 0; orphans: 2; widows: 2; }
a { color: #1d4ed8; text-decoration: none; }
strong { color: #10141a; }
hr { border: 0; border-top: 1px solid var(--rule); margin: 6mm 0; }

ul, ol { margin: 0 0 2.8mm 0; padding-left: 5mm; }
li { margin: 0 0 1mm 0; }

blockquote {
  margin: 3mm 0; padding: 2.6mm 4mm; background: var(--band);
  border-left: 3px solid #d97706; border-radius: 0 3px 3px 0;
  break-inside: avoid; font-size: 8.9pt;
}
blockquote p:last-child { margin-bottom: 0; }

code {
  font-family: "DejaVu Sans Mono", monospace; font-size: .88em;
  background: #f1f3f5; padding: .4mm 1.1mm; border-radius: 2px;
}

/* ───────── tables ───────── */
table {
  width: 100%; border-collapse: collapse; margin: 2.5mm 0 5mm 0;
  font-size: 7.9pt; line-height: 1.35;
}
thead { display: table-header-group; }
tr { break-inside: avoid; page-break-inside: avoid; }
th {
  background: var(--accent); color: #fff; text-align: left; font-weight: 700;
  padding: 1.6mm 1.8mm; border: 1px solid var(--accent); font-size: 7.9pt;
}
td {
  padding: 1.5mm 1.8mm; border: 1px solid var(--rule); vertical-align: top;
  overflow-wrap: anywhere; word-break: normal;
}
tbody tr:nth-child(even) td { background: var(--zebra); }
td a { word-break: break-word; }

/* keep a heading with the table that follows it */
h2 + table, h3 + table, h2 + p + table, h3 + p + table { break-before: avoid; }
"""

HEADER = '<div style="font-size:6pt;color:#fff;width:100%;"></div>'
FOOTER = (
    '<div style="font-family:DejaVu Sans,sans-serif;font-size:7pt;color:#98a0a8;'
    'width:100%;padding:0 11mm;display:flex;justify-content:space-between;'
    'border-top:1px solid #e6e9ec;padding-top:2mm;">'
    '<span>Medieval &amp; Historical Festivals in Europe &nbsp;·&nbsp; compiled Aug 2026</span>'
    '<span>page <span class="pageNumber"></span> / <span class="totalPages"></span></span>'
    "</div>"
)

html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{doc_title}</title>
<style>{CSS}</style></head>
<body>

<section class="cover">
  <div class="crest">⚔️ 🛡️ 🐉</div>
  <h1>{doc_title.replace("⚔️ ", "")}</h1>
  <div class="rule"></div>
  <div class="blurb">{cover_html}</div>
  <div class="foot">A reference guide to medieval, Viking, Roman, Renaissance and reenactment
  festivals across Europe — organised by country, with dates, drive times and trip-planning notes.</div>
</section>

<section class="toc-page">
  <h2>Contents</h2>
  <div class="toc">{toc_html}</div>
</section>

{body_html}
</body></html>"""

HTML_OUT.write_text(html, encoding="utf-8")

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium",
                                args=["--no-sandbox", "--font-render-hinting=none"])
    page = browser.new_page()
    page.goto(HTML_OUT.resolve().as_uri(), wait_until="networkidle")
    page.emulate_media(media="print")
    page.pdf(
        path=str(OUT), format="A4", print_background=True,
        display_header_footer=True, header_template=HEADER, footer_template=FOOTER,
        margin={"top": "13mm", "bottom": "15mm", "left": "11mm", "right": "11mm"},
        prefer_css_page_size=False, outline=True, tagged=True,
    )
    browser.close()

print("wrote", OUT)
