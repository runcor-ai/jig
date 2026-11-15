"""Build the designed edition of the Jig thought paper (adapted from the Describing Reality for AI edition builder).

Usage: python paper/build.py   (reads paper/src/paper.html, writes paper/index.html, paper/print.html and the PDF)

Original notes:

Usage: python build.py <docs-html-export.txt | paper.html> [output folder]
  The output folder (default: this folder) holds src/blobmap.json, optional src/embedmap.json and img/.
  - Reads the export (the Docs tool's JSON result file, or an already decoded paper.html).
  - Writes edition/index.html (the published page body), edition/print.html (a full document for PDF),
    and edition/Describing-Reality-for-AI.pdf (headless Edge).
Figures: edition/src/blobmap.json maps each Docs blob id to an image under edition/img/.
Tables never scroll sideways: wide, text-heavy tables become stacked cards; dense short tables shrink;
every table turns into cards on a phone.
"""
import base64
import datetime as dt
import html as htmlmod
import json
import re
import subprocess
import sys
from pathlib import Path

from lxml import etree
from lxml import html as LH

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else HERE
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def load_export(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix == ".html":
        return text
    # the tool-result file is either a JSON array of text parts or the plain result text
    try:
        parts = json.loads(text)
        t = "".join(x.get("text", "") for x in parts) if isinstance(parts, list) else text
    except ValueError:
        t = text
    j = json.loads(t[t.index('{"verdict"'):])
    return base64.b64decode(j["data"]["bytes_b64"]).decode("utf-8")


def cell_text(el):
    return re.sub(r"\s+", " ", el.text_content()).strip()


def classify(table):
    rows = table.xpath(".//tr")
    cols = max((len(r.xpath("./td|./th")) for r in rows), default=0)
    chars = len(cell_text(table))
    per_row = chars / max(len(rows), 1)
    if cols >= 6 and per_row > 180:
        return "stack"
    if cols >= 6:
        return "dense"
    if cols >= 4 and per_row > 260:
        return "roomy"
    return ""


def display_width(src):
    """CSS width for an image: its pixel width, halved for '@2x' files, so no image is shown larger than its
    resolution (blurry); the stylesheet still caps it at the column width."""
    try:
        from PIL import Image
        w = Image.open(OUT / src).size[0]
    except Exception:
        return None
    return w // 2 if "@2x" in src else w


def transform(src):
    doc = LH.fromstring(f"<div id='root'>{src}</div>")
    root = doc
    blobmap = json.loads((OUT / "src" / "blobmap.json").read_text())
    emb = OUT / "src" / "embedmap.json"
    embedmap = json.loads(emb.read_text()) if emb.exists() else {}

    # Diagrams and charts (Docs widgets) export as empty <figure data-embed>: put in their rendered image.
    for fig in root.xpath(".//figure[@data-embed]"):
        wid = fig.get("data-embed").split("/", 1)[-1]
        fig.set("class", "fig")
        if wid in embedmap:
            img = LH.Element("img")
            img.set("src", embedmap[wid])
            w = display_width(embedmap[wid])
            if w:
                img.set("width", str(w))
            img.set("loading", "lazy")
            fig.insert(0, img)
        for cap in fig.xpath("./figcaption"):
            m = re.match(r"(Figure \w+)\s*[\u00b7:]\s*(.*)", cell_text(cap))
            if m:
                cap.text = None
                lab = etree.SubElement(cap, "span")
                lab.set("class", "figlab")
                lab.text = m.group(1)
                lab.tail = " " + m.group(2)
                for im in fig.xpath("./img"):
                    im.set("alt", m.group(2))

    # Figures: blob ids to local images; captions from alt text.
    for img in root.xpath(".//img"):
        s = img.get("src", "")
        bid = s.split("/", 1)[1] if s.startswith("blob/") else None
        if bid and bid in blobmap:
            img.set("src", blobmap[bid])
            w = display_width(blobmap[bid])
            if w:
                img.set("width", str(w))
        img.set("loading", "lazy")
        alt = img.get("alt", "")
        parent = img.getparent()
        if parent.tag == "p" and len(parent) == 1 and not (parent.text or "").strip():
            fig = LH.Element("figure")
            fig.set("class", "fig")
            parent.addprevious(fig)
            fig.append(img)
            # a "Figure N" paragraph right after the image is the caption already
            has_cap = parent.getnext() is not None and cell_text(parent.getnext()).startswith("Figure ")
            if alt and not has_cap:
                cap = LH.Element("figcaption")
                m = re.match(r"(Figure \w+):\s*(.*)", alt)
                if m:
                    lab = etree.SubElement(cap, "span")
                    lab.set("class", "figlab")
                    lab.text = m.group(1)
                    lab.tail = " " + m.group(2)
                else:
                    cap.text = alt
                fig.append(cap)
            parent.getparent().remove(parent)

    # Byline: drop the mention chip, keep the date.
    for sp in root.xpath(".//span[@data-atom='mention']"):
        sp.drop_tree()

    # Tables: classify, label cells for stacked layout, wrap.
    for i, t in enumerate(root.xpath(".//table")):
        cls = classify(t)
        heads = [cell_text(th) for th in t.xpath(".//thead//th")] or \
                [cell_text(c) for c in (t.xpath(".//tr[1]/th") or [])]
        for tr in t.xpath(".//tbody/tr") or t.xpath(".//tr")[1:]:
            for j, td in enumerate(tr.xpath("./td|./th")):
                if j < len(heads):
                    td.set("data-label", heads[j])
                if re.fullmatch(r"[\s\d.,%+\-−–~✓✗Xx×()/]{1,14}", cell_text(td) or "?") and j > 0:
                    td.set("class", "num")
                # One wrapper per cell, so a cell laid out as a grid (cards) has exactly two items.
                v = LH.Element("div")
                v.set("class", "v")
                v.text, td.text = td.text, None
                for c in list(td):
                    v.append(c)
                td.append(v)
        t.set("class", ("tbl " + cls).strip())
        wrap = LH.Element("div")
        wrap.set("class", "tblwrap")
        t.addprevious(wrap)
        wrap.append(t)

    # Headings: split "01 Title" into number + title; collect contents.
    toc = []
    for h in root.xpath(".//h2"):
        txt = cell_text(h)
        hid = h.get("id") or re.sub(r"[^a-z0-9]+", "-", txt.lower()).strip("-")
        h.set("id", hid)
        m = re.match(r"^(\d\d)\s+(.*)$", txt) or re.match(r"^(Appendix [A-Z])\s*[—–-]\s*(.*)$", txt)
        for c in list(h):
            h.remove(c)
        if m:
            num, title = m.group(1), m.group(2)
            h.text = None
            n = etree.SubElement(h, "span")
            n.set("class", "secnum")
            n.text = num
            tt = etree.SubElement(h, "span")
            tt.set("class", "sectitle")
            tt.text = title
        else:
            num, title = "", txt
            h.text = txt
        h.set("class", "sec")
        toc.append((hid, num, title))

    # Title block is rebuilt as the cover; remove the doc's own h1, subtitle and byline.
    h1 = root.xpath(".//h1")
    subtitle, started = "", ""
    if h1:
        h1 = h1[0]
        nxt = h1.getnext()
        if nxt is not None and nxt.tag == "p" and (nxt.xpath("./em") or not nxt.xpath(".//time")):
            subtitle = cell_text(nxt)
            by = nxt.getnext()
            nxt.getparent().remove(nxt)
            if by is not None and by.tag == "p" and by.xpath(".//time"):
                started = by.xpath(".//time")[0].get("datetime", "")
                by.getparent().remove(by)
        h1.getparent().remove(h1)

    body = "".join(LH.tostring(c, encoding="unicode") for c in root)
    if root.text:
        body = htmlmod.escape(root.text) + body
    # Highlight placeholders in text (outside tags).
    body = re.sub(r"\[(TO FILL[^\]]*|Replace[^\]]*|TABLE[^\]]*|WINNER NAME|FIGURE[^\]]*)\]",
                  lambda m: f'<span class="todo">[{m.group(1)}]</span>', body)
    return body, toc, subtitle, started


CSS = r"""
/* Layout: one reading column of serif text; tables and figures may run a little wider;
   mono, letter-spaced labels for structure, as in the Runcor Lattice white paper. */
:root{
  --ink:#1b1d23; --text:#25282f; --muted:#5a5e68; --faint:#8a8e99;
  --rule:#d6d8dd; --rule2:#c4c7cf; --wash:#f6f8fb; --wash2:#ebecef;
  --navy:#1e4f8c; --navy-soft:#e9eff7; --todo:#8a5a00; --todo-bg:#fbf3e2; --paper:#ffffff;
  --serif:Georgia,"Times New Roman",serif;
  --mono:"IBM Plex Mono",Consolas,ui-monospace,monospace;
  color-scheme:light;
}
body{background:var(--paper);color:var(--text);font-family:var(--serif);font-size:17px;line-height:1.62;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));
  padding-block:0 64px}
.page{max-width:760px;margin:0 auto}
p,li{text-wrap:pretty}
a{color:var(--navy)}
strong{color:var(--ink)}
.eyebrow,.mono{font-family:var(--mono);font-size:12px;letter-spacing:.28em;text-transform:uppercase;color:var(--muted)}

/* Cover */
.cover{min-height:min(88vh,780px);display:flex;flex-direction:column;justify-content:space-between;padding-block:56px 32px;
  border-bottom:1px solid var(--rule)}
.cover h1{font-family:var(--serif);font-weight:400;font-size:clamp(40px,7vw,68px);line-height:1.04;
  color:var(--ink);margin:28px 0 18px;letter-spacing:-.01em;text-wrap:balance}
.cover .sub{font-size:clamp(20px,2.6vw,26px);line-height:1.35;color:var(--text);max-width:30ch;margin:0 0 36px}
.cover .lede{border-top:2px solid var(--navy);padding-top:18px;max-width:46ch;color:var(--muted);font-size:17px}
.cover .lede p{margin:0 0 8px}
.cover .foot{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-top:40px}
.status{display:inline-block;font-family:var(--mono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;
  color:var(--navy);background:var(--navy-soft);padding:4px 10px;border-radius:2px}

/* Contents */
.toc{padding-block:40px 24px;border-bottom:1px solid var(--rule)}
.toc ol{list-style:none;margin:16px 0 0;padding:0;columns:2;column-gap:40px}
.toc li{break-inside:avoid;display:flex;gap:12px;padding:5px 0;border-bottom:1px dotted var(--rule);font-size:15px;line-height:1.35}
.toc .n{font-family:var(--mono);font-size:11.5px;color:var(--navy);min-width:7.4em;white-space:nowrap;padding-top:2px}
.toc a{color:var(--text);text-decoration:none}
.toc a:hover{color:var(--navy);text-decoration:underline}

/* Sections */
h2.sec{font-family:var(--serif);font-weight:400;font-size:32px;line-height:1.15;color:var(--ink);
  margin:72px 0 20px;padding-top:20px;border-top:1px solid var(--rule2);text-wrap:balance}
h2.sec .secnum{display:block;font-family:var(--mono);font-size:13px;letter-spacing:.28em;color:var(--navy);margin-bottom:10px}
h3{font-family:var(--serif);font-weight:700;font-size:19px;color:var(--ink);margin:36px 0 10px;text-wrap:balance}
p{margin:0 0 14px}
ul,ol{padding-left:22px;margin:0 0 14px}
li{margin-bottom:6px} li>p{margin:0 0 6px}
blockquote{margin:22px 0;padding:14px 20px;background:var(--wash);border-left:2px solid var(--navy);color:var(--text)}
blockquote p:last-child{margin-bottom:0}
code{font-family:var(--mono);font-size:.84em;background:var(--wash2);padding:1px 4px;border-radius:2px;overflow-wrap:anywhere}
pre{font-family:var(--mono);font-size:13px;line-height:1.5;background:var(--wash);border:1px solid var(--rule);
  padding:14px 16px;white-space:pre-wrap;overflow-wrap:anywhere;margin:0 0 16px}
pre code{background:none;padding:0;font-size:inherit}
.todo{font-family:var(--mono);font-size:.78em;color:var(--todo);background:var(--todo-bg);padding:1px 5px;border-radius:2px;
  overflow-wrap:anywhere}
time{font-variant-numeric:tabular-nums}

/* Figures */
figure.fig{margin:28px 0}
figure.fig img{display:block;width:auto;max-width:100%;height:auto;margin:0 auto;border:1px solid var(--rule);background:#fff}
figcaption{font-size:14px;line-height:1.45;color:var(--muted);margin-top:8px}
.figlab{font-family:var(--mono);font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--navy);margin-right:6px}

/* Tables: always fit the column. */
.tblwrap{margin:20px 0 22px}
table.tbl{width:100%;border-collapse:collapse;table-layout:auto;font-size:14px;line-height:1.42;
  font-variant-numeric:tabular-nums;border-top:2px solid var(--ink)}
.tbl th{font-family:var(--mono);font-weight:500;font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--muted);text-align:left;vertical-align:bottom;padding:9px 10px 7px;border-bottom:1px solid var(--rule2)}
.tbl td{vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--rule);overflow-wrap:break-word;hyphens:auto}
.tbl td:first-child{color:var(--ink)}
.tbl td.num{text-align:center;white-space:nowrap}
.tbl tbody tr:nth-child(even) td{background:var(--wash)}
.tbl td p{margin:0 0 4px} .tbl td p:last-child{margin:0}
.tbl td ul{margin:0;padding-left:16px}
table.dense{font-size:12px} .dense th{font-size:9px;letter-spacing:.04em;padding:7px 5px;hyphens:auto;overflow-wrap:break-word} .dense td{padding:6px 5px} .dense td:first-child{width:24%;min-width:9em}
table.roomy{font-size:13.5px}
/* Stacked cards: one card per row, header labels beside each value. */
table.stack, table.stack tbody, table.stack tr, table.stack td{display:block;width:100%}
table.stack{border-top:none}
table.stack thead{display:none}
table.stack tr{border-top:2px solid var(--ink);padding:10px 0 6px;margin-bottom:12px;break-inside:avoid}
table.stack tbody tr:nth-child(even) td{background:none}
table.stack td{border:none;padding:3px 0;display:grid;grid-template-columns:minmax(8em,30%) 1fr;gap:14px}
table.stack td::before{content:attr(data-label);font-family:var(--mono);font-size:10px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--muted);padding-top:3px}
table.stack td:first-child{display:block;font-weight:700;font-size:15.5px;padding-bottom:6px}
table.stack td:first-child::before{display:none}

/* Phones: every table becomes cards. */
@media (max-width:640px){
  body{font-size:16px}
  .toc ol{columns:1}
  h2.sec{font-size:27px;margin-top:56px}
  table.tbl, table.tbl tbody, table.tbl tr, table.tbl td{display:block;width:100%}
  table.tbl{border-top:none}
  table.tbl thead{display:none}
  table.tbl tr{border-top:2px solid var(--ink);padding:8px 0 4px;margin-bottom:10px}
  table.tbl tbody tr:nth-child(even) td{background:none}
  table.tbl td{border:none;padding:3px 0;display:grid;grid-template-columns:42% 1fr;gap:10px}
  table.tbl td::before{content:attr(data-label);font-family:var(--mono);font-size:10px;letter-spacing:.1em;
    text-transform:uppercase;color:var(--muted);padding-top:3px}
  table.tbl td:first-child{display:block;font-weight:700}
  table.tbl td:first-child::before{display:none}
}

/* Print / PDF */
@page{size:A4;margin:20mm 18mm 20mm 18mm;
  @bottom-left{content:"ABSTRACTION FOR AI WORK";font-family:"IBM Plex Mono",Consolas,monospace;font-size:7pt;letter-spacing:.25em;color:#8a8e99}
  @bottom-right{content:counter(page);font-family:"IBM Plex Mono",Consolas,monospace;font-size:8pt;color:#8a8e99}}
@page :first{@bottom-left{content:none}@bottom-right{content:none}}
@media print{
  body{font-size:10.4pt;line-height:1.5;padding:0}
  .page{max-width:none}
  .cover{min-height:238mm;break-after:page;border-bottom:none;padding-block:10mm 0}
  .toc{break-after:page;border-bottom:none}
  h2.sec{break-before:page;margin-top:0;border-top:none;font-size:24pt}
  h3{break-after:avoid;font-size:12.5pt}
  figure.fig,blockquote,pre{break-inside:avoid}
  figure.fig img{max-height:205mm;width:auto;max-width:100%;margin:0 auto}
  table.tbl{font-size:8.6pt} .tbl th{font-size:6.8pt} table.dense{font-size:7.6pt} .dense th{font-size:6.2pt}
  .tbl tr{break-inside:avoid}
  .tbl thead{display:table-header-group}
  table.stack thead{display:none}
  table.stack td:first-child{font-size:10pt}
  a{color:inherit;text-decoration:none}
}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
"""


def extra_css():
    # an edition may add its own styles (e.g. a compact print layout) in src/extra.css
    f = OUT / "src" / "extra.css"
    return f.read_text(encoding="utf-8") if f.exists() else ""


# The cover's status: the byline's date is the paper's as-of date, not when the run started, so the run is named here.
STATUS = "Version 0.4"
RUN_LINE = "With a short experiment &nbsp;·&nbsp; 14 Nov 2026"


def page(body, toc, subtitle, started, updated):
    toc_html = "".join(
        f'<li><span class="n">{htmlmod.escape(n) or "&nbsp;"}</span><a href="#{hid}">{htmlmod.escape(t)}</a></li>'
        for hid, n, t in toc)
    upd = dt.date.fromisoformat(updated).strftime("%d %b %Y").lstrip("0")
    st = dt.date.fromisoformat(started).strftime("%d %b %Y").lstrip("0") if started else ""
    return f"""<title>Abstraction for AI Work</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>{CSS}{extra_css()}</style>
<div class="page">
<header class="cover">
  <div>
    <div class="eyebrow">Jig &nbsp;·&nbsp; Thought paper &nbsp;·&nbsp; {STATUS}</div>
    <h1>Abstraction for AI Work</h1>
    <p class="sub">{htmlmod.escape(subtitle or "Controlling complexity by working with AI at the right level, and measuring that the level holds")}</p>
    <div class="lede">
      <p>A biologist explaining a heartbeat does not talk about quantum physics. Every field controls complexity by working at the right level. AI tooling has built powerful machinery: agent teams, hooked harnesses, orchestration frameworks. The way of working itself is still buried inside it, hard to read, change or measure as a unit.</p>
      <p>This paper argues for a level above that machinery: scripts of contracted steps, with the prompts one level down, and every claim checked and every way of working measured before it is trusted.</p>
    </div>
  </div>
  <div class="foot">
    <span class="mono">{RUN_LINE}</span>
    <span class="status">Updated {upd}</span>
  </div>
</header>
<nav class="toc" aria-label="Contents">
  <div class="eyebrow">Contents</div>
  <ol>{toc_html}</ol>
</nav>
<main>
{body}
</main>
</div>
"""


def main():
    src = load_export(sys.argv[1] if len(sys.argv) > 1 else str(HERE / "src" / "paper.html"))
    (OUT / "src" / "paper.html").write_text(src, encoding="utf-8")
    body, toc, subtitle, started = transform(src)
    updated = dt.date.today().isoformat()
    out = page(body, toc, subtitle, started, updated)
    (OUT / "index.html").write_text(out, encoding="utf-8")
    (OUT / "print.html").write_text('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                                     '<meta name="viewport" content="width=device-width,initial-scale=1">'
                                     + out + "</html>", encoding="utf-8")
    pdf = OUT / "Abstraction-for-AI-Work.pdf"
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=15000", f"--print-to-pdf={pdf}",
                    (OUT / "print.html").as_uri()], check=False, capture_output=True)
    print("index.html", len(out), "chars;", len(toc), "sections;", "pdf", pdf.stat().st_size if pdf.exists() else "missing")


if __name__ == "__main__":
    main()
