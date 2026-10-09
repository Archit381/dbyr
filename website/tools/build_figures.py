#!/usr/bin/env python3
"""Regenerate the generated blocks of website/index.html.

Three blocks on the landing page are derived rather than hand-written, so that
they cannot drift from the schemas or the paper:

  fig1      the DBYR lifecycle, laid out from the four record names
  fig2      the record schema, built from the \\fig*List macros that
            code/reproduce.sh writes into generated/schema_fields.tex
  timeline  the Appendix A event table, converted from the paper's longtable

Each is spliced into index.html between
``<!-- BEGIN generated: NAME -->`` and ``<!-- END generated: NAME -->``.

    python website/tools/build_figures.py [--paper PATH_TO_main.tex]

Without --paper the timeline block is left as it is, so the figures can be
rebuilt without a copy of the paper source to hand.  Figure 3 (timeline by
thread) is hand-authored SVG and is not touched.
"""

from __future__ import annotations

import argparse
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
INDEX = ROOT / "website" / "index.html"
SCHEMA_FIELDS = ROOT / "generated" / "schema_fields.tex"

IND = " " * 14  # indentation of elements inside <svg> in index.html


# --------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------
def field_list(tex: str, macro: str) -> list[tuple[str, str]]:
    """Parse one \\newcommand{\\figXList}{P/a, R/b, ...} into [(tier, field)]."""
    m = re.search(r"\\newcommand\{\\" + macro + r"\}\{(.*?)\}\n", tex, re.S)
    if not m:
        raise SystemExit(f"{macro} not found in {SCHEMA_FIELDS}")
    out = []
    for item in m.group(1).split(","):
        tier, field = item.strip().replace("\\_", "_").split("/", 1)
        out.append((tier, field))
    return out


# --------------------------------------------------------------------------
# figure 2: record schema at a glance
# --------------------------------------------------------------------------
ROW, HEAD, PAD = 20.0, 46.0, 10.0
COLW, GAP, X0 = 300.0, 35.0, 10.0


def schema_column(x: float, y: float, title: str, fields: list[tuple[str, str]]):
    h = HEAD + ROW * len(fields) + PAD
    s = [
        f'{IND}<rect class="fig-box" x="{x:g}" y="{y:g}" width="{COLW:g}" height="{h:g}" rx="6" />',
        f'{IND}<line class="tl-grid" x1="{x:g}" y1="{y + HEAD - 8:g}" '
        f'x2="{x + COLW:g}" y2="{y + HEAD - 8:g}" />',
        f'{IND}<text class="fig-label" x="{x + 14:g}" y="{y + 20:g}">{title}</text>',
        f'{IND}<text class="fig-sublabel" x="{x + 14:g}" y="{y + 33:g}">'
        f"{len(fields)} required fields</text>",
    ]
    for i, (tier, field) in enumerate(fields):
        cy = y + HEAD + ROW * i + ROW / 2
        if i:
            s.append(
                f'{IND}<line class="tl-grid" x1="{x + 14:g}" y1="{cy - ROW / 2:g}" '
                f'x2="{x + COLW - 14:g}" y2="{cy - ROW / 2:g}" />'
            )
        cls = "fig-dot-public" if tier == "P" else "fig-dot-restricted"
        s.append(f'{IND}<circle class="{cls}" cx="{x + 24:g}" cy="{cy:g}" r="3.5" />')
        s.append(
            f'{IND}<text class="fig-field" x="{x + 38:g}" y="{cy + 4:g}">'
            f"{html.escape(field)}</text>"
        )
    return s, h


def build_fig2(tex: str) -> str:
    intent = field_list(tex, "figIntentList")
    closeout = field_list(tex, "figCloseoutList")
    notice = field_list(tex, "figNoticeList")
    runtime = field_list(tex, "figRuntimeList")

    parts: list[str] = []
    s, h_intent = schema_column(X0, 10, "TrainingRunIntent", intent)
    parts += s
    s, _ = schema_column(X0 + COLW + GAP, 10, "TrainingRunCloseout", closeout)
    parts += s
    x3 = X0 + 2 * (COLW + GAP)
    s, h_notice = schema_column(x3, 10, "ExceptionNotice", notice)
    parts += s
    s, _ = schema_column(x3, 10 + h_notice + 18, "SystemRuntimeRecord", runtime)
    parts += s

    legy = 10 + h_intent + 30
    parts += [
        f'{IND}<circle class="fig-dot-public" cx="{X0 + 14:g}" cy="{legy:g}" r="3.5" />',
        f'{IND}<text class="fig-sublabel" x="{X0 + 26:g}" y="{legy + 4:g}">Public at filing</text>',
        f'{IND}<circle class="fig-dot-restricted" cx="{X0 + 130:g}" cy="{legy:g}" r="3.5" />',
        f'{IND}<text class="fig-sublabel" x="{X0 + 142:g}" y="{legy + 4:g}">Restricted at filing</text>',
        f'{IND}<text class="fig-sublabel" x="{X0 + 275:g}" y="{legy + 4:g}">'
        "Tiers nest: a public field can hold restricted or sealed parts.</text>",
    ]

    return (
        f'            <svg viewBox="0 0 1000 {legy + 20:g}" role="img" '
        'aria-labelledby="fig2-title fig2-desc">\n'
        f'{IND}<title id="fig2-title">Record schema at a glance</title>\n'
        f'{IND}<desc id="fig2-desc">The fields each of the four DBYR records must carry under '
        f"the v0.3 rules, marked by disclosure tier at filing: TrainingRunIntent "
        f"({len(intent)} fields), TrainingRunCloseout ({len(closeout)}), ExceptionNotice "
        f"({len(notice)}) and SystemRuntimeRecord ({len(runtime)}).</desc>\n"
        + "\n".join(parts)
        + "\n            </svg>"
    )


# --------------------------------------------------------------------------
# figure 1: the lifecycle
# --------------------------------------------------------------------------
BOXES = [
    ("BEFORE THE RUN, \u2265 3 DAYS", "TrainingRunIntent",
     "topology, safeguards,", "criteria, monitors"),
    ("WITHIN 72 H OF DETECTION", "ExceptionNotice",
     "events, kinds, criteria,", "parties, action"),
    ("EVERY 30 DAYS / AT END", "TrainingRunCloseout",
     "events, pauses, notices,", "preservation, scope"),
    ("BEFORE DEPLOYMENT", "SystemRuntimeRecord",
     "scaffolding, scaling,", "inter-agent comms"),
]
TIERS = [
    ("tint", "Public", "existence, compute band,", "commitment hashes", ""),
    ("mid", "Restricted", "full record; vetted evaluator", "and auditor access", ""),
    ("dark", "Sealed", "withheld pending challenge,", "salted hash commitments", " on-dark"),
]
BW, BH, BY = 236.0, 112.0, 10.0
LY, LH = 196.0, 58.0
TY, TH, TW = 300.0, 86.0, 300.0


def build_fig1() -> str:
    q: list[str] = []
    for i, (kick, label, s1, s2) in enumerate(BOXES):
        x = 10 + i * (BW + 12)
        q += [
            f'{IND}<rect class="fig-box" x="{x:g}" y="{BY:g}" width="{BW:g}" height="{BH:g}" rx="6" />',
            f'{IND}<text class="fig-title" x="{x + 16:g}" y="{BY + 26:g}">{html.escape(kick)}</text>',
            f'{IND}<text class="fig-label" x="{x + 16:g}" y="{BY + 52:g}">{label}</text>',
            f'{IND}<text class="fig-sublabel" x="{x + 16:g}" y="{BY + 74:g}">{s1}</text>',
            f'{IND}<text class="fig-sublabel" x="{x + 16:g}" y="{BY + 90:g}">{s2}</text>',
            f'{IND}<line class="fig-arrow" x1="{x + BW / 2:g}" y1="{BY + BH:g}" '
            f'x2="{x + BW / 2:g}" y2="{LY - 4:g}" marker-end="url(#fig1-arrow)" />',
        ]
    q += [
        f'{IND}<rect class="fig-box dark" x="10" y="{LY:g}" width="980" height="{LH:g}" rx="6" />',
        f'{IND}<text class="fig-label on-dark" x="500" y="{LY + 25:g}" text-anchor="middle">'
        "Append-only record: evaluator archive (Layer A) or register (Layer B)</text>",
        f'{IND}<text class="fig-sublabel on-dark" x="500" y="{LY + 44:g}" text-anchor="middle">'
        "hash-chained \u00b7 Ed25519-signed \u00b7 salted commitments for hidden fields</text>",
    ]
    for i, (kind, label, s1, s2, dark) in enumerate(TIERS):
        x = 10 + i * (TW + 40)
        q += [
            f'{IND}<line class="fig-arrow" x1="{x + TW / 2:g}" y1="{LY + LH:g}" '
            f'x2="{x + TW / 2:g}" y2="{TY - 4:g}" marker-end="url(#fig1-arrow)" />',
            f'{IND}<rect class="fig-box {kind}" x="{x:g}" y="{TY:g}" width="{TW:g}" '
            f'height="{TH:g}" rx="6" />',
            f'{IND}<text class="fig-label{dark}" x="{x + 16:g}" y="{TY + 28:g}">{label}</text>',
            f'{IND}<text class="fig-sublabel{dark}" x="{x + 16:g}" y="{TY + 50:g}">{s1}</text>',
            f'{IND}<text class="fig-sublabel{dark}" x="{x + 16:g}" y="{TY + 66:g}">{s2}</text>',
        ]
    q += [
        f'{IND}<text class="fig-sublabel" x="10" y="{TY + TH + 24:g}">filed &amp; signed '
        "\u2192 one append-only record \u2192 projected through a per-field redaction map</text>"
    ]

    return (
        f'            <svg viewBox="0 0 1000 {TY + TH + 34:g}" role="img" '
        'aria-labelledby="fig1-title fig1-desc">\n'
        f'{IND}<title id="fig1-title">The DBYR lifecycle</title>\n'
        f'{IND}<desc id="fig1-desc">Four signed records \u2014 TrainingRunIntent, '
        "ExceptionNotice, TrainingRunCloseout and SystemRuntimeRecord \u2014 are filed at "
        "different points in a covered run\u2019s life and flow into one append-only, "
        "hash-chained record, which projects into Public, Restricted and Sealed disclosure "
        "tiers.</desc>\n"
        f"{IND}<defs>\n"
        f'{IND}  <marker id="fig1-arrow" viewBox="0 0 10 10" refX="8" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">\n'
        f'{IND}    <path class="fig-arrow-head" d="M0,0 L10,5 L0,10 z" />\n'
        f"{IND}  </marker>\n{IND}</defs>\n" + "\n".join(q) + "\n            </svg>"
    )


# --------------------------------------------------------------------------
# timeline table (Appendix A of the paper)
# --------------------------------------------------------------------------
def delatex(s: str) -> str:
    s = s.strip().replace(r"\$", "\x00D\x00")
    s = re.sub(r"\$\\rightarrow\$", "\u2192", s)
    s = re.sub(r"\$\\sim\$", "~", s)
    s = re.sub(r"\$<\$", "<", s)
    s = re.sub(r"\$([^$]*)\$", r"\1", s).replace("\x00D\x00", "$")
    s = re.sub(r"\\textbf\{([^}]*)\}", r"\1", s)
    s = s.replace("``", '"').replace("''", '"').replace("--", "\u2013")
    s = s.replace(r"\&", "&").replace(r"\%", "%").replace(r"\_", "_").replace("\\ ", " ")
    return re.sub(r"\s+", " ", s).strip()


def build_timeline(paper: pathlib.Path) -> str:
    tex = paper.read_text(encoding="utf-8")
    start = tex.index(r"\section{Consolidated timeline of the three threads}")
    body = tex[tex.index(r"\endfoot", start) + 8 : tex.index(r"\end{longtable}", start)]
    rows = []
    for raw in body.split(r"\\"):
        raw = raw.replace(r"\addlinespace", "").strip()
        if not raw:
            continue
        cells = [delatex(c) for c in raw.split("&")]
        if len(cells) != 4:
            print(f"  skipped a row with {len(cells)} cells: {raw[:60]}", file=sys.stderr)
            continue
        rows.append(cells)
    print(f"  timeline: {len(rows)} events")
    return "\n".join(
        "            <tr>\n"
        + "".join(f"              <td>{html.escape(c)}</td>\n" for c in row)
        + "            </tr>"
        for row in rows
    )


# --------------------------------------------------------------------------
def splice(page: str, name: str, block: str) -> str:
    begin, end = f"<!-- BEGIN generated: {name} -->", f"<!-- END generated: {name} -->"
    i, j = page.index(begin) + len(begin), page.index(end)
    return page[:i] + "\n" + block + "\n" + " " * 10 + page[j:]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--paper", type=pathlib.Path,
                    help="path to the paper's main.tex (rebuilds the timeline table)")
    args = ap.parse_args()

    page = INDEX.read_text(encoding="utf-8")
    tex = SCHEMA_FIELDS.read_text(encoding="utf-8")

    page = splice(page, "fig1", build_fig1())
    page = splice(page, "fig2", build_fig2(tex))
    if args.paper:
        page = splice(page, "timeline", build_timeline(args.paper))

    INDEX.write_text(page, encoding="utf-8")
    print(f"wrote {INDEX.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
