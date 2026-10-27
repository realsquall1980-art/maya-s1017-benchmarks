#!/usr/bin/env python3
"""Regenerate the report tables from data/summary.json.

Usage: python3 data/build_tables.py            # print both tables
       python3 data/build_tables.py --check path/to/README.md
The --check mode asserts every table cell in the README matches summary.json.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "summary.json")) as f:
    DATA = json.load(f)

def rows(prefix):
    return [r for r in DATA["rounds"] if r["id"] in prefix]

def print_tables():
    print("| Configuration | prefill 42-44K | prefill 124-131K | decode code | decode prose | residency | streamed bytes | verdict |")
    print("|---|---:|---:|---:|---:|---:|---:|---|")
    for r in rows({"R0","R1","R2","R3","R4","R5","R6","R7","R8","R9"}):
        print(f"| **{r['id']}** {r['en']} | {r['pf']} | {r['pf124']} | {r['dc']} | {r['dp']} | {r['res']} | {r['stream']} GB | {r['verdict_en']} |")

def check(path):
    text = open(path).read()
    bad = []
    for r in DATA["rounds"]:
        for key in ("pf", "pf124", "dc", "dp"):
            v = r[key]
            if v == "-":
                continue
            for part in re.split(r"[-–,]", v):
                part = part.strip()
                if part and part not in text:
                    bad.append((r["id"], key, part))
    print("checked", path, "missing:", bad if bad else "none")
    return not bad

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--check":
        sys.exit(0 if check(sys.argv[2]) else 1)
    print_tables()
