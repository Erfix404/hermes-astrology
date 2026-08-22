#!/usr/bin/env python3
"""OCR table strips via 9Router vision model. Saves text output per image.

Usage: python scripts/vision_ocr.py <image_or_dir> [--out DIR]
Reads OPENROUTER_BASE_URL / OPENROUTER_API_KEY from .env or environment.
"""
import argparse, base64, json, os, sys, urllib.request

def load_env():
    env = os.environ.get
    if env("OPENROUTER_API_KEY"):
        return env("OPENROUTER_BASE_URL", "https://openrouter.ai/v1"), env("OPENROUTER_API_KEY")
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    if os.path.isfile(p):
        for line in open(p, encoding="utf-8"):
            k, _, v = line.strip().partition("=")
            if k == "OPENROUTER_BASE_URL": base = v
            if k == "OPENROUTER_API_KEY": key = v
        return base, key
    sys.exit("no API key: set OPENROUTER_API_KEY or create .env")

PROMPT = ("This image is a row of an astrology terms (bounds) table: planet symbols "
          "followed by degree numbers. Transcribe EXACTLY what you see as a compact "
          "list like: 'Jupiter 6, Venus 14, Mercury 21, Mars 26, Saturn 30'. "
          "Planet symbols: h=Saturn, j=Jupiter, c=Mars, g=Mercury, f=Venus (or "
          "standard glyphs). Output only the transcription, nothing else.")

def ocr_image(path):
    base, key = load_env()
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    body = json.dumps({
        "model": os.environ.get("VISION_MODEL", "Vision"),
        "messages": [{"role": "user", "content": [
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": PROMPT},
        ]}],
        "max_tokens": 300,
    }).encode()
    req = urllib.request.Request(base + "/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"].strip()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--out", default="book/ptolemy_tables/ocr")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    imgs = ([a.path] if os.path.isfile(a.path)
            else [os.path.join(a.path, f) for f in sorted(os.listdir(a.path))
                  if f.lower().endswith(".png")])
    for img in imgs:
        name = os.path.splitext(os.path.basename(img))[0]
        try:
            txt = ocr_image(img)
            open(os.path.join(a.out, name + ".txt"), "w", encoding="utf-8").write(txt)
            print(f"{name}: {txt}")
        except Exception as e:
            print(f"{name}: ERROR {e}", file=sys.stderr)
