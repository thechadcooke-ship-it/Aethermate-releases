#!/usr/bin/env python3
"""Held-out synthetic battery: same task types as vision_bench.build_cases(), entirely different content.

Written AFTER the tuned prompt/Modelfile were frozen and never run through any model while the prompt was being
tuned. Render, then run with vision_bench.py exactly as for the tuning set:

    python3 heldout_cases.py --out ../benchmarks/vision/heldout
    python3 vision_bench.py run --cases ../benchmarks/vision/heldout --model lfm25-vl-tuned --baked --out ...
"""
import argparse
import json
import os

import vision_bench as vb

NEG = vb.NEG_PROMPT


def gradient2(c0, c1):
    I, _, _ = vb._pil()
    im = I.new("RGB", (600, 300))
    px = im.load()
    for y in range(300):
        c = tuple(int(a + (b - a) * y / 299) for a, b in zip(c0, c1))
        for x in range(600):
            px[x, y] = c
    return im


def wallpaper2():
    I, D, _ = vb._pil()
    im = I.new("RGB", (640, 360), (20, 70, 80))
    d = D.Draw(im, "RGBA")
    d.ellipse([300, 120, 700, 480], fill=(255, 255, 255, 28))
    d.ellipse([-120, -80, 240, 240], fill=(255, 140, 160, 36))
    return im


def buttons2():
    I, D, _ = vb._pil()
    im = I.new("RGB", (500, 140), "#2b2b2b")
    d = D.Draw(im)
    for i, (t, c) in enumerate([("Apply", "#2d6cdf"), ("Discard", "#d9822b")]):
        d.rectangle([40 + i * 200, 45, 190 + i * 200, 95], fill=c)
        d.text((115 + i * 200, 70), t, fill="white", font=vb.font(20), anchor="mm")
    return im


def build():
    C = []

    def add(cat, name, img, prompt, gold):
        C.append(dict(category=cat, name=name, img=img, prompt=prompt, gold=gold))

    bakery = vb.receipt("Birch Lane Bakery", "21/08/2026  08:12",
                        [("Sourdough loaf", "5.20"), ("Cinnamon bun", "3.10"), ("Tea", "2.60")], "1.10", "12.00", store="Store #207")
    add("receipt", "bakery_total", bakery, "What is the total amount on this receipt?", ("regex", [r"12\.00"]))
    add("receipt", "bakery_line", bakery, "How much was the tea?", ("regex", [r"2\.60"]))
    add("receipt", "garden_merchant_date",
        vb.receipt("Delta Garden Supply (demo)", "2026-09-18  15:40",
                   [("Potting soil 20L", "8.75"), ("Trowel", "6.40"), ("Plant labels", "2.20")], "3.47", "20.82"),
        "What is the merchant name and the date on this receipt?", ("contains_all", ["delta garden", "2026-09-18"]))
    add("receipt", "fuel_total",
        vb.receipt("Orchard Fuel & Go", "03/11/2026  18:05", [("Fuel 38.2 L", "42.18"), ("Coffee", "3.45")], "0.00", "45.63", store="Pump 4"),
        "What is the total amount on this receipt?", ("regex", [r"45\.63"]))
    I, D, _ = vb._pil()
    inv = I.new("RGB", (560, 330), "white")
    d = D.Draw(inv)
    d.text((28, 22), "Lumen Signs Studio (demo)", fill="#111", font=vb.font(24))
    d.text((28, 70), "INVOICE  #INV-88302", fill="#b00020", font=vb.font(22))
    for i, ln in enumerate(["Issued: 2026-10-09", "Terms: net 14", "Shop sign, painted ..... $3,210.00",
                            "Fitting ................. $265.50"]):
        d.text((28, 112 + i * 30), ln, fill="#222", font=vb.font(17, False, True))
    d.text((28, 256), "Amount due: $3,475.50", fill="#111", font=vb.font(26))
    add("receipt", "signs_invoice", inv, "What is the invoice number and the amount due?",
        ("contains_all", ["inv-88302", "3,475.50"]))
    add("app_ui", "sketchpad_title", vb.window("Sketchpad", "logo-draft.svg", [("<svg width=\"512\">", "#9cdcfe")]),
        "What application and file name are shown in the title bar? Be exact.", ("contains_all", ["sketchpad", "logo-draft.svg"]))
    add("app_ui", "maildesk_title", vb.window("MailDesk", "Inbox (12)", [("From   Subject   Date", "#4ec9b0")]),
        "What application and which folder are shown in the title bar?", ("contains_all", ["maildesk", "inbox"]))
    add("app_ui", "export_error_dialog",
        vb.dialog("Sketchpad", "Error", ["Export failed (code E_EXPORT_507):", "cloud storage quota exceeded."]),
        "What is the error code in this dialog?", ("regex", [r"E_EXPORT_507"]))
    t = vb.toggles([("Wi-Fi sync", True), ("Autosave", False), ("Sound effects", True)], title="Options")
    add("app_ui", "toggle_autosave_off", t, "In this settings panel, is 'Autosave' turned ON or OFF?", ("regex", [r"\boff\b"]))
    add("app_ui", "toggle_sound_on", t, "In this settings panel, is 'Sound effects' turned ON or OFF?", ("regex", [r"\bon\b"]))
    add("app_ui", "project_members", vb.kv_panel("Project", [("Name", "Harvest Planner"), ("Members", "9"), ("Tier", "Pro")]),
        "How many members does this project have? Answer with the number.", ("regex", [r"\b9\b"]))
    add("app_ui", "tickets_open", vb.kv_panel("Support", [("Open tickets", "36"), ("Closed", "211"), ("Avg reply", "4h")]),
        "How many open tickets are shown? Answer with the number.", ("regex", [r"\b36\b"]))
    add("error_read", "valueerror",
        vb.terminal([("Traceback (most recent call last):", False), ('  File "parse.py", line 9, in load', False),
                     ('  File "util.py", line 31, in to_int', False),
                     ("ValueError: invalid literal for int() with base 10: 'abc'", True)]),
        "Read the exact error type and message from this terminal.", ("contains_all", ["valueerror", "invalid literal"]))
    add("error_read", "cargo_e0425",
        vb.terminal([("$ cargo build", False), ("error[E0425]: cannot find value `total` in this scope", True),
                     (" --> src/main.rs:14:20", False)]),
        "What is the compiler error code shown?", ("regex", [r"E0425"]))
    add("error_read", "docker_port",
        vb.terminal([("$ docker run -p 8080:80 web", False),
                     ("docker: Error response from daemon: port is already allocated.", True)]),
        "What error does docker report? Quote it.", ("contains_all", ["port is already allocated"]))
    add("chart_read", "zephx_price", vb.chart("ZEPHX", "1D", "$54.20", 38, up=False),
        "What is the ticker symbol, timeframe, and price on this chart?", ("contains_all", ["zephx", "1d", "54.20"]))
    add("chart_read", "quill_rsi", vb.chart("QUILL", "30m", "$9.85", 71),
        "What is the RSI value shown on this chart?", ("regex", [r"\b71\b"]))
    add("chart_read", "marln_price", vb.chart("MARLN", "1W", "$212.90", 55),
        "What price is shown on this chart?", ("regex", [r"212\.90"]))
    add("small_text", "error_log",
        vb.small_lines(["[08:31:40] api-2 listening on :8443", "[08:31:41] job 7731 queued (batch 12)",
                        "[08:31:44] ERROR upload failed status=503 retry=2", "[08:31:44] job 7732 queued (batch 12)",
                        "[08:31:45] metrics flushed (410 points)"]),
        "What is the ERROR line's status code?", ("regex", [r"\b503\b"]))
    add("grounding", "red_left", vb.grounding(side="left"),
        "There is one red button. Is it on the LEFT or the RIGHT side of the image?", ("regex", [r"\bleft\b"]))
    add("grounding", "red_bottom", vb.grounding(vert="bottom"),
        "There is one red button. Is it in the TOP half or the BOTTOM half?", ("regex", [r"\b(bottom|lower)\b"]))
    add("count", "circles6", vb.shapes(6, "circle"), "How many circles are in this image? Answer with the number.", ("regex", [r"\b(6|six)\b"]))
    add("count", "squares4", vb.shapes(4, "square"), "How many squares are in this image? Answer with the number.", ("regex", [r"\b(4|four)\b"]))
    add("color_layout", "apply_discard", buttons2(), "What buttons are shown and roughly what colours are they?",
        ("contains_all", ["apply", "discard"]))
    add("color_layout", "big_number", vb.bigtext("163", 80), "What number is shown in this image?", ("regex", [r"163"]))
    for n, im, p in (("plain_ochre", vb.plain("#8a6f3a"), NEG), ("plain_teal", vb.plain("#244a5e"), NEG),
                     ("plain_silver", vb.plain("#9a9a9a"), "Is there anything actionable or notable on this screen? If nothing, say 'nothing notable'."),
                     ("gradient_sunset", gradient2((60, 10, 70), (250, 160, 90)), "Are there any UI elements, text or errors here? If none, reply 'nothing notable'."),
                     ("wallpaper_teal", wallpaper2(), "This looks like a desktop wallpaper. Is there any window, text or actionable UI element? If none, reply 'nothing notable'.")):
        add("negative", n, im, p, ("expect_null", []))
    return C


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    meta = []
    for c in build():
        c["img"].save(os.path.join(a.out, c["name"] + ".png"))
        meta.append({k: c[k] for k in ("category", "name", "prompt", "gold")})
    json.dump(meta, open(os.path.join(a.out, "cases.json"), "w", encoding="utf-8"), indent=1)
    print(f"rendered {len(meta)} held-out cases to {a.out}")
