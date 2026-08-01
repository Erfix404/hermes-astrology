#!/usr/bin/env python3
"""Example: full natal chart — Western + Vedic + BaZi for one person.

Usage:  python examples/natal_chart.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from astro_engine import calculate_full_profile

chart = calculate_full_profile({
    "date": "1995-04-15", "time": "14:30", "place": "Tehran",
    "lat": 35.6892, "lng": 51.3890, "tz": "Asia/Tehran",
    "time_known": True, "mode": "natal",
})

print(f"Engine backend: {chart['_meta']['engine_backend']}")
print(f"House system:   {chart['charts']['western']['system']}")

print("\n=== WESTERN ===")
for name, p in chart["charts"]["western"]["planets"].items():
    print(f"{name:<10} {p['sign']:<12} {p['deg_in_sign']:>6.2f}°  H{p['house']}")

print("\n=== VEDIC ===")
for name, p in chart["charts"]["vedic"]["planets"].items():
    print(f"{name:<10} {p['sign']:<12} {p['deg_in_sign']:>6.2f}°  H{p['house']}")

print("\n=== BAZI ===")
bazi = chart["charts"]["bazi"]
for pillar in bazi.get("pillars", []):
    print(pillar)

print("\nBig three:", chart["summary"]["big_three"])
