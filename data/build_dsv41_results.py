#!/usr/bin/env python3
"""Build the machine-readable result tables for every report in this repo.

Why these files exist
    The four reports under bench/results/ state their numbers in prose and
    Markdown tables. A reader who only wants "config -> speed -> caveat" has to
    parse sentences first. These flat files answer that directly:

      dsv41-flash-1017-results.csv / .json    one row per measured value (long form)
      dsv41-config-comparison.csv             one row per tuning round (wide form)

Provenance — read this before citing a number
    * The 2026-10-27 tuning-sweep rows are READ FROM that entry's own
      data/summary.json, so they cannot drift from the published table.
    * The remaining rows are transcribed from the cited report's Results tables.
    * Every row carries `source` (the file the number came from) and `evidence`:
        measured                     engine log or official harness output on this host
        carried_over                 published in that entry but not re-measured there
        derived_estimate             wall-time or approximate figure, not an engine counter
        single_point_not_benchmark   one sample, recorded for completeness only
        external_report              somebody else's machine, quoted as an anchor
    * Raw logs behind every value live in each entry's raw/ directory.

Column conventions
    value_low / value_high   the published interval. When value_semantics is
                             `per_card_pair` these are GPU0 / GPU1 (NOT sorted),
                             otherwise low <= high.
    counter                  which clock the number came from. Engine-log and
                             API-wall-time rates for the same run differ by up to
                             30% — never mix them.
    workload                 what was being generated when a decode rate was read.

Regenerate with:  python3 data/build_dsv41_results.py
"""

import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "bench", "results")

REPORTS = {
    "2026-10-23-maya-s": {
        "date": "2026-10-23",
        "dir": "2026-10-23-community-rtx-pro-5000-72gb-dsv41-maya-s",
        "title": "Maya-S quality-vs-API entry (v1.1.20, 512K)",
        "engine": "Project Maya",
        "engine_version": "v1.1.20",
        "model_pack": "DeepSeek-V4.1-Flash-1017 Maya-S",
        "quant": "mixed IQ2_XXS/IQ2_S/IQ3_S, 2.56 bpw",
        "gpus": 2,
        "gpu_model": "NVIDIA RTX PRO 5000 72GB (Blackwell)",
        "cpu": "AMD Ryzen 9 9950X3D",
        "ram": "249 GiB DDR5-6000 dual-channel",
        "os": "Ubuntu 24.04, CUDA 13.0",
        "context_tokens": 524288,
        "limitations": "custom 24-task set, not an official benchmark; no full-window test; single-turn",
    },
    "2026-10-25-dual-gpu-sweep": {
        "date": "2026-10-25",
        "dir": "2026-10-25-community-rtx-pro-5000-72gb-dsv41-maya-s-dual-gpu-sweep",
        "title": "DSpark x context-window matrix (v1.1.20, archived deployment)",
        "engine": "Project Maya",
        "engine_version": "v1.1.20",
        "model_pack": "DeepSeek-V4.1-Flash-1017 Maya-S, 339.5 GB pack",
        "quant": "mixed IQ2_XXS/IQ2_S/IQ3_S, 2.56 bpw",
        "gpus": 2,
        "gpu_model": "NVIDIA RTX PRO 5000 72GB (Blackwell)",
        "cpu": "AMD Ryzen 9 9950X3D",
        "ram": "249 GiB DDR5-6000 dual-channel",
        "os": "Ubuntu 24.04, CUDA 13.0",
        "context_tokens": 524288,
        "limitations": "archived (superseded by the 2026-10-27 entry); windows never saturated; single-turn, no concurrency",
    },
    "2026-10-25-strata-terminal-iq2xs": {
        "date": "2026-10-25",
        "dir": "2026-10-25-community-rtx-pro-5000-72gb-dsv41-strata-terminal-iq2xs",
        "title": "Single-GPU Strata Terminal IQ2_XS parameter tests",
        "engine": "Strata Terminal",
        "engine_version": "0.2.4.2 (DSV41 engine 0.1.49.2, CUDA 13)",
        "model_pack": "ISTA-DASLab DeepSeek-V4.1-Flash-1017, ~273.8 GB total",
        "quant": "IQ2_XS, 2.25 bpw",
        "gpus": 1,
        "gpu_model": "NVIDIA RTX PRO 5000 72GB (Blackwell, GPU1 only)",
        "cpu": "AMD Ryzen 9 9950X3D",
        "ram": "249 GiB DDR5-6000 dual-channel",
        "os": "Ubuntu, CUDA 13",
        "context_tokens": 262144,
        "limitations": "n=3 per side with a fixed off->on order (possible warm-order bias); not the official Strata community benchmark; no vision or tool calls",
    },
    "2026-10-27-v1128-tuning-sweep": {
        "date": "2026-10-27",
        "dir": "2026-10-27-community-rtx-pro-5000-72gb-dsv41-maya-s-v1128-tuning-sweep",
        "title": "Engine v1.1.28 configuration campaign (current production)",
        "engine": "Project Maya",
        "engine_version": "v1.1.28 (commit 6afa525, build-1128/maya-ds4, sm_120)",
        "model_pack": "DeepSeek-V4.1-Flash-1017 Maya-S, 348.4 GB pack, 18/18 SHA-256 passed",
        "quant": "mixed IQ2_XXS/IQ2_S/IQ3_S, 2.56 bpw",
        "gpus": 2,
        "gpu_model": "NVIDIA RTX PRO 5000 72GB (Blackwell), 73,415 MiB each",
        "cpu": "AMD Ryzen 9 9950X3D",
        "ram": "249 GiB DDR5-6000 dual-channel",
        "os": "Ubuntu 24.04, CUDA 13.0",
        "context_tokens": 524288,
        "limitations": "quick comparison, not a statistical A/B (one boot per condition; differences within +/-3% treated as noise); single-turn, no concurrency; longest prompt 124-131K",
    },
    "2026-10-31-v1141-parallel2-concurrency": {
        "date": "2026-10-31",
        "dir": "2026-10-31-community-rtx-pro-5000-72gb-dsv41-maya-s-v1141-parallel2-concurrency",
        "title": "v1.1.41 --parallel 2: 14h real agent traffic + controlled smoke (concurrency cost)",
        "engine": "Project Maya",
        "engine_version": "v1.1.41 (self-built, sha256 f25394ef...c2c3e4, sm_120)",
        "model_pack": "DeepSeek-V4.1-Flash-1017 Maya-S (same pack as the 2026-10-27 entry)",
        "quant": "mixed IQ2_XXS/IQ2_S/IQ3_S, 2.56 bpw",
        "gpus": 2,
        "gpu_model": "NVIDIA RTX PRO 5000 72GB (Blackwell), PCIe link 28.8 GB/s per card (x8 gen1)",
        "cpu": "AMD Ryzen 9 9950X3D",
        "ram": "249 GiB DDR5-6000 dual-channel",
        "os": "Ubuntu 24.04, CUDA 13.0",
        "context_tokens": 524288,
        "limitations": "soak is observational real traffic (solo/concurrent split from the engine's conversations-running field); no --parallel 4; no 1M window; aggregate x1.3 is inferred from medians, not a fixed-workload test",
    },
}

COLUMNS = [
    "row_id",
    "report_date",
    "report_slug",
    "report_dir",
    "engine",
    "engine_version",
    "model_pack",
    "quant",
    "gpus",
    "context_tokens",
    "config_id",
    "config_summary",
    "metric",
    "counter",
    "workload",
    "value_low",
    "value_high",
    "value_text",
    "value_semantics",
    "unit",
    "prompt_tokens",
    "dspark",
    "evidence",
    "notes",
    "source",
]

COMPARISON_COLUMNS = [
    "round_id",
    "change",
    "engine_version",
    "tp_mode",
    "prefill_chunk",
    "extra_switches",
    "context_tokens",
    "prefill_42_44k_low",
    "prefill_42_44k_high",
    "prefill_124_131k",
    "decode_code_warm_low",
    "decode_code_warm_high",
    "decode_prose_low",
    "decode_prose_high",
    "expert_residency_cuda0_pct",
    "expert_residency_cuda1_pct",
    "streamed_gb_per_42k_prompt",
    "quality_gate",
    "verdict",
    "source",
]


def num(token):
    """'1,626' -> 1626.0 ; '-' / '' -> None."""
    token = (token or "").strip().replace(",", "")
    if token in ("", "-"):
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", token)
    return float(match.group()) if match else None


def split_range(text):
    """Return (low, high, semantics).

    '3,939-4,007'     -> (3939.0, 4007.0, 'range')
    '77.6'            -> (77.6,   77.6,   'single')
    '72.2 / 72.9%'    -> (72.2,   72.9,   'per_card_pair')   # GPU0 / GPU1
    '157-162 tok/s'   -> unit words are stripped before parsing
    """
    text = (text or "").strip()
    if text in ("", "-"):
        return None, None, "missing"
    # drop unit words (tok/s, GB, MiB, %) so their slash is not read as a pair
    probe = re.sub(r"(?i)\b(tok/s|tokens?/s|gb|mib|kib|s\b)", " ", text).strip()
    if "/" in probe:
        parts = probe.split("/")
        return num(parts[0]), num(parts[1]), "per_card_pair"
    parts = [p for p in re.split(r"(?<=\d)-(?=\d)", probe.replace(",", "")) if p != ""]
    if len(parts) == 2:
        low, high = num(parts[0]), num(parts[1])
        if low is not None and high is not None and low > high:
            low, high = high, low
        return low, high, "range"
    value = num(text)
    return value, value, "single"


def row(report, config_id, config_summary, metric, value=None, *, unit, prompt_tokens=None,
        dspark="n/a", evidence="measured", text=None, notes="", counter=None,
        workload=None, source=None):
    meta = REPORTS[report]
    if text is not None:
        low = high = None
        semantics = "text"
    else:
        low, high, semantics = split_range(value)
    return {
        "row_id": None,  # assigned after sorting
        "report_date": meta["date"],
        "report_slug": report,
        "report_dir": meta["dir"],
        "engine": meta["engine"],
        "engine_version": meta["engine_version"],
        "model_pack": meta["model_pack"],
        "quant": meta["quant"],
        "gpus": meta["gpus"],
        "context_tokens": meta["context_tokens"],
        "config_id": config_id,
        "config_summary": config_summary,
        "metric": metric,
        "counter": counter or "engine_log",
        "workload": workload or "n/a",
        "value_low": low,
        "value_high": high,
        "value_text": text,
        "value_semantics": semantics,
        "unit": unit,
        "prompt_tokens": prompt_tokens,
        "dspark": dspark,
        "evidence": evidence,
        "notes": notes,
        "source": source or f"bench/results/{meta['dir']}/README.md",
    }


# --------------------------------------------------------------------------
# 2026-10-23 — Maya-S quality-vs-API entry
# --------------------------------------------------------------------------
R23 = "2026-10-23-maya-s"
CFG23 = "layer split (TP2 falls back to TP1), chunk 8192, --dspark on, 512K"
rows = [
    row(R23, "Q1", CFG23, "decode_tok_s", "71.03", unit="tok_s", prompt_tokens=1024,
        dspark="on", workload="mixed", counter="official_calibrate_ds4",
        notes="official calibrate_ds4.py harness, 1024+ generated tokens; +54.3% vs off"),
    row(R23, "Q1-off", CFG23, "decode_tok_s", "46.03", unit="tok_s", prompt_tokens=1024,
        dspark="off", workload="mixed", counter="official_calibrate_ds4",
        notes="same host and harness, DSpark off"),
    row(R23, "Q1", CFG23, "draft_acceptance_pct", "67", unit="pct", prompt_tokens=1024,
        dspark="on", notes="573/855 draft tokens accepted"),
    row(R23, "Q1", CFG23, "prefill_tok_s", "1553", unit="tok_s", prompt_tokens=443355,
        dspark="on", evidence="derived_estimate",
        notes="'about 1,553 tok/s', derived from wall time, not an engine counter"),
    row(R23, "Q1", CFG23, "retrieval_needles_pass", text="3 of 3", unit="count",
        prompt_tokens=443355, dspark="on",
        notes="synthetic mid-document unique-ID probes; single-turn"),
    row(R23, "Q1", CFG23, "task_score_of_24", "24.000", unit="score_24", dspark="on",
        counter="custom_task_set", notes="local model, custom 24-task set, this host"),
    row(R23, "ref-api", "official DeepSeek API (reference, not this host)", "task_score_of_24",
        "23.975", unit="score_24", evidence="external_report", counter="custom_task_set",
        notes="same small task set; sample too small for a general parity claim"),
]

# --------------------------------------------------------------------------
# 2026-10-25 — DSpark x context matrix (archived v1.1.20 deployment)
# --------------------------------------------------------------------------
R25D = "2026-10-25-dual-gpu-sweep"
MATRIX = [
    # window, off, on, gain, acceptance, accepted/total, kv per card, residency pct, cpu-lane
    (262144, "46.58", "74.48", "+59.9%", "69.2", "557/805", "0.15", "80.0", "3,080 experts (33.9 GB)"),
    (524288, "46.03", "71.03", "+54.3%", "67", "573/855", "0.29 / 0.27", "77.4", "3,850 experts (42.4 GB)"),
    (1048576, "46.22", "69.19", "+49.7%", "65.5", "573/875", "0.58 / 0.54", "77.0", "3,921 experts (43.1 GB)"),
]
for ctx, off, on, gain, acc, accfrac, kv, residency, cpu_lane in MATRIX:
    base = f"layer split (engine auto TP2->TP1), --max-context {ctx}"
    rows += [
        row(R25D, f"W{ctx}-off", base, "decode_tok_s", off, unit="tok_s", prompt_tokens=1024,
            dspark="off", workload="mixed", counter="official_calibrate_ds4",
            notes=f"calibrate_ds4 harness at {ctx} context"),
        row(R25D, f"W{ctx}-on", base, "decode_tok_s", on, unit="tok_s", prompt_tokens=1024,
            dspark="on", workload="mixed", counter="official_calibrate_ds4",
            notes=f"calibrate_ds4 harness at {ctx} context; {gain} vs off"),
        row(R25D, f"W{ctx}-on", base, "draft_acceptance_pct", acc, unit="pct", prompt_tokens=1024,
            dspark="on", notes=f"{accfrac} draft tokens accepted"),
        row(R25D, f"W{ctx}-on", base, "kv_cache_gb_per_gpu", kv, unit="gb",
            notes="per-card KV footprint from the boot banner (GPU0 / GPU1)"),
        row(R25D, f"W{ctx}-on", base, "expert_residency_pct", residency, unit="pct",
            notes=f"of 15,360 experts; CPU lane holds {cpu_lane}"),
    ]

LOADS = [
    # prompt_tokens, prefill, decode, needle, context
    (565, "122-174", "55.9-77.6", None, 524288),
    (7536, "1003", "66.7", None, 524288),
    (21457, "1373", "75.5", "PASS TGT-01399", 524288),
    (127057, "1755", "87.3", "PASS TGT-09999", 524288),
    (431057, "1626", "88.6", "PASS TGT-12345", 524288),
    (431057, "1586", "68.8", "PASS TGT-12345", 1048576),
    (31219, "1483", "56.0", "last-record ID answered correctly", 262144),
]
for prompt, prefill, decode, needle, ctx in LOADS:
    cfg = f"engine-log line, --max-context {ctx}, --dspark on"
    note = ""
    if prompt == 565:
        note = "43-565 token prompts; fixed overhead dominates, not a capability ceiling"
    if ctx == 1048576:
        note = "same prompt at the 1M window (41% of the window)"
    if ctx == 262144:
        note = "read-in 21.05 s"
    rows += [
        row(R25D, f"L{prompt}-c{ctx}", cfg, "prefill_tok_s", prefill, unit="tok_s",
            prompt_tokens=prompt, dspark="on", notes=note),
        row(R25D, f"L{prompt}-c{ctx}", cfg, "decode_tok_s", decode, unit="tok_s",
            prompt_tokens=prompt, dspark="on", workload="code_fastest_of_range",
            notes="code-class prompt is the fastest end of the published range"),
    ]
    if needle:
        rows.append(row(R25D, f"L{prompt}-c{ctx}", cfg, "retrieval_needle", text=needle,
                        unit="result", prompt_tokens=prompt, dspark="on",
                        notes="buried unique CRITICAL-TARGET ID, exact match required"))

rows += [
    row(R25D, "xhw-anchor", "friend's host: 2x RTX PRO 6000 96GB (192 GB VRAM, 1.8 TB/s per GPU)",
        "decode_tok_s", "80", unit="tok_s", dspark="on", evidence="external_report",
        notes="community anchor used for the cross-hardware comparison"),
    row(R25D, "xhw-this", "this host: 2x RTX PRO 5000 72GB (144 GB VRAM, 1.3 TB/s per GPU)",
        "decode_tok_s", "74.5", unit="tok_s", dspark="on", counter="official_calibrate_ds4",
        notes="calibrated value; real requests measured 67-78. 25% less VRAM and 28% less bandwidth cost only ~7%: the engine overlaps CPU-lane work with GPU compute (CPU lane touched 0.1%-8.3% of experts per step)"),
]

# --------------------------------------------------------------------------
# 2026-10-25 — Strata Terminal, single GPU, IQ2_XS
# --------------------------------------------------------------------------
R25S = "2026-10-25-strata-terminal-iq2xs"
CFG_OFF = "1x GPU, n_ctx 262144, --dspark off, 8 CPU expert threads, T=0, max_tokens 512"
CFG_ON = "1x GPU, n_ctx 262144, --dspark on --dspark-conf 0.65, 8 CPU expert threads, T=0, max_tokens 512"
rows += [
    row(R25S, "D-off", CFG_OFF, "throughput_tok_s", "39.05", unit="tok_s",
        prompt_tokens=106, dspark="off", counter="api_wall", workload="fixed_512_tokens",
        notes="mean of 3 runs (36.97 / 39.00 / 41.17); completion_tokens / whole non-streaming wall time"),
    row(R25S, "D-on", CFG_ON, "throughput_tok_s", "42.77", unit="tok_s",
        prompt_tokens=106, dspark="on", counter="api_wall", workload="fixed_512_tokens",
        notes="mean of 3 runs (37.43 / 43.89 / 46.98); +9.5% vs off"),
    row(R25S, "D-off", CFG_OFF, "throughput_tok_s", "38.97", unit="tok_s",
        prompt_tokens=106, dspark="off", counter="aggregate_wall", workload="fixed_512_tokens",
        notes="(prompt+completion) / wall time"),
    row(R25S, "D-on", CFG_ON, "throughput_tok_s", "42.38", unit="tok_s",
        prompt_tokens=106, dspark="on", counter="aggregate_wall", workload="fixed_512_tokens",
        notes="+8.8% vs off"),
    row(R25S, "D-off", CFG_OFF, "decode_tok_s", "40.13", unit="tok_s",
        prompt_tokens=106, dspark="off", counter="engine_decode_segment",
        workload="fixed_512_tokens",
        notes="engine-log generation segments; 495 counted tokens per 512-token response"),
    row(R25S, "D-on", CFG_ON, "decode_tok_s", "52.43", unit="tok_s",
        prompt_tokens=106, dspark="on", counter="engine_decode_segment",
        workload="fixed_512_tokens",
        notes="+30.7% vs off. This counter and the API-wall counter describe the same runs and are reported side by side, never mixed"),
    row(R25S, "D-auto", "1x GPU, --dspark auto (the default kept in production)",
        "throughput_tok_s", text="unknown", unit="tok_s", dspark="auto",
        counter="api_wall", evidence="single_point_not_benchmark",
        notes="single 9-token generation, sample too short; the engine skips DSpark in auto because routed experts (~149 GB) exceed GPU memory (~75 GB)"),
    row(R25S, "LONG", CFG_OFF + ", 240,065-token synthetic prompt", "prefill_tok_s",
        "928.5", unit="tok_s", prompt_tokens=240065, dspark="off",
        notes="read-in rate; 91.6% of the 262,144 window; read-in 258.564 s; needle at ~80% depth retrieved exactly (AMBER-CEDAR-5817)"),
    row(R25S, "LONG", "same request", "wall_time_s", "260.170", unit="s", counter="client_wall",
        prompt_tokens=240065, dspark="off", notes="whole request end to end"),
    row(R25S, "LONG", "same request", "throughput_tok_s", "923", unit="tok_s",
        prompt_tokens=240065, dspark="off", counter="aggregate_wall", evidence="derived_estimate",
        notes="(prompt+completion)/wall; prompt-dominated, NOT a decode figure"),
    row(R25S, "LONG", "same request", "retrieval_needle", text="PASS (exact marker, finish_reason=stop)",
        unit="result", prompt_tokens=240065, dspark="off"),
    row(R25S, "GEN9", "same long request, generation segment", "decode_tok_s", "28.74", unit="tok_s",
        prompt_tokens=240065, dspark="off", counter="client_wall",
        evidence="single_point_not_benchmark",
        notes="9 tokens over 313 ms, far too short to quote as a decode rate"),
    row(R25S, "VRAM", "single-GPU layout: the whole pack on one card", "vram_used_mib", "72342",
        unit="mib", notes="of 73,415 MiB available; peak during the long request 72,384 MiB"),
    row(R25S, "CPU-LANE", "single-GPU layout", "cpu_lane_experts_gb", "91.9", unit="gb",
        dspark="off", notes="8 CPU expert threads; ~83.9 GB in --dspark auto mode"),
    row(R25S, "SMOKE", "20 prompt / 8 completion tokens", "latency_s", "3.262", unit="s",
        prompt_tokens=20, counter="client_wall",
        notes="exact MAY-NORTH-47, HTTP 200"),
    row(R25S, "TUNER", "engine built-in quick tuner", "decode_tok_s", "13.2", unit="tok_s",
        counter="engine_internal", evidence="single_point_not_benchmark",
        notes="single round, not a benchmark"),
]

# --------------------------------------------------------------------------
# 2026-10-27 — v1.1.28 configuration campaign, read from its own summary.json
# --------------------------------------------------------------------------
R27 = "2026-10-27-v1128-tuning-sweep"
SUMMARY = os.path.join(RESULTS, REPORTS[R27]["dir"], "data", "summary.json")
with open(SUMMARY, encoding="utf-8") as handle:
    summary = json.load(handle)

ROUNDS_SRC = f"bench/results/{REPORTS[R27]['dir']}/data/summary.json"
README27 = f"bench/results/{REPORTS[R27]['dir']}/README.md"

FIELD_MAP = (
    ("pf", "prefill_tok_s", "tok_s", 42000, None, "engine_log",
     "engine-log prefill at 42-44K prompts, fresh reads only (0 reused)"),
    ("pf124", "prefill_tok_s", "tok_s", 124000, None, "engine_log",
     "engine-log prefill at a 124-131K prompt"),
    ("dc", "decode_tok_s", "tok_s", None, "code", "engine_log", "warm code-class decode"),
    ("dp", "decode_tok_s", "tok_s", None, "prose", "engine_log", "prose-class decode"),
    ("res", "expert_residency_pct", "pct", None, None, "boot_banner",
     "resident experts per GPU (GPU0 / GPU1)"),
    ("stream", "streamed_weights_gb_per_42k_prompt", "gb", 42000, None, "engine_log",
     "DS4_PREFILL counters summed over both GPUs for one 42-44K prompt"),
)
for rnd in summary["rounds"]:
    cfg_id, cfg = rnd["id"], rnd["en"]
    for field, metric, unit, prompt, workload, counter, note in FIELD_MAP:
        value = rnd.get(field)
        if value in (None, "-", ""):
            continue
        rows.append(row(R27, cfg_id, cfg, metric, value, unit=unit, prompt_tokens=prompt,
                        dspark="on", notes=note, counter=counter, workload=workload or "n/a",
                        source=ROUNDS_SRC))
    rows.append(row(R27, cfg_id, cfg, "verdict", text=rnd["en"], unit="result",
                    dspark="on", notes=f"verdict: {rnd['verdict_en']}", counter="n/a",
                    source=ROUNDS_SRC))

for ctx, off, on, gain, acc in summary["dspark"]:
    ref = f"DSpark reference calibrated on v1.1.20 at {ctx}K (carried into the v1.1.28 report)"
    rows += [
        row(R27, f"DS{ctx}K-off", ref, "decode_tok_s", str(off), unit="tok_s", dspark="off",
            workload="mixed", counter="official_calibrate_ds4", evidence="carried_over",
            notes="not re-measured on v1.1.28; every v1.1.28 round ran with --dspark on",
            source=ROUNDS_SRC),
        row(R27, f"DS{ctx}K-on", ref, "decode_tok_s", str(on), unit="tok_s", dspark="on",
            workload="mixed", counter="official_calibrate_ds4", evidence="carried_over",
            notes=f"{gain} vs off; carried over from v1.1.20, not re-measured on v1.1.28",
            source=ROUNDS_SRC),
        row(R27, f"DS{ctx}K-on", ref, "draft_acceptance_pct", acc.rstrip("%"), unit="pct",
            dspark="on", evidence="carried_over", counter="official_calibrate_ds4",
            source=ROUNDS_SRC),
    ]

final = summary["final"]
pre_pf_low, pre_pf_high, _ = split_range(final["prefill"].split("@")[0])
pre_dc_low, pre_dc_high, _ = split_range(final["decode"].split("(")[0])
residency = final["residency"]
RES_RE = re.compile(r"CUDA(\d) .*?\(([\d.]+)%\)")
res_by_card = {int(m.group(1)): m.group(2) for m in RES_RE.finditer(residency)}
rows += [
    row(R27, "FINAL", final["args"] + " | env: " + final["env"], "prefill_tok_s",
        f"{pre_pf_low:g}-{pre_pf_high:g}", unit="tok_s", prompt_tokens=42000, dspark="on",
        notes="the configuration currently serving on this host; same numbers as R11; "
              f"124K prompt = {final['prefill'].split(';')[1].strip()}", source=ROUNDS_SRC),
    row(R27, "FINAL", final["args"], "decode_tok_s", f"{pre_dc_low}-{pre_dc_high}", unit="tok_s",
        dspark="on", workload="code", notes=f"warm code prompts; prose: {final['decode'].split(';')[1].strip()}",
        source=ROUNDS_SRC),
    row(R27, "FINAL", final["args"], "expert_residency_pct",
        f"{res_by_card[0]} / {res_by_card[1]}",
        unit="pct", dspark="on", counter="boot_banner",
        notes=f"verbatim: {residency}; CPU lane {final['cpu_lane']}", source=ROUNDS_SRC),
    row(R27, "GATE", summary["battery"], "battery_score_of_15", "14", unit="score_15",
        dspark="on", counter="custom_task_set",
        notes="identical on every condition; the one miss is the scorer rejecting the subscript H2O",
        source=ROUNDS_SRC),
    row(R27, "GATE", summary["needles"], "retrieval_needles_pass", "9", unit="count",
        dspark="on", prompt_tokens=44480, counter="custom_probe",
        notes="3 depths x 3 seeds in a 44,480-token prompt, plus the 124K needle correct",
        source=ROUNDS_SRC),
    row(R27, "GATE", "offline --ppl baseline run twice", "ppl_reproducibility",
        text="bit-identical (4.0933 / 3.8300 / 3.7342 / 9.0713 / 7.0358 / 5.3583)",
        unit="ppl", dspark="on", counter="engine_ppl",
        notes="FALSE NEGATIVE for skip-some-work switches: RAM_SKIP_W and DS4_YOCO left it untouched "
              "while DS4_ATTN_MMA moved every value. Only valid for numerical-path changes",
        source=README27),
    row(R27, "GATE", "fixed-seed text similarity at temperature 0", "text_similarity",
        "0.318-0.417", unit="ratio", dspark="on", counter="custom_probe",
        notes="the baseline itself only scores this high (MoE + batching is not deterministic), so "
              "'the wording did not change' cannot be claimed for any switch", source=README27),
    row(R27, "FINAL", "production re-read of a cached 44K context", "kv_reuse_read_s", "0.3",
        unit="s", prompt_tokens=44357, dspark="on", counter="engine_log",
        notes="44,356/44,357 tokens reused on the follow-up prompt instead of a full re-read",
        source=README27),
]

# --------------------------------------------------------------------------
# 2026-10-31 — v1.1.41 --parallel 2 concurrency, read from its own summary.json
# --------------------------------------------------------------------------
R31 = "2026-10-31-v1141-parallel2-concurrency"
SUMMARY31_PATH = os.path.join(RESULTS, REPORTS[R31]["dir"], "data", "summary.json")
with open(SUMMARY31_PATH, encoding="utf-8") as handle:
    s31 = json.load(handle)
SRC31 = f"bench/results/{REPORTS[R31]['dir']}/data/summary.json"
README31 = f"bench/results/{REPORTS[R31]['dir']}/README.md"
RAW31 = f"bench/results/{REPORTS[R31]['dir']}/raw/maya-1141-requests-all.csv"

soak = s31["soak"]
smoke = s31["smoke_controlled"]
CFG31 = s31["engine"]["args"] + " | env: " + s31["engine"]["env"]

rows += [
    row(R31, "P2-soak", CFG31, "requests_observed", text=f'{soak["requests"]}', unit="count",
        notes=f'14h06 boot of real agent traffic; {soak["prompt_tokens_total"]:,} prompt tokens, '
              f'{soak["gen_tokens_total"]:,} generated tokens', counter="engine_log",
        source=RAW31),
    row(R31, "P2-soak", CFG31, "decode_tok_s",
        f'{soak["decode_solo_gen200plus"]["p25"]}-{soak["decode_solo_gen200plus"]["p75"]}',
        unit="tok_s", dspark="on", workload="mixed_real_agent",
        notes=f'solo lane, generation >=200 tokens, n={soak["decode_solo_gen200plus"]["n"]}, '
              f'median {soak["decode_solo_gen200plus"]["median"]}', source=SRC31),
    row(R31, "P2-soak", CFG31, "decode_tok_s",
        f'{soak["decode_concurrent_gen200plus"]["p25"]}-{soak["decode_concurrent_gen200plus"]["p75"]}',
        unit="tok_s", dspark="on", workload="mixed_real_agent",
        notes=f'concurrent lane (other conversation generating), generation >=200 tokens, '
              f'n={soak["decode_concurrent_gen200plus"]["n"]}, median '
              f'{soak["decode_concurrent_gen200plus"]["median"]}', source=SRC31),
    row(R31, "P2-soak", CFG31, "decode_concurrency_ratio_pct",
        str(soak["decode_concurrency_ratio_pct"]), unit="pct", dspark="on",
        workload="mixed_real_agent",
        notes="concurrent-lane median / solo-lane median (generation >=200 tokens); "
              "stable 65-66% across the 50-199 / 200-999 / >=1000 output bands", source=SRC31),
    row(R31, "P2-soak", CFG31, "prefill_tok_s",
        f'{soak["prefill_solo_fresh20kplus"]["p25"]}-{soak["prefill_solo_fresh20kplus"]["p75"]}',
        unit="tok_s", prompt_tokens=100000, dspark="on",
        notes=f'fresh reads >=20K, lane idle, n={soak["prefill_solo_fresh20kplus"]["n"]}, '
              f'median {soak["prefill_solo_fresh20kplus"]["median"]}', source=SRC31),
    row(R31, "P2-soak", CFG31, "prefill_tok_s",
        str(soak["prefill_concurrent_fresh20kplus"]["median"]), unit="tok_s", prompt_tokens=100000,
        dspark="on",
        notes=f'fresh reads >=20K while the other lane also prefilling, '
              f'n={soak["prefill_concurrent_fresh20kplus"]["n"]}, '
              f'{soak["prefill_concurrent_fresh20kplus"]["delta_pct"]}% vs solo', source=SRC31),
    row(R31, "P2-soak", CFG31, "cache_hit_rate_pct", str(soak["cache_hit_request_pct"]),
        unit="pct", dspark="on",
        notes=f'93.3% of requests hit the conversation cache; token-level reuse '
              f'{soak["cache_hit_token_pct"]}% of 293.2M prompt tokens', source=RAW31),
    row(R31, "P2-deepest", CFG31, "prefill_tok_s", str(soak["max_prompt_fresh_read_tps"]),
        unit="tok_s", prompt_tokens=soak["max_prompt_tokens"], dspark="on",
        evidence="single_point_not_benchmark",
        notes="deepest cold read observed: 91.2% of the 524K window", source=RAW31),
    row(R31, "P2-deepest", CFG31, "decode_tok_s",
        str(soak["max_prompt_then_generated"].split("@ ")[1].split(" ")[0]), unit="tok_s",
        prompt_tokens=soak["max_prompt_tokens"], dspark="on", workload="mixed_real_agent",
        evidence="single_point_not_benchmark",
        notes="7,187 tokens generated at 60.8 tok/s right after the 478K cold read, "
              "with one other conversation running", source=RAW31),
    row(R31, "P2-soak", CFG31, "draft_acceptance_pct", str(soak["draft_acceptance_all_pct"]),
        unit="pct", dspark="on", notes="698,157 of 914,979 draft tokens kept, whole soak",
        source=RAW31),
    row(R31, "P2-soak", CFG31, "draft_acceptance_pct",
        str(soak["draft_acceptance_concurrent_pct"]), unit="pct", dspark="on",
        notes="slightly HIGHER with a second conversation running (75.2% solo) — no concurrency "
              "penalty for DSpark batching, consistent with the 1.1.36 design", source=RAW31),
    row(R31, "P2-soak", CFG31, "stability",
        text="0 window-ring / unspecified-launch / fatal / segfault in 14h", unit="result",
        dspark="on", notes="issue #690 crash class did not reproduce on 9950X3D + 2x PRO 5000 "
                           "layer split with two overlapping agent lanes", source=SRC31),
    row(R31, "P2-smoke", CFG31, "prefill_tok_s", str(smoke["first_fresh_prompt_after_boot"]["read_tps"]),
        unit="tok_s", prompt_tokens=24528, dspark="on",
        notes="first fresh read after boot (14.2 s); warm soak median at 50-150K is 3,596 — the "
              "cold-first-read penalty is real even on 1.1.41 (improved vs 1.1.40 by #612, not "
              "measured as an A/B here)", source=SRC31),
    row(R31, "P2-smoke", CFG31, "decode_tok_s",
        f'{min(smoke["two_concurrent_identical_probes"]["a_tps"], smoke["two_concurrent_identical_probes"]["b_tps"])}-{max(smoke["two_concurrent_identical_probes"]["a_tps"], smoke["two_concurrent_identical_probes"]["b_tps"])}',
        unit="tok_s", dspark="on", workload="prose",
        evidence="single_point_not_benchmark",
        notes="two identical concurrent probes = 93-99% of the 57.55 tok/s solo short answer; "
              "controlled bursts overstate what real traffic sees", source=SRC31),
    row(R31, "P2-smoke", CFG31, "two_lane_aggregate_x",
        text="~1.3 (soak medians) / ~1.6-1.9 (controlled burst)", unit="ratio", dspark="on",
        evidence="derived_estimate",
        notes="derived from per-lane figures; no fixed-workload aggregate throughput test",
        source=README31),
    row(R31, "BANNER", s31["boot_banner"]["residency_cuda0"] + " / " + s31["boot_banner"]["residency_cuda1"],
        "expert_residency_pct", "72.2 / 72.5", unit="pct", dspark="on", counter="boot_banner",
        notes=f'KV caches {s31["boot_banner"]["kv_caches_gb_per_card"]} GB per card; CPU lane '
              f'{s31["boot_banner"]["cpu_lane"]}; free '
              f'{s31["boot_banner"]["vram_free_mib_per_card"]} MiB per card', source=SRC31),
]

for band in soak["decode_bands"]:
    rows.append(row(R31, "P2-band", CFG31, "decode_concurrency_ratio_pct", str(band["ratio_pct"]),
                    unit="pct", dspark="on", workload=f"gen_{band['band']}",
                    notes=f'solo median {band["solo_med"]} (n={band["solo_n"]}) -> concurrent median '
                          f'{band["dual_med"]} (n={band["dual_n"]})', source=SRC31))

# ------------------------------- wide table -------------------------------
SWITCHES = {
    "R0": "", "R1": "", "R2": "", "R3": "", "R4": "", "R5": "DS4_FAT_ROWS=128",
    "R6": "DS4_SPLIT=19,21", "R7": "DS4_SPLIT=20,20", "R8": "DS4_REQUIRE_ALL_RAM=1 + --mmap-experts off",
    "R9": "--max-context 262144", "R10": "STRATA_DS4_Q8_BATCH=1",
    "R11": "STRATA_DS4_PROMPT_SKIP=2", "R12": "STRATA_DS4_RAM_SKIP_W=0.10",
    "R13": "STRATA_DS4_RAM_SKIP_W=0.14",
}
comparison = []
for rnd in summary["rounds"]:
    res_low, res_high, res_sem = split_range(rnd.get("res"))
    pf_low, pf_high, _ = split_range(rnd.get("pf"))
    dc_low, dc_high, _ = split_range(rnd.get("dc"))
    dp_low, dp_high, _ = split_range(rnd.get("dp"))
    text = rnd["en"]
    if "TP2" in text:
        tp_mode = "true TP2"
    elif rnd["id"] in ("R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R12", "R13"):
        tp_mode = "layer split (inherited from R3)"
    else:
        tp_mode = "layer split"
    comparison.append({
        "round_id": rnd["id"],
        "change": text,
        "engine_version": "v1.1.20" if rnd["id"] == "R0" else "v1.1.28",
        "tp_mode": tp_mode,
        "prefill_chunk": "32768" if "32768" in text else ("16384" if "16384" in text else "8192"),
        "extra_switches": SWITCHES.get(rnd["id"], ""),
        "context_tokens": 262144 if rnd["id"] == "R9" else 524288,
        "prefill_42_44k_low": pf_low,
        "prefill_42_44k_high": pf_high,
        "prefill_124_131k": num(rnd.get("pf124")),
        "decode_code_warm_low": dc_low,
        "decode_code_warm_high": dc_high,
        "decode_prose_low": dp_low,
        "decode_prose_high": dp_high,
        "expert_residency_cuda0_pct": res_low,
        # an empty cuda1 column means the report published one aggregate figure, not a per-card pair
        "expert_residency_cuda1_pct": res_high if res_sem == "per_card_pair" else None,
        "streamed_gb_per_42k_prompt": num(rnd.get("stream")),
        "quality_gate": "not run" if rnd["id"] not in ("R10", "R11", "R12", "R13")
                        else "14/15 battery; retrieval needle PASS",
        "verdict": rnd["verdict_en"],
        "source": ROUNDS_SRC,
    })

rows.sort(key=lambda r: (r["report_date"], r["config_id"], r["metric"], str(r["workload"])))
for index, entry in enumerate(rows, start=1):
    entry["row_id"] = f"B{index:03d}"

csv_path = os.path.join(HERE, "dsv41-flash-1017-results.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)

cmp_path = os.path.join(HERE, "dsv41-config-comparison.csv")
with open(cmp_path, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=COMPARISON_COLUMNS)
    writer.writeheader()
    writer.writerows(comparison)

json_path = os.path.join(HERE, "dsv41-flash-1017-results.json")
payload = {
    "schema_version": 1,
    "generated_by": "data/build_dsv41_results.py",
    "model": "DeepSeek-V4.1-Flash-1017 (local quantised packs)",
    "row_count": len(rows),
    "field_notes": {
        "value_low/value_high": "the published interval; equal for a single value. "
                                "When value_semantics is per_card_pair these are GPU0 / GPU1 and are NOT sorted",
        "value_semantics": "single | range | per_card_pair | text | missing",
        "evidence": "measured | carried_over | derived_estimate | single_point_not_benchmark | external_report",
        "counter": "which clock the number came from — engine_log | api_wall | aggregate_wall | "
                   "engine_decode_segment | official_calibrate_ds4 | boot_banner | client_wall | "
                   "engine_internal | engine_ppl | custom_probe | custom_task_set | n/a. "
                   "Engine-log and API-wall rates for the same run differ by up to 30%; never mix them",
        "workload": "what was being generated: code | prose | mixed | fixed_512_tokens | "
                    "code_fastest_of_range | n/a",
        "prompt_tokens": "prompt length the number was taken at; null means not prompt-dependent",
    },
    "evidence_legend": {
        "measured": "engine log or official harness output on this host",
        "carried_over": "published in that entry but not re-measured there",
        "derived_estimate": "wall-time or approximate figure, not an engine counter",
        "single_point_not_benchmark": "one sample, recorded for completeness only",
        "external_report": "another person's machine, quoted as an anchor",
    },
    "reports": REPORTS,
    "rows": rows,
    "config_comparison": comparison,
    "caveats": [
        "Not an official leaderboard benchmark; every entry used custom probes.",
        "Entries before 2026-10-31 are solo, single-turn runs (no --parallel > 1). The 2026-10-31 entry adds a 14h --parallel 2 soak of real agent traffic with a per-request concurrency flag; it still has no --parallel 4, no 1M-window, and no fixed-workload aggregate throughput test.",
        "Host-specific: a Ryzen 9 9950X3D with dual-channel DDR5-6000 bounds the CPU expert lane, and this board's PCIe link runs at 28.8 GB/s (x8 gen1). Copy the ordering of the knobs, not the residency or thread numbers.",
        "Differences within +/-3% are treated as drift on this host (sequential runs drift up to 20%).",
        "Large context windows are YaRN x16 extrapolation over a native 64K model: 'retrievable' is not 'as sharp as within 64K'.",
        "The 2026-10-27 entry quotes the DSpark on/off matrix from v1.1.20 rather than re-measuring it on v1.1.28; those rows are marked evidence=carried_over.",
    ],
}
with open(json_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=1)
    handle.write("\n")

print(f"rows={len(rows)} comparison_rows={len(comparison)} columns={len(COLUMNS)}")
print(csv_path)
print(cmp_path)
print(json_path)
