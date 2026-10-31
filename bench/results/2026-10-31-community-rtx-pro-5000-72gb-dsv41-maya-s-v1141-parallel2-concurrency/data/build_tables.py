#!/usr/bin/env python3
"""Verify this entry's README numbers against data/summary.json and that every
cited raw file exists.

Usage: python3 data/build_tables.py          # print the headline table
       python3 data/build_tables.py --check  # assert README + sources (exit 1 on drift)
Stdlib only.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENTRY = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(ENTRY)))

with open(os.path.join(HERE, "summary.json"), encoding="utf-8") as handle:
    DATA = json.load(handle)

soak = DATA["soak"]


def headline_table():
    rows = [
        ("decode solo gen>=200 median", soak["decode_solo_gen200plus"]["median"]),
        ("decode concurrent gen>=200 median", soak["decode_concurrent_gen200plus"]["median"]),
        ("per-lane concurrency ratio %", soak["decode_concurrency_ratio_pct"]),
        ("prefill fresh>=20K solo median", soak["prefill_solo_fresh20kplus"]["median"]),
        ("prefill fresh>=20K concurrent median", soak["prefill_concurrent_fresh20kplus"]["median"]),
        ("cache hit requests %", soak["cache_hit_request_pct"]),
        ("cache hit tokens %", soak["cache_hit_token_pct"]),
        ("deepest prompt tokens", soak["max_prompt_tokens"]),
        ("deepest cold read tok/s", soak["max_prompt_fresh_read_tps"]),
        ("draft acceptance all %", soak["draft_acceptance_all_pct"]),
        ("draft acceptance concurrent %", soak["draft_acceptance_concurrent_pct"]),
    ]
    for name, value in rows:
        print(f"{value:>12}  {name}")


def check():
    problems = []
    sources = [DATA["sources"]["requests_csv"]] + DATA["sources"]["run_excerpts"] + [DATA["sources"]["config"]]
    for rel in sources:
        if not os.path.exists(os.path.join(ENTRY, rel)):
            problems.append(f"missing source: {rel}")
    text = open(os.path.join(ENTRY, "README.md"), encoding="utf-8").read()
    zh = os.path.join(ENTRY, "README.zh-CN.md")
    texts = [text] + ([open(zh, encoding="utf-8").read()] if os.path.exists(zh) else [])
    must = [
        str(soak["decode_solo_gen200plus"]["median"]),
        str(soak["decode_concurrent_gen200plus"]["median"]),
        str(soak["decode_concurrency_ratio_pct"]),
        f'{soak["prefill_solo_fresh20kplus"]["median"]:,}',
        f'{soak["prefill_concurrent_fresh20kplus"]["median"]:,}',
        str(soak["cache_hit_request_pct"]),
        str(soak["cache_hit_token_pct"]),
        f'{soak["max_prompt_tokens"]:,}',
        f'{soak["max_prompt_fresh_read_tps"]:,}',
        str(soak["draft_acceptance_all_pct"]),
        str(soak["draft_acceptance_concurrent_pct"]),
        str(DATA["smoke_controlled"]["first_fresh_prompt_after_boot"]["read_tps"]),
        DATA["engine"]["sha256"],
    ]
    for value in must:
        joined = "\n".join(texts)
        if value in joined or value.replace(",", "") in joined.replace(",", ""):
            continue
        problems.append(f"number not found in README: {value}")
    # raw request count cross-check
    with open(os.path.join(ENTRY, DATA["sources"]["requests_csv"]), encoding="utf-8") as handle:
        n = sum(1 for _ in handle) - 1
    if n != 1554:
        problems.append(f"raw csv rows {n} != 1554")
    if soak["requests"] != 1495:
        problems.append("soak request count drifted")
    return problems


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        bad = check()
        print("check:", "OK" if not bad else bad)
        sys.exit(0 if not bad else 1)
    headline_table()
