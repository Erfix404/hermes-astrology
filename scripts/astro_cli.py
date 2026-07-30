#!/usr/bin/env python3
"""CLI entry point for hermes-astrology."""
import argparse, json, sys, os

# Add scripts dir to path for importing astro_engine
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from astro_engine import calculate_full_profile, _demo


def _load_data(args):
    if args.json:
        return json.loads(args.json)
    if args.file:
        with open(args.file) as f:
            return json.load(f)
    return _demo()


def _format_output(data, fmt):
    if fmt == "json":
        return json.dumps(data, indent=2, default=str)
    return json.dumps(data, indent=2, default=str)


def main():
    ap = argparse.ArgumentParser(
        description="hermes-astrology — deterministic multi-tradition chart engine",
        epilog="Modes: natal, transit, synastry, compatibility, composite, "
               "solar_return, lunar_return, planetary_return, navamsa, varga, "
               "panchang, moon_phase, numerology, progressions, planetary_hours, "
               "transit_natal_aspects, horary, astrocartography",
    )
    ap.add_argument("--json", help="birth data as JSON string")
    ap.add_argument("--file", help="path to birth data JSON file")
    ap.add_argument("--mode", "-m", default="natal",
                    help="chart mode (default: natal)")
    ap.add_argument("--systems", "-s", nargs="*",
                    default=["western", "vedic", "bazi"],
                    help="systems: western vedic bazi")
    ap.add_argument("--summary", action="store_true",
                    help="short summary instead of full JSON")
    ap.add_argument("--date", help="transit date YYYY-MM-DD")
    ap.add_argument("--partner", type=str,
                    help="partner birth data JSON (for synastry/compatibility)")
    a = ap.parse_args()

    data = _load_data(a)
    if a.mode:
        data["mode"] = a.mode
    if a.systems:
        data["systems"] = a.systems
    if a.date:
        data["transit_date"] = a.date
    if a.partner:
        data["partner"] = json.loads(a.partner)

    result = calculate_full_profile(data)

    if a.summary:
        _print_summary(result, data)
    else:
        print(json.dumps(result, indent=2, default=str))


def _print_summary(result, data):
    charts = result.get("charts", {})
    for sys_name in data.get("systems", ["western"]):
        ch = charts.get(sys_name)
        if not ch:
            continue
        print(f"\n=== {sys_name.upper()} ===")
        asc = ch.get("ascendant") or ch.get("lagna") or {}
        print(f"  Rising: {asc.get('sign', '?')} "
              f"{asc.get('deg_in_sign', 0):.1f}°")
        planets = ch.get("planets", {})
        if not isinstance(planets, dict):
            planets = {p.get("name", f"#{i}"): p for i, p in enumerate(planets)}
        for name, p in planets.items():
            if isinstance(p, dict):
                ret = " ℞" if p.get("retrograde") else ""
                house = p.get("house", p.get("bhava", ""))
                print(f"  {name:12s} {p.get('sign', '?'):10s} "
                      f"{p.get('degrees', p.get('deg_in_sign', 0)):.1f}°"
                      f"  H{house}{ret}")
    sd = result.get("summary", {})
    if sd:
        print(f"\n  Summary: {sd.get('text', '')}")


if __name__ == "__main__":
    main()
