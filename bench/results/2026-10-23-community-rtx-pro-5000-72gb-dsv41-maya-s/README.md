# DeepSeek-V4.1-Flash-1017 Maya-S on 2× RTX PRO 5000 72GB

Community benchmark report — Project Maya v1.1.20, 512K context

## Headline results

| Test | Result | Scope / caveat |
|---|---:|---|
| DSpark calibration, 512K | 71.03 tok/s; 46.03 tok/s with DSpark off | 1024+ generated tokens; same host and harness; +54.3%, 573/855 draft tokens accepted (67%) |
| 24-task local/API check | Local 24.000/24; official API 23.975/24 | Small custom set, not an official benchmark or general parity claim |
| 443,355-token retrieval probe | 3/3 needles retrieved | Single-turn synthetic retrieval test; not multi-turn agent evaluation |
| Long-prompt prefill | about 1,553 tok/s at 443K | Approximate wall-time-derived figure; see detailed report |

## Setup

- 2× NVIDIA RTX PRO 5000 72GB (Blackwell), Ryzen 9 9950X3D, 249GB DDR5-6000
- Ubuntu 24.04, CUDA 13.0; Project Maya v1.1.20, self-built for sm_120
- DeepSeek-V4.1-Flash-1017 Maya-S, mixed IQ2_XXS/IQ2_S/IQ3_S, 2.56 bpw; 512K context, DSpark on
- Two-card layer split; TP2 request falls back to TP1 internally due to expert block constraints

## Interpretation

The measurements show that this Maya-S pack can serve 512K context on this two-GPU host and that DSpark materially improves decode throughput. On the small paired task set, local scores were close to the official API under the tested sampling settings. The sample is too small to establish broad quality parity. No long-horizon autonomous-agent benchmark was run.

## Limitations

- Not an official DeepSeek benchmark; custom 24-task set.
- No Terminal-Bench, DeepSWE, or HLE reproduction.
- No full 512K-window test; longest retrieval prompt was 443,355 tokens.
- No multi-turn long-running agent task, tool-execution trajectory, concurrency test, or long-duration stability test.
- Vision check was one image with four questions; small sample.
- Results are hardware-, build-, prompt-, and sampling-specific; do not compare directly to runs using different harnesses or model quantizations.

See [detailed report](./maya-s1017-report.md) and [sanitized Maya report attachment](./maya-report.txt).
