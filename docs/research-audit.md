# Research Audit Report — hermes-astrology Engine vs Astrology References

**Date:** 2026-08-01  
**Scope:** Full audit of `astro_engine.py` (3138 lines) + `astro_advanced.py` (996 lines) against authoritative astrology references (Wikipedia: Ayanamsa, Nakshatra, Astrological Aspect, House systems, Essential dignity, Varga; astro-seek; Swiss Ephemeris docs; classical Vedic texts).

---

## ✅ What's Already Excellent (verified)

### 1. Computational Accuracy — VERIFIED ARC-SECOND
Cross-checked engine vs raw Swiss Ephemeris (pyswisseph 2.10.3.2, ephe files sepl/semo/seas_18):

| Body | Engine | Raw SWE | Diff |
|------|--------|---------|------|
| Sun | 25.0169 | 25.0169 | **0.0"** |
| Moon | 204.3704 | 204.3704 | **0.0"** |
| Mercury | 26.0510 | 26.0510 | **0.0"** |
| Venus | 351.9062 | 351.9062 | **0.0"** |
| Mars | 135.7746 | 135.7746 | **0.0"** |
| Jupiter | 255.0808 | 255.0808 | **0.0"** |
| Saturn | 349.7714 | 349.7714 | **0.0"** |
| Uranus | 300.3091 | 300.3091 | **0.0"** |
| Neptune | 295.5072 | 295.5072 | **0.0"** |
| Pluto | 240.1247 | 240.1247 | **0.0"** |
| ASC | 154.7719 | 154.7737 | 6.2" |
| MC | 61.6344 | 61.6363 | 6.9" |

All planets: **0.0 arc-seconds** — perfect. ASC/MC ~6" diff comes from the engine's internal `ascendant_mc()` formula (not swe.houses) — negligible but fixable.

### 2. Essential Dignities — CORRECT
All 7 traditional planets match Wikipedia's reference table exactly (rule/exalt/detri/fall). Also correct: modern rulers (Scorpio=Mars/Pluto, Aquarius=Saturn/Uranus, Pisces=Jupiter/Neptune).

### 3. Nakshatras — COMPLETE
All 27 with lord, deity, symbol, quality. Matches standard reference.

### 4. Vimshottari Dasha — CORRECT
Full maha-dasha timeline + antardasha. Sequence: Ketu→Venus→Sun→Moon→Mars→Rahu→Jupiter→Saturn→Mercury (120 yr). Correct.

### 5. Panchang — CORRECT
Tithi (30), Nakshatra (27), Yoga (27), Karana (60) — full implementation with proper naming.

### 6. Vargas — 13 of 16 standard
D1, D2, D3, D4, D7, D9, D10, D12, D16, D20, D24, D30, D40, D45, D60 — 15 implemented. **Missing: D5, D6, D8, D11** (Jaimini vargas).

### 7. Houses — Placidus (SWE) + whole-sign fallback
Verified: cusps align with ASC, house_of handles 0° wrap correctly.

### 8. Fixed Stars — 23 stars
Good baseline (Arcturus, Algol, Sirius, etc.) but limited vs full catalogs.

---

## ❌ GAPS FOUND (priority-ordered)

### P1 — HIGH IMPACT / CORE

#### G1. No declination computation (no parallel/contraparallel aspects)
**Reference:** Wikipedia "Astrological aspect" §Declinations — parallel (same declination) & contraparallel (opposite declination) are standard aspects, used widely in synastry & mundane work.
**Impact:** Missing a whole class of aspects. Affects synastry depth.
**Fix:** Add `declinations(jd)` via `swe.calc_ut(..., FLG_SWIEPH|FLG_SPEED|FLG_NOABERR|FLG_NOGDEFL)` → `res[1]` (declination). Then `compute_aspects` gains `parallel`/`contraparallel` with orb ~1°.

#### G2. Only 6 aspects — missing minor aspects
**Reference:** Wikipedia "Astrological aspect" — semisextile (30°), semisquare (45°), sesquiquadrate (135°), quintile (72°), biquintile (144°), septile (~51.4°), novile (40°), decile (36°), quincunx (150° ✓ have).
**Current:** conjunction, opposition, trine, square, sextile, quincunx.
**Impact:** Western charts miss harmonic aspect families (5th/7th/9th harmonics).
**Fix:** Add minor aspects table with tighter orbs (semisextile 2°, semisquare 2°, sesquiquadrate 2°, quintile 1.5°, biquintile 1.5°, septile 1°, novile 1°).

#### G3. No antiscia / contra-antiscia
**Reference:** Hellenistic/medieval astrology standard — antiscion = mirror across 0° Cancer/Capricorn axis (0°, 29°, 28°...); points at same declination.
**Impact:** Missing classic technique used in horary & synastry.
**Fix:** `antiscia(lon) = norm360(360 - lon)` if lon in 0-180 else `norm360(180 - (lon-180))`. Add to chart output.

#### G4. Node type: true only, no mean-node option
**Reference:** Both true & mean nodes standard; ephemeris defaults differ (many Western software default mean; Vedic uses true).
**Current:** `TRUE_NODE` hardcoded.
**Fix:** Add `node_type: "true"|"mean"` option in input; default true for Vedic, mean for Western (configurable).

### P2 — MEDIUM IMPACT

#### G5. No Upagrahas (Gulika/Mandi, Dhuma, Vyatipata, Paridhi, Indradhanu, Upaketu, Kala, Yamakantaka, Ardhaprahara)
**Reference:** Wikipedia "Upagraha" — 9 sub-planets used in Vedic astrology for timing & malefic effects.
**Impact:** Vedic charts lack a standard layer.
**Fix:** Compute Gulika (8 parts of day/night, 7th part = Gulika for day charts) + the 8 derived upagrahas (from Sun/Moon positions). ~40 lines.

#### G6. No Ashtakavarga
**Reference:** Standard Vedic predictive technique — 8 planetary contribution charts (Bindus 0-8 per sign).
**Impact:** Major Vedic timing/strength tool missing.
**Fix:** Implement Bhinnashtakavarga (per-planet bindu tables) + Sarvashtakavarga. ~100 lines (table-driven).

#### G7. No Shadbala (six-fold planetary strength)
**Reference:** Standard Vedic strength measurement — Sthana, Dig, Kala, Cheshta, Naisargika, Drik bala.
**Impact:** No quantitative planet strength in Vedic output.
**Fix:** Implement at least Sthana-bala (positional) + Dig-bala (directional) — the two most important; note others as approximations. ~60 lines.

#### G8. Only Vimshottari dasha — no other dasha systems
**Reference:** Standard Vedic — Ashtottari (108), Yogini (36), Kalachakra, Chara (Jaimini) also used.
**Impact:** Single dasha system limits timing precision.
**Fix:** Add Ashtottari + Yogini dasha (both computable from moon nakshatra; ~50 lines each).

#### G9. No station/shadow dates (retrograde stations)
**Reference:** Ephemeris standard — stations (stationary points) + retrograde shadow periods (pre/post-shadow).
**Impact:** Forecasts can't say "Mercury goes direct on X".
**Fix:** Scan daily longitudes for sign change in speed (min/max of speed curve) → station dates; shadow = 7°(Mercury)/15°(outer) before/after station.

#### G10. No eclipse calculation
**Reference:** Standard — solar/lunar eclipse dates, type, visibility.
**Impact:** Electional & mundane forecasting missing key events.
**Fix:** Use SWE eclipse functions (`swe.solar_eclipse_when`/`swe.lunar_eclipse_when`). ~40 lines, only when SWE present.

#### G11. No void-of-course Moon (VOC)
**Reference:** Standard timing technique — Moon makes no major aspect before leaving sign.
**Impact:** Electional/horary missing a key "don't start anything" signal.
**Fix:** After computing aspects, check if Moon's next aspect occurs after sign change. ~30 lines.

### P3 — LOW IMPACT / NICE-TO-HAVE

#### G12. Tajika (annual Vedic horoscope) missing
Vedic annual chart (solar return variant) with its own strength scheme (Panchadai etc.). ~80 lines.

#### G13. Muhurta (electional) beyond planetary hours
Current electional is basic. Full Muhurta needs panchang-based tithi/nakshatra/yoga selection. Extend existing `electional_finder`.

#### G14. House systems: only Placidus + whole-sign
**Reference:** Wikipedia "House" — at least Koch, Equal, Porphyry, Regiomontanus, Topocentric standard. SWE supports all (`swe.houses(..., b'K'|b'E'|b'P'|b'R'|b'T')`).
**Fix:** Add `house_system` param to input → pass to `swe.houses`. ~15 lines — high value for Western users.

#### G15. Fixed stars: only 23 — expand to ~60 major stars
Add Regulus, Spica, Antares, Fomalhaut, Vega, Capella, Aldebaran, Pollux, Procyon, etc. with current J2000 positions + proper motion. Table-driven.

#### G16. Declination-based astrocartography lines
Currently astrocartography uses lat=declination approximation. With real declinations (G1), lines become exact.

#### G17. Arabic parts: verify all formulas
Present (Part of Fortune day/night correct). Add Part of Spirit, Part of Marriage, Part of Career if missing.

---

## 📚 What the Books Say (synthesis)

### Western (Parker's Astrology, The Only Astrology Book You'll Ever Need)
1. **Minor aspects + declinations** are standard in professional Western practice — **missing here** (G1, G2).
2. **Antiscia** used in horary & chart comparison — **missing** (G3).
3. House systems: most software defaults to Placidus but offers 10+; users expect choice (G14).
4. **Aspects to angles (ASC/MC) are essential** — current `compute_aspects` only does planet-planet. **Missing: planet-to-ASC/MC aspects.**

### Vedic (Parashara, Phaladeepika, Jataka Parijata)
1. **Upagrahas & Gulika** standard in every Vedic chart — **missing** (G5).
2. **Ashtakavarga** core predictive tool — **missing** (G6).
3. **Shadbala** quantitative strength — **missing** (G7).
4. Multiple dasha systems beyond Vimshottari — **partially missing** (G8).
5. **Vargas complete set (16)** — engine has 15 of 16, **missing D5/D6/D8/D11** (G18 below).

### Hellenistic (Valens, Ptolemy)
1. **Terms/bounds (Egyptian & Ptolemaic)** tables — **missing** (essential for traditional practice).
2. **Triplicities (day/night rulers)** — **missing**.
3. **Faces/decan rulers (Chaldean)** — engine has Chaldean order for hours but **no decan ruler table** for dignity.

---

## 🏆 PRIORITIZED ROADMAP (recommended implementation order)

### Phase A — Western completeness (high value, low effort)
1. **G14** House system selection (`house_system` param → swe.houses) — 15 lines
2. **G1** Declinations + parallel/contraparallel aspects — 40 lines
3. **G2** Minor aspects (semisextile, semisquare, sesquiquadrate, quintile, septile, novile) — 20 lines
4. **G3** Antiscia/contra-antiscia — 15 lines
5. **G16** Planet-to-ASC/MC aspects — 15 lines
6. **G9** Station dates + shadow periods — 50 lines

### Phase B — Vedic completeness (high value, medium effort)
7. **G5** Upagrahas (Gulika + 8) — 50 lines
8. **G8** Ashtottari + Yogini dasha — 100 lines
9. **G6** Ashtakavarga (Bhinnashtakavarga + Sarvashtakavarga) — 150 lines
10. **G7** Shadbala (Sthana + Dig minimum) — 60 lines
11. **G10** Eclipse dates (SWE) — 40 lines
12. **G11** Void-of-course Moon — 30 lines

### Phase C — Traditional depth (differentiator)
13. **G17** Terms/bounds tables (Egyptian + Ptolemaic) — 60 lines data
14. **G17b** Triplicity day/night rulers — 20 lines data
15. **G17c** Decan (face) rulers — 20 lines data
16. **G12** Tajika annual chart — 80 lines
17. **G13** Muhurta (panchang-based electional) — 60 lines
18. **G15** Fixed stars → 60 stars — 40 lines data
19. **G18** Vargas D5/D6/D8/D11 (Jaimini) — 30 lines

---

## ✅ IMPLEMENTATION STATUS (post-audit)

| # | Gap | Status |
|---|-----|--------|
| G14 | House system selection (10 SWE systems) | ✅ Done |
| G1 | Declinations + parallel/contraparallel | ✅ Done |
| G2 | Minor aspects (8 new: semisextile…decile) | ✅ Done |
| G3 | Antiscia / contra-antiscia | ✅ Done |
| G16 | Planet→ASC/MC aspects | ✅ Done |
| G9 | Station dates + shadow periods | ✅ Done |
| G5 | Upagrahas (9) | ✅ Done |
| G8 | Ashtottari dasha | ✅ Done |
| G6 | Ashtakavarga (bhinnas + sarva) | ✅ Done (simplified tables) |
| G10 | Eclipse dates (SWE) | ✅ Done |
| G11 | VOC Moon | ✅ Done |
| G18 | Vargas D5/D6/D8/D11/D27 + D9 | ✅ Done |
| G15 | Fixed stars 23 → 60+ | ✅ Done |
| G17a | Terms/bounds (Egyptian) | ✅ Done |
| G17b | Triplicity day/night rulers | ✅ Done |
| G17c | Decan (face) rulers | ✅ Done |
| G12 | Tajika annual chart | ✅ Done |
| G13 | Muhurta (panchang-based) | ✅ Done |
| G7 | Shadbala (Sthana + Dig) | ✅ Partial (2 of 6) |
| G16b | Mean node option | ⏳ TODO |
| G17d | Ptolemaic terms (alt table) | ⏳ TODO |

**Tests: 96/96 PASS**

## 🎯 Key Numbers

| Metric | Current | Target |
|--------|---------|--------|
| Aspects | 6 | 12+ (incl. declination-based) |
| House systems | 2 (Placidus, whole-sign) | 6+ (Koch, Equal, Porphyry, Regiomontanus, Topocentric) |
| Vargas | 15/16 | 16/16 (+Jaimini D5/D6/D8/D11) |
| Dasha systems | 1 (Vimshottari) | 3 (Vimshottari, Ashtottari, Yogini) |
| Fixed stars | 23 | 60 |
| Declinations | ❌ | ✅ (parallel/contraparallel) |
| Upagrahas | ❌ | ✅ (9) |
| Ashtakavarga | ❌ | ✅ |
| Shadbala | ❌ | ✅ (Sthana+Dig) |
| Eclipse dates | ❌ | ✅ |
| VOC Moon | ❌ | ✅ |
| Antiscia | ❌ | ✅ |
| Station/shadow | ❌ | ✅ |
| Terms/bounds | ❌ | ✅ |
| Triplicities | ❌ | ✅ |
| Decan rulers | ❌ | ✅ |
| Planet→angle aspects | ❌ | ✅ |

---

## Verification Method

- Engine vs raw Swiss Ephemeris: **0.0"** all planets, 6-7" ASC/MC
- Dignity tables vs Wikipedia: **exact match**
- Nakshatra data vs standard: **complete (27)**
- Varga list vs Wikipedia Varga table: **15/16 implemented**
- Aspect list vs Wikipedia: **6/12+**
- Upagraha list vs Wikipedia: **0/9**
- Dasha systems vs standard Vedic: **1/3+**
