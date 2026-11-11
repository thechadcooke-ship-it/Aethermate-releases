# open-models

Small, local-first building blocks for on-device agents, with honest benchmarks. This is the first release.

> **Built on a stock model. Our contribution is the layer around it.** We did not retrain or fine-tune the model, and no
> model weights are in this repository. You download them from their makers.

| | What it is | Built on |
|---|---|---|
| [`vision/`](vision/) | A tuned Ollama runtime config, system prompt and image handling for reading screens and receipts, plus a synthetic test battery | [LFM2.5-VL-3B](https://huggingface.co/LiquidAI/LFM2.5-VL-3B-GGUF) (Liquid AI, LFM Open License v1.0) |

Coming next: a fine-tuned **Laya** decision model and its confidence gate, released once the fine-tune is benchmarked.

## Why

It is local-first, fast and private. Screen and receipt reads stay on your machine and cost nothing. A 3B vision model is enough
to pair with a non-vision LLM: the small model looks, and your main model thinks.

## Results

These were run on synthetic cases. The details and caveats are in [`benchmarks/`](benchmarks/).

- **Held-out set:** 30 fresh synthetic screen and receipt images (90 runs), scored with the prompt frozen.
  - The tuned config got **90/90**, against **85/90** for stock Ollama defaults.
  - Its answers are about **3x shorter** and easier to parse.
  - Stock's misses are mostly answer format, not misreads.
- **Tuning set:** 28 images (84 runs), the set the prompt was fixed against, so it is not a clean test. Tuned 84/84, stock 79/84.
- **Speed:** about 50 ms to first token when warm, and about 140 tokens/s on a laptop RTX 4070.
- **Against LFM3-VL-2B:** on an earlier internal 22-case battery (cited, not re-run here), both scored 22/22. LFM2.5-VL-3B decoded about twice as fast, with lower time-to-first-token.

## Quick start (Ollama)

```bash
cd vision
ollama create lfm25-vl-tuned -f Modelfile        # pulls the official GGUF and bakes in the config
ollama run lfm25-vl-tuned "What is the total?" ./receipt.png
```

`vision/README.md` has the settings and why each one is set, plus llama.cpp and MLX equivalents (not tested for this release).
`vision/vision_bench.py` and `vision/heldout_cases.py` regenerate the synthetic images and re-run the scores.

## Licences

- **Our code and config:** Apache-2.0 (see [`LICENSE`](LICENSE)).
- **The base model:** LFM2.5-VL-3B is Liquid AI's, under the LFM Open License v1.0. Commercial use is licensed only below US$10M annual revenue, and redistribution has conditions. Read [`NOTICE`](NOTICE) and Liquid AI's licence before you use it commercially.

## Layout

```
vision/        Modelfile, README, bench + held-out case generator
benchmarks/    method, hardware, result tables, the synthetic images, raw results
NOTICE         third-party licences (verbatim LFM licence excerpts)
LICENSE        Apache-2.0 for the code in this folder
```
