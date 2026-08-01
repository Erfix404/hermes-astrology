#!/usr/bin/env python3
"""Example: compatibility score + synastry between two people.

Usage:  python examples/compatibility.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from astro_engine import calculate_full_profile

alice = {"date": "1995-04-15", "time": "14:30", "place": "Tehran",
         "lat": 35.6892, "lng": 51.3890, "tz": "Asia/Tehran", "time_known": True}
bob = {"date": "1992-11-03", "time": "09:15", "place": "Berlin",
       "lat": 52.52, "lng": 13.405, "tz": "Europe/Berlin", "time_known": True}

result = calculate_full_profile({
    **alice, "mode": "compatibility", "partner": bob,
})

score = result.get("compatibility", result)
print("Compatibility:", score.get("overall_score"), "/ 100")
for k, v in score.items():
    if isinstance(v, (int, float)) and k not in ("overall_score",):
        print(f"  {k}: {v}")
