# TokWatt paper

LaTeX source of *TokWatt: an open, boundary-annotated database of AI inference energy, from chat answers to agents* (Abderaouf Bahi, LIMA Laboratory).

| File | Role |
|---|---|
| `main.tex` | Article (pdfLaTeX, natbib author–year, `plainnat`) |
| `references.bib` | Bibliography; every entry was checked against the publisher, Crossref, arXiv or the original page |
| `analysis.py` | Regenerates every database-derived number, table and figure from `../data/` |
| `generated/` | Output of `analysis.py`: `stats.tex` (macros used in the text) and `tab_*.tex` (tables). Do not edit by hand |
| `figures/` | Output of `analysis.py`: `fig_ladder.pdf`, `fig_chat.pdf`, `fig_boundary.pdf` |
| `arxiv_metadata.txt` | Title, plain-text abstract, comments and categories for the arXiv form |

## Build

```bash
python paper/analysis.py          # from the repository root; needs matplotlib
cd paper
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Every number derived from the data comes from `generated/stats.tex`. After any change to `data/`, run `scripts/build.py`, `scripts/validate.py`, then `paper/analysis.py`, and recompile: the text, tables and figures update together. The sentence on verification status (`\verificationSentence`) also updates itself from the `verification` column.

## Before submitting

1. Replace the placeholder `USERNAME` (GitHub account) in `main.tex`, `references.bib` and `arxiv_metadata.txt`.
2. Check every row of `data/estimates.csv` against its locator and set `verification` to `human_verified`; rerun the build and `analysis.py`.
3. Confirm the affiliation line and the competing-interests statement.
4. Build the arXiv package: `main.tex`, `main.bbl`, `references.bib`, `generated/`, `figures/` (no subfolder above them).
