#!/usr/bin/env python3
"""Embed the current data tables in the TokWatt app.

  app/tokwatt.html   page source; its <script id="tokwatt-data"> block is rewritten in place
  app/index.html     the same page wrapped as a standalone document (GitHub Pages, local use)

Run after scripts/build.py whenever data/ changes:
  python scripts/build.py && python scripts/validate.py && python scripts/build_app.py
"""
import datetime
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SRC = os.path.join(ROOT, "app", "tokwatt.html")
OUT = os.path.join(ROOT, "app", "index.html")
OUT_ROOT = os.path.join(ROOT, "index.html")  # served by GitHub Pages at https://<user>.github.io/tokwatt/
VERSION = "0.1.0"
FILES = ["estimates.csv", "sources.csv", "task_defaults.csv", "tasks.csv", "grid_carbon.csv",
         "macro.csv", "equivalents.csv", "parameters.csv", "token_factors.csv", "boundary_components.csv"]

WRAPPER = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>:root{{color-scheme:light;padding-top:env(safe-area-inset-top);padding-bottom:env(safe-area-inset-bottom)}}body{{margin:0;font:14px system-ui,sans-serif}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
</head>
<body>
{page}
</body>
</html>
"""


def main():
    files = {}
    for name in FILES:
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            files[name] = f.read()
    payload = {"version": VERSION, "built": datetime.date.today().isoformat(), "files": files}
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    with open(SRC, encoding="utf-8") as f:
        page = f.read()
    pattern = re.compile(r'(<script type="application/json" id="tokwatt-data">)(.*?)(</script>)', re.S)
    if not pattern.search(page):
        raise SystemExit("data block not found in app/tokwatt.html")
    page = pattern.sub(lambda m: m.group(1) + blob + m.group(3), page, count=1)
    with open(SRC, "w", encoding="utf-8") as f:
        f.write(page)
    for out in (OUT, OUT_ROOT):
        with open(out, "w", encoding="utf-8") as f:
            f.write(WRAPPER.format(page=page))
    print(f"embedded {len(files)} tables ({len(blob) // 1024} KB) -> app/tokwatt.html, app/index.html, index.html")


if __name__ == "__main__":
    main()
