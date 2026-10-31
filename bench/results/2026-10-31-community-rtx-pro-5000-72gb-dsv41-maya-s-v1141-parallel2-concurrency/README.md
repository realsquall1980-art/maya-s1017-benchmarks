# Maya-S (DeepSeek-V4.1-Flash-1017) on 2× RTX PRO 5000 72GB — engine v1.1.41 with `--parallel 2`: first real-traffic concurrency numbers

Community benchmark report — Project Maya v1.1.41 (self-built for sm_120), measured 2026-10-30/31.

The earlier reports on this host measured single-lane behavior (v1.1.20 quality/API, the v1.1.28
configuration campaign). This entry answers the one question those reports could not: **what does
`--parallel 2` actually cost and give on real long-context agent traffic?** It combines (a) a
14-hour soak of production agent sessions (1,495 requests, 293M prompt tokens) and (b) a small
controlled smoke run, with every rate taken from the engine's own per-request log lines.
Raw data for all 1,554 logged requests across all six boots is in `raw/`.

## Headline results (engine-log counter, never API wall time)

| Metric (v1.1.41, `--parallel 2`, 512K) | Value | Grade |
|---|---|---|
| Decode, lane idle otherwise, gen ≥200 tok | median **96.7 tok/s** (n=597, p25–p75 86.6–115.3) | measured |
| Decode, other lane active, gen ≥200 tok | median **63.5 tok/s** (n=482, p25–p75 53.3–76.2) | measured |
| **Per-lane cost of concurrency** | **65.7%** of solo (≈66%; stable across gen 50–199 / 200–999 / ≥1000 bands: 66/65/66%) | measured |
| Implied 2-lane aggregate capacity | ≈**1.3×** a single lane (inferred from medians, not a fixed-workload throughput test) | derived |
| Prefill, fresh reads ≥20K, lane idle | median **3,596 tok/s** (n=45) | measured |
| Prefill, fresh reads ≥20K, other lane active | median **3,361 tok/s** (**−6.6%**) | measured |
| Conversation cache hits (real agent traffic) | **93.3%** of requests, **94.1%** of prompt tokens (293.2M prompt tokens total) | measured |
| Deepest fresh read | **478,303 tokens = 91.2% of the 524K window**, cold-read at 1,707.9 tok/s, then generated 7,187 tokens at 60.8 tok/s | single point |
| Draft acceptance (DSpark) | 76.3% overall; **77.7% with a second conversation running** (no concurrency penalty) | measured |
| Stability | 0 occurrences of `window ring` / `unspecified launch` / fatal / segfault in 14h soak (issue #690 risk did not reproduce here) | measured |
| Controlled smoke, two identical concurrent probes | 53.7 / 56.8 tok/s = **93–99% of the solo short-answer rate** | measured (n=2) |
| First fresh 24,528-token read after boot | **1,730.4 tok/s** (14.2 s) vs the warm soak median 3,596 at the same depth: the cold-first-read penalty survives on 1.1.41 (#612 improves it vs 1.1.40; we did not A/B versions) | single point |

**Reading:** the official release notes for v1.1.36/1.1.37 describe DSpark draft batching under
`--parallel` with roughly ×1.1 aggregate on three V100s. Our controlled smoke (93–99% per lane)
matches that order of magnitude — but under **real interleaved traffic** (long prompts streaming
in while the other lane answers) the honest planning number on this hardware is **~66% per lane,
~1.3× aggregate**. Both figures are in `data/summary.json`; use the real-traffic one.

## Setup

- 2× NVIDIA RTX PRO 5000 72GB (Blackwell), 73,415 MiB each; engine-measured PCIe link 28.8 GB/s per card (x8 gen1 on this board); AMD Ryzen 9 9950X3D; 249 GiB DDR5-6000 dual-channel; Ubuntu 24.04; CUDA 13.0
- Project Maya **v1.1.41**, self-built `maya-ds4`, sha256 `f25394ef43343f77631de72523380f54b5bac22cfdb5a285893f0c4433c2c3e4`
- Maya-S pack (mixed IQ2_XXS/IQ2_S/IQ3_S, 2.56 bpw), DeepSeek-V4.1-Flash-1017
- Verbatim serving config: `raw/maya-ds4-par2-1141-config.json` (args + env, `--parallel 2`, 512K)
- Boot banner (stable across all six boots): residency CUDA0 5,549/7,680 (72.2%), CUDA1 5,852/8,064 (72.5%), KV caches 0.59/0.55 GB per card, CPU lane 4,343–4,358 experts / ~48 GB RAM, 483–563 MiB free per card

## Method

1. **Soak (primary evidence).** One 14h06 boot (2026-10-30 23:53 → next-day 09:59) serving real
   agent sessions through a local OpenAI-compatible gateway; at least two long-context sessions
   overlapped for most of the window. Each request line carries the engine's own
   `N conversations running` field, which is how lanes are split into solo vs concurrent — no
   timestamps were needed and no client-side clock was used.
2. **Engine-log timing only.** prefill = `prompt N tokens = R reused + X read in T ms (P tok/s)`;
   decode = the generation segment of the same line. API wall time differs up to ~30% and is
   deliberately absent from every headline number.
3. **Fresh reads only for prefill.** Rows with `R > 0` are cache hits and are counted in the cache
   statistics, never in the prefill rate medians.
4. **Controlled smoke (secondary).** Two identical short probes fired concurrently onto both
   lanes; plus two fresh ~42K reads fired concurrently. n=1–2 per condition: these are single
   points recorded for direction, graded `single_point_not_benchmark`.
5. **Everything is recomputable.** `raw/maya-1141-requests-all.csv` has one row per logged request
   (1,554 rows, all six boots, `run` column identifies the boot); the run-5 subset is exactly the
   soak. `data/summary.json` is the single source for every number above.

## What this adds to the community picture

- A **long-soak concurrency cost figure** (≈66% per lane) that, to our knowledge, no published
  report had for this hardware class — most published `--parallel` numbers are short controlled
  bursts and land optimistically close to the controlled-smoke figure we also measured.
- **Concurrency does not hurt DSpark**: acceptance is slightly *higher* with a second conversation
  running (77.7% vs 75.2%), consistent with the 1.1.36 draft-batching design.
- **Prefill depth curve** on fresh reads from 50K to ~478K tokens is published per bucket, showing
  the gentle decline (3,687 → ~2,900 tok/s from 50–100K to 350–400K) that only long real sessions
  produce.
- **Issue #690 counter-observation**: on the same CPU (9950X3D), dual-GPU layer-split, two
  overlapping agent lanes, 14h — no `window ring` crash. Configuration details above may help
  narrow that report.

## Limitations

- L1 — the soak is observational, not scheduled: the solo/concurrent split comes from the engine's
  own field; concurrent-lane requests skew toward two heavy long-context sessions (this is the
  traffic we care about, but it is not a uniform workload).
- L2 — all counters are engine-log; do not compare them against someone's API wall-time figures.
- L3 — 512K window only (deepest 91.2%); no 1M context, no `--parallel 4`.
- L4 — aggregate ≈1.3× is inferred from per-lane medians, not a fixed-workload throughput test.
- L5 — this board's PCIe link runs at 28.8 GB/s (x8 gen1); machines with full-width links will
  show different prefill-depth numbers.
- L6 — the soak ended because the GPU was handed back for another service (operational stop),
  not because of any failure.

## Data & sources

- `data/summary.json` — single source for every headline number (soak + smoke + banner).
- `raw/maya-1141-requests-all.csv` — every logged request across six boots (1,554 rows).
- `raw/maya-1141-run5-excerpt.txt` — boot-5 (soak) request/cache/banner lines.
- `raw/maya-1141-run1..4,6-excerpt.txt` — the other five boots, including the controlled smoke.
- `raw/maya-ds4-par2-1141-config.json` — verbatim serving args/env + binary sha256.

Acknowledgements: thanks to the Maya maintainers for shipping `--parallel` with per-request
concurrency logging — the `conversations running` field is what makes an honest observational
concurrency report possible.
