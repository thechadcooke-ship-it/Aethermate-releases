# vision: tuned runtime config for LFM2.5-VL-3B

Built on Liquid AI's stock **LFM2.5-VL-3B** (weights not included, not retrained). What we add is the
decoding config, the system prompt and the image handling that we run in production for screen and receipt reading.

## Quick start (Ollama)

```bash
ollama create lfm25-vl-tuned -f Modelfile        # pulls the official GGUF, bakes in the config
ollama run lfm25-vl-tuned "What is the total?" ./receipt.png
```

The Modelfile sets `temperature 0.1`, `min_p 0.15`, `repeat_penalty 1.05`, `num_predict 160`, and a terse
"precise screen-reader" system prompt. Over the API also send `"keep_alive": "30m"` (or `-1`).

| knob | value | why |
|---|---|---|
| temperature / min_p / repeat_penalty | 0.1 / 0.15 / 1.05 | Liquid's recommended sampling family, pushed toward exact extraction |
| num_predict | 160 (screen), 400 (describe an image), 512 (transcribe a screen) | short answers by default; big budget only when asked |
| system prompt | "extract EXACT text ... answer ONLY what is asked, tersely" | ~3x fewer output tokens than stock, easy to parse |
| no "reply nothing notable" clause in the system prompt | | with it, the model takes that exit on busy images (see benchmarks) |
| keep_alive | 30m, or -1 | a cold reload after expiry costs ~3.5 s inside the request (internal measurement), warm calls are ~0.5-1 s |
| image long edge | cap at 2048, or 1024 for speed | on a 2560x1440 screenshot, 1024 cut prompt-eval from ~1.2 s to ~0.35 s; fine text suffers below ~1024 |
| image format | RGB JPEG, <= 4 MB | avoids intermittent loader errors on odd PNG variants |

`vision_bench.py` is the battery used for the numbers in `../benchmarks/`: it renders 28 synthetic images
(made-up receipts, an invoice, made-up app windows, dialogs, toggles, terminals, charts, shapes, blank negatives)
and scores the answers.

```bash
python3 vision_bench.py render --out ../benchmarks/vision/tuning_cases   # tuning set; heldout_cases.py renders the held-out set
python3 vision_bench.py run --cases ../benchmarks/vision/tuning_cases --model lfm25-vl-tuned --baked --out tuned.json
python3 vision_bench.py run --cases ../benchmarks/vision/tuning_cases --model hf.co/LiquidAI/LFM2.5-VL-3B-GGUF:Q4_K_M --stock --out stock.json
```

## llama.cpp and MLX equivalents (NOT tested for this release)

The same settings expressed for other runtimes. We ran the numbers on Ollama only; treat these as a starting
point and check flag names against your build.

```bash
# llama.cpp (llama-server pulls the model and its mmproj from the official GGUF repo)
llama-server -hf LiquidAI/LFM2.5-VL-3B-GGUF:Q4_K_M --temp 0.1 --min-p 0.15 --repeat-penalty 1.05 -n 160 \
  --system-prompt "You are a precise screen-reader for a desktop assistant. Extract EXACT text, numbers, and app/file names verbatim. Answer ONLY what is asked, tersely. Do not read back passwords or secret tokens."

# MLX (Apple silicon): use an MLX conversion of LiquidAI/LFM2.5-VL-3B with mlx-vlm
python3 -m mlx_vlm.generate --model <your-mlx-conversion> --image receipt.png --prompt "What is the total?" \
  --temperature 0.1 --max-tokens 160
# mlx-vlm may not expose min_p / repeat_penalty on every version; with only temperature and max-tokens set you
# get most of the effect. We have not measured MLX with this config.
```

Licence: LFM Open License v1.0 for the base model (commercial use licensed only under US$10M annual
revenue). See `../NOTICE`.
