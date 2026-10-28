#!/usr/bin/env python3
"""Schema and consistency checks for the TokWatt tables. Exit code 1 on any error."""
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
errors, warnings = [], []


def read(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(x, ctx, field):
    if x in ("", None):
        return None
    try:
        return float(x)
    except ValueError:
        errors.append(f"{ctx}: {field} is not numeric ({x!r})")
        return None


FLAG_VALUES = {
    "incl_accelerator": {"yes", "no", "unknown"},
    "incl_host": {"yes", "approx", "no", "unknown"},
    "incl_idle": {"yes", "partial", "approx", "no", "unknown"},
    "incl_overhead_pue": {"yes", "approx", "no", "unknown"},
    "incl_embodied": {"yes", "no", "unknown"},
}
METHODS = {"measured", "modeled", "disclosed", "lca", "estimated_from_tokens", "measured_gpu_x2_heuristic", "secondary_report"}

sources = read("sources.csv")
src_ids = [s["source_id"] for s in sources]
if len(src_ids) != len(set(src_ids)):
    errors.append("duplicate source_id")
for s in sources:
    if not s["url"].startswith("https://"):
        errors.append(f"{s['source_id']}: url must be https")
tasks = {t["task_id"] for t in read("tasks.csv")}
est = read("estimates.csv")
ids = [e["estimate_id"] for e in est]
if len(ids) != len(set(ids)):
    errors.append("duplicate estimate_id")
used = set()
for e in est:
    c = e["estimate_id"]
    used.add(e["source_id"])
    if e["source_id"] not in src_ids:
        errors.append(f"{c}: unknown source_id {e['source_id']}")
    if e["task"] not in tasks:
        errors.append(f"{c}: unknown task {e['task']}")
    if e["method"] not in METHODS:
        errors.append(f"{c}: unknown method {e['method']}")
    for k, allowed in FLAG_VALUES.items():
        if e[k] not in allowed:
            errors.append(f"{c}: {k}={e[k]!r} not in {sorted(allowed)}")
    if e["in_reference_set"] not in ("TRUE", "FALSE"):
        errors.append(f"{c}: in_reference_set must be TRUE/FALSE")
    p = num(e["energy_wh"], c, "energy_wh")
    lo = num(e["energy_wh_low"], c, "energy_wh_low")
    hi = num(e["energy_wh_high"], c, "energy_wh_high")
    sd = num(e["energy_wh_sd"], c, "energy_wh_sd")
    f = num(e["harmonization_factor"], c, "harmonization_factor")
    h = num(e["energy_wh_harmonized"], c, "energy_wh_harmonized")
    for v, name in ((p, "energy_wh"), (lo, "low"), (hi, "high"), (sd, "sd")):
        if v is not None and v < 0:
            errors.append(f"{c}: negative {name}")
    if p is not None and lo is not None and lo > p:
        errors.append(f"{c}: low > point")
    if p is not None and hi is not None and hi < p:
        errors.append(f"{c}: high < point")
    if p is not None and (f is None or h is None):
        errors.append(f"{c}: missing derived columns, run scripts/build.py")
    if p is not None and f is not None and h is not None and abs(p * f - h) > 1e-6 * max(1.0, h):
        errors.append(f"{c}: energy_wh_harmonized != energy_wh x factor")
    if e["in_reference_set"] == "TRUE" and p is None:
        errors.append(f"{c}: reference-set row without a point estimate")
    if e["method"] == "secondary_report" and e["in_reference_set"] == "TRUE":
        errors.append(f"{c}: secondary reports cannot be in the reference set")
    num(e["co2e_g"], c, "co2e_g")
    num(e["water_ml"], c, "water_ml")
    if e["reported_in"]:
        used.add(e["reported_in"])
        if e["reported_in"] not in src_ids:
            errors.append(f"{c}: unknown reported_in {e['reported_in']}")

for name, id_field, src_fields in (("macro.csv", "macro_id", ("source_id", "reported_in")),
                                   ("token_factors.csv", "factor_id", ("source_id",)),
                                   ("equivalents.csv", "eq_id", ("source_id",)),
                                   ("parameters.csv", "parameter", ("source_id",)),
                                   ("grid_carbon.csv", "region", ("source_id",))):
    rows = read(name)
    if len({r[id_field] for r in rows}) != len(rows):
        errors.append(f"{name}: duplicate {id_field}")
    for r in rows:
        for fld in src_fields:
            for sid in [x.strip() for x in r.get(fld, "").split(";") if x.strip()]:
                used.add(sid)
                if sid not in src_ids:
                    errors.append(f"{name} {r[id_field]}: unknown {fld} {sid}")

for s in src_ids:
    if s not in used:
        warnings.append(f"source {s} is not referenced by any table")

for r in read("grid_carbon.csv"):
    v = num(r["carbon_intensity_gco2e_per_kwh"], r["region"], "carbon_intensity")
    if v is None or not (0 <= v <= 1500):
        errors.append(f"grid_carbon {r['region']}: implausible value {v}")
    if int(r["year"]) < 2022:
        errors.append(f"grid_carbon {r['region']}: stale year {r['year']}")

for w in warnings:
    print("WARN ", w)
for e in errors:
    print("ERROR", e)
print(f"{len(est)} estimates, {len(sources)} sources, {len(errors)} errors, {len(warnings)} warnings")
sys.exit(1 if errors else 0)
