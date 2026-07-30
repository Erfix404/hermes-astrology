#!/usr/bin/env python3
"""Daily astrology data fetcher - outputs current planetary positions and key transits."""
import json, subprocess, sys, os
from datetime import datetime

ENGINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "astro_engine.py")

def run_engine(json_input):
    """Run the astrology engine and return parsed JSON."""
    result = subprocess.run(
        ["python3", ENGINE, "--json", json.dumps(json_input)],
        capture_output=True, text=True, timeout=30
    )
    return json.loads(result.stdout)

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
    now = datetime.utcnow()
    
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
            "time_utc": now.strftime("%H:%M UTC"),
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
