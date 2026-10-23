# DeepSeek-V4.1-Flash-1017 Maya-S: Local Evaluation Report

**Status:** measured local results; not an official benchmark.  
**Test date:** 2026-10-22 (performance/quality runs); 2026-10-23 reload health check.  
**Engine:** Project Maya v1.1.20 (`35bb2b2`), self-built for SM120.  
**Model:** Maya-S mixed IQ2_XXS/IQ2_S/IQ3_S, measured 2.56 bpw, approximately 325 GB in the local test record.  
**Hardware:** 2× RTX PRO 5000 72GB, Ryzen 9 9950X3D, 249 GB DDR5-6000, Ubuntu 24.04, CUDA 13.0.  
**Configuration:** 512K context, DSpark enabled, temperature 1.0, top_p 1.0, reasoning effort high. The engine uses two-GPU layer split; TP2 is internally reduced to TP1 because the packed expert blocks cannot be split as TP2.

## Summary

- At 512K configured context, DSpark calibration measured **71.03 tok/s** versus **46.03 tok/s** with DSpark disabled (**+54.3%**); draft acceptance was **573/855 = 67%**.
- At 256K and 1M, DSpark measured 74.48 and 69.19 tok/s, respectively. These are calibration runs, not sustained production throughput guarantees.
- Prefill/decode log samples at 512K included 21,457 tokens at 1,373/75.5 tok/s, 127,057 tokens at 1,755/87.3 tok/s, and 431,057 tokens at 1,626/88.6 tok/s.
- Three synthetic long-context retrieval probes at 21,457, 127,057, and 431,057 prompt tokens each retrieved the planted identifier (3/3 at each length).
- On a custom 24-task paired check using temperature=1, top_p=1, reasoning_effort=high, Maya-S scored 24.000/24 and the official API 23.975/24. This narrow result is not proof of general parity.
- At temperature=0, one coding task showed repeated-reasoning degeneration in 6/6 aggregate trials across two batches (1/6 and 5/6); the documented official settings had 0/6 degeneration in the comparison batch. This is an observed sampling-sensitive failure, not evidence that temperature=0 always fails.

## Throughput method and measurements

The DSpark comparison used the same machine and calibration harness, with each run generating 1,024+ tokens. At 512K: no DSpark 46.03 tok/s; DSpark on 71.03 tok/s; acceptance 573/855. At 256K: 46.58 versus 74.48 tok/s, +59.9%, acceptance 557/805 (69.2%). At 1M: 46.22 versus 69.19 tok/s, +49.7%, acceptance 573/875 (65.5%).

512K prompt samples recorded by the engine:

| Prompt tokens | Prefill tok/s | Decode tok/s |
|---:|---:|---:|
| 565 | 159 | 74.5 |
| 21,457 | 1,373 | 75.5 |
| 127,057 | 1,755 | 87.3 |
| 431,057 | 1,626 | 88.6 |

Do not interpret the 431K single sample as a stable long-context decode benchmark. The longest context experiment measured retrieval correctness, not a broad quality suite. Maximum tested prompt was 443,355 tokens in the separate local-vs-API probe; full 524,288-token window was not tested.

## Local vs official API paired task check

The custom set contained 14 basic and 10 harder questions covering arithmetic, logic, probability, executable code cases, JSON constraints, Chinese constraints, knowledge, and short long-text retrieval. Code answers were executed against test cases; JSON and constrained writing were checked mechanically. Under temperature=1, top_p=1, reasoning_effort=high, scores were 24.000/24 local and 23.975/24 official API. The 0.025 difference came from one constrained Chinese summary exceeding its length bound by one character. Each question has high leverage in a 24-item set; these scores must not be generalized to broad model quality.

Efficiency for this set: local total output 7,918 tokens versus API 6,715; wall time 102.1 s versus 47.5 s. This is harness- and request-specific.

## Temperature-zero degeneration observation

On one hard code-format task, two local temperature-zero batches of six trials each produced 1/6 and 5/6 degenerate outputs. The symptom was finish_reason=length with empty final content and repeated reasoning text. A comparison batch of six calls under temperature=1, top_p=1, reasoning_effort=high had 0/6 such outputs. This is a small repeated-prompt observation and should not be treated as a universal failure rate.

## Long-context retrieval

A synthetic document contained three planted identifiers; one prompt asked for all three. Maya-S and the official API each returned all identifiers at 29,782, 221,690, and 443,355 prompt tokens (3/3 each). Wall time on Maya-S was 22.73, 135.34, and 285.45 seconds; official API was 2.15, 6.15, and 8.48 seconds. Wall-time-derived prefill estimates for Maya-S were approximately 1,310, 1,638, and 1,553 tok/s; these include small generation overhead and are approximate.

## Vision spot check

One 1400×900 report image was queried with four questions (table value, seven-digit code, original value in a note, and color ordering). Local and API answers matched on all four. This is a small spot check, not a comprehensive multimodal benchmark.

## Not measured / limitations

- Official HLE, Terminal-Bench, and DeepSWE results were not reproduced (dataset/harness/runtime prerequisites unavailable during the test).
- No multi-turn long-horizon autonomous-agent benchmark, tool-execution trajectory benchmark, or recovery-after-tool-failure test.
- No full 512K-window test; longest retrieval prompt was 443,355 tokens.
- No multi-request concurrency or long-duration soak test.
- Vision sample size: one image, four questions.
- Custom 24-task score is small and cannot support a claim of general parity or superiority.
- The 512K context setting uses the model's extended context configuration; retrieval success does not establish equal quality to shorter-context use.

## Reproduction materials and privacy

The original test's prompts/raw responses and private endpoint setup were stored locally. They are not included in this public package. This public report omits API credentials, private host paths, private IP addresses, tunnel commands, process IDs, service tokens, and raw request payloads. The sanitized `maya-report.txt` includes only hardware/runtime/model/build summary suitable for the Project Maya community.

## Source records

- Local evidence: `MAYA-S-DEPLOY-ACCEPTANCE-20261022.md`
- Local evidence: `MAYA-S-CONTEXT-3WAY-20261022.md`
- Local evidence: `MAYA-S-VS-OFFICIAL-AB-20261022.md`
- Reload check: `MAYA-S-RELOAD-20261023.md`

These internal source records are not part of this public repository.
