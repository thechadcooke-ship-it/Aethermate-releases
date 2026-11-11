#!/usr/bin/env python3
"""Synthetic screen/receipt vision battery for LFM2.5-VL through Ollama.

    python3 vision_bench.py render --out ../benchmarks/vision/tuning_cases
    python3 vision_bench.py run --cases ../benchmarks/vision/tuning_cases --model lfm25-vl-tuned \
        --label "tuned (Modelfile)" --repeat 3 --out ../benchmarks/vision/tuned.json
    python3 vision_bench.py run ... --model hf.co/LiquidAI/LFM2.5-VL-3B-GGUF:Q4_K_M --stock   # untuned baseline

Every image is generated here (made-up apps, made-up merchants, no real screenshots). Needs Pillow for `render`.
`run` is standard library only and talks to a local Ollama (http://127.0.0.1:11434).
"""
import argparse
import base64
import io
import json
import re
import statistics
import time
import urllib.request

OLLAMA = "http://127.0.0.1:11434"
# The tuned runtime config (identical to the Modelfile).
TUNED_OPTIONS = {"temperature": 0.1, "min_p": 0.15, "repeat_penalty": 1.05, "num_predict": 160}
SYSTEM = ("You are a precise screen-reader for a desktop assistant. Extract EXACT text, numbers, and "
          "app/file names verbatim. Answer ONLY what is asked, tersely. Do not read back passwords or secret tokens.")
NEG_PROMPT = ("Describe any windows, text, errors, buttons or UI elements. "
              "If there are none, reply exactly 'nothing notable'.")


# ----------------------------------------------------------------------------- rendering
def _pil():
    from PIL import Image, ImageDraw, ImageFont
    return Image, ImageDraw, ImageFont


def font(sz, bold=True, mono=False):
    _, _, F = _pil()
    name = "DejaVuSansMono" if mono else "DejaVuSans"
    for p in (f"/usr/share/fonts/truetype/dejavu/{name}{'-Bold' if bold else ''}.ttf",
              f"/usr/share/fonts/truetype/dejavu/{name}.ttf", f"{name}.ttf"):
        try:
            return F.truetype(p, sz)
        except Exception:
            pass
    return F.load_default()


def receipt(merchant, date, items, tax, total, store="Store #014"):
    I, D, _ = _pil()
    im = I.new("RGB", (380, 120 + 34 * (len(items) + 4)), "#fbfbf6")
    d = D.Draw(im)
    d.text((190, 20), merchant, fill="#111", font=font(24), anchor="mt")
    d.text((190, 52), store, fill="#444", font=font(15, False, True), anchor="mt")
    d.text((190, 74), date, fill="#444", font=font(15, False, True), anchor="mt")
    y = 112
    for name, price in items:
        d.text((24, y), name, fill="#111", font=font(17, False, True))
        d.text((356, y), price, fill="#111", font=font(17, False, True), anchor="ra")
        y += 34
    d.line([24, y, 356, y], fill="#888", width=1)
    y += 10
    sub = f"{sum(float(p) for _, p in items):.2f}"
    for lab, val, b in (("Subtotal", sub, False), ("Tax", tax, False), ("TOTAL", total, True)):
        d.text((24, y), lab, fill="#111", font=font(18 if b else 17, b, True))
        d.text((356, y), val, fill="#111", font=font(18 if b else 17, b, True), anchor="ra")
        y += 34
    return im


def invoice_img():
    I, D, _ = _pil()
    im = I.new("RGB", (560, 330), "white")
    d = D.Draw(im)
    d.text((28, 22), "Kestrel Print Co (demo)", fill="#111", font=font(24))
    d.text((28, 70), "INVOICE  #INV-20417", fill="#b00020", font=font(22))
    for i, ln in enumerate(["Issued: 2026-05-02", "Terms: net 30", "Posters A2 x 40 ........ $1,120.00",
                            "Delivery ................ $164.00"]):
        d.text((28, 112 + i * 30), ln, fill="#222", font=font(17, False, True))
    d.text((28, 256), "Amount due: $1,284.00", fill="#111", font=font(26))
    return im


def window(app, title, body=None, w=760, h=200):
    I, D, _ = _pil()
    im = I.new("RGB", (w, h), "#1e1e1e")
    d = D.Draw(im)
    d.rectangle([0, 0, w, 34], fill="#323233")
    d.text((10, 7), f"{app} — {title}", fill="#ccc", font=font(18))
    y = 70
    for ln, col in body or [("# Weekly notes", "#9cdcfe")]:
        d.text((20, y), ln, fill=col, font=font(20, False, True))
        y += 30
    return im


def dialog(app, title, lines):
    I, D, _ = _pil()
    im = I.new("RGB", (640, 260), "#2b2b30")
    d = D.Draw(im)
    d.rectangle([60, 30, 580, 230], fill="#3a3a42", outline="#666")
    d.rectangle([60, 30, 580, 62], fill="#4a4a55")
    d.text((72, 36), f"{app} — {title}", fill="#fff", font=font(16))
    for i, ln in enumerate(lines):
        d.text((76, 80 + i * 28), ln, fill="#f2f2f2", font=font(16, False))
    d.rectangle([450, 188, 560, 218], fill="#2d6cdf")
    d.text((505, 196), "OK", fill="white", font=font(16), anchor="mt")
    return im


def terminal(lines, w=760, h=240):
    I, D, _ = _pil()
    im = I.new("RGB", (w, h), "#0c0c0c")
    d = D.Draw(im)
    for i, (ln, err) in enumerate(lines):
        d.text((12, 14 + i * 28), ln, fill="#f14c4c" if err else "#d4d4d4", font=font(16, False, True))
    return im


def chart(sym, tf, price, rsi, up=True):
    I, D, _ = _pil()
    im = I.new("RGB", (760, 340), "#131722")
    d = D.Draw(im)
    col = "#26a69a" if up else "#ef5350"
    d.text((14, 10), f"{sym}   {tf}", fill="#d1d4dc", font=font(24))
    d.text((14, 44), price, fill=col, font=font(30))
    pts = [(40, 260), (140, 210), (240, 240), (340, 160), (440, 190), (540, 120), (660, 140)]
    d.line(pts if up else [(x, 380 - y) for x, y in pts], fill=col, width=3)
    d.text((14, 292), f"RSI {rsi}", fill="#787b86", font=font(18))
    return im


def small_lines(lines):
    I, D, _ = _pil()
    im = I.new("RGB", (560, 200), "#f4f4f4")
    d = D.Draw(im)
    for i, ln in enumerate(lines):
        d.text((14, 12 + i * 28), ln, fill="#222", font=font(15, False, True))
    return im


def toggles(rows, title="Preferences"):
    I, D, _ = _pil()
    w, h = 520, 60 + len(rows) * 52
    im = I.new("RGB", (w, h), "#252526")
    d = D.Draw(im)
    d.text((18, 16), title, fill="#fff", font=font(22))
    y = 60
    for label, on in rows:
        d.text((20, y + 8), label, fill="#ddd", font=font(18, False))
        pill = [w - 130, y + 4, w - 20, y + 40]
        d.rounded_rectangle(pill, radius=18, fill="#2ea043" if on else "#555")
        kx = pill[2] - 34 if on else pill[0] + 2
        d.ellipse([kx, y + 6, kx + 32, y + 38], fill="#fff")
        d.text((pill[0] + (14 if on else 44), y + 10), "ON" if on else "OFF", fill="#fff", font=font(15))
        y += 52
    return im


def kv_panel(title, rows):
    I, D, _ = _pil()
    im = I.new("RGB", (520, 70 + 44 * len(rows)), "#f7f7f9")
    d = D.Draw(im)
    d.text((20, 16), title, fill="#222", font=font(22))
    for i, (k, v) in enumerate(rows):
        d.text((24, 64 + i * 44), k, fill="#555", font=font(18, False))
        d.text((300, 64 + i * 44), v, fill="#111", font=font(18))
    return im


def grounding(side=None, vert=None):
    I, D, _ = _pil()
    im = I.new("RGB", (640, 360), "#20232a")
    d = D.Draw(im)
    for bx in ((40, 60), (40, 240), (440, 60), (440, 240)):
        d.rectangle([bx[0], bx[1], bx[0] + 160, bx[1] + 70], fill="#3b3f47")
    rx, ry = (440 if side == "right" else 40, 150) if side else (240, 40 if vert == "top" else 250)
    d.rectangle([rx, ry, rx + 160, ry + 70], fill="#d23b3b")
    d.text((rx + 80, ry + 35), "DELETE", fill="white", font=font(20), anchor="mm")
    return im


def shapes(n, kind):
    I, D, _ = _pil()
    im = I.new("RGB", (600, 220), "white")
    d = D.Draw(im)
    for i in range(n):
        box = [20 + i * 100, 70, 90 + i * 100, 140]
        (d.ellipse if kind == "circle" else d.rectangle)(box, fill="#e0503a" if kind == "circle" else "#3a7ad0")
    return im


def buttons():
    I, D, _ = _pil()
    im = I.new("RGB", (500, 140), "#2b2b2b")
    d = D.Draw(im)
    for i, (t, c) in enumerate([("Save", "#0a7a4a"), ("Cancel", "#a33030")]):
        d.rectangle([40 + i * 200, 45, 190 + i * 200, 95], fill=c)
        d.text((115 + i * 200, 70), t, fill="white", font=font(20), anchor="mm")
    return im


def bigtext(txt, sz=90):
    I, D, _ = _pil()
    im = I.new("RGB", (400, 300), "white")
    D.Draw(im).text((200, 150), txt, fill="black", font=font(sz), anchor="mm")
    return im


def plain(color):
    I, _, _ = _pil()
    return I.new("RGB", (600, 300), color)


def gradient():
    I, _, _ = _pil()
    im = I.new("RGB", (600, 300))
    px = im.load()
    for y in range(300):
        c = tuple(int(a + (b - a) * y / 299) for a, b in zip((20, 20, 40), (200, 120, 60)))
        for x in range(600):
            px[x, y] = c
    return im


def wallpaper():
    I, D, _ = _pil()
    im = I.new("RGB", (640, 360), (60, 40, 110))
    d = D.Draw(im, "RGBA")
    d.ellipse([-80, 180, 260, 460], fill=(255, 255, 255, 30))
    d.ellipse([360, -60, 720, 260], fill=(255, 200, 120, 40))
    return im


def build_cases():
    C = []

    def add(cat, name, img, prompt, gold):
        C.append(dict(category=cat, name=name, img=img, prompt=prompt, gold=gold))

    cafe = receipt("Maple Pine Cafe", "14/03/2026  12:41",
                   [("Flat white", "3.80"), ("Croissant", "2.90"), ("Orange juice", "3.20")], "0.99", "10.89")
    add("receipt", "cafe_total", cafe, "What is the total amount on this receipt?", ("regex", [r"10\.89"]))
    add("receipt", "cafe_line", cafe, "How much was the croissant?", ("regex", [r"2\.90"]))
    add("receipt", "hardware_merchant_date",
        receipt("Harbor Hardware (demo)", "2026-07-02  09:15",
                [("Wood screws x200", "6.50"), ("Drill bit set", "14.99")], "2.15", "23.64"),
        "What is the merchant name and the date on this receipt?",
        ("contains_all", ["harbor", "2026-07-02"]))
    add("receipt", "invoice_number_amount", invoice_img(),
        "What is the invoice number and the amount due?", ("contains_all", ["inv-20417", "1,284.00"]))
    add("app_ui", "notely_title", window("Notely", "meeting-notes.md"),
        "What application and file name are shown in the title bar? Be exact.",
        ("contains_all", ["notely", "meeting-notes.md"]))
    add("app_ui", "taskboard_title", window("TaskBoard", "Sprint 14 - Board", [("Backlog   Doing   Done", "#4ec9b0")]),
        "What application and which board are shown in the title bar?", ("contains_all", ["taskboard", "sprint 14"]))
    add("app_ui", "sync_error_dialog",
        dialog("TaskBoard", "Error", ["Sync failed (code E_SYNC_409):", "workspace was modified on another device."]),
        "What is the error code in this dialog?", ("regex", [r"E_SYNC_409"]))
    t = toggles([("Dark Mode", True), ("Notifications", False), ("Auto-update", True)])
    add("app_ui", "toggle_notifications_off", t, "In this settings panel, is 'Notifications' turned ON or OFF?", ("regex", [r"\boff\b"]))
    add("app_ui", "toggle_darkmode_on", t, "In this settings panel, is 'Dark Mode' turned ON or OFF?", ("regex", [r"\bon\b"]))
    add("app_ui", "workspace_seats", kv_panel("Workspace", [("Name", "Demo Workspace"), ("Seats", "14"), ("Plan", "Team")]),
        "How many seats does this workspace have? Answer with the number.", ("regex", [r"\b14\b"]))
    add("app_ui", "dashboard_refunds", kv_panel("Today", [("Orders", "128"), ("Refunds", "7"), ("Revenue", "$4,310")]),
        "How many refunds are shown? Answer with the number.", ("regex", [r"\b7\b"]))
    add("error_read", "py_traceback",
        terminal([("Traceback (most recent call last):", False), ('  File "app.py", line 42, in run', False),
                  ('  File "db.py", line 17, in query', False), ("TypeError: 'NoneType' object is not subscriptable", True)]),
        "Read the exact error type and message from this terminal.", ("contains_all", ["typeerror", "nonetype", "subscriptable"]))
    add("error_read", "npm_enoent",
        terminal([("$ npm run build", False), ("npm ERR! code ENOENT", True), ("npm ERR! syscall open", True),
                  ("npm ERR! enoent ENOENT: no such file, open 'package.json'", True)]),
        "What is the npm error code and the missing file?", ("contains_all", ["enoent", "package.json"]))
    add("error_read", "git_fatal",
        terminal([("$ git push origin main", False), ("fatal: The current branch main has no upstream branch.", True),
                  ("    git push --set-upstream origin main", False)]),
        "What git error is shown? Quote the fatal line.", ("contains_all", ["upstream"]))
    add("chart_read", "acmex_price", chart("ACMEX", "1H", "$128.40", 62),
        "What is the ticker symbol, timeframe, and price on this chart?", ("contains_all", ["acmex", "1h", "128.40"]))
    add("chart_read", "bolt_rsi", chart("BOLTX", "4H", "$31.07", 44, up=False),
        "What is the RSI value shown on this chart?", ("regex", [r"\b44\b"]))
    add("small_text", "dense_log",
        small_lines(["[12:04:07] worker-3 connected (pid 8814)", "[12:04:07] cache warm: 1,204 keys in 38ms",
                     "[12:04:08] WARN retry queue depth = 9", "[12:04:09] request 0xA31F served 200 in 12ms",
                     "[12:04:09] flush ok -> disk (seq 55219)"]),
        "What is the WARN message and its numeric value in this log?", ("regex", [r"depth\D*9|queue.{0,20}\b9\b"]))
    add("grounding", "red_right", grounding(side="right"),
        "There is one red button. Is it on the LEFT or the RIGHT side of the image?", ("regex", [r"\bright\b"]))
    add("grounding", "red_top", grounding(vert="top"),
        "There is one red button. Is it in the TOP half or the BOTTOM half?", ("regex", [r"\b(top|upper)\b"]))
    add("count", "circles5", shapes(5, "circle"), "How many circles are in this image? Answer with the number.", ("regex", [r"\b(5|five)\b"]))
    add("count", "squares3", shapes(3, "square"), "How many squares are in this image? Answer with the number.", ("regex", [r"\b(3|three)\b"]))
    add("color_layout", "save_cancel", buttons(), "What buttons are shown and roughly what colours are they?",
        ("contains_all", ["save", "cancel"]))
    add("color_layout", "big_number", bigtext("87"), "What number is shown in this image?", ("regex", [r"87"]))
    for n, im, p in (("plain_blue", plain("#3a5f8a"), NEG_PROMPT), ("plain_green", plain("#2f7d4f"), NEG_PROMPT),
                     ("plain_grey", plain("#777777"), "Is there anything actionable or notable on this screen? If nothing, say 'nothing notable'."),
                     ("gradient", gradient(), "Are there any UI elements, text or errors here? If none, reply 'nothing notable'."),
                     ("wallpaper", wallpaper(), "This looks like a desktop wallpaper. Is there any window, text or actionable UI element? If none, reply 'nothing notable'.")):
        add("negative", n, im, p, ("expect_null", []))
    return C


# ----------------------------------------------------------------------------- scoring
NEG_OK = ("nothing notable", "nothing", "no windows", "no window", "no text", "no error", "none", "blank", "empty",
          "solid", "plain", "no actionable", "no ui", "no elements", "gradient", "background", "wallpaper",
          "no buttons", "no notable", "not notable")


def score(gold, resp):
    kind, vals = gold
    r = resp.lower()
    if kind == "contains_all":
        return all(v.lower() in r for v in vals)
    if kind == "regex":
        return all(re.search(p, resp, re.I) for p in vals)
    if kind == "expect_null":
        return any(k in r for k in NEG_OK)
    return False


# ----------------------------------------------------------------------------- running
def to_jpeg_b64(path, max_dim):
    """Mirror of the production image handling: RGB JPEG, long edge capped (default 2048)."""
    I, _, _ = _pil()
    im = I.open(path).convert("RGB")
    im.thumbnail((max_dim, max_dim))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


def ask(model, prompt, img_b64, tuned, keep_alive="30m"):
    """One streamed /api/chat call. Returns (text, ttft_s, tok_per_s, output_tokens)."""
    msgs = [{"role": "user", "content": prompt, "images": [img_b64]}]
    body = {"model": model, "messages": msgs, "stream": True, "keep_alive": keep_alive}
    if tuned:                # explicit options + system prompt (a Modelfile model already has both baked in)
        body["options"] = TUNED_OPTIONS
        msgs.insert(0, {"role": "system", "content": SYSTEM})
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    first, text, last = None, "", {}
    with urllib.request.urlopen(req, timeout=180) as r:
        for line in r:
            ch = json.loads(line)
            piece = (ch.get("message") or {}).get("content") or ""
            if piece and first is None:
                first = time.perf_counter() - t0
            text += piece
            if ch.get("done"):
                last = ch
    total = time.perf_counter() - t0
    tps = last["eval_count"] / (last["eval_duration"] / 1e9) if last.get("eval_duration") else 0.0
    return text.strip(), (first if first is not None else total), tps, last.get("eval_count", 0)


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def run(a):
    import os
    meta = json.load(open(os.path.join(a.cases, "cases.json"), encoding="utf-8"))
    tuned = not (a.stock or a.baked)
    imgs = {c["name"]: to_jpeg_b64(os.path.join(a.cases, c["name"] + ".png"), a.max_dim) for c in meta}
    ask(a.model, "Say ok.", imgs[meta[0]["name"]], tuned)       # warm-up (model load), not recorded
    rows, ttfts, tpss, toks = [], [], [], []
    for c in meta:
        passes = 0
        for _ in range(a.repeat):
            txt, ttft, tps, ntok = ask(a.model, c["prompt"], imgs[c["name"]], tuned)
            ok = score(c["gold"], txt)
            passes += ok
            ttfts.append(ttft * 1000)
            tpss.append(tps)
            toks.append(ntok)
            last = txt
        rows.append({"category": c["category"], "name": c["name"], "passes": passes, "of": a.repeat,
                     "sample_answer": last[:200]})
        print(f"{c['category']}/{c['name']}: {passes}/{a.repeat}  {last[:70]!r}", flush=True)
    total, ok = sum(r["of"] for r in rows), sum(r["passes"] for r in rows)
    cats = {}
    for r in rows:
        x = cats.setdefault(r["category"], [0, 0])
        x[0] += r["passes"]
        x[1] += r["of"]
    out = {"label": a.label, "model": a.model, "mode": "stock" if a.stock else ("baked" if a.baked else "api-tuned"), "max_dim": a.max_dim, "repeat": a.repeat,
           "n_cases": len(rows), "passes": ok, "runs": total, "case_pass_all": sum(r["passes"] == r["of"] for r in rows),
           "per_category": {k: f"{v[0]}/{v[1]}" for k, v in cats.items()},
           "ttft_ms_p50": round(pct(ttfts, 50)), "ttft_ms_p95": round(pct(ttfts, 95)),
           "tok_per_s_median": round(statistics.median(tpss), 1), "mean_output_tokens": round(statistics.mean(toks), 1), "rows": rows}
    json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1)
    print(f"\n{a.label}: {ok}/{total} runs, {out['case_pass_all']}/{len(rows)} cases all-pass, "
          f"TTFT p50/p95 {out['ttft_ms_p50']}/{out['ttft_ms_p95']} ms, {out['tok_per_s_median']} tok/s")


def render(a):
    import os
    os.makedirs(a.out, exist_ok=True)
    meta = []
    for c in build_cases():
        c["img"].save(os.path.join(a.out, c["name"] + ".png"))
        meta.append({k: c[k] for k in ("category", "name", "prompt", "gold")})
    json.dump(meta, open(os.path.join(a.out, "cases.json"), "w", encoding="utf-8"), indent=1)
    print(f"rendered {len(meta)} cases to {a.out}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--out", required=True)
    u = sub.add_parser("run")
    u.add_argument("--cases", required=True)
    u.add_argument("--model", required=True)
    u.add_argument("--label", default=None)
    u.add_argument("--stock", action="store_true", help="no system prompt, no options: Ollama defaults")
    u.add_argument("--baked", action="store_true", help="model already has the tuned config (Modelfile): send nothing extra")
    u.add_argument("--repeat", type=int, default=3)
    u.add_argument("--max-dim", type=int, default=2048)
    u.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "run":
        a.label = a.label or a.model
        run(a)
    else:
        render(a)


if __name__ == "__main__":
    main()
