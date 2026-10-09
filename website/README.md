# DBYR landing page

Static HTML/CSS paper page for the v0.3 protocol. No build step, no JavaScript.

## Preview locally

```bash
cd website && python -m http.server 8000
```

Then open `http://localhost:8000/`.

## Deployment

`.github/workflows/deploy-pages.yml` publishes this directory to GitHub Pages on
every push to `main` that touches `website/**`.

## Regenerating the figures

Figures 1 and 2 and the Appendix A timeline table are generated rather than hand
written, so that they cannot drift from the schemas or the paper:

- **Figure 2 (record schema)** is built from the `\fig*List` macros in
  `generated/schema_fields.tex`, which `code/reproduce.sh` writes from the JSON
  Schemas. If a field is added or its tier changes, rerun `reproduce.sh` and
  rebuild the figure.
- **Figure 1 (lifecycle)** is laid out from the same four record names.
- **Table 1 (timeline)** is converted from the Appendix A `longtable` in the
  paper's `main.tex`.

Figure 3 (timeline by thread) is hand-authored SVG. Its horizontal scale is
~6.89 px/day with 1 May 2026 at x=90, so a marker's x is
`90 + (days since 1 May) * 6.89`.

## Assets

| File | What it is |
|---|---|
| `assets/declare_before_you_run_frontier_training_evaluation_filing_standard.pdf` | the current paper. The filename is the one already in circulation, so keep it stable when dropping in a new build. |

The original September 2026 submission is not kept here; the endnote at the foot
of the page links to the
[Apart project page](https://apartresearch.com/sprints/projects/declare-before-you-run-an-open-filing-standard-for-frontier-training-and-evaluation-runs-dkok)
for it.
