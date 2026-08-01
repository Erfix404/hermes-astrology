# 🔮 Hermes Astrology

**Deterministic multi-tradition astrology engine** — Western tropical, Vedic/Jyotisha sidereal, Chinese BaZi (Four Pillars). Zero‑dependency pure‑Python ephemeris. 19 modes. CLI + API + MCP.

| Tradition | System | Basis |
|-----------|--------|-------|
| ♈ Western | Tropical (seasons) | Psychological, archetypal, personality‑focused |
| ☪ Vedic / Jyotisha | Sidereal (Lahiri ~24°) | Karma, dasha timing, life events, nakshatras |
| 木 Chinese BaZi | Four Pillars (solar terms) | Elemental balance, luck cycles, Ten Gods |

## ✨ Features

- **Zero‑dependency** — pure Python geocentric ephemeris (Schlyter + perturbations). Only `math` / `datetime` / `json`. Works out‑of‑the‑box.
- **14‑function CLI** — `astro --json`, `astro --file`, `astro --summary`
- **19 chart modes + 11 advanced** — natal, transit, synastry, compatibility, composite, solar/lunar/planetary return, navamsa, varga (D2–D60), panchang, moon phase, numerology, progressions, planetary hours, transit‑natal aspects, horary, astrocartography + eclipses, stations, upagrahas, ashtakavarga, VOC Moon, ashtottari, tajika, muhurta, shadbala
- **Auto‑enriched** — aspect patterns (Grand Trine, T‑Square, Yod, Kite, Grand Cross), Arabic Parts, fixed stars (60+), Black Moon Lilith, dignities (domicile/exalt + triplicity/term/decan), declination aspects, antiscia, Mangal Dosha, Kaalsarpa Dosha
- **Swiss Ephemeris upgrade** — `pip install pyswisseph` → arcsecond precision + Placidus/Koch/Equal/Regiomontanus houses. No code change.
- **8 reference rulesets** — grounded classical interpretation, no hallucinated Barnum fluff
- **FastAPI REST** (19 routes + pricing/auth/rate‑limiting) + **MCP server** (18 tools, Claude Desktop / Cursor / Devin)

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

### Daily astrology fetch

```bash
python scripts/daily-astrology-fetch.py
# → JSON with today's planet positions, signs, degrees, retrograde status
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
│   ├── astro_engine.py        # ~2960 lines, zero-dep ephemeris engine
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
│   └── test_engine.py         # 66 tests, stdlib unittest
├── SKILL.md                   # Agent integration skill
├── pyproject.toml
├── Dockerfile
└── LICENSE (MIT)
```

## 🧪 Tests

```bash
python -m unittest tests.test_engine -v
# → 66/66 pass
```

CI runs on Python 3.10–3.13 via GitHub Actions.

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
