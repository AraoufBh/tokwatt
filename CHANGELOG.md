# Changelog

## 0.1.0 — 2026-10-25

First public draft.

- 134 estimates from 13 sources covering chat, long-document, reasoning, agentic, image, video and classic ML tasks.
- Five-component boundary annotation and reproducible harmonization (`scripts/build.py`).
- Derived per-task reference values (`data/task_defaults.csv`).
- Token factors, data-centre macro indicators (IEA 2025, Gartner 2026, LBNL 2024), grid carbon intensity for 220 regions (Our World in Data / Ember), everyday equivalents.
- Article source in `paper/` (LaTeX), with `paper/analysis.py` generating its numbers, tables and figures from `data/`.
- Source metadata corrections before release: ML.ENERGY Benchmark recorded as peer reviewed (NeurIPS 2025); exact headline for the EIA price source; Jegham et al. values spot-checked against arXiv v6.
- All rows checked by the author against their cited locator (`verification = human_verified`).
