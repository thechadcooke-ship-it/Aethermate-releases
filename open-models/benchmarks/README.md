# Benchmarks

Everything here was run on **synthetic cases generated for this release** (fictional merchants, companies and apps;
no real screenshots, emails, invoices or messages). Raw per-case results sit next to the tables so you can re-score
them. The sets are small: read the numbers as direction, not precision.

**About earlier numbers.** Before this release we had an internal 8-case decision set (and a 22-case screen set).
The "100% accuracy, 62.5% fewer LLM calls" figure came from the 8-case set and **assumed every escalated case
was answered correctly**; it is not a measurement and is not reproduced here. Everything below is re-run, with
escalations answered by a real model.

## Hardware and setup

| | |
|---|---|
| Machine | gaming laptop, NVIDIA RTX 4070 Laptop GPU (8 GB), Windows 11, 11 Nov 2026 |
| Vision runtime | Ollama 0.40.14 on the GPU, model `hf.co/LiquidAI/LFM2.5-VL-3B-GGUF:Q4_K_M` (same blob as `lfm2.5-vl:3b`); benchmark client in WSL2 over localhost |
| Not run | LFM3-VL-2B (cited row only) |


## 2. LFM2.5-VL-3B tuned runtime (`vision/`)

Two batteries of generated images, same task types, different content: receipts and an invoice (total, line item,
merchant + date, invoice number + amount due), made-up app screens (title bars, error dialog, toggles, form and
dashboard values), terminal errors, charts, a dense log, grounding, counting, colour/number, and blank/negative
images. Scoring is automatic (regex / contains). 3 runs per case. Config: `vision/Modelfile`.

### Headline: held-out set (30 images, 90 runs per configuration)

The tuned prompt and Modelfile were **frozen** before this set was written. Its images were never shown to a
model while the prompt was being tuned. Files: `benchmarks/vision/heldout/` (PNGs + `cases.json`),
`heldout_stock.json`, `heldout_tuned.json`.

| Configuration | Runs correct | Cases all-pass | TTFT p50 / p95 | Decode tok/s (median) | Mean output tokens |
|---|---|---|---|---|---|
| Stock Ollama defaults, no system prompt | 85/90 (94%) | 28/30 | 41 / 144 ms | 126.4 | 20.1 |
| **Tuned (shipped Modelfile)** | **90/90 (100%)** | **30/30** | 57 / 160 ms | 141.2 | 6.5 |

Per category, stock / tuned: receipts 12/15 vs 15/15, charts 7/9 vs 9/9; all other categories (app UI, terminal
errors, small text, grounding, counting, colour, negatives) were perfect in both.

How to read it:
- The tuned config answers in **~3x fewer tokens** (6.5 vs 20) and scored 5 more runs out of 90. Stock's misses are
  mostly format: it answers in sentences ("the date is September ...", "timeframe is 1 day") against a strict
  scorer that expected the literal on-image text. So the accuracy gap overstates the tuning's effect on *reading*;
  the terse, literal output style, which a program can parse, is the real difference.
- Tuned TTFT was a little slower in this run (57 vs 41 ms p50); the system prompt adds tokens to prefill. Both are
  warm, small images.
- 30 images x 3 runs on one machine. No confidence intervals; treat 100% as "no failures seen", not "perfect".

### Secondary: tuning set (28 images, 84 runs) - NOT a clean test

This is the set the prompt was developed against, so its numbers are optimistic. Files:
`benchmarks/vision/tuning_cases/`, `tuning_*.json`.

| Configuration | Runs correct | Cases all-pass | TTFT p50 / p95 | Decode tok/s | Mean output tokens |
|---|---|---|---|---|---|
| Stock Ollama defaults | 79/84 (94%) | 25/28 | 46 / 142 ms | 126.6 | 21.8 |
| Tuned, first version, with a "reply nothing notable" clause (ablation) | 75/84 (89%) | 25/28 | 50 / 142 ms | 142.5 | 6.2 |
| Tuned (shipped Modelfile) | 84/84 (100%) | 28/28 | 52 / 147 ms | 143.4 | 7.3 |

The first version of the system prompt ended with a "reply nothing notable if nothing is present" clause and
scored 75/84: the model took that exit on two busy images (a git error, a down-trending chart). Removing the clause
fixed those. That fix was made after seeing this set, which is why the held-out set above is the headline. It held up:
the same frozen prompt scored 90/90 on fresh images.

### Other notes
- Latency depends on warm/cold state and image size. Internal measurement on a real 2560x1440 screenshot: 2048 px
  cap ~1.2 s first-eval vs ~0.35 s at 1024 px; a cold reload after `keep_alive` expiry added ~3.5 s. Not reproduced
  on these synthetic sets (small images, warm model).
- Temperature 0.1, so repeats vary slightly; each case was run 3 times.

### Comparison row: LFM3-VL-2B (cited, not re-run)

Re-running LFM3-VL-2B (MLX 8-bit on an Apple-silicon Mac) on these sets was not easy, so this row is from an
**internal 22-case screen battery run on 27-28 Oct 2026**, not the cases published here. Both models ran that same
internal set:

| Model | Host | Accuracy (22 cases) | TTFT p50 / p95 | Decode tok/s |
|---|---|---|---|---|
| LFM2.5-VL-3B (Ollama, Q4_K_M) | laptop GPU | 22/22 | 120 / 160 ms | 114 |
| LFM3-VL-2B (MLX 8-bit) | Apple-silicon Mac | 22/22 | 190 / 390 ms | 57 |

A tie on accuracy; LFM3-VL-2B decoded at about half the speed on a different runtime and host (direction only).

Reproduce: `ollama create lfm25-vl-tuned -f vision/Modelfile`, then
`python3 vision/vision_bench.py run --cases benchmarks/vision/heldout --model lfm25-vl-tuned --baked --out tuned.json`
(and `--model hf.co/LiquidAI/LFM2.5-VL-3B-GGUF:Q4_K_M --stock` for the baseline).
