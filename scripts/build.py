#!/usr/bin/env python3
"""Recompute TokWatt derived columns and the task_defaults table.

Usage:  python scripts/build.py [--factor-accel 1.72] [--pue-ref 1.13]

Derived values (never edit them by hand):
  data/estimates.csv      -> harmonization_factor, energy_wh_harmonized
  data/task_defaults.csv  -> central / low / high per task
"""
import argparse
import csv
import math
import os
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def read(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        return rows, list(rows[0].keys()) if rows else []


def num(x):
    return None if x in ("", None) else float(x)


def factor_for(row, f_accel, pue_ref):
    """Scale a reported value to the 'server + facility overhead' boundary."""
    if num(row["energy_wh"]) is None and num(row["energy_wh_low"]) is None:
        return None
    if row["method"] == "measured_gpu_x2_heuristic":
        return 1.0  # source already doubled GPU energy to approximate the total
    acc, host, pue = row["incl_accelerator"], row["incl_host"], row["incl_overhead_pue"]
    if acc == "yes" and host == "no":
        return f_accel
    if host in ("yes", "approx") and pue == "no":
        return pue_ref
    return 1.0  # already at the target boundary, or boundary unknown (left unadjusted)


def main():
    ap = argparse.ArgumentParser()
    params = {r["parameter"]: float(r["value"]) for r in read("parameters.csv")[0]}
    ap.add_argument("--factor-accel", type=float, default=params["F_ACCELERATOR_TO_FULL"])
    ap.add_argument("--pue-ref", type=float, default=params["PUE_REF"])
    a = ap.parse_args()

    est, header = read("estimates.csv")
    for r in est:
        f = factor_for(r, a.factor_accel, a.pue_ref)
        r["harmonization_factor"] = "" if f is None else f"{f:g}"
        e = num(r["energy_wh"])
        r["energy_wh_harmonized"] = "" if (f is None or e is None) else f"{round(e * f, 6):g}"
    with open(os.path.join(DATA, "estimates.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(est)

    tasks, _ = read("tasks.csv")
    out = []
    for t in tasks:
        tid = t["task_id"]
        rows = [r for r in est if r["task"] == tid and r["energy_wh_harmonized"] != ""]
        ref = [r for r in rows if r["in_reference_set"] == "TRUE"]
        if not ref:
            continue
        pts, lows, highs = [], [], []
        for r in ref:
            f = float(r["harmonization_factor"])
            p = float(r["energy_wh"])
            sd = num(r["energy_wh_sd"])
            lo, hi = num(r["energy_wh_low"]), num(r["energy_wh_high"])
            lo = lo if lo is not None else (max(0.0, p - sd) if sd is not None else p)
            hi = hi if hi is not None else (p + sd if sd is not None else p)
            pts.append(p * f)
            lows.append(lo * f)
            highs.append(hi * f)
        geo = math.exp(sum(math.log(x) for x in pts) / len(pts))
        all_pts = [float(r["energy_wh_harmonized"]) for r in rows]
        out.append({
            "task_id": tid,
            "label": t["label"],
            "family": t["family"],
            "in_app": t["in_app"],
            "central_wh": f"{statistics.median(pts):.4g}",
            "low_wh": f"{min(lows):.4g}",
            "high_wh": f"{max(highs):.4g}",
            "geomean_wh": f"{geo:.4g}",
            "n_estimates": len(ref),
            "n_sources": len({r['source_id'] for r in ref}),
            "median_all_rows_wh": f"{statistics.median(all_pts):.4g}",
            "n_all_rows": len(rows),
            "estimate_ids": " ".join(r["estimate_id"] for r in ref),
            "rule": "central = median of harmonized reference-set points; low/high = min/max of harmonized reported intervals (IQR, range, or mean +/- SD clipped at 0)",
            "factor_accel": f"{a.factor_accel:g}",
            "pue_ref": f"{a.pue_ref:g}",
        })
    with open(os.path.join(DATA, "task_defaults.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    for o in out:
        print(f"{o['task_id']:<24} {o['central_wh']:>8} Wh  [{o['low_wh']} - {o['high_wh']}]  n={o['n_estimates']} ({o['n_sources']} sources)")


if __name__ == "__main__":
    main()
