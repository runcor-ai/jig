"""Make the paper's result figures (SVG) from the Reality Engine run's analysis, in the style of the run 5 charts.

    py paper/figures.py experiments/trust/work/pilot2

Writes paper/img/p2-compare.svg, p2-leads.svg, p2-parts.svg and p2-final.svg (only those the analysis has data for).
Forest plots: dot = mean, line = 95% range, shaded rows could still be the best, the value in a right-hand column.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "img"
NAMES = {"OPUS_PROSE": "Opus builds from prose", "OPUS_FACTS": "Opus builds from FACTS",
         "LUNA_PROSE": "Luna builds from prose", "LUNA_FACTS": "Luna builds from FACTS"}
PART = {"format": "Spec format FACTS → prose", "tests": "Test step switched off",
        "verify": "Verify step switched off", "fixes": "Fix rounds 2 → 0"}
BLUE, ORANGE, GRID, AXIS, INK, INK2, BAND = "#2a78d6", "#eb6834", "#e1e0d9", "#c3c2b7", "#0b0b0b", "#52514e", "#eaf1fb"


def esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def nice_step(span: float) -> float:
    raw = span / 5
    p = 10 ** math.floor(math.log10(raw))
    m = raw / p
    return (1 if m < 1.5 else 2 if m < 3 else 5 if m < 7 else 10) * p


def forest(rows, *, left, right, axis, zero=False, lo=None, hi=None, pct=False, title="") -> str:
    vals = [v for r in rows for v in [r["mean"], *(r.get("range") or [])] if v is not None]
    a, b = min(vals), max(vals)
    if zero:
        a, b = min(a, 0), max(b, 0)
    if lo is not None:
        a = min(a, lo)
    if hi is not None:
        b = max(b, hi)
    if b - a < 0.1:
        c = (a + b) / 2
        a, b = c - 0.05, c + 0.05
    step = nice_step(b - a)
    a, b = math.floor(a / step + 1e-9) * step, math.ceil(b / step - 1e-9) * step
    if pct:
        a, b = max(a, 0.0), min(b, 1.0)
    W, L, R, rowH, top = 1000, 330, 120, 44, 92
    H = top + len(rows) * rowH + 70
    x = lambda v: L + (v - a) / (b - a) * (W - L - R)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'font-family="Segoe UI, system-ui, sans-serif" font-size="17">',
           f'<rect width="{W}" height="{H}" fill="#fcfcfb"/>']
    if title:
        out.append(f'<text x="20" y="32" font-size="20" font-weight="600" fill="{INK}">{esc(title)}</text>')
    out.append(f'<text x="{L - 16}" y="{top - 14}" text-anchor="end" fill="{INK2}">{esc(left)}</text>')
    out.append(f'<text x="{W - R + 16}" y="{top - 14}" fill="{INK2}">{esc(right)}</text>')
    for i, r in enumerate(rows):
        if r.get("shade"):
            out.append(f'<rect x="{L - 6}" y="{top + i * rowH + 3}" width="{W - L - R + 12}" height="{rowH - 6}" rx="5" fill="{BAND}"/>')
    t = a
    while t <= b + step / 2:
        v = round(t / step) * step
        is0 = zero and abs(v) < 1e-9
        out.append(f'<line x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{top}" y2="{top + len(rows) * rowH}" '
                   f'stroke="{AXIS if is0 else GRID}" stroke-width="{2 if is0 else 1}"/>')
        label = f"{round(v * 100)}%" if pct else f"{v:.2f}"
        out.append(f'<text x="{x(v):.1f}" y="{top + len(rows) * rowH + 26}" text-anchor="middle" fill="{INK2}">{label}</text>')
        t += step
    for i, r in enumerate(rows):
        y = top + i * rowH + rowH / 2
        c = r.get("color", BLUE)
        weight = ' font-weight="600"' if r.get("bold") else ""
        out.append(f'<text x="{L - 16}" y="{y + 6}" text-anchor="end" fill="{INK}"{weight}>{esc(r["label"])}</text>')
        if r.get("range"):
            out.append(f'<line x1="{x(r["range"][0]):.1f}" x2="{x(r["range"][1]):.1f}" y1="{y}" y2="{y}" stroke="{c}" '
                       f'stroke-width="4" stroke-linecap="round"/>')
        if r["mean"] is not None:
            out.append(f'<circle cx="{x(r["mean"]):.1f}" cy="{y}" r="8" fill="{c}" stroke="#fcfcfb" stroke-width="2.5"/>')
        out.append(f'<text x="{W - R + 16}" y="{y + 6}" fill="{INK}">{esc(r.get("right", ""))}</text>')
    out.append(f'<text x="{(L + W - R) / 2}" y="{H - 14}" text-anchor="middle" fill="{INK2}">{esc(axis)}</text>')
    return "\n".join(out + ["</svg>"])


def main() -> int:
    work = Path(sys.argv[1] if len(sys.argv) > 1 else "experiments/trust/work/pilot2")
    an = json.loads((work / "analysis.json").read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    made = []
    comp = an.get("compare")
    if comp:
        d = comp["main"]["designs"]
        rows = [{"label": NAMES.get(k, k) + (" (control)" if k == "OPUS_PROSE" else ""), "mean": v["mean"],
                 "range": v["range"], "shade": v.get("could_be_best"), "right": f'{v["mean"]:.3f}',
                 "color": BLUE if k.startswith("OPUS") else ORANGE, "bold": k == "OPUS_PROSE"}
                for k, v in sorted(d.items(), key=lambda kv: -kv[1]["mean"])]
        (OUT / "p2-compare.svg").write_text(forest(rows, left="Way of working (best at top)", right="Average",
            axis="Share of hidden checks passed. Dot = average, line = 95% range over briefs", lo=0.5, hi=1.0, pct=True,
            title="Ways of working on the comparison briefs"), encoding="utf-8")
        made.append("p2-compare.svg")
        leads = comp["main"].get("leads_over_control") or {}
        if leads:
            rows = [{"label": NAMES.get(k, k), "mean": v["lead"], "range": v["range"],
                     "right": f'{v["lead"]:+.3f}  p={v["p_holm"]:.2f}', "color": BLUE if k.startswith("OPUS") else ORANGE}
                    for k, v in leads.items()]
            (OUT / "p2-leads.svg").write_text(forest(rows, left="Against Opus builds from prose", right="Lead (Holm p)",
                axis="Lead over the control (right of 0 = better). Line = 95% range", zero=True,
                title="Leads over the control"), encoding="utf-8")
            made.append("p2-leads.svg")
    ta = an.get("takeapart")
    if ta:
        rows = [{"label": PART.get(k, k), "mean": v["effect"], "range": v["range"], "right": f'{v["effect"]:+.3f}',
                 "color": ORANGE} for k, v in ta["effects"].items() if k in PART]
        (OUT / "p2-parts.svg").write_text(forest(rows, left="Part of the script", right="Effect",
            axis="Effect on the share of checks passed (right of 0 = helps, left = hurts). Line = 95% range", zero=True,
            title="What each part of the script does"), encoding="utf-8")
        made.append("p2-parts.svg")
    fin = an.get("final")
    if fin and fin.get("sealed_means"):
        rows = [{"label": NAMES.get(k, k), "mean": v["mean"], "range": v.get("range"), "right": f'{v["mean"]:.3f}',
                 "color": BLUE} for k, v in sorted(fin["sealed_means"].items(), key=lambda kv: -kv[1]["mean"])]
        (OUT / "p2-final.svg").write_text(forest(rows, left="Design", right="Average",
            axis="Share of hidden checks passed on the sealed briefs. Line = 95% range", lo=0.5, hi=1.0, pct=True,
            title="Final check on the sealed briefs"), encoding="utf-8")
        made.append("p2-final.svg")
    print("made:", ", ".join(made) or "nothing yet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
