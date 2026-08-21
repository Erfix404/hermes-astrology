#!/usr/bin/env python3
"""Daily astrology data fetcher - outputs current planetary positions and key transits."""
import json, subprocess, sys, os
from datetime import datetime, timezone, timedelta

ENGINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "astro_engine.py")

def run_engine(json_input):
    """Run the astrology engine and return parsed JSON."""
    # Prefer the venv python with swisseph for arcsecond precision
    candidates = [
        "/opt/data/.venv/bin/python",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".venv", "bin", "python"),
        "python3",
    ]
    for py in candidates:
        if py != "python3" and not os.path.exists(py):
            continue
        try:
            result = subprocess.run(
                [py, ENGINE, "--json", json.dumps(json_input)],
                capture_output=True, text=True, timeout=30
            )
            data = json.loads(result.stdout)
            # verify swisseph backend actually engaged
            meta = data.get("_meta", {})
            if meta.get("engine_backend") == "swisseph":
                return data
            if py == "python3":
                return data  # last resort, accept whatever backend
        except Exception:
            continue
    return {"error": "engine failed"}

def get_current_planets(collected, key, data):
    """Extract planet info from chart data."""
    planets = {}
    charts = data.get("charts", {})
    for sys_name, chart in charts.items():
        for pname, pdata in chart.get("planets", {}).items():
            if pname not in planets:
                deg = pdata.get("degree") or pdata.get("degrees") or pdata.get("deg_in_sign")
                planets[pname] = {
                    "sign": pdata.get("sign"),
                    "degree": round(deg, 1) if deg is not None else None,
                    "house": pdata.get("house"),
                    "retrograde": pdata.get("retrograde", False),
                }
    return planets

def main():
    # Tehran-local "now" (UTC+3:30, no DST since 2022) — the engine expects
    # local wall-clock time at the chart location, not UTC.
    now = datetime.now(timezone(timedelta(hours=3, minutes=30)))

    # Current transit chart for Tehran (or UTC)
    transit_input = {
        "mode": "natal",  # Just get planets for today's date
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "hour": now.hour,
        "minute": now.minute,
        "lat": 35.6892,
        "lng": 51.3890,
        "tz": "Asia/Tehran",
        "time_known": True,
        "systems": ["western"]
    }

    try:
        data = run_engine(transit_input)
        planets = get_current_planets(None, "today", data)

        result = {
            "date": now.strftime("%Y-%m-%d"),
            "time_tehran": now.strftime("%H:%M Tehran"),
            "planets": planets,
            "sunrise": data.get("time_info", {}).get("sunrise"),
            "sunset": data.get("time_info", {}).get("sunset"),
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e), "date": now.strftime("%Y-%m-%d")}))
        sys.exit(1)

if __name__ == "__main__":
    main()
