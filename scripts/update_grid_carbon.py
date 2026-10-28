#!/usr/bin/env python3
"""Rebuild data/grid_carbon.csv from the Our World in Data energy dataset.

Usage:
  1. Download https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv
  2. python scripts/update_grid_carbon.py path/to/owid-energy-data.csv

Keeps, for every country and the main world regions, the latest year with a value of
`carbon_intensity_elec` (life-cycle gCO2e per kWh of generated electricity, from Ember),
and drops years before MIN_YEAR.
"""
import csv
import os
import sys

MIN_YEAR = 2022
REGIONS = {"World", "Africa", "Asia", "Europe", "European Union (27)", "North America", "South America", "Oceania"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "grid_carbon.csv")


def main(src):
    best = {}
    with open(src, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            value, iso, name = r.get("carbon_intensity_elec", ""), r.get("iso_code", ""), r["country"]
            if not value or (not iso and name not in REGIONS):
                continue
            key, year = iso or name, int(r["year"])
            if key not in best or year > best[key][1]:
                best[key] = (name, year, float(value), iso)
    rows = sorted((v for v in best.values() if v[1] >= MIN_YEAR), key=lambda v: (v[3] != "", v[0]))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["region", "iso_code", "year", "carbon_intensity_gco2e_per_kwh", "source_id"])
        for name, year, value, iso in rows:
            w.writerow([name, iso, year, round(value, 1), "OWID_ENERGY"])
    print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
