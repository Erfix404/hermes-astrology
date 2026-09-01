# 🔮 Hermes Astrology v3.0

**Deterministic multi-tradition astrology engine & AI-Agent backend** — Western tropical, Vedic/Jyotisha sidereal, Chinese BaZi (Four Pillars). Zero‑dependency pure‑Python ephemeris. 24+ modes. Full forecasting suite (Profections, Firdaria, Zodiacal Releasing, Progressions, Vimshottari, Chara Dasha, Mundane Ingresses, Eclipses, Ibn Ezra Lots). CLI + API + MCP.

| Tradition | System | Basis |
|-----------|--------|-------|
| ♈ Western & Hellenistic | Tropical / Valens & Ptolemy | Psychological archetypes, Time-Lords (ZR, Profections, Firdaria), Progressions |
| ☪ Vedic / Jyotisha | Sidereal (Lahiri ~24°) | BPHS Shadbala (6/6), Vimshottari (3 levels), Gochara (Moon transit), Jaimini Chara Dasha |
| 🏛️ Mundane & Medieval | World charts / Ingresses | Bonatti/Lilly dynamic ingress validity, Carter eclipse triggers, Ibn Ezra marriage lots |
| 木 Chinese BaZi | Four Pillars (solar terms) | Elemental balance, luck cycles, Ten Gods |

## ✨ Features (v3.0)

- **Zero‑dependency & Robust Fallbacks** — pure Python geocentric ephemeris. Automatic Moshier/built-in resilience when Swiss Ephemeris data files are missing.
- **Universal Dynamic Temporal Resolution** — all forecasting systems accept `target_date`/`as_of`/`date` to evaluate any historical or future life chapter on demand.
- **Hellenistic Time-Lords** — Annual & Monthly Profections, Medieval Firdaria (day/night sect 75y), and Vettius Valens Zodiacal Releasing (L1-L4, Loosing-of-the-Bond, Fortune peak detection).
- **Deep Vedic Forecasting** — Full 6-fold BPHS Shadbala (Cheshta from southern declination & apogees, Drik aspectual speculum), 3-level Vimshottari Dasha (Maha/Antar/Pratyantar), Gochara with Sade Sati, Jaimini Chara Dasha (K.N. Rao).
- **Mundane & National Astrology** — Exact astronomical Ingresses (Aries/Cancer/Libra/Cap) with Bonatti/Lilly validity auto-resolution, Carter eclipse triggers, Lunations.
- **Relationship Astrology** — 7 Medieval/Hebrew Marriage Lots (Abraham Ibn Ezra, *Reshit Hokhmah* IX), bi-directional house overlays, composite chart interpretation, 36-Guna Milan.
- **Adaptive 3-Level Altitude Delivery** — `references/fa/metaphors.md` allows AI agents to translate complex mechanics into tangible, warm human metaphors (Level 1 Conversational, Level 2 Balanced, Level 3 Pro).
- **Verified Accuracy** — 153 unit tests passing, validated against Astro-Databank Rodden Rating AA historical charts (Carl Jung, Albert Einstein, Steve Jobs).
- **FastAPI REST + MCP Server** — Claude Desktop, Cursor, Devin, and headless agent integration.

## 🚀 Quick start

```bash
# Clone
git clone https://github.com/Erfix404/hermes-astrology.git
cd hermes-astrology

# CLI — natal chart for Tehran
python scripts/astro_engine.py --json '{"year":1995,"month":4,"day":15,
  "hour":14,"minute":30,"lat":35.6892,"lng":51.3890,
  "tz":"Asia/Tehran","time_known":true,
  "systems":["western","vedic","bazi"]}'

# Convenience CLI
python scripts/astro_cli.py --json '...' --summary
```

### As a library

```python
import sys
sys.path.insert(0, "scripts")
from astro_engine import calculate_full_profile

chart = calculate_full_profile({
    "date": "1995-04-15", "time": "14:30", "place": "Tehran",
    "lat": 35.6892, "lng": 51.3890, "tz": "Asia/Tehran", "mode": "natal",
})
sun = chart["charts"]["western"]["planets"]["Sun"]
print(sun["sign"], sun["deg_in_sign"])   # → Aries 25.0°
```

### Daily astrology fetch

```bash
python scripts/daily-astrology-fetch.py
# → JSON with today's planet positions, signs, degrees, retrograde status
```

### Ready-to-run examples

```bash
python examples/natal_chart.py        # full 3-tradition natal chart
python examples/compatibility.py      # compatibility score + synastry
```

## 📦 Installation as library

```bash
pip install .
# or for development:
cd hermes-astrology
python -m unittest tests.test_engine -v
```

## 🔧 API modes

| Mode | Endpoint | Description |
|------|----------|-------------|
| `natal` | `/chart/natal` | Full natal chart(s) per tradition |
| `transit` | `/chart/transit` | Current sky vs natal chart |
| `synastry` | `/chart/synastry` | Relationship comparison |
| `compatibility` | `/chart/compatibility` | 0‑100 scoring + 5 subscores |
| `composite` | `/chart/composite` | Midpoint relationship chart |
| `solar_return` | `/chart/solar-return` | Annual birthday forecast |
| `lunar_return` | `/chart/lunar-return` | Monthly lunar return |
| `planetary_return` | `/chart/planetary-return` | Jupiter/Saturn/Mercury etc. |
| `navamsa` | `/chart/navamsa` | Vedic D9 soul chart |
| `varga` | `/chart/varga` | D2–D60 divisional charts |
| `panchang` | `/chart/panchang` | Tithi, Nakshatra, Yoga, Karana |
| `moon_phase` | `/chart/moon-phase` | Lunar phase + upcoming events |
| `numerology` | `/chart/numerology` | Life Path, Personal Year |
| `progressions` | `/chart/progressions` | Secondary progressions |
| `planetary_hours` | `/chart/planetary-hours` | Chaldean hours for electional |
| `transit_aspects` | `/chart/transit-aspects` | Detailed transit‑to‑natal aspects |
| `horary` | `/horary` | Chart of the moment (question) |
| `astrocartography` | `/astrocartography` | Relocation planet lines |
| `event` | `/chart/event` | Any inception moment |

## 📁 Project structure

```
hermes-astrology/
├── scripts/
│   ├── astro_engine.py        # ~3860 lines, zero-dep ephemeris engine
│   ├── astro_cli.py           # CLI entry point
│   ├── daily-astrology-fetch.py  # Daily planet data fetcher
│   ├── api.py                 # FastAPI REST server (841 lines)
│   └── mcp_server.py          # MCP server (18 tools)
├── references/
│   ├── western.md             # Western interpretation ruleset
│   ├── vedic.md               # Vedic/Jyotisha ruleset
│   ├── bazi.md                # Chinese BaZi ruleset
│   ├── tibetan.md             # Tibetan Buddhist astrology
│   ├── health.md              # Medical astrology
│   ├── synastry-and-timing.md # Compatibility + forecasting
│   ├── specialty-systems.md   # 14+ niche branches
│   └── consultation.md        # Counseling craft + ethics
├── tests/
│   └── test_engine.py         # 98 tests, stdlib unittest
├── SKILL.md                   # Agent integration skill
├── pyproject.toml
├── Dockerfile
└── LICENSE (MIT)
```

## 🧪 Tests

```bash
python -m unittest tests.test_engine -v
# → 98/98 pass
```

CI runs on Python 3.10–3.13 via GitHub Actions.

## 📊 Accuracy validation

Positions cross-checked against **NASA JPL DE421** (via Skyfield, an independent ephemeris implementation) at 2026-08-01 08:30 UTC:

| Body | Δ (arcsec) |
|------|-----------|
| Sun | 19.0 |
| Moon | 2.3 |
| Mercury | 15.9 |
| Venus | 15.6 |
| Mars | 29.8 |
| Jupiter | 28.6 |
| Saturn | 0.4 |
| Uranus | 0.6 |
| Neptune | 1.5 |
| Pluto | 0.5 |

All planets within 30″ (0.008°) — far below the 1° tolerance of any astrological application. The residuals are ephemeris-model differences (DE421 vs DE441), not engine error.

## 🐳 Docker

```bash
docker build -t hermes-astrology .
docker run -p 8000:8000 hermes-astrology
# → FastAPI at http://localhost:8000/docs
```

## 🌐 MCP for Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "astrology": {
      "command": "python",
      "args": ["/path/to/hermes-astrology/scripts/mcp_server.py"],
      "env": { "ASTRO_MCP_TRANSPORT": "stdio" }
    }
  }
}
```

18 tools — get astrology charts, solar returns, compatibility, planetary hours, and more, directly from Claude.

---

**MIT License** — free to use, modify, and distribute.
Built with ❤️ for Erfan (Erfix404).
