#!/usr/bin/env python3
"""One-shot cleanup of OCR artifacts in data/planet_in_house.json.

Removes page-number noise from the Woolfolk PDF extraction:
  "... 3 --PAGE 317 ---"          → "..."
  "302 • Understanding Astrology 3 --PAGE 318 --The Houses of Astrology • 303"
      → "" (running header/footer, not content)
Also collapses whitespace and stray bullet glyphs left by the scan.
Validates: 12 houses × 10 planets, every text ends with sentence punctuation.
"""
import json
import re
import sys

SRC = "data/planet_in_house.json"

FOOTER_RE = re.compile(
    r"\s*\d{1,3}\s*[•·]\s*[A-Za-z ,&]+?\s*\d{0,3}\s*--PAGE\s*\d+\s*--?"
    r"(?:[A-Za-z ,&]+?[•·]?\s*\d{1,3})?",   # optional trailing running header
)
PAGE_MARK = re.compile(r"\s*\d{0,3}\s*--PAGE\s*\d+\s*--?")
# Running footer without --PAGE marker: "…304 • Understanding Astrology 3" /
# "…The Houses of Astrology 305" — running header/footer glued to content.
RUNNING_FOOTER = re.compile(
    r"\s*\d{0,3}\s*[•·]?\s*(?:Understanding Astrology|The Houses of Astrology)"
    r"(?:\s*[•·]\s*\d{0,3}|\s+\d{1,3})?\s*"
)
# Truncated footer at a page boundary: trailing "… 3" / "… -" / "… 30" fragment
TRAILING_FRAGMENT = re.compile(r"\s+\d{1,3}\s*$|\s+-\s*$")
STRAY_BULLET = re.compile(r"\s*[•·]\s*")
MULTISPACE = re.compile(r"  +")
SPACE_BEFORE_DOT = re.compile(r"\s+([.,;!?])")
DASH_PAGE_MARK = re.compile(r"\s*-?-PAGE\s*\d+\s*-?-?")   # "--PAGE 323 ---"


def clean(text):
    t = text
    # TWELFTH/PLUTO has a whole extra book chapter pasted after its real
    # reading ("--PAGE 334 --I n this chapter you will learn…") — keep only
    # the part up to the first page marker.
    m = PAGE_MARK.search(t)
    if m and len(t) > 700:
        t = t[:m.start()]
    t = FOOTER_RE.sub(" ", t)
    t = PAGE_MARK.sub(" ", t)
    while "--PAGE" in t:
        t = DASH_PAGE_MARK.sub(" ", t) or t.replace("--PAGE", "")
    for _ in range(4):                       # footer can repeat across pages
        new = (RUNNING_FOOTER.sub("", t))
        new = TRAILING_FRAGMENT.sub("", new) if not new.endswith((".", "!", "?")) else new
        if new == t:
            break
        t = new
    t = STRAY_BULLET.sub(" ", t)
    t = MULTISPACE.sub(" ", t)
    t = SPACE_BEFORE_DOT.sub(r"\1", t)
    return t.strip()


def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)

    changed = 0
    for house, planets in data.items():
        for planet, text in planets.items():
            new = clean(text)
            if new != text:
                data[house][planet] = new
                changed += 1

    # validation
    errors = []
    houses = list(data.keys())
    if len(houses) != 12:
        errors.append(f"expected 12 houses, got {len(houses)}")
    for house in houses:
        if len(data[house]) < 10:
            errors.append(f"{house}: only {len(data[house])} planets")
        for planet, text in data[house].items():
            if "--PAGE" in text or "•" in text:
                errors.append(f"{house}/{planet}: residue remains: {text[-60:]!r}")
            if not re.search(r"[.!\"\)]$", text):
                errors.append(f"{house}/{planet}: bad ending: {text[-50:]!r}")
            if len(text) < 80:
                errors.append(f"{house}/{planet}: suspiciously short")

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(" -", e)
        sys.exit(1)

    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)

    print(f"OK - cleaned {changed}/120 entries; 12 houses x 10 planets intact")


if __name__ == "__main__":
    main()
