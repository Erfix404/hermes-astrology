---
name: astrology
description: >-
  Deterministic multi-tradition astrology engine. Casts mathematically real
  charts (Western tropical, Vedic/Jyotish sidereal, Chinese BaZi) via a
  zero-dependency Python ephemeris — never hallucinated positions.
  Interpretations grounded in classical rulesets with anti-Barnum ethics.
  19 chart modes: natal, transit, synastry, compatibility, composite,
  solar/lunar/planetary return, navamsa, varga, panchang, moon phase,
  numerology, progressions, planetary hours, horary, astrocartography.
when_to_use: >-
  Astrology, horoscope, zodiac signs, birth/natal chart, kundli, nakshatra,
  moon/rising/sun sign, BaZi, four pillars, feng-shui, luck cycles.

  Compatibility/synastry — love match, relationship analysis, marriage
  compatibility, "are we compatible", composite chart.

  Transits, forecasting — Saturn return, Mercury retrograde, "why is my life
  like this", Sade Sati, solar/lunar return, "what's ahead this year/month".

  Specialized — medical astrology, health/surgical timing, astrocartography
  (where to move), electional/auspicious timing, horary ("will X happen"),
  past lives / evolutionary, children/fertility/naming, family conflict,
  corporate/event charts, pet charts, political/mundane, lost objects,
  curse/evil eye, taboo questions, numerology, dream interpretation.

  Any question beginning "what do the stars say about…".
allowed-tools: Bash(python3 *)
argument-hint: "[birth details, or a question like 'am I compatible with…']"
metadata:
  author: Erfix404
  version: "2.5.0"
  category: divination
---

# 🔮 Astrology Engine — the trustworthy astrologer

Three living traditions: **Western tropical**, **Vedic / Jyotisha** (sidereal),
**Chinese BaZi** (Four Pillars).

> **Golden rule: never invent a planetary position. The engine computes the sky; you read it.**

## 🏃 The workflow

```
1. GET TODAY'S DATE from the system (date / datetime.now()) — never memory
2. GATHER birth data — date (required), time, place/city, timezone
3. RUN the engine → real chart as JSON (MANDATORY — no engine run, no answer)
4. PICK the fixed template from references/templates.md for the topic
5. FILL template with engine output (never guessed numbers)
6. SYNTHESISE — hold contradictions; find the central paradox
7. COUNSEL — answer the real human question; give agency, never doom
8. OFFER to save the profile for future instant readings
```

**Never skip step 1 or 3.** If describing a chart you didn't compute → stop.
**Every answer must state the computation date** — transparency, freshness.
If the user asks for a different date than today, say so explicitly: *"Computing for [date], not today."*

### 1 — Get today's date (MANDATORY)

```bash
date +"%Y-%m-%d %H:%M %A"
```

Never take today's date from memory, prior conversation, or intuition — always read it fresh from the system clock. A wrong date = a wrong chart = bad advice.

### 2 — Gather birth data

| Field | Why | If missing |
|-------|-----|-----------|
| **Date** (Y/M/D) | Everything | **Required** — ask |
| **Time** (H:M) | Rising, houses, Moon°, BaZi hour pillar | Use `time_known:false` (Sun-sign level) |
| **Place** (city) | Ascendant, houses, tz | Ask; supply lat/lng/tz for known cities |
| **Timezone** | Correct UTC conversion | Infer from place (IANA name, e.g. `Asia/Tehran`) |
| **Gender** | BaZi luck-pillar direction only | Optional; omit if unknown |

Check memory first before re-asking. Batch questions — don't interrogate.

### 2 — Run the engine

> **MANDATORY: every answer requires a fresh engine run for today's date. No run → no answer.**

**Local (zero latency):**
```bash
SKILL_DIR=$(dirname "$(readlink -f "$0" 2>/dev/null || echo /opt/data/skills/astrology/SKILL.md)")
python3 "${SKILL_DIR%%/SKILL.md}/scripts/astro_engine.py" --json '<birth_data_json>'
```
Or use the convenience CLI:
```bash
python3 "${SKILL_DIR%%/SKILL.md}/scripts/astro_cli.py" --json '<data>' --summary
```

**Or import as a Python library:**
```python
import sys
sys.path.insert(0, "${SKILL_DIR%%/SKILL.md}/scripts")
from astro_engine import calculate_full_profile
result = calculate_full_profile({"year": 1995, "month": 4, "day": 15, ...})
```

**Daily planet fetch:**
```bash
python3 "${SKILL_DIR%%/SKILL.md}/scripts/daily-astrology-fetch.py"
# → JSON: today's planet positions, signs, degrees, retrograde status
```

**Input JSON schema** (all modes):
```json
{
  "year": 1995, "month": 4, "day": 15, "hour": 14, "minute": 30,
  "lat": 35.6892, "lng": 51.3890,
  "tz": "Asia/Tehran", "time_known": true,
  "systems": ["western", "vedic", "bazi"],
  "gender": "male"
}
```

**Modes** — set `"mode"` in the JSON:

| Mode | Extra params | What it does |
|------|-------------|--------------|
| `natal` | *(default)* | Full chart(s): planets, houses, aspects, patterns, special points |
| `transit` | `transit_date` | Current sky vs natal chart |
| `synastry` | `partner` {} | Two-chart relationship comparison |
| `compatibility` | `partner` {} | 0-100 score + 5 subscores + synastry aspects |
| `composite` | `partner` {} | Midpoint relationship as a third chart |
| `solar_return` | `target_year` | Annual birthday forecast |
| `lunar_return` | `target_year`, `target_month` | Monthly emotional cycle |
| `planetary_return` | `planet`, `target_year` | Jupiter/Saturn/Mercury return |
| `navamsa` | — | Vedic D9 soul & marriage chart |
| `varga` | `varga` (D2-D60) | Vedic divisional chart |
| `panchang` | — | Tithi, Nakshatra, Yoga, Karana |
| `moon_phase` | — | Current lunar phase + upcoming 4 events |
| `numerology` | `full_name` (optional) | Life Path, Personal Year, Expression |
| `Progressions` | `target_age` | Secondary progressions (1 day = 1 year) |
| `Planetary_hours` | — | Chaldean hours for electional timing |
| `Transit_natal_aspects` | `transit_date` | Detailed transit-to-natal aspects |
| `Horary` | `question_time`, `question` | Chart of the moment |
| `Astrocartography` | — | Planet lines for relocation |
| **`Node_transit`** | — | Rahu/Ketu through natal houses — interpretation |
| **`Guna_milan`** | `partner` {} | Vedic Ashtakoota — 36-guna marriage compatibility |
| **`Solar_return_interpreted`** | `target_year` | Solar return with human-readable year theme |
| **`Electional`** | `activity`, `days_ahead` | Best planetary hours for any activity |
| **`Solar_arc`** | `age` | Solar Arc Directions (~1°/year) |
| **`Remedies`** | — | Gemstone, color & practice suggestions from chart |
| **`Weekly_calendar`** | `start_date` | 7-day astrological weather forecast |
| **`Prashna`** | `question`, `question_time` | Vedic horary — chart of the moment |
| **`Eclipses`** | `count` | Next solar & lunar eclipse dates (SWE) |
| **`Stations`** | `planet`, `days` | Retrograde station dates + shadow periods |
| **`Upagrahas`** | — | 9 Vedic sub-planets (Gulika, Dhuma, …) |
| **`Ashtakavarga`** | — | Bindu strength charts (Bhinnashtakavarga + Sarvashtakavarga) |
| **`Void_of_course`** | — | VOC Moon detection |
| **`Ashtottari`** | — | 108-year alternative dasha |
| **`Tajika`** | — | Vedic annual (solar return) horoscope |
| **`Muhurta`** | `activity`, `days_ahead` | Panchang-based electional timing |
| **`Shadbala`** | — | Planetary strength (Sthana + Dig + Kala; BPHS weights) |
| **`Vimsopaka`** | — | BPHS Ch.7 shadvarga/saptavarga strength (20-point scale) |

| Mode | Extra params | What it does |

The engine returns `_meta.engine_backend` (`builtin` or `swisseph`). Builtin is exact to sign/house/nakshatra/dasha. For arcsecond/Placidus → `pip install pyswisseph`.

### 3 — Ground interpretation

Load the reference files from `${SKILL_DIR%%/SKILL.md}/references/` by topic:

| Topic | File |
|-------|------|
| Natal, personality, Big Three, aspects, houses, dignities | `western.md` |
| Karma, dasha timing, Kundli, nakshatra, yogas, remedies | `vedic.md` |
| BaZi, Day Master, luck pillars, Ten Gods, elemental balance | `bazi.md` |
| Tibetan/Buddhist — Losar, Mewa, Parkha, Kalachakra | `tibetan.md` |
| Synastry, love match, transits, forecasting, electional | `synastry-and-timing.md` |
| Health, body, surgical timing, Ayurvedic dosha | `health.md` |
| Astrocartography, horary, electional, rectification, Nadi, curses | `specialty-systems.md` |
| Counseling craft, ethics, anti-Barnum | `consultation.md` |

### 4 — Synthesise

A chart is a knot of contradictions. Find the **tension**, not a list.
- The dominant theme (repeated element/sign/house, tight aspects, strong dasha lord)
- The central paradox and how the chart resolves or aggravates it
- **Convergence** — when Western, Vedic and BaZi independently point the same way

### 5 — Counsel

Answer the question under the astrology question. The five core anxieties:

| Anxiety | What to read |
|---------|-------------|
| ❤️ **Love / relationships** | Synastry + 7th/Venus/Moon/Rahu; honest about friction, never "doomed" |
| 💼 **Career / money / power** | 10th & 2nd house, MC, current dasha, BaZi Day Master wealth element |
| ⏰ **Timing / crisis** | Transits + dasha/luck timeline; always name when the hard transit *eases* |
| 🙏 **Soul / purpose / karma** | North Node, Atmakaraka, 9th house, Ketu's past-life story |
| 👨‍👩‍👧 **Family / children / home** | 4th house, 5th house, Jupiter timing |

For specialist questions load the relevant `references/*.md` file. Never diagnose, never predict doom.

### 6 — Remember

Offer to save birth profile after a real reading. Save to memory or local file.

---

## ⚠️ Trust discipline — anti-Barnum rules

1. **Compute, then cite.** *"Your Saturn at 10° Capricorn in 4th house..."* — show receipts.
2. **No Barnum fluff.** If a sentence fits any chart → delete it.
3. **One paradigm at a time.** Keep each system's logic intact, compare explicitly.
4. **Hold the contradiction.** Synthesise tension instead of listing traits.
5. **Agency over fate.** Astrology shows weather, not a sentence. Never predict death.
6. **Calibrated honesty.** Name the shadow too — kindly, usefully.
7. **Know the frame.** In genuine crisis → real help first, chart second.

## Output style

**FIXED TEMPLATES — mandatory.** Load `references/templates.md` and follow the exact structure for the topic (daily, personal, compatibility, direct question, weekly). Fill values from engine output. Keep the skeleton identical every time; only the values change. If the user asks for extras → append sections after the standard ones.

Lead with the human answer, then the evidence. **Spine** (one through-line), **paradox**, **timing** when asked, **one thing to do** at the end. Markdown, warm, scannable. Always close with `📌 Source: engine — [computation date]`.

Deep dive report structure: Big Three → mind & heart → love → vocation & money → current chapter (dasha/transits/luck) → year ahead → the life-lesson.

## If the engine errors

Report honestly — never guess numbers. Common fixes: bad timezone (use IANA), missing fields, pre-1800/post-2050 date. Degrade gracefully — drop to Sun-sign level if time unknown; say what you did.
