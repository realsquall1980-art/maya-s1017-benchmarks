# Maya-S / DeepSeek-V4.1-Flash-1017 community benchmarks

Community benchmark reports for local Project Maya deployments.

## Reports

- [2026-10-27 — 2× RTX PRO 5000 72GB, DeepSeek-V4.1-Flash-1017 Maya-S, engine v1.1.28 tuning sweep (true TP2 vs layer split, prefill chunk 8192/16384/32768, opt-in switches)](bench/results/2026-10-27-community-rtx-pro-5000-72gb-dsv41-maya-s-v1128-tuning-sweep/README.md) — [中文全文](bench/results/2026-10-27-community-rtx-pro-5000-72gb-dsv41-maya-s-v1128-tuning-sweep/README.zh-CN.md)
- [2026-10-25 — 1× RTX PRO 5000 72GB, DeepSeek-V4.1-Flash-1017 IQ2_XS, Strata Terminal 0.2.4.2, DSpark off/on A/B + 256K near-window](bench/results/2026-10-25-community-rtx-pro-5000-72gb-dsv41-strata-terminal-iq2xs/README.md)
- [2026-10-25 — 2× RTX PRO 5000 72GB, DeepSeek-V4.1-Flash-1017 Maya-S, full parameter sweep (DSpark × 256K/512K/1M), archived](bench/results/2026-10-25-community-rtx-pro-5000-72gb-dsv41-maya-s-dual-gpu-sweep/README.md)
- [2026-10-23 — 2× RTX PRO 5000 72GB, DeepSeek-V4.1-Flash-1017 Maya-S, 512K context](bench/results/2026-10-23-community-rtx-pro-5000-72gb-dsv41-maya-s/README.md)

Each report distinguishes measured values from estimates, lists limitations, and excludes credentials and private host information.

## Machine-readable tables

One row per number, no prose to parse — for scripts, spreadsheets, and AI agents:

- [`data/dsv41-flash-1017-results.csv`](data/dsv41-flash-1017-results.csv) / [`.json`](data/dsv41-flash-1017-results.json) — all 148 published values across the four reports, each with config, engine version, GPU count, prompt length, unit, the timing counter used (`engine_log` vs `api_wall` — they differ up to 30%, never mix them), and an `evidence` grade (`measured` 132 / `carried_over` 9 / `single_point_not_benchmark` 3 / `derived_estimate` 2 / `external_report` 2).
- [`data/dsv41-config-comparison.csv`](data/dsv41-config-comparison.csv) — the 2026-10-27 tuning campaign as one wide row per round (R0–R13): prefill/decode/residency/streamed-bytes side by side with the verdict.
- Regenerate both with `python3 data/build_dsv41_results.py` (stdlib only). The 10-27 rows are read from that entry's own `data/summary.json`, so they cannot drift.
