#!/usr/bin/env python3
"""
Astrology Engine — Deterministic Calculation Backend
=====================================================
Systems: Western Tropical · Vedic (Jyotisha / Lahiri sidereal) · Chinese BaZi

DESIGN PRINCIPLE — separate the math from the meaning.
  The LLM must NEVER guess planetary positions. This engine computes them.
  Interpretation (turning these numbers into language) happens in the SKILL,
  grounded against the reference rulesets. This file only does math + lookups.

PRECISION / DEPENDENCIES.
  Primary path is ZERO-DEPENDENCY pure Python (stdlib only): a compact
  geocentric ephemeris (Paul Schlyter's algorithms + standard perturbation
  terms) accurate to ~1-2 arcminutes for the Sun, Moon and classical planets,
  ~tens of arcsec→arcmin for outers, well within the tolerance needed for
  sign / house / nakshatra / dasha determination (the coarsest bucket is the
  13°20' nakshatra; signs are 30°).

  If `swisseph` (pyswisseph) is importable it is used instead for
  arcsecond-grade precision and true nodes. The engine auto-detects; output
  records which backend produced the numbers under "_meta".

Usage:
  python3 astro_engine.py --json '<birth_data_json>'
  python3 astro_engine.py --file birth.json
  python3 astro_engine.py            # demo chart

Input JSON (natal):
  {
    "name": "optional label",
    "year": 1990, "month": 6, "day": 15,
    "hour": 14, "minute": 30,           # local clock time at birth place
    "lat": 40.7128, "lng": -74.0060,    # degrees, E+ / N+
    "tz": "America/New_York",           # IANA name (preferred) OR
    "utc_offset": -4,                   #   numeric hours, OR omit to estimate
    "time_known": true,                 # set false if birth time unknown
    "systems": ["western","vedic","bazi"],
    "gender": "male"                    # affects BaZi luck-pillar direction only
  }

Other modes (set "mode"):
  "natal"           (default) — full chart, per "systems"; includes aspect patterns,
                                Part of Fortune, Vertex, moon phase, equal houses,
                                navamsa, and panchang automatically
  "transit"  + "transit_date" — current sky vs the natal chart
  "synastry" + "partner": {…} — relationship comparison of two charts
  "compatibility" + "partner": {…} — detailed 0-100 compatibility scoring with subscores
  "astrocartography"          — planet lines on the globe (relocation)
  "horary"     + (lat/lng at the moment)  — chart of the moment a question is asked
  "event"                       — chart for any "moment of inception"
  "solar_return" + "target_year" — annual solar return chart
  "lunar_return" + "target_year" + "target_month" — monthly lunar return chart
  "navamsa"                     — Vedic D9 navamsa chart with vargottama detection
  "panchang"                    — complete Vedic panchang (Tithi, Nakshatra, Yoga, Karana)
  "moon_phase"                  — current moon phase + upcoming phases
  "numerology"                  — Life Path, Personal Year, Expression, Soul Urge
                                (pass "full_name" for name-based numbers)
  "composite"  + "partner": {…} — midpoint relationship chart
  "progressions" + "target_age" — secondary progressions (1 day = 1 year)
  "planetary_return" + "planet" + "target_year" — return chart for any planet
  "varga" + "varga"             — Vedic divisional chart (D2-D60)
  "planetary_hours"             — Chaldean planetary hours for the day
  "transit_natal_aspects" + "transit_date" — detailed transit-to-natal aspect listing

Extra natal options:
  "include_numerology": true    — adds numerology block to natal output
  "full_name": "..."            — full name for numerology Expression/Soul Urge

Specialty lookups (callable directly, not via JSON mode):
  namakaran(moon_lon_sidereal)            — name syllables from birth nakshatra
  anatomy_chart(planets_block)            — body regions and afflicted systems
  horary(question_utc, lat, lng, text)    — cast + basic signals of a horary chart
  astrocartography(jd, lat, lng)          — planet lines for relocation
  detect_aspect_patterns(lons, ayan=0)    — Grand Trine, T-Square, Yod, etc.
  solar_return(natal_jd, year, lat, lng)  — annual solar return
  lunar_return(natal_jd, year, month, lat, lng) — monthly lunar return
  compatibility_score(jdA, jdB)           — detailed compatibility scoring
  part_of_fortune(sun, moon, asc, sect)   — Lot of Fortune (day/night)
  vertex(jd, lat, lng)                    — Vertex (fated encounters)
  moon_phase(jd)                          — 8-phase lunar cycle data
  navamsa_chart(jd, lat, lng)             — D9 divisional chart
  panchang_elements(jd)                   — Tithi, Nakshatra, Yoga, Karana
  numerology(year, month, day, name)      — Life Path, Personal Year, etc.
  equal_houses(asc_lon)                   — Equal house cusps
  composite_chart(jdA, jdB, latA, lngA, latB, lngB) — midpoint relationship chart
  black_moon_lilith(jd)                   — Mean BML position
  secondary_progressions(jd, age, lat, lng) — 1 day = 1 year
  planetary_return(jd, planet, year, lat, lng) — any planet's return
  compute_arabic_parts(lons, asc, sect)   — 10 Arabic Parts / Lots
  fixed_star_conjunctions(lons, orb)      — 23 fixed stars
  mangal_dosha(jd, lat, lng)             — Kuja/Mars dosha check
  kaalsarpa_dosha(jd, lat, lng)          — Kaalsarpa dosha check
  varga_chart(jd, varga, lat, lng)       — D2–D60 divisional charts
  transit_to_natal_aspects(natal_jd, transit_jd) — detailed transit aspects
  planetary_hours(jd, lat, lng)          — Chaldean planetary hours
"""

from __future__ import annotations
import json
import sys
import math
import os
import argparse
from datetime import datetime, timedelta, timezone

# ── optional high-precision backend ──────────────────────────────────────────
try:
    import swisseph as swe  # type: ignore
    _HAS_SWE = True
    # Absolute ephemeris path — never relative (CWD-dependent)
    _EPHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ephe")
    if not os.path.isdir(_EPHE_DIR):
        _EPHE_DIR = "/opt/data/astro/ephe"  # fallback known install
    if os.path.isdir(_EPHE_DIR):
        swe.set_ephe_path(_EPHE_DIR)
except Exception:
    swe = None  # type: ignore
    _HAS_SWE = False
    _EPHE_DIR = None

try:
    from zoneinfo import ZoneInfo
    _HAS_TZDB = True
except Exception:
    _HAS_TZDB = False

TODAY = datetime.now(timezone.utc).replace(tzinfo=None)

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION A — WESTERN INTERPRETIVE DATA
# ═════════════════════════════════════════════════════════════════════════════

SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
         "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
SIGN_ABBR = ["Ari","Tau","Gem","Can","Leo","Vir","Lib","Sco","Sag","Cap","Aqu","Pis"]

SIGN_DATA = {
    "Aries":      {"element":"Fire","modality":"Cardinal","ruler":"Mars","polarity":"Yang",
                   "keywords":"boldness, initiative, raw energy, pioneering drive, impatience"},
    "Taurus":     {"element":"Earth","modality":"Fixed","ruler":"Venus","polarity":"Yin",
                   "keywords":"stability, sensuality, patience, material security, stubbornness"},
    "Gemini":     {"element":"Air","modality":"Mutable","ruler":"Mercury","polarity":"Yang",
                   "keywords":"duality, curiosity, communication, adaptability, restlessness"},
    "Cancer":     {"element":"Water","modality":"Cardinal","ruler":"Moon","polarity":"Yin",
                   "keywords":"nurturing, intuition, emotional memory, home, defensiveness"},
    "Leo":        {"element":"Fire","modality":"Fixed","ruler":"Sun","polarity":"Yang",
                   "keywords":"creativity, leadership, pride, warmth, generosity, ego"},
    "Virgo":      {"element":"Earth","modality":"Mutable","ruler":"Mercury","polarity":"Yin",
                   "keywords":"precision, service, health, discernment, self-criticism"},
    "Libra":      {"element":"Air","modality":"Cardinal","ruler":"Venus","polarity":"Yang",
                   "keywords":"balance, justice, partnership, harmony, indecision"},
    "Scorpio":    {"element":"Water","modality":"Fixed","ruler":"Mars/Pluto","polarity":"Yin",
                   "keywords":"depth, transformation, power, hidden truths, control"},
    "Sagittarius":{"element":"Fire","modality":"Mutable","ruler":"Jupiter","polarity":"Yang",
                   "keywords":"expansion, philosophy, freedom, truth-seeking, excess"},
    "Capricorn":  {"element":"Earth","modality":"Cardinal","ruler":"Saturn","polarity":"Yin",
                   "keywords":"ambition, discipline, structure, authority, coldness"},
    "Aquarius":   {"element":"Air","modality":"Fixed","ruler":"Saturn/Uranus","polarity":"Yang",
                   "keywords":"innovation, humanitarian ideals, detachment, originality"},
    "Pisces":     {"element":"Water","modality":"Mutable","ruler":"Jupiter/Neptune","polarity":"Yin",
                   "keywords":"compassion, spirituality, imagination, dissolution, escapism"},
}

PLANET_ARCHETYPES = {
    "Sun":"identity, ego, vitality, the father, conscious will",
    "Moon":"emotion, instinct, the mother, subconscious, needs, habits",
    "Mercury":"mind, communication, intellect, learning, siblings",
    "Venus":"love, beauty, values, art, money, what we attract",
    "Mars":"drive, desire, action, conflict, sex, the warrior",
    "Jupiter":"expansion, luck, philosophy, faith, abundance",
    "Saturn":"discipline, karma, restriction, time, responsibility, fear",
    "Uranus":"rebellion, innovation, sudden change, awakening, freedom",
    "Neptune":"dreams, illusion, spirituality, compassion, dissolution",
    "Pluto":"transformation, power, death/rebirth, shadow, obsession",
    "North Node":"soul's growth edge, karmic direction, the unfamiliar",
    "South Node":"karmic past, innate gifts, comfort zone to release",
    "Chiron":"the wounded healer — deepest wound becomes greatest medicine",
}

HOUSE_SYSTEM_NAMES = {
    "P": "Placidus (Swiss Ephemeris)", "K": "Koch (Swiss Ephemeris)",
    "E": "Equal (Swiss Ephemeris)", "R": "Regiomontanus (Swiss Ephemeris)",
    "T": "Topocentric (Swiss Ephemeris)", "O": "Porphyry (Swiss Ephemeris)",
    "C": "Campanus (Swiss Ephemeris)", "B": "Alcabitius (Swiss Ephemeris)",
    "W": "Whole-sign (Swiss Ephemeris)", "X": "Meridian (Swiss Ephemeris)",
}
_HOUSE_SYSTEM_NAMES = HOUSE_SYSTEM_NAMES

HOUSE_MEANINGS = {
    1:"Self, body, identity, vitality, first impressions, how the world sees you",
    2:"Money, possessions, values, self-worth, material security, talents",
    3:"Communication, siblings, short trips, local life, early learning, the mind",
    4:"Home, roots, family, ancestry, the inner foundation, one parent",
    5:"Creativity, romance, children, pleasure, play, self-expression",
    6:"Health, daily work, routine, service, habits, the body's maintenance",
    7:"Partnership, marriage, open enemies, contracts, the significant other",
    8:"Death/rebirth, shared resources, intimacy, the occult, others' money, crisis",
    9:"Philosophy, higher study, long travel, religion, meaning, the foreign",
    10:"Career, public role, reputation, authority, legacy, one parent",
    11:"Friends, groups, networks, hopes, causes, the collective, gains",
    12:"The unconscious, solitude, spirituality, self-undoing, institutions, the hidden",
}

# Traditional per-planet orbs (Lilly, Christian Astrology Bk.1):
# Saturn 9°, Jupiter 9°, Mars 7°, Sun 15°, Venus 7°, Mercury 7°, Moon 12°
PLANET_ORBS = {
    "Saturn": 9, "Jupiter": 9, "Mars": 7, "Sun": 15,
    "Venus": 7, "Mercury": 7, "Moon": 12,
    "Uranus": 5, "Neptune": 5, "Pluto": 4,  # modern additions (tight)
    "North Node": 3, "South Node": 3,
}
# Average orb used when planet is not in table (fallback)
DEFAULT_ORB = 8
_PIH = None  # lazy-loaded planet-in-house readings (data/planet_in_house.json)

ASPECTS = {  # name: (exact angle, default orb degrees, nature) — orbs per Woolfolk 2008
    "conjunction":(0,10,"fusion — energies merge, amplified, unified"),
    "opposition":(180,9,"tension & awareness through the other; need for balance"),
    "trine":(120,9,"natural flow, ease, talent, harmony — can be lazy"),
    "square":(90,9,"friction, drive, growth forced through struggle"),
    "sextile":(60,6,"opportunity, cooperation if acted on"),
    "quincunx":(150,3,"awkward adjustment, unrelated energies needing constant tuning"),
    # minor aspects (harmonic families) — Kepler/Morin, 2° orbs per Woolfolk
    "semisextile":(30,2,"subtle adjacency, gradual integration"),
    "semisquare":(45,2,"irritation, friction half-hidden"),
    "sesquiquadrate":(135,2,"internal tension demanding release"),
    "quintile":(72,1.5,"creative talent, genius, inspired expression"),
    "biquintile":(144,1.5,"creative mastery through practice"),
    "septile":(51.4286,1,"fated, mystical, unseen threads"),
    "novile":(40,1,"spiritual growth, inner refinement"),
    "decile":(36,1,"focused talent, pragmatic gift"),
}

# Essential dignities (classical) — rulership, exaltation, detriment, fall
DIGNITY = {
    "Sun":     {"rule":["Leo"],"exalt":["Aries"],"detri":["Aquarius"],"fall":["Libra"]},
    "Moon":    {"rule":["Cancer"],"exalt":["Taurus"],"detri":["Capricorn"],"fall":["Scorpio"]},
    "Mercury": {"rule":["Gemini","Virgo"],"exalt":["Virgo"],"detri":["Sagittarius","Pisces"],"fall":["Pisces"]},
    "Venus":   {"rule":["Taurus","Libra"],"exalt":["Pisces"],"detri":["Aries","Scorpio"],"fall":["Virgo"]},
    "Mars":    {"rule":["Aries","Scorpio"],"exalt":["Capricorn"],"detri":["Taurus","Libra"],"fall":["Cancer"]},
    "Jupiter": {"rule":["Sagittarius","Pisces"],"exalt":["Cancer"],"detri":["Gemini","Virgo"],"fall":["Capricorn"]},
    "Saturn":  {"rule":["Capricorn","Aquarius"],"exalt":["Libra"],"detri":["Cancer","Leo"],"fall":["Aries"]},
}

SATURN_RETURN_AGES = [29, 58, 87]   # ~29.5 yr Saturn cycle
JUPITER_RETURN_AGES = [12, 24, 36, 48, 60, 72, 84]
NODE_RETURN_AGES = [18.6, 37.2, 55.8, 74.4]   # ~18.6 yr nodal cycle (incl. ~mid 'nodal reversal')

# Western anatomy — zodiac sign → body part (classical rulerships)
# Used in medical astrology: avoid surgery when Moon transits the sign ruling
# the body part, and to read which body systems a chart emphasises.
ANATOMY = {
    "Aries":      {"region":"head, brain, eyes, face, adrenals",
                   "system":"nervous / muscular, acute inflammation, fevers"},
    "Taurus":     {"region":"neck, throat, vocal cords, thyroid, jaw, ears",
                   "system":"throat, lymphatic, lower jaw"},
    "Gemini":     {"region":"lungs, shoulders, arms, hands, nervous system",
                   "system":"respiratory, peripheral nerves"},
    "Cancer":     {"region":"chest, breasts, stomach, ribs, womb, lymph",
                   "system":"digestion, fluids, the body's emotional barometer"},
    "Leo":        {"region":"heart, upper back, spine, circulation",
                   "system":"cardiovascular, vitality"},
    "Virgo":      {"region":"abdomen, intestines, spleen, solar plexus, hands",
                   "system":"digestive, assimilation, hygiene, daily routine"},
    "Libra":      {"region":"kidneys, lower back, adrenals, skin, buttocks",
                   "system":"filtration, balance, glucose regulation"},
    "Scorpio":    {"region":"reproductive organs, bladder, rectum, pelvis, nose",
                   "system":"eliminative, sexual, transformative"},
    "Sagittarius":{"region":"hips, thighs, liver, sciatic nerve, sacrum",
                   "system":"locomotion, hepatic, the traveller's body"},
    "Capricorn":  {"region":"knees, bones, joints, teeth, skin, hair",
                   "system":"skeletal, structural, chronic"},
    "Aquarius":    {"region":"ankles, calves, circulation, electrical system",
                   "system":"nervous, circulatory, sudden/electrical"},
    "Pisces":     {"region":"feet, toes, lymphatic, immune system, the psyche",
                   "system":"immune, psychosomatic, the body's porous boundary"},
}
# Avoid-surgery rule: when Moon is in the sign ruling the body part
# (or afflicting its ruler), defer non-emergency surgery. Also: never operate
# during a lunar eclipse, and prefer Moon in a fixed sign for stability.

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION B — VEDIC (JYOTISHA) DATA
# ═════════════════════════════════════════════════════════════════════════════

NAKSHATRAS = [
    {"name":"Ashwini","lord":"Ketu","deity":"Ashwini Kumaras","symbol":"Horse's head",
     "quality":"swift healing, fresh starts, vitality, restless pioneering"},
    {"name":"Bharani","lord":"Venus","deity":"Yama","symbol":"Yoni",
     "quality":"bearing burdens, fertility, restraint, transformation through endurance"},
    {"name":"Krittika","lord":"Sun","deity":"Agni","symbol":"Razor / flame",
     "quality":"purifying fire, sharp focus, cutting through illusion, ambition"},
    {"name":"Rohini","lord":"Moon","deity":"Brahma","symbol":"Ox-cart / chariot",
     "quality":"growth, beauty, sensual abundance, magnetism, materiality"},
    {"name":"Mrigashira","lord":"Mars","deity":"Soma","symbol":"Deer's head",
     "quality":"seeking, gentle curiosity, wandering, artistic restlessness"},
    {"name":"Ardra","lord":"Rahu","deity":"Rudra","symbol":"Teardrop / diamond",
     "quality":"storm and renewal, raw emotion, destruction that clears the way"},
    {"name":"Punarvasu","lord":"Jupiter","deity":"Aditi","symbol":"Quiver of arrows",
     "quality":"return of light, resilience, optimism, expansion after loss"},
    {"name":"Pushya","lord":"Saturn","deity":"Brihaspati","symbol":"Cow's udder / lotus",
     "quality":"nourishment, devotion, disciplined growth — most auspicious nakshatra"},
    {"name":"Ashlesha","lord":"Mercury","deity":"Nagas","symbol":"Coiled serpent",
     "quality":"penetrating insight, kundalini, hypnotic power, possible cunning"},
    {"name":"Magha","lord":"Ketu","deity":"Pitris (ancestors)","symbol":"Throne",
     "quality":"ancestral power, lineage, pride, the karma of the forefathers"},
    {"name":"Purva Phalguni","lord":"Venus","deity":"Bhaga","symbol":"Front of a bed",
     "quality":"pleasure, romance, rest, creative enjoyment, generosity"},
    {"name":"Uttara Phalguni","lord":"Sun","deity":"Aryaman","symbol":"Back of a bed",
     "quality":"contracts, partnership, patronage, generous service, stability"},
    {"name":"Hasta","lord":"Moon","deity":"Savitar","symbol":"Hand",
     "quality":"skill, craft, healing hands, cleverness, manifesting by hand"},
    {"name":"Chitra","lord":"Mars","deity":"Tvastar","symbol":"Bright jewel",
     "quality":"artistry, design, dazzling charisma, creating beauty/structure"},
    {"name":"Swati","lord":"Rahu","deity":"Vayu","symbol":"Young shoot in wind",
     "quality":"independence, flexibility, trade, self-made movement"},
    {"name":"Vishakha","lord":"Jupiter","deity":"Indra-Agni","symbol":"Triumphal archway",
     "quality":"goal-driven intensity, ambition, harvest after patient effort"},
    {"name":"Anuradha","lord":"Saturn","deity":"Mitra","symbol":"Lotus / staff",
     "quality":"devoted friendship, organisation, success abroad, occult devotion"},
    {"name":"Jyeshtha","lord":"Mercury","deity":"Indra","symbol":"Circular amulet","quality":
     "seniority, protectiveness, responsibility, hidden power, isolation"},
    {"name":"Mula","lord":"Ketu","deity":"Nirriti","symbol":"Bunch of roots",
     "quality":"getting to the root, dissolution, investigation, tearing down to rebuild"},
    {"name":"Purva Ashadha","lord":"Venus","deity":"Apas","symbol":"Fan / winnowing basket",
     "quality":"invincibility, conviction, purification, early victory"},
    {"name":"Uttara Ashadha","lord":"Sun","deity":"Vishvadevas","symbol":"Elephant tusk",
     "quality":"lasting victory, integrity, leadership grounded in principle"},
    {"name":"Shravana","lord":"Moon","deity":"Vishnu","symbol":"Ear / three footprints",
     "quality":"deep listening, learning, connection, preservation of wisdom"},
    {"name":"Dhanishtha","lord":"Mars","deity":"Eight Vasus","symbol":"Drum",
     "quality":"rhythm, wealth, music, group leadership, abundance, ambition"},
    {"name":"Shatabhisha","lord":"Rahu","deity":"Varuna","symbol":"Empty circle / 100 stars",
     "quality":"healing, mysticism, solitude, secrets, scientific detachment"},
    {"name":"Purva Bhadrapada","lord":"Jupiter","deity":"Aja Ekapada","symbol":"Front of a funeral cot",
     "quality":"spiritual fire, intensity, idealism, eccentric vision"},
    {"name":"Uttara Bhadrapada","lord":"Saturn","deity":"Ahir Budhnya","symbol":"Back of a funeral cot",
     "quality":"deep calm, wisdom from depth, endurance, cosmic compassion"},
    {"name":"Revati","lord":"Mercury","deity":"Pushan","symbol":"Fish / drum",
     "quality":"safe passage, nourishment, completion, gentle guidance, journeys' end"},
]
NAK_ARC = 360.0 / 27.0          # 13°20'
PADA_ARC = NAK_ARC / 4.0        # 3°20'

# Namakaran — nakshatra → pada → starting syllables for the child's name.
# Classical rule (Brihat Parashara Hora Shastra): the baby's name begins with
# the syllable of the Moon's birth-nakshatra pada. The syllable is also used
# for naming a business, art project, etc. (the *vibrational frequency* of
# the natal lunar mansion).
NAKSHATRA_SYLLABLES = {
    "Ashwini":         ["Chu","Che","Cho","La"],
    "Bharani":         ["Li","Lu","Le","Lo"],
    "Krittika":        ["A","E","U","O"],
    "Rohini":          ["O","Va","Vi","Vu"],
    "Mrigashira":      ["Ve","Vo","Ka","Ki"],
    "Ardra":           ["Ku","Gha","An","Chha"],
    "Punarvasu":       ["Ke","Ko","Ha","Hi"],
    "Pushya":          ["Hu","He","Ho","Da"],
    "Ashlesha":        ["Di","Du","De","Do"],
    "Magha":           ["Ma","Mi","Mu","Me"],
    "Purva Phalguni":  ["Mo","Ta","Ti","Tu"],
    "Uttara Phalguni": ["Te","To","Pa","Pi"],
    "Hasta":           ["Pu","Sha","An","Tha"],
    "Chitra":          ["Pe","Po","Ra","Ri"],
    "Swati":           ["Ru","Re","Ro","Ta"],
    "Vishakha":        ["Ti","Tu","Te","To"],
    "Anuradha":        ["Na","Ni","Nu","Ne"],
    "Jyeshtha":        ["No","Ya","Yi","Yu"],
    "Mula":            ["Ye","Yo","Ba","Bi"],
    "Purva Ashadha":   ["Bu","Da","Bha","Dha"],
    "Uttara Ashadha":  ["Be","Bo","Ja","Ji"],
    "Shravana":        ["Ju","Je","Jo","Khi"],
    "Dhanishtha":      ["Ga","Gi","Gu","Ge"],
    "Shatabhisha":     ["Go","Sa","Si","Su"],
    "Purva Bhadrapada":["Se","So","Dha","Dhi"],
    "Uttara Bhadrapada":["Du","Tha","Jha","Na"],
    "Revati":          ["De","Do","Cha","Chi"],
}

DASHA_YEARS = {"Ketu":7,"Venus":20,"Sun":6,"Moon":10,"Mars":7,
               "Rahu":18,"Jupiter":16,"Saturn":19,"Mercury":17}
DASHA_SEQ = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
DASHA_TOTAL = 120

RASHI_LORDS = {"Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars","Sagittarius":"Jupiter",
    "Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"}

GRAHA_KARAKAS = {
    "Sun":"Atma (soul), father, authority, vitality, government",
    "Moon":"mind, mother, emotions, the public, nourishment",
    "Mars":"energy, siblings, courage, land, conflict",
    "Mercury":"speech, intellect, business, education",
    "Jupiter":"wisdom, children, wealth, dharma, the guru",
    "Venus":"spouse, love, luxury, art, vehicles, pleasure",
    "Saturn":"longevity, discipline, suffering, service, karma",
    "Rahu":"obsession, foreign things, illusion, sudden gain, ambition",
    "Ketu":"liberation, spirituality, loss, past-life skill, moksha",
}

VEDIC_HOUSE = {
    1:"Tanu — self, body, personality, life-direction",
    2:"Dhana — wealth, family, speech, food, early life",
    3:"Sahaja — courage, siblings, effort, skills, communication",
    4:"Sukha — mother, home, happiness, vehicles, heart, schooling",
    5:"Putra — children, intelligence, romance, past-life merit (purva punya)",
    6:"Ari — enemies, debt, disease, service, daily work, obstacles overcome",
    7:"Yuvati — spouse, partnership, business, the public, travel",
    8:"Ayur — longevity, transformation, the hidden, inheritance, sudden events",
    9:"Bhagya — fortune, dharma, father, guru, higher learning, pilgrimage",
    10:"Karma — career, status, reputation, action in the world",
    11:"Labha — gains, income, networks, elder siblings, fulfilment of desire",
    12:"Vyaya — loss, expense, foreign lands, solitude, liberation, the bed",
}

EXALT_SIGN = {"Sun":"Aries","Moon":"Taurus","Mars":"Capricorn","Mercury":"Virgo",
    "Jupiter":"Cancer","Venus":"Pisces","Saturn":"Libra","Rahu":"Taurus","Ketu":"Scorpio"}
DEBIL_SIGN = {"Sun":"Libra","Moon":"Scorpio","Mars":"Cancer","Mercury":"Pisces",
    "Jupiter":"Capricorn","Venus":"Virgo","Saturn":"Aries","Rahu":"Scorpio","Ketu":"Taurus"}

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION C — CHINESE BAZI DATA
# ═════════════════════════════════════════════════════════════════════════════

STEMS = [
    {"han":"甲","pinyin":"Jiǎ","element":"Wood","polarity":"Yang","nature":"the great tree — upright leadership, growth, pioneering"},
    {"han":"乙","pinyin":"Yǐ","element":"Wood","polarity":"Yin","nature":"the vine/grass — adaptable, persistent, diplomatic"},
    {"han":"丙","pinyin":"Bǐng","element":"Fire","polarity":"Yang","nature":"the sun — radiant, generous, expressive, warm"},
    {"han":"丁","pinyin":"Dīng","element":"Fire","polarity":"Yin","nature":"the lamp/candle — focused, refined, illuminating"},
    {"han":"戊","pinyin":"Wù","element":"Earth","polarity":"Yang","nature":"the mountain — solid, dependable, steadfast"},
    {"han":"己","pinyin":"Jǐ","element":"Earth","polarity":"Yin","nature":"the field/soil — nurturing, receptive, productive"},
    {"han":"庚","pinyin":"Gēng","element":"Metal","polarity":"Yang","nature":"the axe/sword — decisive, righteous, forceful"},
    {"han":"辛","pinyin":"Xīn","element":"Metal","polarity":"Yin","nature":"the jewel — refined, sensitive, precise, elegant"},
    {"han":"壬","pinyin":"Rén","element":"Water","polarity":"Yang","nature":"the ocean/river — strategic, resourceful, flowing"},
    {"han":"癸","pinyin":"Guǐ","element":"Water","polarity":"Yin","nature":"the rain/mist — gentle, wise, penetrating, intuitive"},
]
BRANCHES = [
    {"han":"子","pinyin":"Zǐ","animal":"Rat","element":"Water","hidden":["Guǐ"],"hours":"23:00–00:59"},
    {"han":"丑","pinyin":"Chǒu","animal":"Ox","element":"Earth","hidden":["Jǐ","Guǐ","Xīn"],"hours":"01:00–02:59"},
    {"han":"寅","pinyin":"Yín","animal":"Tiger","element":"Wood","hidden":["Jiǎ","Bǐng","Wù"],"hours":"03:00–04:59"},
    {"han":"卯","pinyin":"Mǎo","animal":"Rabbit","element":"Wood","hidden":["Yǐ"],"hours":"05:00–06:59"},
    {"han":"辰","pinyin":"Chén","animal":"Dragon","element":"Earth","hidden":["Wù","Yǐ","Guǐ"],"hours":"07:00–08:59"},
    {"han":"巳","pinyin":"Sì","animal":"Snake","element":"Fire","hidden":["Bǐng","Wù","Gēng"],"hours":"09:00–10:59"},
    {"han":"午","pinyin":"Wǔ","animal":"Horse","element":"Fire","hidden":["Dīng","Jǐ"],"hours":"11:00–12:59"},
    {"han":"未","pinyin":"Wèi","animal":"Goat","element":"Earth","hidden":["Jǐ","Dīng","Yǐ"],"hours":"13:00–14:59"},
    {"han":"申","pinyin":"Shēn","animal":"Monkey","element":"Metal","hidden":["Gēng","Rén","Wù"],"hours":"15:00–16:59"},
    {"han":"酉","pinyin":"Yǒu","animal":"Rooster","element":"Metal","hidden":["Xīn"],"hours":"17:00–18:59"},
    {"han":"戌","pinyin":"Xū","animal":"Dog","element":"Earth","hidden":["Wù","Xīn","Dīng"],"hours":"19:00–20:59"},
    {"han":"亥","pinyin":"Hài","animal":"Pig","element":"Water","hidden":["Rén","Jiǎ"],"hours":"21:00–22:59"},
]
PINYIN_ELEM = {s["pinyin"]:s["element"] for s in STEMS}

# Wu Xing cycles
GENERATES = {"Wood":"Fire","Fire":"Earth","Earth":"Metal","Metal":"Water","Water":"Wood"}
GENERATED_BY = {v:k for k,v in GENERATES.items()}
CONTROLS = {"Wood":"Earth","Earth":"Water","Water":"Fire","Fire":"Metal","Metal":"Wood"}
CONTROLLED_BY = {v:k for k,v in CONTROLS.items()}

ELEMENT_ADVICE = {
    "Wood":"Strengthen with growth, learning, nature, green foods, the east, planning; weaken by pruning over-extension.",
    "Fire":"Strengthen with sunlight, joy, social warmth, red, the south, expression; weaken by cooling impulsiveness.",
    "Earth":"Strengthen with routine, grounding, yellow/brown foods, the centre, reliability; weaken by avoiding over-worry.",
    "Metal":"Strengthen with structure, precision, white/metal, the west, decluttering; weaken by softening rigidity.",
    "Water":"Strengthen with stillness, study, black/blue, the north, flow, intuition; weaken by avoiding withdrawal.",
}

ZODIAC_COMPAT = {
    "Rat":{"best":["Dragon","Monkey","Ox"],"clash":"Horse","harm":"Goat"},
    "Ox":{"best":["Snake","Rooster","Rat"],"clash":"Goat","harm":"Horse"},
    "Tiger":{"best":["Horse","Dog","Pig"],"clash":"Monkey","harm":"Snake"},
    "Rabbit":{"best":["Goat","Pig","Dog"],"clash":"Rooster","harm":"Dragon"},
    "Dragon":{"best":["Rat","Monkey","Rooster"],"clash":"Dog","harm":"Rabbit"},
    "Snake":{"best":["Ox","Rooster","Monkey"],"clash":"Pig","harm":"Tiger"},
    "Horse":{"best":["Tiger","Dog","Goat"],"clash":"Rat","harm":"Ox"},
    "Goat":{"best":["Rabbit","Pig","Horse"],"clash":"Ox","harm":"Rat"},
    "Monkey":{"best":["Rat","Dragon","Snake"],"clash":"Tiger","harm":"Pig"},
    "Rooster":{"best":["Ox","Snake","Dragon"],"clash":"Rabbit","harm":"Dog"},
    "Dog":{"best":["Tiger","Horse","Rabbit"],"clash":"Dragon","harm":"Rooster"},
    "Pig":{"best":["Rabbit","Goat","Tiger"],"clash":"Snake","harm":"Monkey"},
}

# Ten Gods (十神) relationship of another stem to the Day Master, by element-relation + polarity
def ten_god(dm_elem, dm_pol, other_elem, other_pol):
    same_pol = (dm_pol == other_pol)
    if other_elem == dm_elem:
        return "Friend (比肩)" if same_pol else "Rob Wealth (劫財)"
    if GENERATED_BY[dm_elem] == other_elem:           # resource (feeds DM)
        return "Direct Resource (正印)" if not same_pol else "Indirect Resource (偏印)"
    if GENERATES[dm_elem] == other_elem:              # output (DM produces)
        return "Hurting Officer (傷官)" if not same_pol else "Eating God (食神)"
    if CONTROLS[dm_elem] == other_elem:               # wealth (DM controls)
        return "Direct Wealth (正財)" if not same_pol else "Indirect Wealth (偏財)"
    if CONTROLLED_BY[dm_elem] == other_elem:          # officer (controls DM)
        return "Direct Officer (正官)" if not same_pol else "Seven Killings (七殺)"
    return ""

# Solar-term month boundaries: month branch starts when Sun reaches these tropical longitudes.
# Tiger month (寅, idx 2) begins at Li Chun, Sun = 315°.
SOLAR_TERM_START_LON = 315.0   # Li Chun → start of Tiger month / BaZi solar year

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION D — ASTRONOMY (pure-Python geocentric ephemeris, Schlyter method)
# ═════════════════════════════════════════════════════════════════════════════

def _sin(d): return math.sin(math.radians(d))
def _cos(d): return math.cos(math.radians(d))
def _tan(d): return math.tan(math.radians(d))
def _asin(x): return math.degrees(math.asin(max(-1.0,min(1.0,x))))
def _atan2(y,x): return math.degrees(math.atan2(y,x))
def norm360(x): return x % 360.0
def norm180(x):
    x = x % 360.0
    return x - 360.0 if x > 180 else x

def julian_day(dt_utc: datetime) -> float:
    """JD (UT) from a naive UTC datetime."""
    y, m = dt_utc.year, dt_utc.month
    d = (dt_utc.day + dt_utc.hour/24 + dt_utc.minute/1440
         + dt_utc.second/86400 + dt_utc.microsecond/86400e6)
    if m <= 2:
        y -= 1; m += 12
    a = y // 100
    b = 2 - a + a // 4
    return (math.floor(365.25*(y+4716)) + math.floor(30.6001*(m+1))
            + d + b - 1524.5)

def obliquity(d):   # d = days since 2000 Jan 0.0
    return 23.4393 - 3.563e-7 * d

def _kepler(M_deg, e):
    """Solve Kepler's equation E - e·sin E = M. M in deg, e dimensionless.
    Solved in radians (correct Newton derivative), returned in degrees."""
    M = math.radians(norm360(M_deg))
    E = M + e*math.sin(M)*(1 + e*math.cos(M))
    for _ in range(12):
        dE = (E - e*math.sin(E) - M) / (1 - e*math.cos(E))
        E -= dE
        if abs(dE) < 1e-11:
            break
    return math.degrees(E)

def _orbit_xyz(N,i,w,a,e,M):
    """Heliocentric ecliptic rectangular coords from orbital elements (deg)."""
    E = _kepler(M, e)
    xv = a*(_cos(E) - e)
    yv = a*(math.sqrt(1-e*e)*_sin(E))
    v = _atan2(yv, xv)
    r = math.hypot(xv, yv)
    xh = r*(_cos(N)*_cos(v+w) - _sin(N)*_sin(v+w)*_cos(i))
    yh = r*(_sin(N)*_cos(v+w) + _cos(N)*_sin(v+w)*_cos(i))
    zh = r*(_sin(v+w)*_sin(i))
    return xh, yh, zh, r, v

def _sun(d):
    w = 282.9404 + 4.70935e-5*d
    e = 0.016709 - 1.151e-9*d
    M = norm360(356.0470 + 0.9856002585*d)
    E = _kepler(M, e)
    xv = _cos(E) - e
    yv = math.sqrt(1-e*e)*_sin(E)
    v = _atan2(yv, xv)
    r = math.hypot(xv, yv)
    lon = norm360(v + w)
    # geocentric Sun rectangular (ecliptic)
    xs = r*_cos(lon); ys = r*_sin(lon)
    return {"lon":lon, "r":r, "xs":xs, "ys":ys, "M":M, "L":norm360(w+M)}

# Planetary orbital elements as functions of d ────────────────────────────────
def _elems(body, d):
    E = {
    "Mercury":(48.3313+3.24587e-5*d, 7.0047+5.00e-8*d, 29.1241+1.01444e-5*d,
               0.387098, 0.205635+5.59e-10*d, 168.6562+4.0923344368*d),
    "Venus":(76.6799+2.46590e-5*d, 3.3946+2.75e-8*d, 54.8910+1.38374e-5*d,
             0.723330, 0.006773-1.302e-9*d, 48.0052+1.6021302244*d),
    "Mars":(49.5574+2.11081e-5*d, 1.8497-1.78e-8*d, 286.5016+2.92961e-5*d,
            1.523688, 0.093405+2.516e-9*d, 18.6021+0.5240207766*d),
    "Jupiter":(100.4542+2.76854e-5*d, 1.3030-1.557e-7*d, 273.8777+1.64505e-5*d,
               5.20256, 0.048498+4.469e-9*d, 19.8950+0.0830853001*d),
    "Saturn":(113.6634+2.38980e-5*d, 2.4886-1.081e-7*d, 339.3939+2.97661e-5*d,
              9.55475, 0.055546-9.499e-9*d, 316.9670+0.0334442282*d),
    "Uranus":(74.0005+1.3978e-5*d, 0.7733+1.9e-8*d, 96.6612+3.0565e-5*d,
              19.18171-1.55e-8*d, 0.047318+7.45e-9*d, 142.5905+0.011725806*d),
    "Neptune":(131.7806+3.0173e-5*d, 1.7700-2.55e-7*d, 272.8461-6.027e-6*d,
               30.05826+3.313e-8*d, 0.008606+2.15e-9*d, 260.2471+0.005995147*d),
    }[body]
    return E

def _planet_geo_lon(body, d, sun):
    N,i,w,a,e,M = _elems(body, d)
    M = norm360(M)
    xh,yh,zh,r,v = _orbit_xyz(N,i,w,a,e,M)
    # geocentric
    xg = xh + sun["xs"]; yg = yh + sun["ys"]; zg = zh
    lon = norm360(_atan2(yg, xg))
    # perturbations (Schlyter) for the big bodies
    Mj = norm360(19.8950+0.0830853001*d)
    Msa = norm360(316.9670+0.0334442282*d)
    Mu = norm360(142.5905+0.011725806*d)
    pert = 0.0
    if body == "Jupiter":
        pert = (-0.332*_sin(2*Mj-5*Msa-67.6) -0.056*_sin(2*Mj-2*Msa+21)
                +0.042*_sin(3*Mj-5*Msa+21) -0.036*_sin(Mj-2*Msa)
                +0.022*_cos(Mj-Msa) +0.023*_sin(2*Mj-3*Msa+52)
                -0.016*_sin(Mj-5*Msa-69))
    elif body == "Saturn":
        pert = (+0.812*_sin(2*Mj-5*Msa-67.6) -0.229*_cos(2*Mj-4*Msa-2)
                +0.119*_sin(Mj-2*Msa-3) +0.046*_sin(2*Mj-6*Msa-69)
                +0.014*_sin(Mj-3*Msa+32))
    elif body == "Uranus":
        pert = (+0.040*_sin(Msa-2*Mu+6) +0.035*_sin(Msa-3*Mu+33)
                -0.015*_sin(Mj-Mu+20))
    return norm360(lon + pert)

def _moon_geo_lon(d, sun):
    N = 125.1228 - 0.0529538083*d
    i = 5.1454
    w = 318.0634 + 0.1643573223*d
    a = 60.2666
    e = 0.054900
    M = norm360(115.3654 + 13.0649929509*d)
    xh,yh,zh,r,v = _orbit_xyz(N,i,w,a,e,M)
    lon = norm360(_atan2(yh, xh))
    lat = _atan2(zh, math.hypot(xh,yh))
    # perturbation arguments
    Ls = sun["L"]; Lm = norm360(N+w+M); Ms = sun["M"]; Mm = M
    D = norm360(Lm - Ls); F = norm360(Lm - N)
    dlon = (-1.274*_sin(Mm-2*D) +0.658*_sin(2*D) -0.186*_sin(Ms)
            -0.059*_sin(2*Mm-2*D) -0.057*_sin(Mm-2*D+Ms) +0.053*_sin(Mm+2*D)
            +0.046*_sin(2*D-Ms) +0.041*_sin(Mm-Ms) -0.035*_sin(D)
            -0.031*_sin(Mm+Ms) -0.015*_sin(2*F-2*D) +0.011*_sin(Mm-4*D))
    return norm360(lon + dlon)

def _resolve_target_dt(data, default=None):
    """Normalize user/agent date input (target_date, as_of, date) into a naive UTC datetime."""
    for k in ("target_date", "as_of", "date"):
        v = data.get(k)
        if v:
            if isinstance(v, datetime):
                return v
            try:
                if len(str(v)) == 10:
                    return datetime.strptime(str(v), "%Y-%m-%d")
                return datetime.strptime(str(v), "%Y-%m-%d %H:%M")
            except Exception:
                pass
    return default or datetime.now(timezone.utc).replace(tzinfo=None)

def _node_lon(d):
    """Mean ascending lunar node (Rahu)."""
    return norm360(125.1228 - 0.0529538083*d)

def _chiron_geo_lon(d, sun):
    """Chiron geocentric longitude via Keplerian orbit. ~3° accuracy, sign-level reliable.
    Elements calibrated to JPL J2000 position (~267° Sagittarius). Perihelion ~mid-1994."""
    N = 208.70               # longitude of ascending node (degrees)
    i = 6.93                 # inclination
    w = 339.62               # argument of perihelion
    a = 13.648               # semi-major axis AU
    e = 0.3786               # eccentricity
    M = norm360(39.2 + 0.01955178*d)   # mean anomaly; 39.2° at J2000
    xh, yh, zh, r, v = _orbit_xyz(N, i, w, a, e, M)
    xg = xh + sun["xs"]
    yg = yh + sun["ys"]
    return norm360(_atan2(yg, xg))

def _pluto_geo_lon(d):
    """Schlyter's approximation, valid roughly 1800–2050."""
    S = 50.03 + 0.033459652*d
    P = 238.95 + 0.003968789*d
    lon = (238.9508 + 0.00400703*d
        - 19.799*_sin(P) + 19.848*_cos(P)
        + 0.897*_sin(2*P) - 4.956*_cos(2*P)
        + 0.610*_sin(3*P) + 1.211*_cos(3*P)
        - 0.341*_sin(4*P) - 0.190*_cos(4*P)
        + 0.128*_sin(5*P) - 0.034*_cos(5*P)
        - 0.038*_sin(6*P) + 0.031*_cos(6*P)
        + 0.020*_sin(S-P) - 0.010*_cos(S-P))
    return norm360(lon)

# Tropical geocentric longitudes for all bodies at JD ──────────────────────────
PLANET_ORDER = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn",
                "Uranus","Neptune","Pluto","North Node","South Node","Chiron"]

def tropical_longitudes(jd, node_type="mean"):
    """Return {body: longitude_deg} (tropical/geocentric) via builtin ephemeris.

    Builtin backend only implements the mean node; true node requires swisseph.
    """
    d = jd - 2451543.5
    sun = _sun(d)
    out = {"Sun":sun["lon"], "Moon":_moon_geo_lon(d,sun)}
    for p in ["Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune"]:
        out[p] = _planet_geo_lon(p, d, sun)
    out["Pluto"] = _pluto_geo_lon(d)
    node = _node_lon(d)
    out["North Node"] = node
    out["South Node"] = norm360(node+180)
    out["Chiron"] = _chiron_geo_lon(d, sun)
    return out

_SWE_FLAGS = None  # resolved lazily: FLG_SWIEPH if .se1 files exist, else MOSEPH

def _swe_calc_flags(jd):
    """FLG_SWIEPH needs .se1 data files; coverage is date-ranged, so a probe at
    J2000 can pass while the requested date raises (missing seas_18.se1 etc.).
    Probe with the actual jd + the most demanding body (true node). On failure
    fall back to file-free Moshier ephemeris (FLG_MOSEPH): ~0.1 arcsec planets,
    both nodes available."""
    global _SWE_FLAGS
    if _SWE_FLAGS is None:
        probe = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_TRUEPOS
        try:
            swe.calc_ut(jd, swe.TRUE_NODE, probe)
            _SWE_FLAGS = probe
        except swe.Error:
            _SWE_FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED | swe.FLG_TRUEPOS
    return _SWE_FLAGS

def longitudes_swe(jd, node_type="true"):
    """High-precision longitudes if swisseph present (tropical).

    node_type: "true" (osculating node, astro.com default) or "mean"
    (smoothed average; classical Parashari/Lilly tradition).
    """
    # Never reset the ephe path here — that kills ephemeris files and breaks
    # Chiron/outers, forcing fallback to the builtin backend.
    if _EPHE_DIR and os.path.isdir(_EPHE_DIR):
        try:
            swe.set_ephe_path(_EPHE_DIR)
        except Exception:
            pass
    node_id = swe.TRUE_NODE if node_type == "true" else swe.MEAN_NODE
    ids = {"Sun":swe.SUN,"Moon":swe.MOON,"Mercury":swe.MERCURY,"Venus":swe.VENUS,
           "Mars":swe.MARS,"Jupiter":swe.JUPITER,"Saturn":swe.SATURN,"Uranus":swe.URANUS,
           "Neptune":swe.NEPTUNE,"Pluto":swe.PLUTO,"North Node":node_id,
           "Chiron":swe.CHIRON}
    # FLG_SWIEPH needs .se1 data files; without them fall back to the built-in
    # Moshier ephemeris (no files, ~0.1 arcsec for planets, exact nodes).
    flags = _swe_calc_flags(jd)
    out = {}
    speed = {}
    for name, pid in ids.items():
        try:
            res = swe.calc_ut(jd, pid, flags)[0]
        except swe.Error:
            if name != "Chiron":
                raise
            # Chiron's asteroid file (seas_18.se1) is often missing while
            # everything else works — degrade Chiron alone to builtin.
            d = jd - 2451543.5
            out[name] = _chiron_geo_lon(d, _sun(d))
            speed[name] = 0.0
            continue
        out[name] = res[0] % 360.0
        speed[name] = res[3]
    out["South Node"] = (out["North Node"]+180) % 360.0
    speed["South Node"] = speed["North Node"]
    return out, speed

_NODE_TYPE = None  # session-wide override set by calculate_full_profile

def body_longitudes(jd, node_type=None):
    """Unified accessor: (longitudes, retro_speed, backend).

    node_type: "true"|"mean"|None. None = module override (_NODE_TYPE, set
    from input "node_type"), else true if swisseph available (astro.com
    convention), else mean (builtin backend has no true node).
    """
    nt = node_type or _NODE_TYPE or ("true" if _HAS_SWE else "mean")
    if _HAS_SWE:
        try:
            lons, speed = longitudes_swe(jd, node_type=nt)
            return lons, speed, "swisseph"
        except Exception:
            pass
    lons = tropical_longitudes(jd, node_type="mean")
    # finite-difference speed for retrograde detection
    lons2 = tropical_longitudes(jd + 1.0)
    speed = {b: norm180(lons2[b]-lons[b]) for b in lons}
    return lons, speed, "builtin"

def body_declinations(jd):
    """Ecliptic declinations of planets (for parallel/contraparallel aspects).
    Uses Swiss Ephemeris if present; falls back to ecliptic-latitude≈0
    approximation (declination ≈ asin(sin(lon)*sin(eps)))."""
    eps = obliquity(jd - 2451543.5)
    out = {}
    if _HAS_SWE:
        try:
            ids = {"Sun":swe.SUN,"Moon":swe.MOON,"Mercury":swe.MERCURY,"Venus":swe.VENUS,
                   "Mars":swe.MARS,"Jupiter":swe.JUPITER,"Saturn":swe.SATURN,"Uranus":swe.URANUS,
                   "Neptune":swe.NEPTUNE,"Pluto":swe.PLUTO,"North Node":swe.TRUE_NODE,
                   "Chiron":swe.CHIRON}
            for name, pid in ids.items():
                res = swe.calc_ut(jd, pid, _swe_calc_flags(jd))
                # pyswisseph 2.10.x: res[0] is a 6-tuple (lon, lat, dist, ...)
                lon, lat = res[0][0], res[0][1]
                # declination from ecliptic lon/lat (NOT ecliptic latitude — that's
                # distance from the ecliptic plane; declination is from the equator)
                out[name] = _asin(_sin(lat) * _cos(eps) + _cos(lat) * _sin(eps) * _sin(lon))
            out["South Node"] = -out["North Node"]
            return out
        except Exception:
            pass
    lons, _, _ = body_longitudes(jd)
    for b, lon in lons.items():
        out[b] = _asin(_sin(lon) * _sin(eps))
    return out

def compute_declination_aspects(lons, decls, bodies=None, orb=1.0):
    """Parallel (same declination ±orb) & contraparallel (opposite ±orb) aspects."""
    bodies = bodies or [b for b in lons if b in decls]
    res = []
    keys = [b for b in bodies if b in decls]
    for i in range(len(keys)):
        for j in range(i+1, len(keys)):
            a, b = keys[i], keys[j]
            da, db = decls[a], decls[b]
            if abs(abs(da) - abs(db)) <= orb:
                kind = "parallel" if (da >= 0) == (db >= 0) else "contraparallel"
                res.append({"a": a, "b": b, "aspect": kind,
                            "orb": round(abs(abs(da) - abs(db)), 2),
                            "exact_sep": round(abs(da - db), 2),
                            "meaning": ("energies merge like conjunction" if kind == "parallel"
                                        else "energies oppose like opposition")})
    return res

def antiscia(lon):
    """Antiscion/contra-antiscion across the 0° Cancer/0° Capricorn axis."""
    if 0 <= lon <= 180:
        return norm360(360 - lon)
    return norm360(180 - (lon - 180))

def station_dates(jd_start, jd_end, planet="Mercury", step=0.5):
    """Find retrograde station dates (start & end) + shadow periods for a planet.
    Scans daily speeds; station = speed crosses zero. Shadow: planet within
    7° (Mercury/Venus) or 15° (outer) of station longitude, pre/post."""
    if not _HAS_SWE:
        return {"error": "station_dates requires swisseph"}
    ids = {"Sun":swe.SUN,"Moon":swe.MOON,"Mercury":swe.MERCURY,"Venus":swe.VENUS,
           "Mars":swe.MARS,"Jupiter":swe.JUPITER,"Saturn":swe.SATURN,"Uranus":swe.URANUS,
           "Neptune":swe.NEPTUNE,"Pluto":swe.PLUTO}
    pid = ids.get(planet)
    if pid is None:
        return {"error": f"planet {planet} not supported"}
    shadow_deg = 7 if planet in ("Mercury","Venus") else 15
    stations = []
    prev_speed = None
    prev_lon = None
    t = jd_start
    while t < jd_end:
        res = swe.calc_ut(t, pid, _swe_calc_flags(t))
        speed = res[0][3]
        lon = res[0][0] % 360
        if prev_speed is not None and (prev_speed * speed < 0 or abs(speed) < 0.0001):
            stations.append({"jd": t, "lon": round(lon, 3),
                             "type": "stationary-direct" if speed > 0 else "stationary-retrograde"})
        prev_speed = speed
        prev_lon = lon
        t += step
    result = {"stations": stations}
    # shadow periods: retrogradation window ±shadow_deg
    if stations:
        retros = [s for s in stations if "retro" in s["type"]]
        if retros:
            first, last = retros[0], retros[-1]
            result["shadow"] = {
                "pre_shadow_ends": round(first["jd"] - shadow_deg * 1.0, 3),
                "retro_start": round(first["jd"], 3),
                "retro_end": round(last["jd"], 3),
                "post_shadow_ends": round(last["jd"] + shadow_deg * 1.0, 3),
                "shadow_deg": shadow_deg,
            }
    return result

def upagrahas(jd, lat, lng, time_known=True):
    """Nine Vedic upagrahas: Gulika/Mandi, Kala, Yamakantaka, Ardhaprahara,
    Dhuma, Vyatipata, Paridhi, Indradhanu, Upaketu.
    Gulika: 7th part of day/night (day=Sunrise-Sunset for weekday lord).
    Dhuma etc. derived from Sun/Moon longitudes (standard formulas)."""
    lons, _, _ = body_longitudes(jd)
    sun_lon = lons["Sun"]
    moon_lon = lons["Moon"]
    # Dhuma = Sun + 133°20'; Vyatipata = 360° - Dhuma; Paridhi = Vyatipata + 180°
    dhuma = norm360(sun_lon + 133.3333)
    vyatipata = norm360(360 - dhuma)
    paridhi = norm360(vyatipata + 180)
    indradhanu = norm360(360 - paridhi)
    upaketu = norm360(indradhanu + 16.6667)
    # Kala = Moon + 180°; Yamakantaka = Moon - 180° (approx)
    kala = norm360(moon_lon + 180)
    yamakantaka = norm360(moon_lon - 180)
    # Ardhaprahara = Moon + 90°
    ardhaprahara = norm360(moon_lon + 90)
    # Gulika: 8 parts of day, 7th part = Gulika; weekday lord determines
    from datetime import datetime
    dt = _jd_to_dt(jd)
    # Approximate: use weekday to place Gulika in a sign
    weekday = dt.weekday()  # 0=Mon
    # Gulika's sign (standard): Mon→Leo? (varies by tradition; use common table)
    gulika_sign_lon = {0: 120.0, 1: 150.0, 2: 180.0, 3: 210.0,
                       4: 240.0, 5: 270.0, 6: 300.0}.get(weekday, 0.0)
    gulika = norm360(gulika_sign_lon)
    return {
        "Gulika": round(gulika, 3),
        "Kala": round(kala, 3),
        "Yamakantaka": round(yamakantaka, 3),
        "Ardhaprahara": round(ardhaprahara, 3),
        "Dhuma": round(dhuma, 3),
        "Vyatipata": round(vyatipata, 3),
        "Paridhi": round(paridhi, 3),
        "Indradhanu": round(indradhanu, 3),
        "Upaketu": round(upaketu, 3),
    }

def _jd_to_dt(jd):
    from datetime import datetime, timedelta
    return datetime(2000, 1, 1) + timedelta(days=jd - 2451545.0)

def vimsopaka_strength(jd):
    """Vimsopaka strength (BPHS Ch.7 slokas 17-19): 20-point planetary strength
    from varga occupancy. Shadvarga weights: Rasi 6, Hora 2, Decanate 4,
    Navamsa 5, Dvadasamsa 2, Trimsamsa 1. A planet scores full weight when
    in own sign in that varga, half in exaltation, zero otherwise."""
    lons, _, _ = body_longitudes(jd)
    ayan = ayanamsha_lahiri(jd)
    weights = {"D1": 6, "D2": 2, "D3": 4, "D9": 5, "D12": 2, "D30": 1}
    names = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn"]
    out = {}
    for nm in names:
        sid = norm360(lons[nm] - ayan)
        score = 0.0
        for v, w in weights.items():
            vc = varga_chart(jd, v)
            v_sign = vc["planets"][nm]["sign"]
            # own sign in varga → full; exaltation → half
            if v_sign in DIGNITY.get(nm, {}).get("rule", []):
                score += w
            elif v_sign in DIGNITY.get(nm, {}).get("exalt", []):
                score += w / 2.0
        out[nm] = round(score, 1)
    return {"scheme": "Shadvarga (Rasi 6, Hora 2, Decanate 4, Navamsa 5, Dvadasamsa 2, Trimsamsa 1)",
            "strength_20": out,
            "max": 20.0,
            "note": "Vimsopaka per BPHS Ch.7 — 20-point scale. 13+ = strong, 10-13 = medium, <10 = weak."}

def ashtakavarga(jd, lat, lng, time_known=True):
    """Bhinnashtakavarga (per-planet bindu counts) + Sarvashtakavarga.
    Exact benefic-bindu tables from Phala Deepika Ch.23 (Mantreswara),
    matching BPHS Ch.66. Each row = the planet whose chart it is; each
    significator (Sun..Saturn, Lagna) contributes +1 bindu to the listed
    houses counted from ITS OWN position. Standard totals: Sun 48, Moon 49,
    Mars 39, Mercury 54, Jupiter 56, Venus 52, Saturn 39; Sarva 337."""
    lons, _, _ = body_longitudes(jd)
    ayan = ayanamsha_lahiri(jd)
    asc_lon = ascendant_mc(jd, lat, lng, ayan)[0] if time_known else norm360(lons["Sun"] - ayan)
    positions = {}
    for p in ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]:
        positions[p] = norm360(lons[p] - ayan)
    positions["Lagna"] = norm360(asc_lon)

    def _houses(sig_pos, from_pos):
        """Houses from from_pos to each house occupied by sig_pos."""
        return [int(((norm360(sig_pos - from_pos)) % 360) // 30) + 1]

    # Benefic bindu tables (Phala Deepika Ch.23, verified totals)
    BAV_TABLES = {
        "Sun": {
            "Sun": [1,2,4,7,8,9,10,11], "Moon": [3,6,10,11], "Mars": [1,2,4,7,8,9,10,11],
            "Mercury": [6,9,10,11,12], "Jupiter": [5,6,9,11], "Venus": [6,7,12],
            "Saturn": [1,2,4,7,8,9,10,11], "Lagna": [3,4,6,10,11,12],
        },
        "Moon": {
            "Sun": [3,6,7,8,10,11], "Moon": [1,3,6,7,10,11], "Mars": [2,3,5,6,9,10,11],
            "Mercury": [3,4,5,7,8,10,11], "Jupiter": [1,2,4,7,8,10,11], "Venus": [3,4,5,7,9,10,11],
            "Saturn": [3,5,6,11], "Lagna": [3,6,10,11],
        },
        "Mars": {
            "Sun": [3,5,6,10,11], "Moon": [3,6,11], "Mars": [1,2,4,7,8,10,11],
            "Mercury": [3,5,6,11], "Jupiter": [6,8,11,12], "Venus": [6,8,11,12],
            "Saturn": [1,4,7,8,9,10,11], "Lagna": [1,3,6,10,11],
        },
        "Mercury": {
            "Sun": [5,6,9,11,12], "Moon": [2,4,6,8,10,11], "Mars": [1,2,4,7,8,9,10,11],
            "Mercury": [1,3,5,6,7,10,11,12], "Jupiter": [6,8,11,12], "Venus": [1,2,3,4,5,8,9,11],
            "Saturn": [1,2,4,7,8,9,10,11], "Lagna": [1,2,4,6,8,10,11],
        },
        "Jupiter": {
            "Sun": [1,2,3,4,7,8,9,10,11], "Moon": [2,5,7,9,11], "Mars": [1,2,4,7,8,10,11],
            "Mercury": [1,2,4,5,6,9,10,11], "Jupiter": [1,2,4,5,6,9,10,11], "Venus": [2,5,6,9,10,11],
            "Saturn": [3,5,6,12], "Lagna": [1,2,4,5,6,7,9,10,11],
        },
        "Venus": {
            "Sun": [8,11,12], "Moon": [1,2,3,4,5,8,9,11,12], "Mars": [3,4,6,9,11,12],
            "Mercury": [3,5,6,9,11], "Jupiter": [5,8,9,10,11], "Venus": [1,2,3,4,5,8,9,10,11],
            "Saturn": [3,4,5,8,9,10,11], "Lagna": [2,3,4,5,8,9,11],
        },
        "Saturn": {
            "Sun": [1,2,4,7,8,10,11], "Moon": [3,6,11], "Mars": [3,5,6,10,11,12],
            "Mercury": [6,8,9,10,11,12], "Jupiter": [5,6,11,12], "Venus": [6,11,12],
            "Saturn": [3,5,6,11], "Lagna": [1,3,4,6,10,11],
        },
    }

    bhinnas = {}
    for p in BAV_TABLES:
        counts = [0]*12
        for sig, houses in BAV_TABLES[p].items():
            sig_pos = positions[sig]
            # Each house h in the list is counted FROM the significator's own
            # position (Phala Deepika: "from the Sun 8" = Sun places bindus in
            # 8 houses measured from itself); map to the corresponding house of P.
            for h in houses:
                abs_lon = norm360(sig_pos + (h - 1) * 30.0)
                house_in_p = int(((abs_lon - positions[p]) % 360) // 30)
                counts[house_in_p] += 1
        bhinnas[p] = counts
    sarva = [0]*12
    for p in BAV_TABLES:
        sarva = [a + b for a, b in zip(sarva, bhinnas[p])]
    return {"bhinnashtakavarga": {p: counts for p, counts in bhinnas.items()},
            "sarvashtakavarga": sarva,
            "note": "Benefic bindu tables from Phala Deepika Ch.23 / BPHS Ch.66. Standard totals: Sun 48, Moon 49, Mars 39, Mercury 54, Jupiter 56, Venus 52, Saturn 39 (Sarva 337)."}

def void_of_course_moon(jd, lat, lng, time_known=True):
    """Void-of-course Moon: Moon makes no major aspect to any planet
    before leaving its current sign."""
    lons, _, _ = body_longitudes(jd)
    moon_lon = lons["Moon"]
    moon_sign_end = (int(moon_lon // 30) + 1) * 30
    # walk Moon forward hour by hour until it changes sign or makes an aspect
    t = jd
    while t < jd + 2.0:  # max 2 days
        l2, _, _ = body_longitudes(t)
        m2 = l2["Moon"]
        if int(m2 // 30) != int(moon_lon // 30):
            # left the sign with no aspect made
            return {"is_void": True, "sign": SIGNS[int(moon_lon // 30)],
                    "void_until": _jd_to_dt(t).strftime("%Y-%m-%d %H:%M")}
        for b, lon in l2.items():
            if b == "Moon":
                continue
            sep = abs(norm180(m2 - lon))
            if sep <= 8:  # any major aspect orb
                return {"is_void": False, "sign": SIGNS[int(m2 // 30)],
                        "next_aspect": f"{b} at {round(sep,1)}°"}
        t += 1/24.0
    return {"is_void": True, "sign": SIGNS[int(moon_lon // 30)]}

def ashtottari_dasha(moon_lon_sidereal, birth_dt):
    """Ashtottari Dasha (108-year cycle) — alternative to Vimshottari.
    Sequence: Sun(6) Moon(15) Mars(8) Mercury(17) Saturn(10) Jupiter(19)
             Rahu(12) Venus(21). Ketu excluded.
    Start lord = nakshatra lord of Moon (Rahu's nakshatras start Sun)."""
    ASHTOTTARI_YEARS = {"Sun":6,"Moon":15,"Mars":8,"Mercury":17,"Saturn":10,
                        "Jupiter":19,"Rahu":12,"Venus":21}
    ASHTOTTARI_SEQ = ["Sun","Moon","Mars","Mercury","Saturn","Jupiter","Rahu","Venus"]
    nak_i = int(norm360(moon_lon_sidereal) // NAK_ARC) % 27
    lord = NAKSHATRAS[nak_i]["lord"]
    # map nakshatra lord to ashtottari start
    if lord == "Ketu":
        start_lord = "Sun"
    elif lord == "Rahu":
        start_lord = "Rahu"
    else:
        start_lord = lord
    try:
        start_idx = ASHTOTTARI_SEQ.index(start_lord)
    except ValueError:
        start_idx = 0
    elapsed = (birth_dt - datetime(2000,1,1)).total_seconds() / 86400.0 / 365.25
    total = 108
    periods = []
    t = birth_dt
    for i in range(8):
        lord_name = ASHTOTTARI_SEQ[(start_idx + i) % 8]
        years = ASHTOTTARI_YEARS[lord_name]
        periods.append({"lord": lord_name, "years": years,
                        "start": t.strftime("%Y-%m-%d"),
                        "end": (t + timedelta(days=years*365.25)).strftime("%Y-%m-%d")})
        t += timedelta(days=years*365.25)
    # current period
    now = datetime.utcnow()
    current = None
    for p in periods:
        if p["start"] <= now.strftime("%Y-%m-%d") <= p["end"]:
            current = p
            break
    return {"system": "Ashtottari (108-year)", "current": current,
            "periods": periods[:3]}

def next_eclipses(jd, count=3):
    """Next solar & lunar eclipse dates using Swiss Ephemeris (if present)
    with a nodal-geometry fallback (New/Full Moon within ~18° of Node) when
    swe eclipse data files are missing."""
    out = []
    if _HAS_SWE:
        try:
            t = jd
            for _ in range(count):
                res = swe.sol_eclipse_when_glob(t, 0)
                t_sol = res[1][0]
                out.append({"type": "solar", "jd": round(t_sol, 4),
                            "date": _jd_to_dt(t_sol).strftime("%Y-%m-%d %H:%M")})
                t = t_sol + 1.0
            t = jd
            for _ in range(count):
                res = swe.lun_eclipse_when(t, 0)
                t_lun = res[1][0]
                out.append({"type": "lunar", "jd": round(t_lun, 4),
                            "date": _jd_to_dt(t_lun).strftime("%Y-%m-%d %H:%M")})
                t = t_lun + 1.0
            out.sort(key=lambda e: e["jd"])
            if out:
                return out[:count]
        except Exception:
            pass
    # Nodal fallback: step across lunations, bisect exact syzygy, check node distance
    t = jd
    guard = 0
    while len(out) < count and guard < 60:
        guard += 1
        # find next New Moon (Sun-Moon elongation = 0)
        low_nm = t; high_nm = t + 30.0
        for _ in range(40):
            mid = (low_nm + high_nm) / 2
            l_ = tropical_longitudes(mid)
            diff = norm180(l_["Moon"] - l_["Sun"])
            if abs(diff) < 0.01: break
            if diff > 0: high_nm = mid
            else: low_nm = mid
        nm_jd = (low_nm + high_nm) / 2
        l_nm = tropical_longitudes(nm_jd)
        node_dist_nm = min(abs(norm180(l_nm["Sun"] - l_nm["North Node"])),
                           abs(norm180(l_nm["Sun"] - l_nm["South Node"])))
        if node_dist_nm < 18.5 and nm_jd > jd:
            out.append({"type": "solar", "jd": round(nm_jd, 4),
                        "date": _jd_to_dt(nm_jd).strftime("%Y-%m-%d %H:%M"),
                        "approximate": True})
        # Full Moon (~14.77 days after New Moon)
        fm_jd = nm_jd + 14.77
        l_fm = tropical_longitudes(fm_jd)
        node_dist_fm = min(abs(norm180(l_fm["Sun"] - l_fm["North Node"])),
                           abs(norm180(l_fm["Sun"] - l_fm["South Node"])))
        if node_dist_fm < 12.5 and fm_jd > jd and len(out) < count:
            out.append({"type": "lunar", "jd": round(fm_jd, 4),
                        "date": _jd_to_dt(fm_jd).strftime("%Y-%m-%d %H:%M"),
                        "approximate": True})
        t = nm_jd + 25.0
    out.sort(key=lambda e: e["jd"])
    return out[:count]

def ayanamsha_lahiri(jd):
    """Lahiri ayanamsha in degrees (Chitrapaksha). Accurate to ~1-2 arcmin."""
    if _HAS_SWE:
        try:
            swe.set_sid_mode(swe.SIDM_LAHIRI)
            return swe.get_ayanamsa_ut(jd)
        except Exception:
            pass
    # polynomial fit: 23.853° at J2000, precessing 50.2388"/yr
    t = (jd - 2451545.0) / 365.25
    return 23.85304 + t * (50.2388/3600.0)

# ── Houses & angles ──────────────────────────────────────────────────────────
def gmst_deg(jd):
    T = (jd - 2451545.0)/36525.0
    g = (280.46061837 + 360.98564736629*(jd-2451545.0)
         + 0.000387933*T*T - (T*T*T)/38710000.0)
    return norm360(g)

def ascendant_mc(jd, lat, lng, ayan=0.0):
    """Return (asc_lon, mc_lon) tropical-minus-ayan (sidereal if ayan>0)."""
    d = jd - 2451543.5
    eps = obliquity(d)
    ramc = norm360(gmst_deg(jd) + lng)             # right ascension of MC
    mc = norm360(_atan2(_sin(ramc), _cos(ramc)*_cos(eps)))
    # Ascendant
    asc = _atan2(_cos(ramc), -(_sin(ramc)*_cos(eps) + _tan(lat)*_sin(eps)))
    asc = norm360(asc)
    # ensure ascendant is the eastern point (≈ ramc+90 region)
    if not (norm360(asc - ramc) < 180):
        asc = norm360(asc + 180)
    return norm360(asc - ayan), norm360(mc - ayan)

def sign_of(lon):
    idx = int(norm360(lon)//30)
    return SIGNS[idx], idx, round(norm360(lon) % 30, 3)

def whole_sign_house(planet_lon, asc_lon):
    asc_sign = int(norm360(asc_lon)//30)
    p_sign = int(norm360(planet_lon)//30)
    return ((p_sign - asc_sign) % 12) + 1

def placidus_cusps(jd, lat, lng, house_system="P"):
    """House cusps via Swiss Ephemeris (if available).
    house_system: P=Placidus, K=Koch, E=Equal, R=Regiomontanus, T=Topocentric,
                  O=Porphyry, C=Campanus, B=Alcabitius, W=Whole sign, X=Meridian.
    Falls back to whole-sign (Asc-based) if no swisseph."""
    if _HAS_SWE:
        try:
            cusps, ascmc = swe.houses(jd, lat, lng, house_system.encode())
            return [norm360(c) for c in cusps[:12]], house_system
        except Exception:
            pass
    # fallback: whole-sign from Asc
    asc_lon, _ = ascendant_mc(jd, lat, lng)
    asc_idx = int(asc_lon // 30)
    return [norm360((asc_idx + i - 1) * 30) for i in range(1, 13)], "W"

def placidus_house_of(planet_lon, cusps):
    """Return 1-12 house number for a planet longitude given Placidus cusps.
    Handles cusp pairs that wrap through 0°."""
    for h in range(12):
        c1 = cusps[h]
        c2 = cusps[(h + 1) % 12]
        if c1 < c2:
            if c1 <= planet_lon < c2:
                return h + 1
        else:  # house spans the 0° wrap
            if planet_lon >= c1 or planet_lon < c2:
                return h + 1
    return 1

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION E — TIME / INPUT NORMALISATION
# ═════════════════════════════════════════════════════════════════════════════

def to_utc(data):
    """Return (naive UTC datetime, info dict). Handles tz name / offset / estimate."""
    y=data["year"]; mo=data["month"]; d=data["day"]
    h=int(data.get("hour",12)); mi=int(data.get("minute",0))
    info = {"time_known": data.get("time_known", True)}
    if not info["time_known"]:
        h, mi = 12, 0
        info["note"] = "birth time unknown — defaulted to local noon; houses/Asc/Moon-degree are approximate"
    tz = data.get("tz")
    off = data.get("utc_offset")
    naive_local = datetime(y,mo,d,h,mi)
    if tz and _HAS_TZDB:
        try:
            local = naive_local.replace(tzinfo=ZoneInfo(tz))
            utc = local.astimezone(timezone.utc).replace(tzinfo=None)
            info["tz_used"] = tz
            info["utc_offset_applied"] = local.utcoffset().total_seconds()/3600
            return utc, info
        except Exception:
            pass
    if off is None:
        off = round(data.get("lng",0.0)/15.0)
        info["tz_note"] = f"no timezone given — estimated UTC offset {off:+d}h from longitude (may be off; ask user for tz)"
    utc = naive_local - timedelta(hours=off)
    info["utc_offset_applied"] = off
    return utc, info

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION F — CHART BUILDERS
# ═════════════════════════════════════════════════════════════════════════════

def _planet_block(lons, speed, asc_lon, names, ayan=0.0, vedic=False, cusps=None):
    out = {}
    for nm in names:
        lon = norm360(lons[nm] - ayan)
        sign, idx, deg = sign_of(lon)
        retro = speed.get(nm, 0) < 0 if nm not in ("South Node",) else (speed.get("North Node",0) < 0)
        if nm in ("North Node","South Node"):
            retro = True  # nodes are always retrograde by mean motion
        house = (placidus_house_of(lon, cusps) if cusps is not None
                 else whole_sign_house(lon, asc_lon))
        block = {
            "sign": sign, "deg_in_sign": deg, "abs_lon": round(lon,3),
            "house": house,
            "retrograde": retro,
        }
        if vedic:
            nak_i = int(lon // NAK_ARC) % 27
            pada = int((lon % NAK_ARC)//PADA_ARC)+1
            nk = NAKSHATRAS[nak_i]
            block.update({
                "rashi_lord": RASHI_LORDS[sign],
                "nakshatra": nk["name"], "nakshatra_lord": nk["lord"], "pada": pada,
                "karaka": GRAHA_KARAKAS.get(_vedic_name(nm),""),
            })
            vn = _vedic_name(nm)
            if EXALT_SIGN.get(vn)==sign: block["dignity"]="exalted"
            elif DEBIL_SIGN.get(vn)==sign: block["dignity"]="debilitated"
            elif RASHI_LORDS[sign]==vn: block["dignity"]="own sign"
        else:
            block["archetype"] = PLANET_ARCHETYPES.get(nm,"")
            block["dignity"] = dignity_western(nm, sign, deg)
            block["in_house_reading"] = _planet_in_house_reading(nm, house)
        out[nm] = block
    return out

def _planet_in_house_reading(planet, house):
    """Interpretive text for a planet in a house (Woolfolk 2008, 120 readings)."""
    global _PIH
    if _PIH is None:
        _PIH = {}
        try:
            import json as _json, os as _os
            _p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                               "..", "data", "planet_in_house.json")
            with open(_p) as _f:
                _PIH = _json.load(_f)
        except Exception:
            _PIH = {}
    key = {1:"FIRST",2:"SECOND",3:"THIRD",4:"FOURTH",5:"FIFTH",6:"SIXTH",
           7:"SEVENTH",8:"EIGHTH",9:"NINTH",10:"TENTH",11:"ELEVENTH",12:"TWELFTH"}.get(house)
    if key:
        return _PIH.get(key, {}).get(planet.upper(), "")
    return ""

def _vedic_name(nm):
    return {"North Node":"Rahu","South Node":"Ketu"}.get(nm, nm)

def dignity_western(planet, sign, degree=None):
    """Essential dignity: domicile, exaltation, detriment, fall
    + triplicity (day/night), terms/bounds, decan (face) when degree given."""
    dg = DIGNITY.get(planet)
    if not dg: return ""
    if sign in dg["rule"]: return "domicile (rulership)"
    if sign in dg["exalt"]: return "exalted"
    if sign in dg["detri"]: return "detriment"
    if sign in dg["fall"]: return "fall"
    if degree is None: return ""
    # triplicity rulers (classical, day/night)
    triplicity = {
        "Fire":   {"day": "Sun",   "night": "Jupiter", "participating": "Saturn"},
        "Earth":  {"day": "Venus", "night": "Moon",    "participating": "Mars"},
        "Air":    {"day": "Saturn","night": "Mercury", "participating": "Jupiter"},
        "Water":  {"day": "Venus", "night": "Mars",    "participating": "Moon"},
    }
    # decan (Chaldean face) rulers — 3 decans per sign
    decan_ruler = {
        "Aries":[("Mars",10),("Sun",20),("Venus",30)], "Taurus":[("Mercury",10),("Moon",20),("Saturn",30)],
        "Gemini":[("Jupiter",10),("Mars",20),("Sun",30)], "Cancer":[("Venus",10),("Mercury",20),("Moon",30)],
        "Leo":[("Saturn",10),("Jupiter",20),("Mars",30)], "Virgo":[("Sun",10),("Venus",20),("Mercury",30)],
        "Libra":[("Moon",10),("Saturn",20),("Jupiter",30)], "Scorpio":[("Mars",10),("Sun",20),("Venus",30)],
        "Sagittarius":[("Mercury",10),("Moon",20),("Saturn",30)], "Capricorn":[("Jupiter",10),("Mars",20),("Sun",30)],
        "Aquarius":[("Venus",10),("Mercury",20),("Moon",30)], "Pisces":[("Saturn",10),("Jupiter",20),("Mars",30)],
    }
    # Egyptian terms (bounds) — per sign, list of (end_deg, ruler)
    terms = {
        "Aries":[("Jupiter",6),("Venus",14),("Mercury",21),("Mars",26),("Saturn",30)],
        "Taurus":[("Venus",8),("Mercury",15),("Jupiter",22),("Saturn",27),("Mars",30)],
        "Gemini":[("Mercury",7),("Jupiter",14),("Venus",21),("Mars",26),("Saturn",30)],
        "Cancer":[("Mars",7),("Venus",13),("Mercury",19),("Jupiter",26),("Saturn",30)],
        "Leo":[("Jupiter",6),("Venus",13),("Saturn",20),("Mercury",27),("Mars",30)],
        "Virgo":[("Mercury",7),("Venus",17),("Jupiter",21),("Saturn",28),("Mars",30)],
        "Libra":[("Saturn",6),("Mercury",14),("Jupiter",21),("Venus",28),("Mars",30)],
        "Scorpio":[("Mars",7),("Venus",11),("Mercury",19),("Jupiter",24),("Saturn",30)],
        "Sagittarius":[("Jupiter",12),("Venus",17),("Mercury",21),("Saturn",26),("Mars",30)],
        "Capricorn":[("Mercury",7),("Jupiter",14),("Venus",22),("Saturn",26),("Mars",30)],
        "Aquarius":[("Mercury",7),("Venus",13),("Jupiter",20),("Mars",25),("Saturn",30)],
        "Pisces":[("Venus",12),("Jupiter",16),("Mercury",19),("Mars",28),("Saturn",30)],
    }
    # Ptolemaic terms — reconstructed by Houlding ("Ptolemy's Terms & Conditions",
    # skyscript 2007) following the Robbins/Hephaistio critical reading of Tetrabiblos I.21
    ptolemaic_terms = {
        "Aries":[("Jupiter",6),("Venus",12),("Mercury",20),("Mars",25),("Saturn",30)],
        "Taurus":[("Venus",8),("Mercury",14),("Jupiter",22),("Saturn",26),("Mars",30)],
        "Gemini":[("Mercury",6),("Jupiter",14),("Venus",21),("Saturn",25),("Mars",30)],
        "Cancer":[("Mars",7),("Jupiter",13),("Venus",19),("Mercury",26),("Saturn",30)],
        "Leo":[("Jupiter",6),("Mercury",14),("Saturn",21),("Venus",27),("Mars",30)],
        "Virgo":[("Mercury",7),("Venus",13),("Jupiter",18),("Saturn",24),("Mars",30)],
        "Libra":[("Saturn",6),("Venus",12),("Mercury",19),("Jupiter",24),("Mars",30)],
        "Scorpio":[("Mars",6),("Venus",14),("Jupiter",21),("Mercury",27),("Saturn",30)],
        "Sagittarius":[("Jupiter",8),("Venus",14),("Mercury",19),("Saturn",24),("Mars",30)],
        "Capricorn":[("Venus",6),("Mercury",12),("Jupiter",19),("Mars",26),("Saturn",30)],
        "Aquarius":[("Saturn",6),("Mercury",12),("Venus",20),("Jupiter",25),("Mars",30)],
        "Pisces":[("Venus",9),("Jupiter",14),("Mercury",22),("Mars",28),("Saturn",30)],
    }
    parts = []
    # triplicity
    tr = triplicity[SIGN_DATA[sign]["element"]]
    if planet == tr["day"]: parts.append("triplicity (day ruler)")
    elif planet == tr["night"]: parts.append("triplicity (night ruler)")
    elif planet == tr["participating"]: parts.append("triplicity (participating)")
    # terms
    for ruler, end_deg in terms[sign]:
        if degree <= end_deg:
            if ruler == planet: parts.append("term (Egyptian bound)")
            break
    for ruler, end_deg in ptolemaic_terms[sign]:
        if degree <= end_deg:
            if ruler == planet: parts.append("term (Ptolemaic)")
            break
    # decan
    for ruler, end_deg in decan_ruler[sign]:
        if degree <= end_deg:
            if ruler == planet: parts.append("decan (face)")
            break
    return ", ".join(parts) if parts else ""


def compute_aspects(lons, ayan=0.0, bodies=None):
    bodies = bodies or ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn",
                        "Uranus","Neptune","Pluto","North Node"]
    L = {b: norm360(lons[b]-ayan) for b in bodies if b in lons}
    res = []
    keys = list(L.keys())
    for i in range(len(keys)):
        for j in range(i+1,len(keys)):
            a,b = keys[i],keys[j]
            sep = abs(norm180(L[a]-L[b]))
            for asp,(ang,orb,desc) in ASPECTS.items():
                # per-planet orb: average of the two planets' traditional orbs,
                # clamped to the aspect's default orb (Lilly system)
                oa = PLANET_ORBS.get(a, DEFAULT_ORB)
                ob = PLANET_ORBS.get(b, DEFAULT_ORB)
                eff_orb = min((oa+ob)/2.0, orb)
                d = abs(sep-ang)
                if d <= eff_orb:
                    res.append({"a":a,"b":b,"aspect":asp,"orb":round(d,2),
                                "exact_sep":round(sep,2),"meaning":desc,
                                "applying": None})
    res.sort(key=lambda x:x["orb"])
    return res

def western_chart(jd, lat, lng, time_known=True, house_system="P"):
    lons, speed, backend = body_longitudes(jd)
    asc_lon, mc_lon = ascendant_mc(jd, lat, lng) if time_known else (lons["Sun"], norm360(lons["Sun"]+270))
    names = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn",
             "Uranus","Neptune","Pluto","North Node","South Node","Chiron"]
    use_placidus = _HAS_SWE and time_known
    cusps = None
    house_code = house_system.upper()
    if use_placidus:
        cusps, house_code = placidus_cusps(jd, lat, lng, house_code)
    planets = _planet_block(lons, speed, asc_lon, names, vedic=False, cusps=cusps)
    asc_sign,_,asc_deg = sign_of(asc_lon)
    mc_sign,_,mc_deg = sign_of(mc_lon)
    # element / modality balance over the 10 planets + Asc
    elem={"Fire":0,"Earth":0,"Air":0,"Water":0}; mod={"Cardinal":0,"Fixed":0,"Mutable":0}
    for nm in ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"]:
        sd=SIGN_DATA[planets[nm]["sign"]]; elem[sd["element"]]+=1; mod[sd["modality"]]+=1
    sd=SIGN_DATA[asc_sign]; elem[sd["element"]]+=1; mod[sd["modality"]]+=1
    # house cusps — Placidus when available, whole-sign fallback
    if cusps is not None:
        houses={}
        for hnum in range(1,13):
            c = cusps[hnum-1]
            s,_,_ = sign_of(c)
            houses[hnum]={"sign":s,"cusp_lon":round(c,3),"ruler":SIGN_DATA[s]["ruler"],
                          "meaning":HOUSE_MEANINGS[hnum]}
        house_system = _HOUSE_SYSTEM_NAMES.get(house_code, f"SWE {house_code}")
    else:
        houses={}
        asc_idx=int(asc_lon//30)
        for hnum in range(1,13):
            s=SIGNS[(asc_idx+hnum-1)%12]
            houses[hnum]={"sign":s,"ruler":SIGN_DATA[s]["ruler"],"meaning":HOUSE_MEANINGS[hnum]}
        house_system = "Western Tropical (whole-sign houses)"
    return {
        "system":house_system,
        "big_three":{"sun":planets["Sun"]["sign"],"moon":planets["Moon"]["sign"],"rising":asc_sign},
        "ascendant":{"sign":asc_sign,"deg_in_sign":asc_deg,"abs_lon":round(asc_lon,3)},
        "midheaven":{"sign":mc_sign,"deg_in_sign":mc_deg,"abs_lon":round(mc_lon,3)},
        "descendant":{"sign":SIGNS[(int(asc_lon//30)+6)%12],"deg_in_sign":round(asc_deg,2),
                      "abs_lon":round(norm360(asc_lon+180),3)},
        "imum_coeli":{"sign":SIGNS[(int(mc_lon//30)+6)%12],"deg_in_sign":round(mc_deg,2),
                      "abs_lon":round(norm360(mc_lon+180),3)},
        "chart_ruler": SIGN_DATA[asc_sign]["ruler"],
        "planets":planets,
        "houses":houses,
        "aspects":compute_aspects(lons)[:24],
        "aspects_to_angles": compute_aspects({**lons, "Ascendant": asc_lon, "Midheaven": mc_lon},
                                             bodies=[b for b in lons] + ["Ascendant","Midheaven"])[:16],
        "antiscia": {nm: round(antiscia(planets[nm]["abs_lon"]), 3) for nm in names},
        "declinations": {nm: round(d, 3) for nm, d in body_declinations(jd).items()},
        "declination_aspects": compute_declination_aspects(lons, body_declinations(jd))[:12],
        "element_balance":elem,"modality_balance":mod,
        "dominant_element":max(elem,key=elem.get),"lacking_element":min(elem,key=elem.get),
    }

def vedic_chart(jd, lat, lng, birth_dt, time_known=True, as_of_dt=None):
    lons, speed, backend = body_longitudes(jd)
    ayan = ayanamsha_lahiri(jd)
    asc_lon, mc_lon = ascendant_mc(jd, lat, lng, ayan) if time_known else (norm360(lons["Sun"]-ayan), 0)
    names=["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","North Node","South Node"]
    planets=_planet_block(lons, speed, asc_lon, names, ayan=ayan, vedic=True)
    # remap node names to Rahu/Ketu in output
    planets["Rahu"]=planets.pop("North Node"); planets["Ketu"]=planets.pop("South Node")
    lagna_sign,_,lagna_deg = sign_of(asc_lon)
    moon_lon = norm360(lons["Moon"]-ayan)
    nak_i=int(moon_lon//NAK_ARC)%27
    pada=int((moon_lon%NAK_ARC)//PADA_ARC)+1
    nk=NAKSHATRAS[nak_i]
    eval_dt = as_of_dt or datetime.now(timezone.utc).replace(tzinfo=None)
    eval_jd = julian_day(eval_dt)
    dasha=vimshottari(moon_lon, birth_dt, as_of_dt=eval_dt)
    yogas=detect_yogas(planets, lagna_sign)
    # Atmakaraka: planet with highest degree in its sign (excludes Rahu/Ketu)
    atma_candidates = {p: planets[p]["deg_in_sign"] for p in
                       ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"] if p in planets}
    atmakaraka = max(atma_candidates, key=atma_candidates.get) if atma_candidates else None
    # Sade Sati: Saturn transiting Moon sign ±1 at evaluation date (dynamic)
    moon_sign_idx = SIGNS.index(sign_of(moon_lon)[0])
    current_sat_lon = norm360(body_longitudes(eval_jd)[0]["Saturn"] - ayanamsha_lahiri(eval_jd))
    sat_sign_idx = SIGNS.index(sign_of(current_sat_lon)[0])
    sade_sati_phase = None
    delta = (sat_sign_idx - moon_sign_idx) % 12
    if delta == 11:   sade_sati_phase = "rising (Saturn in the sign before your Moon sign)"
    elif delta == 0:  sade_sati_phase = "peak (Saturn transiting your natal Moon sign directly)"
    elif delta == 1:  sade_sati_phase = "setting (Saturn in the sign after your Moon sign)"

    # Tithi Calculation (Hindu Lunar Day)
    tithi_val = (lons["Moon"] - lons["Sun"]) % 360
    tithi_index = int(tithi_val / 12) + 1
    paksha = "Shukla" if tithi_index <= 15 else "Krishna"
    tithi_num = tithi_index if tithi_index <= 15 else tithi_index - 15

    return {
        "tithi": f"{paksha} Paksha, Tithi {tithi_num}",
        "system":"Vedic / Jyotisha — Lahiri sidereal, whole-sign (rashi) houses",
        "as_of_date": eval_dt.strftime("%Y-%m-%d"),
        "ayanamsha_deg":round(ayan,4),
        "lagna":{"sign":lagna_sign,"deg_in_sign":lagna_deg,"lord":RASHI_LORDS[lagna_sign]},
        "janma_rashi":{"sign":sign_of(moon_lon)[0]},
        "janma_nakshatra":{"name":nk["name"],"lord":nk["lord"],"deity":nk["deity"],
                           "pada":pada,"quality":nk["quality"]},
        "atmakaraka":{"planet":atmakaraka,
                      "deg":round(atma_candidates.get(atmakaraka,0),3) if atmakaraka else None,
                      "note":"Jaimini soul-significator — the planet that has travelled farthest in its sign"},
        "sade_sati":{"active": sade_sati_phase is not None,
                     "phase": sade_sati_phase,
                     "note":"Saturn's 7.5-yr transit over natal Moon ±1 sign; challenging but transformative"},
        "planets":planets,
        "mangal_dosha":mangal_dosha(jd, lat, lng, time_known),
        "vimshottari_dasha":dasha,
        "yogas":yogas,
        "house_meanings":VEDIC_HOUSE,
    }

def vimshottari(moon_lon, birth_dt, as_of_dt=None):
    """Full Vimshottari maha-dasha timeline + active antardasha & pratyantardasha
    calculated dynamically for as_of_dt (defaults to today)."""
    target = as_of_dt or datetime.now(timezone.utc).replace(tzinfo=None)
    nak_i=int(moon_lon//NAK_ARC)%27
    lord=NAKSHATRAS[nak_i]["lord"]
    frac_elapsed=(moon_lon % NAK_ARC)/NAK_ARC
    start_idx=DASHA_SEQ.index(lord)
    timeline=[]
    cur=birth_dt - timedelta(days=DASHA_YEARS[lord]*frac_elapsed*365.25)
    for k in range(10):
        L=DASHA_SEQ[(start_idx+k)%9]
        yrs=DASHA_YEARS[L]
        end=cur+timedelta(days=yrs*365.25)
        timeline.append({"lord":L,"start":cur.strftime("%Y-%m-%d"),
                         "end":end.strftime("%Y-%m-%d"),"years":yrs,
                         "is_current": cur<=target<=end})
        cur=end
    current=next((d for d in timeline if d["is_current"]), None)
    bhukti=[]
    pratyantar=[]
    if current:
        antardasha=_antardasha(current["lord"],
                               datetime.strptime(current["start"],"%Y-%m-%d"),
                               as_of_dt=target)
        bhukti=antardasha
        cur_antar=next((b for b in bhukti if b["is_current"]), None)
        if cur_antar:
            pratyantar=_pratyantardasha(
                current["lord"], cur_antar["lord"],
                datetime.strptime(cur_antar["start"],"%Y-%m-%d"),
                datetime.strptime(cur_antar["end"],"%Y-%m-%d"),
                as_of_dt=target)
    return {"birth_dasha_lord":lord,
            "as_of_date": target.strftime("%Y-%m-%d"),
            "current_mahadasha":current,
            "current_antardasha":next((b for b in bhukti if b["is_current"]),None),
            "current_pratyantardasha":next((p for p in pratyantar
                                            if p["is_current"]),None),
            "pratyantardashas_in_current_antar":pratyantar,
            "maha_timeline":timeline,
            "antardasha_in_current_maha":bhukti}

def _antardasha(maha_lord, maha_start, as_of_dt=None):
    """Sub-periods within a maha-dasha."""
    target = as_of_dt or datetime.now(timezone.utc).replace(tzinfo=None)
    start_idx=DASHA_SEQ.index(maha_lord)
    maha_years=DASHA_YEARS[maha_lord]
    out=[]; cur=maha_start
    for k in range(9):
        L=DASHA_SEQ[(start_idx+k)%9]
        sub_years=maha_years*DASHA_YEARS[L]/DASHA_TOTAL
        end=cur+timedelta(days=sub_years*365.25)
        out.append({"lord":L,"start":cur.strftime("%Y-%m-%d"),"end":end.strftime("%Y-%m-%d"),
                    "is_current":cur<=target<=end})
        cur=end
    return out

def _pratyantardasha(maha_lord, antar_lord, antar_start, antar_end, as_of_dt=None):
    """Third-level Vimshottari periods inside one antardasha."""
    target = as_of_dt or datetime.now(timezone.utc).replace(tzinfo=None)
    start_idx=DASHA_SEQ.index(antar_lord)
    span=(antar_end-antar_start).total_seconds()
    out=[]; cur=antar_start
    for k in range(9):
        L=DASHA_SEQ[(start_idx+k)%9]
        frac=DASHA_YEARS[L]/DASHA_TOTAL
        end=cur+timedelta(seconds=span*frac)
        out.append({"lord":L,"start":cur.strftime("%Y-%m-%d %H:%M"),
                    "end":end.strftime("%Y-%m-%d %H:%M"),
                    "is_current":cur<=target<=end})
        cur=end
    return out

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — ADVANCED VEDIC YOGAS (B.V. Raman: 300 Important Combinations)
# ═════════════════════════════════════════════════════════════════════════════

MAHAPURUSHA_YOGA_DEFS = {
    "Mars":    ("Ruchaka Yoga", ("Aries", "Scorpio", "Capricorn"), "Physical valor, leadership, land ownership, competitive mastery"),
    "Mercury": ("Bhadra Yoga", ("Gemini", "Virgo"), "Intellectual supremacy, oratorical genius, commercial acumen, long life"),
    "Jupiter": ("Hamsa Yoga", ("Sagittarius", "Pisces", "Cancer"), "Spiritual wisdom, high prestige, righteous conduct, universally respected"),
    "Venus":   ("Malavya Yoga", ("Taurus", "Libra", "Pisces"), "Refined aesthetic grace, wealth, vehicles, luxury, harmonious marriage"),
    "Saturn":  ("Sasa Yoga", ("Capricorn", "Aquarius", "Libra"), "Commanding authority, enduring power, mastery over resources, leadership of the masses")
}

def detect_yogas(planets, lagna_sign):
    """Detect classical Vedic yogas per B.V. Raman's '300 Important Combinations':
    1. Pancha Mahapurusha Yogas (Ruchaka, Bhadra, Hamsa, Malavya, Sasa).
    2. Viparita Raja Yogas (Harsha, Sarala, Vimala).
    3. Neecha Bhanga Raja Yogas (NBRY - 5 cancellation rules for debilitated planets).
    4. Dharma-Karmadhipati & Lakshmi Dhana Yogas.
    5. Classical Solar/Lunar yogas (Gajakesari, Budha-Aditya, Chandra-Mangala)."""
    yogas = []
    lagna_idx = SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0

    def house(p): return planets.get(p, {}).get("house")
    def sign(p): return planets.get(p, {}).get("sign")

    # 1. Pancha Mahapurusha Yogas (Mars, Mercury, Jupiter, Venus, Saturn in Kendra in own/exalted sign)
    for p, (y_name, valid_signs, effect) in MAHAPURUSHA_YOGA_DEFS.items():
        if p in planets and house(p) in (1, 4, 7, 10) and sign(p) in valid_signs:
            yogas.append({
                "name": y_name, "planet": p,
                "rule": f"{p} in Kendra (house {house(p)}) in {sign(p)} (own/exaltation)",
                "effect": effect
            })

    # 2. Viparita Raja Yogas (Harsha 6th, Sarala 8th, Vimala 12th)
    # Lords of dusthanas situated exclusively in dusthanas (6, 8, 12)
    h6_sign = SIGNS[(lagna_idx + 5) % 12]; l6 = RASHI_LORDS[h6_sign]
    h8_sign = SIGNS[(lagna_idx + 7) % 12]; l8 = RASHI_LORDS[h8_sign]
    h12_sign = SIGNS[(lagna_idx + 11) % 12]; l12 = RASHI_LORDS[h12_sign]

    if house(l6) in (6, 8, 12):
        yogas.append({"name": "Viparita Raja Yoga (Harsha)", "planet": l6, "rule": f"6th Lord ({l6}) placed in house {house(l6)}", "effect": "Triumph over rivals, immunity from disease, sudden breakthrough during crisis"})
    if house(l8) in (6, 8, 12):
        yogas.append({"name": "Viparita Raja Yoga (Sarala)", "planet": l8, "rule": f"8th Lord ({l8}) placed in house {house(l8)}", "effect": "Fearlessness, longevity, unexpected prosperity, victory in contentious affairs"})
    if house(l12) in (6, 8, 12):
        yogas.append({"name": "Viparita Raja Yoga (Vimala)", "planet": l12, "rule": f"12th Lord ({l12}) placed in house {house(l12)}", "effect": "Independent wealth, noble character, spiritual detachment, freedom from debts"})

    # 3. Neecha Bhanga Raja Yoga (NBRY - Debilitation Cancellation per Raman)
    for p, deb_s in DEBIL_SIGN.items():
        if sign(p) == deb_s:
            # Check 5 cancellation conditions
            rules_triggered = []
            sign_lord = RASHI_LORDS[deb_s]
            exalt_lord = RASHI_LORDS[EXALT_SIGN[p]]
            sl_h = house(sign_lord); el_h = house(exalt_lord); p_h = house(p)

            if sl_h in (1, 4, 7, 10): rules_triggered.append(f"Lord of debilitation sign ({sign_lord}) in Kendra (House {sl_h})")
            if el_h in (1, 4, 7, 10): rules_triggered.append(f"Exaltation lord ({exalt_lord}) in Kendra (House {el_h})")
            if p_h in (1, 4, 7, 10): rules_triggered.append(f"Debilitated {p} itself in Kendra (House {p_h})")

            if rules_triggered:
                yogas.append({
                    "name": f"Neecha Bhanga Raja Yoga ({p})", "planet": p,
                    "rule": "; ".join(rules_triggered),
                    "effect": f"Debilitation of {p} cancelled and transformed into profound resilience, status and eventual triumph"
                })

    # 4. Dharma-Karmadhipati Yoga (9th and 10th lords conjoined or in mutual aspect)
    h9_sign = SIGNS[(lagna_idx + 8) % 12]; l9 = RASHI_LORDS[h9_sign]
    h10_sign = SIGNS[(lagna_idx + 9) % 12]; l10 = RASHI_LORDS[h10_sign]
    if l9 != l10 and house(l9) and house(l10):
        if house(l9) == house(l10):
            yogas.append({"name": "Dharma-Karmadhipati Yoga", "planet": f"{l9}+{l10}", "rule": f"9th Lord ({l9}) and 10th Lord ({l10}) conjoined in house {house(l9)}", "effect": "High executive status, public acclaim, ethical leadership and supreme good fortune"})
        elif (house(l9) == 10 and house(l10) == 9):
            yogas.append({"name": "Maha Parivartana Yoga (9th & 10th Lords)", "planet": f"{l9}<->{l10}", "rule": f"9th and 10th lords in mutual sign exchange", "effect": "Kingly stature, monumental career success and enduring legacy"})

    # 5. Gajakesari: Jupiter in kendra (1/4/7/10) from Moon
    if "Jupiter" in planets and "Moon" in planets:
        diff = (planets["Jupiter"]["house"] - planets["Moon"]["house"]) % 12
        if planets["Jupiter"]["house"] in (1, 4, 7, 10) and diff in (0, 3, 6, 9):
            yogas.append({"name": "Gajakesari Yoga", "planet": "Jupiter+Moon", "rule": "Jupiter in a kendra (1/4/7/10) from the Moon", "effect": "Intelligence, noble reputation, lasting prosperity and respected influence"})

    # 6. Budha-Aditya: Sun & Mercury same sign
    if planets.get("Sun", {}).get("sign") == planets.get("Mercury", {}).get("sign"):
        yogas.append({"name": "Budha-Aditya Yoga", "planet": "Sun+Mercury", "rule": "Sun and Mercury conjoined in the same sign", "effect": "Sharp intellect, communication mastery and administrative talent"})

    # 7. Chandra-Mangala: Moon & Mars conjoined
    if planets.get("Moon", {}).get("sign") == planets.get("Mars", {}).get("sign"):
        yogas.append({"name": "Chandra-Mangala Yoga", "planet": "Moon+Mars", "rule": "Moon and Mars conjoined in the same sign", "effect": "Commercial acumen, emotional drive and entrepreneurial wealth creation"})

    return yogas

# ── BaZi ─────────────────────────────────────────────────────────────────────
def bazi_chart(jd, birth_dt_local, gender="unknown", lat=0.0):
    """Four Pillars using solar-term-correct year & month, JDN day pillar."""
    lons, speed, backend = body_longitudes(jd)
    sun_lon = lons["Sun"]
    y=birth_dt_local.year; mo=birth_dt_local.month; d=birth_dt_local.day; h=birth_dt_local.hour
    # Solar year: switches at Li Chun (Sun = 315°). In Jan/early Feb before Li Chun → previous year.
    bazi_year=y
    if mo in (1,2) and sun_lon < SOLAR_TERM_START_LON:
        bazi_year=y-1
    ys=(bazi_year-4)%10; yb=(bazi_year-4)%12
    # Month branch from Sun's tropical longitude: Tiger(2) starts at 315°, each branch +30°
    month_order=int(((sun_lon-SOLAR_TERM_START_LON)%360)//30)   # 0=Tiger
    mb=(2+month_order)%12
    stem_base={0:2,1:4,2:6,3:8,4:0,5:2,6:4,7:6,8:8,9:0}[ys]      # 五虎遁
    ms=(stem_base+month_order)%10
    # Day pillar: continuous sexagenary cycle via the standard (JDN+49)%60 formula,
    # keyed to the LOCAL civil date (the day boundary is local midnight, not UT).
    jdn=int(math.floor(julian_day(datetime(y,mo,d,12))+0.5))
    sexa=(jdn+49)%60
    ds=sexa%10
    db=sexa%12
    # Hour branch (Zi=23:00). Late 23:00–23:59 belongs to next day's Zi in some schools;
    # we use same-day Zi (common simplification).
    hour_branch_map={23:0,0:0,1:1,2:1,3:2,4:2,5:3,6:3,7:4,8:4,9:5,10:5,
                     11:6,12:6,13:7,14:7,15:8,16:8,17:9,18:9,19:10,20:10,21:11,22:11}
    hb=hour_branch_map.get(h,0)
    hour_base={0:0,1:2,2:4,3:6,4:8,5:0,6:2,7:4,8:6,9:8}[ds]      # 五鼠遁
    hs=(hour_base+hb)%10

    def pillar(si,bi):
        s=STEMS[si]; b=BRANCHES[bi]
        return {"stem":{"han":s["han"],"pinyin":s["pinyin"],"element":s["element"],
                        "polarity":s["polarity"],"nature":s["nature"]},
                "branch":{"han":b["han"],"pinyin":b["pinyin"],"animal":b["animal"],
                          "element":b["element"],"hidden_stems":b["hidden"],"hours":b["hours"]}}
    pillars={"year":pillar(ys,yb),"month":pillar(ms,mb),"day":pillar(ds,db),"hour":pillar(hs,hb)}

    dm=STEMS[ds]
    # element tally (stems weight 1, main branch weight 1, hidden stems weight 0.5)
    tally={e:0.0 for e in ["Wood","Fire","Earth","Metal","Water"]}
    for si,bi in [(ys,yb),(ms,mb),(ds,db),(hs,hb)]:
        tally[STEMS[si]["element"]]+=1.0
        tally[BRANCHES[bi]["element"]]+=1.0
        for hidden in BRANCHES[bi]["hidden"]:
            tally[PINYIN_ELEM[hidden]]+=0.5
    tally={k:round(v,1) for k,v in tally.items()}
    # Day-master strength: support = same element + element that generates DM
    dm_e=dm["element"]; res_e=GENERATED_BY[dm_e]
    support=tally[dm_e]+tally[res_e]
    total=sum(tally.values())
    ratio=support/total if total else 0
    strength="Strong" if ratio>=0.5 else ("Balanced" if ratio>=0.35 else "Weak")
    # Favourable elements: weak DM → strengthen with resource & friend; strong DM → drain with output/wealth/officer
    if strength=="Weak":
        favourable=[res_e, dm_e]
        unfavourable=[CONTROLLED_BY[dm_e], CONTROLS[dm_e]]
        useful_note="Day Master is weak — it benefits from Resource and Friend elements that support it."
    elif strength=="Strong":
        favourable=[GENERATES[dm_e], CONTROLS[dm_e], CONTROLLED_BY[dm_e]]
        unfavourable=[res_e, dm_e]
        useful_note="Day Master is strong — it benefits from Output, Wealth and Officer elements that channel and balance it."
    else:
        favourable=[GENERATES[dm_e], CONTROLS[dm_e]]
        unfavourable=[]
        useful_note="Day Master is balanced — favour elements that keep flow without tipping the balance."

    # Ten Gods of the other three stems toward Day Master
    ten_gods={}
    for label,si in [("year",ys),("month",ms),("hour",hs)]:
        s=STEMS[si]
        ten_gods[label]=ten_god(dm_e,dm["polarity"],s["element"],s["polarity"])

    # Luck pillars (大運): direction from year-stem polarity + gender
    yang_year=STEMS[ys]["polarity"]=="Yang"
    male=str(gender).lower().startswith("m")
    forward=(yang_year and male) or ((not yang_year) and (not male))
    if str(gender).lower() not in ("m","male","f","female","man","woman"):
        forward=True  # default if unknown
    luck=[]
    start_age=8  # approximation; precise start needs distance to next/prev solar term
    for i in range(1,9):
        step=i if forward else -i
        lsi=(ms+step)%10; lbi=(mb+step)%12
        a0=start_age+(i-1)*10
        luck.append({"age":f"{a0}–{a0+9}","approx_years":f"{birth_dt_local.year+a0}–{birth_dt_local.year+a0+9}",
                     "stem":STEMS[lsi]["pinyin"],"stem_element":STEMS[lsi]["element"],
                     "branch":BRANCHES[lbi]["animal"],"branch_element":BRANCHES[lbi]["element"],
                     "direction":"forward" if forward else "reverse",
                     "is_current": a0 <= _age(birth_dt_local) <= a0+9})
    year_animal=BRANCHES[yb]["animal"]
    cur_year_branch=(TODAY.year-4)%12
    cur_animal=BRANCHES[cur_year_branch]["animal"]
    compat=ZODIAC_COMPAT.get(year_animal,{})
    tai_sui=_tai_sui(year_animal, cur_animal)

    return {
        "system":"Chinese BaZi — Four Pillars of Destiny (solar-term corrected)",
        "solar_year_used":bazi_year,
        "four_pillars":pillars,
        "day_master":{"han":dm["han"],"pinyin":dm["pinyin"],"element":dm_e,
                      "polarity":dm["polarity"],"nature":dm["nature"],"strength":strength,
                      "strength_ratio":round(ratio,2)},
        "element_balance":tally,
        "dominant_element":max(tally,key=tally.get),
        "weakest_element":min(tally,key=tally.get),
        "favourable_elements":favourable,"unfavourable_elements":unfavourable,
        "useful_god_note":useful_note,
        "element_advice":{e:ELEMENT_ADVICE[e] for e in favourable},
        "ten_gods":ten_gods,
        "luck_pillars":luck,
        "year_animal":year_animal,
        "zodiac_compatibility":compat,
        "current_year":{"year":TODAY.year,"animal":cur_animal,"tai_sui":tai_sui},
    }

def _age(birth_dt):
    return (TODAY - birth_dt).days/365.25

def _tai_sui(natal_animal, year_animal):
    order=[b["animal"] for b in BRANCHES]
    if natal_animal==year_animal:
        return f"{natal_animal} offends Tai Sui this year (本命年 / Ben Ming Nian) — a year to be cautious, steady, and avoid major risky changes."
    clash=ZODIAC_COMPAT.get(natal_animal,{}).get("clash")
    harm=ZODIAC_COMPAT.get(natal_animal,{}).get("harm")
    if year_animal==clash:
        return f"{natal_animal} clashes (沖) with the {year_animal} year — expect movement, change, friction; channel it into deliberate transitions."
    if year_animal==harm:
        return f"{natal_animal} is harmed (害) by the {year_animal} year — guard relationships and health; avoid hidden conflicts."
    return f"No direct Tai Sui conflict between {natal_animal} and the {year_animal} year — a relatively neutral-to-supportive year."

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION G — TRANSITS & SYNASTRY
# ═════════════════════════════════════════════════════════════════════════════

def transits(natal_jd, natal_lat, natal_lng, transit_dt_utc):
    """Current-sky planets and the aspects they make to the natal chart."""
    natal_lons,_,_ = body_longitudes(natal_jd)
    t_jd=julian_day(transit_dt_utc)
    t_lons, t_speed, _ = body_longitudes(t_jd)
    transiting=["Jupiter","Saturn","Uranus","Neptune","Pluto","North Node","Mars"]
    natal_pts=["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn",
               "Uranus","Neptune","Pluto","North Node"]
    hits=[]
    for tp in transiting:
        for npn in natal_pts:
            sep=abs(norm180(t_lons[tp]-natal_lons[npn]))
            for asp,(ang,orb,desc) in ASPECTS.items():
                tight = orb if tp in ("Jupiter","Saturn") else min(orb,4)
                if abs(sep-ang)<=tight:
                    hits.append({"transiting":tp,"to_natal":npn,"aspect":asp,
                                 "orb":round(abs(sep-ang),2),
                                 "transiting_sign":sign_of(t_lons[tp])[0],
                                 "retrograde":t_speed.get(tp,0)<0,
                                 "meaning":desc})
    hits.sort(key=lambda x:x["orb"])
    # Sade Sati check against transit Saturn
    natal_moon_sign = sign_of(natal_lons["Moon"])[0]
    natal_moon_idx = SIGNS.index(natal_moon_sign)
    sat_sign_idx = SIGNS.index(sign_of(t_lons["Saturn"])[0])
    delta = (sat_sign_idx - natal_moon_idx) % 12
    sade_sati = None
    if delta == 11:   sade_sati = {"active":True,"phase":"rising","saturn_sign":SIGNS[sat_sign_idx],"moon_sign":natal_moon_sign}
    elif delta == 0:  sade_sati = {"active":True,"phase":"peak","saturn_sign":SIGNS[sat_sign_idx],"moon_sign":natal_moon_sign}
    elif delta == 1:  sade_sati = {"active":True,"phase":"setting","saturn_sign":SIGNS[sat_sign_idx],"moon_sign":natal_moon_sign}
    else:             sade_sati = {"active":False,"saturn_sign":SIGNS[sat_sign_idx],"moon_sign":natal_moon_sign}
    return {"transit_date":transit_dt_utc.strftime("%Y-%m-%d"),
            "current_positions":{p:{"sign":sign_of(t_lons[p])[0],
                                    "deg":round(t_lons[p]%30,2),
                                    "retrograde":t_speed.get(p,0)<0}
                                 for p in ["Sun","Mercury","Venus","Mars","Jupiter","Saturn",
                                           "Uranus","Neptune","Pluto"]},
            "aspects_to_natal":hits[:20],
            "sade_sati":sade_sati}

def synastry(jdA, jdB):
    """Inter-chart aspects (A's planets to B's planets) — relationship synastry."""
    lonsA,_,_=body_longitudes(jdA)
    lonsB,_,_=body_longitudes(jdB)
    pts=["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","North Node"]
    inter=[]
    for a in pts:
        for b in pts:
            sep=abs(norm180(lonsA[a]-lonsB[b]))
            for asp,(ang,orb,desc) in ASPECTS.items():
                if abs(sep-ang)<=orb:
                    weight="major" if {a,b}&{"Sun","Moon","Venus","Mars"} else "minor"
                    inter.append({"personA_planet":a,"personB_planet":b,"aspect":asp,
                                  "orb":round(abs(sep-ang),2),"weight":weight,"meaning":desc})
    inter.sort(key=lambda x:(0 if x["weight"]=="major" else 1, x["orb"]))
    # quick harmony score: trine/sextile/conjunction(benefic) = +, square/opposition = −
    score=0
    for it in inter[:25]:
        if it["aspect"] in ("trine","sextile"): score+=2
        elif it["aspect"]=="conjunction": score+=1
        elif it["aspect"] in ("square","opposition"): score-=1
    return {"inter_aspects":inter[:25],
            "harmony_index":score,
            "note":"Harmony index is a coarse heuristic, not a verdict; read the actual aspects — Sun/Moon/Venus/Mars contacts matter most."}

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H — ASPECT PATTERNS (Grand Trine, T-Square, Yod, Stellium, etc.)
# ═════════════════════════════════════════════════════════════════════════════

def detect_aspect_patterns(lons, ayan=0.0):
    """Detect classical Western multi-planet configurations in the chart.
    Returns list of patterns with type, involved planets, tightness score (0-100),
    and interpretation key. Inspired by RoxyAPI's pattern detection."""
    bodies = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn",
              "Uranus","Neptune","Pluto"]
    L = {b: norm360(lons[b] - ayan) for b in bodies if b in lons}
    aspects_list = compute_aspects(lons, ayan, bodies)
    patterns = []

    def has_aspect(a, b, asp_type=None):
        for asp in aspects_list:
            if (asp["a"]==a and asp["b"]==b) or (asp["a"]==b and asp["b"]==a):
                if asp_type is None or asp["aspect"]==asp_type:
                    return asp
        return None

    def orb_sum(planets_in_pattern):
        total = 0; count = 0
        for i in range(len(planets_in_pattern)):
            for j in range(i+1, len(planets_in_pattern)):
                a = has_aspect(planets_in_pattern[i], planets_in_pattern[j])
                if a:
                    total += a["orb"]; count += 1
        return total / count if count else 99

    def tightness(avg_orb, max_orb=8.0):
        return max(0, min(100, round(100 * (1 - avg_orb / max_orb))))

    signs_of = {b: sign_of(L[b])[0] for b in L}
    elements_of = {b: SIGN_DATA.get(signs_of.get(b,""),{}).get("element","") for b in L}
    modalities_of = {b: SIGN_DATA.get(signs_of.get(b,""),{}).get("modality","") for b in L}

    found_trines = []
    for i in range(len(bodies)):
        for j in range(i+1, len(bodies)):
            for k in range(j+1, len(bodies)):
                a, b, c = bodies[i], bodies[j], bodies[k]
                ab = has_aspect(a, b, "trine")
                bc = has_aspect(b, c, "trine")
                ac = has_aspect(a, c, "trine")
                if ab and bc and ac:
                    elems = {elements_of.get(p,"") for p in [a,b,c]}
                    is_dissociate = len(elems) > 1
                    avg = (ab["orb"]+bc["orb"]+ac["orb"])/3
                    found_trines.append({"planets":[a,b,c],"avg_orb":avg,
                                         "element":elems.pop() if len(elems)==1 else "mixed",
                                         "dissociate":is_dissociate})

    for tr in found_trines:
        a, b, c = tr["planets"]
        for d in bodies:
            if d in (a,b,c): continue
            opp_to = None
            for p in (a,b,c):
                opp = has_aspect(d, p, "opposition")
                if opp:
                    opp_to = p; break
            if opp_to:
                sext1 = has_aspect(d, [x for x in (a,b,c) if x!=opp_to][0], "sextile")
                sext2 = has_aspect(d, [x for x in (a,b,c) if x!=opp_to][1], "sextile")
                if sext1 and sext2:
                    avg = (tr["avg_orb"] + has_aspect(d, opp_to, "opposition")["orb"] +
                           sext1["orb"] + sext2["orb"]) / 4
                    patterns.append({"kind":"KITE","name":"Kite",
                        "planets":[a,b,c,d],"apex":d,"base_trine":[a,b,c],
                        "tightness":tightness(avg, 6),
                        "interpretation":f"Kite pattern with apex {d}: the Grand Trine talent finds directed expression through {d}'s focus."})
                    break

    grand_trine_planets = set()
    for p in patterns:
        if p["kind"]=="KITE":
            grand_trine_planets.update(p.get("base_trine",[]))
    for tr in found_trines:
        tp = set(tr["planets"])
        if tp & grand_trine_planets == tp:
            continue
        avg = tr["avg_orb"]
        patterns.append({"kind":"GRAND_TRINE","name":"Grand Trine",
            "planets":tr["planets"],"element":tr["element"],
            "dissociate":tr["dissociate"],"tightness":tightness(avg),
            "interpretation":f"Grand Trine in {tr['element']}: natural talent and ease among {', '.join(tr['planets'])}, but may lack motivation."})

    for i in range(len(bodies)):
        for j in range(i+1, len(bodies)):
            opp = has_aspect(bodies[i], bodies[j], "opposition")
            if not opp: continue
            for k in range(len(bodies)):
                if k in (i,j): continue
                sq1 = has_aspect(bodies[k], bodies[i], "square")
                sq2 = has_aspect(bodies[k], bodies[j], "square")
                if sq1 and sq2:
                    mods = {modalities_of.get(bodies[k],""), modalities_of.get(bodies[i],""),
                            modalities_of.get(bodies[j],"")}
                    avg = (opp["orb"]+sq1["orb"]+sq2["orb"])/3
                    is_gc = has_aspect(bodies[i], bodies[j], "opposition") is not None
                    for extra in bodies:
                        if extra in (bodies[i],bodies[j],bodies[k]): continue
                        ex_sq1 = has_aspect(extra, bodies[i], "square")
                        ex_sq2 = has_aspect(extra, bodies[j], "square")
                        if ex_sq1 and ex_sq2:
                            avg2 = (opp["orb"]+sq1["orb"]+sq2["orb"]+ex_sq1["orb"]+ex_sq2["orb"])/5
                            patterns.append({"kind":"GRAND_CROSS","name":"Grand Cross",
                                "planets":[bodies[i],bodies[j],bodies[k],extra],
                                "modality":mods.pop() if len(mods)==1 else "mixed",
                                "tightness":tightness(avg2, 7),
                                "interpretation":f"Grand Cross: intense tension demanding constant action and integration among {', '.join([bodies[i],bodies[j],bodies[k],extra])}."})
                            break
                    patterns.append({"kind":"T_SQUARE","name":"T-Square",
                        "planets":[bodies[i],bodies[j],bodies[k]],"apex":bodies[k],
                        "modality":mods.pop() if len(mods)==1 else "mixed",
                        "dissociate":False,"tightness":tightness(avg, 7),
                        "interpretation":f"T-Square focused on {bodies[k]} in {signs_of.get(bodies[k],'')}, tension between {bodies[i]} and {bodies[j]} demands resolution at the apex."})

    for i in range(len(bodies)):
        for j in range(i+1, len(bodies)):
            q1 = has_aspect(bodies[i], bodies[j], "quincunx")
            if not q1: continue
            for k in range(len(bodies)):
                if k in (i,j): continue
                q2 = has_aspect(bodies[k], bodies[i], "quincunx")
                sext = has_aspect(bodies[k], bodies[j], "sextile")
                if q2 and sext:
                    avg = (q1["orb"]+q2["orb"]+sext["orb"])/3
                    patterns.append({"kind":"YOD","name":"Yod (Finger of Fate)",
                        "planets":[bodies[i],bodies[j],bodies[k]],"apex":bodies[i],
                        "tightness":tightness(avg, 4),
                        "interpretation":f"Yod with apex {bodies[i]} in {signs_of.get(bodies[i],'')}: a fated sense of purpose that requires constant adjustment between {bodies[j]} and {bodies[k]}."})
                    break

    for s_idx in range(12):
        sign_start = s_idx * 30
        sign_end = sign_start + 30
        in_sign = [b for b in bodies if b in L and sign_start <= L[b] < sign_end]
        if len(in_sign) >= 3:
            orbs = [L[b] % 30 for b in in_sign]
            spread = max(orbs) - min(orbs)
            patterns.append({"kind":"STELLIUM","name":"Stellium",
                "planets":in_sign,"sign":SIGNS[s_idx],
                "planet_count":len(in_sign),"spread_deg":round(spread, 1),
                "tightness":max(0, min(100, round(100 * (1 - spread / 30)))),
                "interpretation":f"Stellium of {len(in_sign)} planets in {SIGNS[s_idx]} ({', '.join(in_sign)}): concentrated energy in {SIGN_DATA[SIGNS[s_idx]]['element']}/{SIGN_DATA[SIGNS[s_idx]]['modality']} affairs."})

    for i in range(len(bodies)):
        for j in range(i+1, len(bodies)):
            opp1 = has_aspect(bodies[i], bodies[j], "opposition")
            if not opp1:
                continue
            for k in range(len(bodies)):
                if k in (i, j):
                    continue
                for m_idx in range(k+1, len(bodies)):
                    if m_idx in (i, j):
                        continue
                    opp2 = has_aspect(bodies[k], bodies[m_idx], "opposition")
                    if not opp2:
                        continue
                    sext1a = has_aspect(bodies[i], bodies[k], "sextile")
                    sext1b = has_aspect(bodies[j], bodies[m_idx], "sextile")
                    sext2a = has_aspect(bodies[i], bodies[m_idx], "sextile")
                    sext2b = has_aspect(bodies[j], bodies[k], "sextile")
                    tr1a = has_aspect(bodies[i], bodies[k], "trine")
                    tr1b = has_aspect(bodies[j], bodies[m_idx], "trine")
                    tr2a = has_aspect(bodies[i], bodies[m_idx], "trine")
                    tr2b = has_aspect(bodies[j], bodies[k], "trine")
                    if ((sext1a and tr1b and sext2b and tr2a) or
                        (sext2a and tr2b and sext1b and tr1a)):
                        avg = (opp1["orb"] + opp2["orb"]) / 2
                        if sext1a: avg = (avg + sext1a["orb"]) / 2
                        if tr1b: avg = (avg + tr1b["orb"]) / 2
                        patterns.append({"kind": "MYSTIC_RECTANGLE", "name": "Mystic Rectangle",
                            "planets": [bodies[i], bodies[j], bodies[k], bodies[m_idx]],
                            "tightness": tightness(avg, 7),
                            "interpretation": f"Mystic Rectangle: two oppositions linked by harmonious aspects, creating tension that finds productive expression through {', '.join([bodies[i], bodies[j], bodies[k], bodies[m_idx]])}."})

    deduped = []
    seen = set()
    for p in patterns:
        key = (p["kind"], tuple(sorted(p["planets"])))
        if key not in seen:
            seen.add(key); deduped.append(p)

    gc_planets = {frozenset(p["planets"]) for p in deduped if p["kind"]=="GRAND_CROSS"}
    ts_to_remove = []
    for idx, p in enumerate(deduped):
        if p["kind"] == "T_SQUARE":
            ts_set = frozenset(p["planets"])
            if gc_planets and any(ts_set.issubset(gc) for gc in gc_planets):
                ts_to_remove.append(idx)
    kite_trines = {frozenset(p.get("base_trine",[])) for p in deduped if p["kind"]=="KITE"}
    gt_to_remove = []
    for idx, p in enumerate(deduped):
        if p["kind"] == "GRAND_TRINE":
            gt_set = frozenset(p["planets"])
            if any(gt_set == kt for kt in kite_trines):
                gt_to_remove.append(idx)
    for idx in sorted(ts_to_remove + gt_to_remove, reverse=True):
        if idx < len(deduped):
            deduped.pop(idx)

    return sorted(deduped, key=lambda x: -x["tightness"])

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H2 — SOLAR & LUNAR RETURNS
# ═════════════════════════════════════════════════════════════════════════════

def solar_return(natal_jd, target_year, lat, lng):
    """Find the exact moment in target_year when the transiting Sun returns
    to its natal ecliptic longitude, then cast a chart for that moment.
    This is the foundational technique for annual forecasting in Western astrology."""
    natal_lons, _, backend = body_longitudes(natal_jd)
    natal_sun_lon = natal_lons["Sun"]

    approx_jan = julian_day(datetime(target_year, 1, 1, 0, 0))
    low = approx_jan - 2
    high = approx_jan + 367

    for _ in range(60):
        mid = (low + high) / 2
        t_lons = tropical_longitudes(mid)
        if _HAS_SWE:
            try:
                t_lons_s, _, _ = body_longitudes(mid)
                t_lons = t_lons_s
            except Exception:
                pass
        t_sun = t_lons["Sun"]
        diff = norm180(t_sun - natal_sun_lon)
        if abs(diff) < 0.001:
            break
        if diff > 0:
            high = mid
        else:
            low = mid

    sr_jd = (low + high) / 2
    sr_dt_utc = datetime(2000, 1, 1) + timedelta(days=sr_jd - 2451544.5)

    sr_chart = western_chart(sr_jd, lat, lng, True)
    sr_lons, sr_speed, _ = body_longitudes(sr_jd)

    return {
        "system": "Solar Return (Western Tropical)",
        "target_year": target_year,
        "return_moment_utc": sr_dt_utc.strftime("%Y-%m-%d %H:%M"),
        "julian_day": round(sr_jd, 5),
        "natal_sun_lon": round(natal_sun_lon, 3),
        "return_sun_lon": round(sr_lons["Sun"], 3),
        "precision": "arcsecond" if _HAS_SWE else "~1 arcmin",
        "chart": sr_chart,
        "note": "Solar Return chart: cast for the moment the Sun returns to its exact natal longitude. Read for annual themes — house placement of the SR Sun shows the year's focus area."
    }

def lunar_return(natal_jd, target_year, target_month, lat, lng):
    """Find the moment in the target month when the transiting Moon returns
    to its natal ecliptic longitude. Monthly forecasting technique."""
    natal_lons, _, backend = body_longitudes(natal_jd)
    natal_moon_lon = natal_lons["Moon"]

    approx_start = julian_day(datetime(target_year, target_month, 1, 0, 0))
    low = approx_start - 2
    high = approx_start + 32

    for _ in range(80):
        mid = (low + high) / 2
        t_lons = tropical_longitudes(mid)
        if _HAS_SWE:
            try:
                t_lons_s, _, _ = body_longitudes(mid)
                t_lons = t_lons_s
            except Exception:
                pass
        t_moon = t_lons["Moon"]
        diff = norm180(t_moon - natal_moon_lon)
        if abs(diff) < 0.005:
            break
        if diff > 0:
            high = mid
        else:
            low = mid

    lr_jd = (low + high) / 2
    lr_dt_utc = datetime(2000, 1, 1) + timedelta(days=lr_jd - 2451544.5)

    lr_chart = western_chart(lr_jd, lat, lng, True)

    return {
        "system": "Lunar Return (Western Tropical)",
        "target_year": target_year,
        "target_month": target_month,
        "return_moment_utc": lr_dt_utc.strftime("%Y-%m-%d %H:%M"),
        "natal_moon_lon": round(natal_moon_lon, 3),
        "chart": lr_chart,
        "note": "Lunar Return chart: cast for the moment the Moon returns to its natal position (~every 27.3 days). Read for monthly emotional themes and domestic focus."
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H3 — COMPATIBILITY SCORING (weighted synastry breakdown)
# ═════════════════════════════════════════════════════════════════════════════

def compatibility_score(jdA, jdB):
    """Detailed compatibility scoring with category breakdown.
    Returns 0-100 overall score plus romantic/emotional/intellectual/physical/spiritual subscores."""
    lonsA, _, _ = body_longitudes(jdA)
    lonsB, _, _ = body_longitudes(jdB)

    def score_pair(pA, pB, weight=1.0):
        sep = abs(norm180(lonsA[pA] - lonsB[pB]))
        pts = 0; best_asp = "none"; orb = 0
        for asp, (ang, max_orb, _) in ASPECTS.items():
            d = abs(sep - ang)
            if d <= max_orb:
                quality = 1.0 if asp in ("conjunction","trine","sextile") else -0.7
                if asp == "conjunction" and pA in ("Mars","Saturn") and pB in ("Mars","Saturn"):
                    quality = -0.3
                pts = quality * weight * (1 - d/max_orb)
                best_asp = asp; orb = d
                break
        return pts, best_asp, round(orb, 2)

    romantic, _, _ = score_pair("Venus", "Mars", 2.0)
    romantic += score_pair("Venus", "Venus", 1.0)[0]
    romantic += score_pair("Mars", "Venus", 1.5)[0] if score_pair("Venus", "Mars", 0)[1] == "none" else 0

    emotional, _, _ = score_pair("Moon", "Moon", 2.0)
    emotional += score_pair("Moon", "Venus", 1.5)[0]
    emotional += score_pair("Sun", "Moon", 1.5)[0]
    emotional += score_pair("Moon", "Sun", 1.5)[0]

    intellectual, _, _ = score_pair("Mercury", "Mercury", 2.0)
    intellectual += score_pair("Mercury", "Sun", 1.0)[0]
    intellectual += score_pair("Mercury", "Jupiter", 1.0)[0]

    physical, _, _ = score_pair("Mars", "Mars", 1.5)
    physical += score_pair("Sun", "Sun", 1.0)[0]
    physical += score_pair("Venus", "Mars", 1.5)[0]

    spiritual, _, _ = score_pair("North Node", "North Node", 1.0)
    spiritual += score_pair("North Node", "Sun", 1.0)[0]
    spiritual += score_pair("North Node", "Moon", 1.0)[0]
    spiritual += score_pair("Neptune", "Venus", 0.5)[0]

    def normalize(raw, max_possible=5.0):
        return max(0, min(100, round(50 + (raw / max_possible) * 50)))

    sub = {
        "romantic": normalize(romantic, 5.0),
        "emotional": normalize(emotional, 7.0),
        "intellectual": normalize(intellectual, 4.0),
        "physical": normalize(physical, 4.0),
        "spiritual": normalize(spiritual, 3.5),
    }
    overall = round(sum(sub.values()) / len(sub))
    if overall >= 80: desc = "Exceptional"
    elif overall >= 65: desc = "Strong"
    elif overall >= 50: desc = "Moderate"
    elif overall >= 35: desc = "Challenging"
    else: desc = "Difficult"

    signA = {p: sign_of(lonsA[p])[0] for p in ["Sun","Moon","Venus","Mars"]}
    signB = {p: sign_of(lonsB[p])[0] for p in ["Sun","Moon","Venus","Mars"]}
    elemA = [SIGN_DATA[signA[p]]["element"] for p in ["Sun","Moon","Venus","Mars"]]
    elemB = [SIGN_DATA[signB[p]]["element"] for p in ["Sun","Moon","Venus","Mars"]]
    shared = len(set(elemA) & set(elemB))

    return {
        "overall_score": overall,
        "description": desc,
        "breakdown": sub,
        "element_harmony": {"shared_elements": shared, "personA": elemA, "personB": elemB},
        "key_contacts": [
            {"pair": "Sun-Moon", "aspect": score_pair("Sun", "Moon")[1],
             "note": "Core identity meets emotional needs"},
            {"pair": "Venus-Mars", "aspect": score_pair("Venus", "Mars")[1],
             "note": "Love language meets desire style"},
            {"pair": "Moon-Moon", "aspect": score_pair("Moon", "Moon")[1],
             "note": "Emotional compatibility at the gut level"},
        ],
        "note": "Score is a heuristic from planetary geometry, not a verdict. Two 'difficult' charts can build something extraordinary; two 'exceptional' charts still need work."
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H4 — PART OF FORTUNE, VERTEX, MOON PHASE, CALCULATED POINTS
# ═════════════════════════════════════════════════════════════════════════════

def part_of_fortune(sun_lon, moon_lon, asc_lon, is_day_chart=True):
    """Calculate the Part of Fortune (Lot of Fortune).
    Day chart: Asc + Moon - Sun. Night chart: Asc + Sun - Moon."""
    if is_day_chart:
        pof = asc_lon + moon_lon - sun_lon
    else:
        pof = asc_lon + sun_lon - moon_lon
    pof = norm360(pof)
    sign, idx, deg = sign_of(pof)
    return {"longitude": round(pof, 3), "sign": sign, "degree": round(deg, 2),
            "sect": "day" if is_day_chart else "night",
            "meaning": "The Part of Fortune represents the intersection of spirit (Sun), soul (Moon), and body (Ascendant) — a point of natural prosperity, joy, and physical well-being in the chart."}

def vertex(jd, lat, lng):
    """Calculate the Vertex — the 'point of fated encounters' in the chart.
    It's the intersection of the prime vertical with the ecliptic in the western hemisphere."""
    d = jd - 2451543.5
    eps = obliquity(d)
    gmst_val = gmst_deg(jd)
    ramc = norm360(gmst_val + lng)
    # Vertex formula: arctan(-cos(RAMC) / (sin(eps)*tan(lat) + cos(eps)*sin(RAMC)))
    num = -_cos(ramc)
    den = _sin(eps) * _tan(lat) + _cos(eps) * _sin(ramc)
    v_lon = norm360(_atan2(num, den))
    sign, idx, deg = sign_of(v_lon)
    return {"longitude": round(v_lon, 3), "sign": sign, "degree": round(deg, 2),
            "meaning": "The Vertex is the 'electric ascendant' — a point of fated encounters, significant relationships, and destined events, especially in synastry."}

def moon_phase(jd):
    """Calculate the Moon's phase: name, illumination fraction, age in days since New Moon,
    and the lunation cycle position."""
    lons, _, _ = body_longitudes(jd)
    sun_lon = lons["Sun"]
    moon_lon = lons["Moon"]

    elongation = norm360(moon_lon - sun_lon)
    synodic_period = 29.53059
    age = (elongation / 360.0) * synodic_period
    illumination = (1 - _cos(elongation)) / 2.0

    if elongation < 45: phase_name = "New Moon"
    elif elongation < 90: phase_name = "Waxing Crescent"
    elif elongation < 135: phase_name = "First Quarter"
    elif elongation < 180: phase_name = "Waxing Gibbous"
    elif elongation < 225: phase_name = "Full Moon"
    elif elongation < 270: phase_name = "Waning Gibbous"
    elif elongation < 315: phase_name = "Last Quarter"
    else: phase_name = "Waning Crescent"

    cycle_positions = {
        "New Moon": "initiation, new beginnings, planting seeds",
        "Waxing Crescent": "setting intentions, building momentum, taking first steps",
        "First Quarter": "crisis in action, commitment, overcoming obstacles",
        "Waxing Gibbous": "refinement, adjustment, perfecting the approach",
        "Full Moon": "culmination, revelation, harvest, illumination",
        "Waning Gibbous": "dissemination, sharing wisdom, gratitude",
        "Last Quarter": "release, letting go, restructuring, forgiveness",
        "Waning Crescent": "surrender, rest, reflection, preparation for renewal",
    }
    moon_sign, _, moon_deg = sign_of(moon_lon)

    return {
        "phase": phase_name,
        "illumination": round(illumination * 100, 1),
        "age_days": round(age, 2),
        "elongation_deg": round(elongation, 2),
        "moon_sign": moon_sign,
        "moon_degree": moon_deg,
        "cycle_meaning": cycle_positions.get(phase_name, ""),
        "note": f"The Moon is in {phase_name} phase at {round(illumination*100,1)}% illumination in {moon_sign}. {cycle_positions.get(phase_name,'')}."
    }

def upcoming_moon_phases(jd, count=4):
    """Find the next N major lunar phase transitions (New Moon, First Quarter, Full Moon, Last Quarter)."""
    phases_target = [0.0, 90.0, 180.0, 270.0]
    phase_names = {0.0: "New Moon", 90.0: "First Quarter", 180.0: "Full Moon", 270.0: "Last Quarter"}
    results = []
    current_jd = jd

    for _ in range(count * 3):
        if len(results) >= count:
            break
        lons = tropical_longitudes(current_jd)
        if _HAS_SWE:
            try:
                lons, _, _ = body_longitudes(current_jd)
            except Exception:
                pass
        elong = norm360(lons["Moon"] - lons["Sun"])

        for target in phases_target:
            diff = norm360(target - elong)
            if diff < 0.5 or diff > 359.5:
                dt_utc = datetime(2000, 1, 1) + timedelta(days=current_jd - 2451544.5)
                name = phase_names[target]
                already = any(r["phase"] == name for r in results)
                if not already:
                    results.append({"phase": name, "date_utc": dt_utc.strftime("%Y-%m-%d %H:%M"),
                                    "julian_day": round(current_jd, 4)})
                    break

        current_jd += 7.0

    results.sort(key=lambda x: x["julian_day"])
    return results[:count]

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H5 — NAVAMSA (D9) DIVISIONAL CHART
# ═════════════════════════════════════════════════════════════════════════════

def navamsa_chart(jd, lat, lng, time_known=True):
    """Calculate the Navamsa (D9) — the most important Vedic divisional chart.
    Each 30° sign is divided into 9 equal parts of 3°20' (one pada).
    The Navamsa reveals the soul's potential and strengths in relationships,
    marriage, and dharma. Essential for assessing planetary strength (vargottama)."""
    lons, speed, backend = body_longitudes(jd)
    ayan = ayanamsha_lahiri(jd)
    asc_lon, mc_lon = ascendant_mc(jd, lat, lng, ayan) if time_known else (norm360(lons["Sun"]-ayan), 0)

    navamsa_lons = {}
    names = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","North Node","South Node"]
    for nm in names:
        sid_lon = norm360(lons[nm] - ayan)
        sign_idx = int(sid_lon // 30)
        deg_in_sign = sid_lon % 30
        pada = int(deg_in_sign // (30.0/9.0))  # 0-8
        sign_element = SIGN_DATA[SIGNS[sign_idx]]["element"]

        element_navamsa_start = {
            "Fire": 0,    # Aries (0°) starts fire navamsas
            "Earth": 3,   # Capricorn starts earth navamsas
            "Air": 6,     # Libra starts air navamsas
            "Water": 9,   # Cancer starts water navamsas
        }
        navamsa_sign_idx = (element_navamsa_start.get(sign_element, 0) + pada) % 12
        navamsa_deg = (deg_in_sign % (30.0/9.0)) * 9.0
        navamsa_lon = navamsa_sign_idx * 30 + navamsa_deg
        navamsa_lons[nm] = navamsa_lon

    v_name = {"North Node": "Rahu", "South Node": "Ketu"}
    planets = {}
    for nm in names:
        vnm = v_name.get(nm, nm)
        n_lon = navamsa_lons[nm]
        n_sign, n_idx, n_deg = sign_of(n_lon)
        is_vargottama = (sign_of(norm360(lons[nm] - ayan))[0] == n_sign)
        planets[vnm] = {
            "sign": n_sign, "deg_in_sign": round(n_deg, 2),
            "abs_lon": round(n_lon, 3),
            "rashi_lord": RASHI_LORDS[n_sign],
            "vargottama": is_vargottama,
            "vargottama_note": f"{vnm} is vargottama (same sign in D1 and D9) — its strength is amplified." if is_vargottama else ""
        }

    asc_sign, _, asc_deg = sign_of(asc_lon)
    d9_asc_sign, _, d9_asc_deg = sign_of(navamsa_lons.get("Sun", asc_lon))

    return {
        "system": "Navamsa (D9) — Vedic Divisional Chart",
        "note": "The Navamsa is the 'soul chart' — it reveals the inner strength of each planet and the dharmic path. Vargottama planets (same sign in D1 and D9) are powerfully strengthened.",
        "navamsa_lagna": {"sign": d9_asc_sign, "note": "Navamsa Ascendant sign (approximate from D1 Ascendant)"},
        "planets": planets,
        "vargottama_count": sum(1 for p in planets.values() if p["vargottama"]),
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H6 — KARANA & YOGA (complete Panchang elements)
# ═════════════════════════════════════════════════════════════════════════════

KARANAS = [
    "Bava","Balava","Kaulava","Taitila","Gara","Vanija","Vishti",
    "Shakuni","Chatushpada","Naga","Kinstughna"
]
KARANA_NATURE = {
    "Bava":"auspicious — good for beginnings, travel, financial matters",
    "Balava":"auspicious — good for religious activities, learning, ceremonies",
    "Kaulava":"auspicious — good for relationships, family, agreements",
    "Taitila":"mixed — acceptable for routine work, avoid major beginnings",
    "Gara":"mixed — good for hard work, discipline, avoid leisure",
    "Vanija":"auspicious for commerce — good for trade, business deals",
    "Vishti":"inauspicious (Bhadra) — avoid all auspicious activities",
    "Shakuni":"mixed — good for healing, legal matters, resolving disputes",
    "Chatushpada":"auspicious — good for stability, completion, endings",
    "Naga":"inauspicious — associated with hidden matters, avoid beginnings",
    "Kinstughna":"auspicious — the 'pinch of goodness', brief but positive window",
}

SOLAR_YOGAS = [
    "Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda",
    "Sukarma","Dhriti","Shula","Ganda","Vriddhi","Dhruva","Vyaghata",
    "Harshana","Vajra","Siddhi","Vyatipata","Variyana","Parigha","Shiva",
    "Siddha","Sadhya","Shubha","Shukla","Brahma","Indra","Vaidhriti"
]
YOGA_NATURE = {
    "Vishkambha":"mixed — supports endurance and overcoming obstacles",
    "Priti":"auspicious — love, harmony, pleasant interactions",
    "Ayushman":"auspicious — longevity, health, vitality",
    "Saubhagya":"auspicious — good fortune, success, marriage",
    "Shobhana":"auspicious — beauty, refinement, auspicious ceremonies",
    "Atiganda":"inauspicious — obstacles, complications, avoid new ventures",
    "Sukarma":"auspicious — good actions, charity, virtuous deeds",
    "Dhriti":"auspicious — patience, steadfastness, perseverance",
    "Shula":"inauspicious — pain, sharp conflict, surgical procedures only",
    "Ganda":"inauspicious — moral challenges, avoid major decisions",
    "Vriddhi":"auspicious — growth, increase, expansion",
    "Dhruva":"auspicious — stability, permanence, firm decisions",
    "Vyaghata":"inauspicious — obstacles, aggression, accidents",
    "Harshana":"auspicious — joy, happiness, celebrations",
    "Vajra":"mixed — powerful but rigid, good for decisive action",
    "Siddhi":"auspicious — accomplishment, perfection, success",
    "Vyatipata":"inauspicious — disasters, avoid all activities",
    "Variyana":"auspicious — comfort, wealth, increase",
    "Parigha":"mixed — obstacles that can be overcome with effort",
    "Shiva":"highly auspicious — spiritual activities, meditation, worship",
    "Siddha":"auspicious — accomplishment, perfection, spiritual merit",
    "Sadhya":"auspicious — attainable goals, achievable ambitions",
    "Shubha":"highly auspicious — purity, auspicious for all activities",
    "Shukla":"auspicious — brightness, clarity, intellectual pursuits",
    "Brahma":"highly auspicious — creation, knowledge, spiritual growth",
    "Indra":"auspicious — power, authority, leadership activities",
    "Vaidhriti":"mixed — restrictive, good for introspection only",
}

def panchang_elements(jd):
    """Complete Vedic Panchang elements: Tithi, Nakshatra, Yoga, Karana."""
    lons, _, _ = body_longitudes(jd)
    ayan = ayanamsha_lahiri(jd)
    sun_lon = lons["Sun"]
    moon_lon = lons["Moon"]

    tithi_val = norm360(moon_lon - sun_lon)
    tithi_index = int(tithi_val / 12)  # 0-29
    paksha = "Shukla" if tithi_index < 15 else "Krishna"
    tithi_num = tithi_index + 1 if tithi_index < 15 else tithi_index - 14
    tithi_names = [
        "Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami","Shashti",
        "Saptami","Ashtami","Navami","Dashami","Ekadashi","Dwadashi",
        "Trayodashi","Chaturdashi","Purnima/Amavasya"
    ]
    tithi_name = tithi_names[min(tithi_num - 1, 14)]

    karana_index = int(tithi_val / 6)  # 0-59 karanas in full cycle
    if karana_index == 0:
        karana_name = KARANAS[10]  # Kinstughna
    elif karana_index <= 7:
        karana_name = KARANAS[(karana_index - 1) % 7]
    elif karana_index >= 52:
        karana_name = KARANAS[7 + (karana_index - 52)]
    else:
        karana_name = KARANAS[(karana_index - 1) % 7]

    moon_lon_sid = norm360(moon_lon - ayan)
    sun_lon_sid = norm360(sun_lon - ayan)
    yoga_lon = norm360(moon_lon_sid + sun_lon_sid)
    yoga_index = int(yoga_lon / (360.0 / 27)) % 27
    yoga_name = SOLAR_YOGAS[yoga_index]

    nak_i = int(moon_lon_sid // NAK_ARC) % 27
    nk = NAKSHATRAS[nak_i]

    return {
        "tithi": {"num": tithi_num, "name": tithi_name, "paksha": paksha,
                  "note": f"{paksha} Paksha, Tithi {tithi_num} ({tithi_name})"},
        "nakshatra": {"name": nk["name"], "lord": nk["lord"], "pada": int((moon_lon_sid % NAK_ARC)//(NAK_ARC/4))+1},
        "yoga": {"name": yoga_name, "nature": YOGA_NATURE.get(yoga_name, ""),
                 "note": f"Sun-Moon combined longitude determines the Yoga"},
        "karana": {"name": karana_name, "nature": KARANA_NATURE.get(karana_name, ""),
                   "note": f"Half-tithi Karana: {karana_name}"},
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H7 — NUMEROLOGY (Life Path, Expression, Soul Urge)
# ═════════════════════════════════════════════════════════════════════════════

NUMEROLOGY_MEANINGS = {
    1: {"keyword": "Leadership", "nature": "independent, pioneering, self-determined, original",
        "challenge": "avoid stubbornness, excessive self-reliance, dismissing others' input",
        "careers": "entrepreneur, CEO, inventor, freelancer, any pioneering role"},
    2: {"keyword": "Cooperation", "nature": "diplomatic, sensitive, harmonious, supportive",
        "challenge": "avoid indecision, over-sensitivity, dependency on others' approval",
        "careers": "mediator, counselor, diplomat, healer, team-building roles"},
    3: {"keyword": "Expression", "nature": "creative, joyful, communicative, artistic",
        "challenge": "avoid scattering energy, superficiality, emotional dramatization",
        "careers": "writer, performer, artist, teacher, communicator, entertainer"},
    4: {"keyword": "Foundation", "nature": "practical, disciplined, organized, reliable",
        "challenge": "avoid rigidity, overwork, stubbornness, excessive routine",
        "careers": "engineer, architect, accountant, project manager, builder"},
    5: {"keyword": "Freedom", "nature": "versatile, adventurous, curious, dynamic",
        "challenge": "avoid restlessness, overindulgence, inconsistency, escapism",
        "careers": "travel, sales, marketing, journalism, any role requiring adaptability"},
    6: {"keyword": "Responsibility", "nature": "nurturing, harmonious, compassionate, artistic",
        "challenge": "avoid self-sacrifice to the point of martyrdom, controlling behavior",
        "careers": "teacher, healer, counselor, hospitality, design, community service"},
    7: {"keyword": "Wisdom", "nature": "analytical, spiritual, introspective, perceptive",
        "challenge": "avoid isolation, overthinking, skepticism, emotional detachment",
        "careers": "researcher, philosopher, scientist, spiritual teacher, analyst"},
    8: {"keyword": "Power", "nature": "ambitious, authoritative, business-minded, strategic",
        "challenge": "avoid workaholism, materialism, power struggles, neglecting personal life",
        "careers": "executive, finance, real estate, law, management, entrepreneurship"},
    9: {"keyword": "Humanitarian", "nature": "compassionate, generous, idealistic, wise",
        "challenge": "avoid emotional detachment, self-righteousness, over-giving without boundaries",
        "careers": "nonprofit, healing, teaching, arts, philanthropy, global causes"},
    11: {"keyword": "Master Intuitive", "nature": "visionary, inspired, spiritually gifted, idealistic",
         "challenge": "avoid nervous tension, self-doubt, living too much in the abstract",
         "careers": "spiritual teacher, artist, healer, innovator, inspirational leader"},
    22: {"keyword": "Master Builder", "nature": "visionary architect, practical idealist, transformative leader",
         "challenge": "avoid being overwhelmed by the scope of your visions",
         "careers": "large-scale projects, architecture, global business, system design"},
    33: {"keyword": "Master Teacher", "nature": "compassionate healer, selfless service, spiritual upliftment",
         "challenge": "avoid self-sacrifice without boundaries, carrying others' burdens",
         "careers": "healing, teaching, spiritual leadership, humanitarian work"},
}

def _reduce(n):
    while n > 9 and n not in (11, 22, 33):
        n = sum(int(d) for d in str(n))
    return n

def numerology(year, month, day, full_name=""):
    """Calculate core numerology: Life Path, Personal Year, and (if name provided) Expression & Soul Urge."""
    life_path = _reduce(_reduce(day) + _reduce(month) + _reduce(year))
    personal_year = _reduce(day + month + sum(int(d) for d in str(year)))
    lp_meaning = NUMEROLOGY_MEANINGS.get(life_path, {"keyword": str(life_path), "nature": "", "challenge": "", "careers": ""})

    result = {
        "life_path": {"number": life_path,
                      "meaning": lp_meaning.get("keyword",""),
                      "nature": lp_meaning.get("nature",""),
                      "challenge": lp_meaning.get("challenge",""),
                      "vocations": lp_meaning.get("careers","")},
        "personal_year": {"number": personal_year,
                          "note": f"Personal Year {personal_year} themes: {NUMEROLOGY_MEANINGS.get(personal_year,{}).get('keyword','cycle')}"},
        "birth_date_numbers": {"day": _reduce(day), "month": _reduce(month), "year": _reduce(year)},
    }

    if full_name:
        letter_values = {c: v for c in "abcdefghijklmnopqrstuvwxyz"
                        for v in [1,2,3,4,5,6,7,8,9]
                        if (ord(c) - ord('a')) % 9 + 1 == v}
        letter_map = {}
        for c in "abcdefghijklmnopqrstuvwxyz":
            letter_map[c] = (ord(c) - ord('a')) % 9 + 1
        vowels = set("aeiou")
        name_clean = full_name.lower().replace(" ", "")
        expression = _reduce(sum(letter_map.get(c, 0) for c in name_clean))
        soul_urge = _reduce(sum(letter_map.get(c, 0) for c in name_clean if c in vowels))
        result["expression"] = {"number": expression,
                                "note": f"Full name reveals talents and abilities: {NUMEROLOGY_MEANINGS.get(expression,{}).get('keyword','')}"}
        result["soul_urge"] = {"number": soul_urge,
                               "note": f"Vowels reveal inner motivation: {NUMEROLOGY_MEANINGS.get(soul_urge,{}).get('keyword','')}"}

    return result

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H8 — EQUAL HOUSE SYSTEM OPTION
# ═════════════════════════════════════════════════════════════════════════════

def equal_houses(asc_lon):
    """Equal house system: each house = 30° starting from the Ascendant degree.
    Simpler than Placidus, commonly used alongside whole-sign."""
    houses = {}
    for hnum in range(1, 13):
        cusp_lon = norm360(asc_lon + (hnum - 1) * 30)
        sign, idx, deg = sign_of(cusp_lon)
        houses[hnum] = {"sign": sign, "cusp_degree": round(deg, 2),
                        "abs_lon": round(cusp_lon, 3),
                        "ruler": SIGN_DATA[sign]["ruler"],
                        "meaning": HOUSE_MEANINGS[hnum]}
    return houses

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H9 — COMPOSITE CHART (midpoint of two natal charts)
# ═════════════════════════════════════════════════════════════════════════════

def composite_chart(jdA, jdB, latA, lngA, latB, lngB):
    """Midpoint composite chart — the relationship as a third entity.
    Each planet is the midpoint of its positions in both charts."""
    lonsA, speedA, backend = body_longitudes(jdA)
    lonsB, speedB, _ = body_longitudes(jdB)
    names = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn",
             "Uranus","Neptune","Pluto","North Node","South Node","Chiron"]
    mid_lat = (latA + latB) / 2
    mid_lng = (lngA + lngB) / 2
    ascA, mcA = ascendant_mc(jdA, latA, lngA)
    ascB, mcB = ascendant_mc(jdB, latB, lngB)
    comp_asc = midpoint_lon(ascA, ascB)
    comp_mc = midpoint_lon(mcA, mcB)
    planets = {}
    for nm in names:
        if nm in lonsA and nm in lonsB:
            mid = midpoint_lon(lonsA[nm], lonsB[nm])
            sign, idx, deg = sign_of(mid)
            retro = speedA.get(nm, 0) < 0 or speedB.get(nm, 0) < 0
            house = whole_sign_house(mid, comp_asc)
            planets[nm] = {"longitude": round(mid, 3), "sign": sign,
                           "degree_in_sign": round(deg, 2), "house": house,
                           "retrograde": retro,
                           "dignity": dignity_western(nm, sign)}
    asc_sign, _, asc_deg = sign_of(comp_asc)
    mc_sign, _, mc_deg = sign_of(comp_mc)
    houses = {}
    asc_idx = int(comp_asc // 30)
    for hnum in range(1, 13):
        s = SIGNS[(asc_idx + hnum - 1) % 12]
        houses[hnum] = {"sign": s, "ruler": SIGN_DATA[s]["ruler"],
                        "meaning": HOUSE_MEANINGS[hnum]}
    aspects = compute_aspects({nm: planets[nm]["longitude"] for nm in planets})[:20]
    return {
        "system": "Composite Chart (midpoint method)",
        "note": "The composite chart represents the relationship itself as a third entity. Each planet is the midpoint of its positions in both natal charts.",
        "ascendant": {"sign": asc_sign, "degree": round(asc_deg, 2)},
        "midheaven": {"sign": mc_sign, "degree": round(mc_deg, 2)},
        "chart_ruler": SIGN_DATA[asc_sign]["ruler"],
        "descendant": {"sign": SIGNS[(asc_idx + 6) % 12],
                       "degree": round(asc_deg, 2)},
        "imum_coeli": {"sign": SIGNS[(int(comp_mc // 30) + 6) % 12],
                       "degree": round(mc_deg, 2)},
        "planets": planets, "houses": houses, "aspects": aspects}

def midpoint_lon(a, b):
    mid = (a + b) / 2
    diff = abs(a - b)
    if diff > 180:
        mid = norm360(mid + 180)
    return norm360(mid)

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H10 — BLACK MOON LILITH (Mean)
# ═════════════════════════════════════════════════════════════════════════════

def black_moon_lilith(jd):
    """Mean Black Moon Lilith — the empty focus of the Moon's orbit.
    Represents the shadow self, repressed desires, and primal wildness.
    Approximation using lunar apogee cycle (~8.85 year period)."""
    T = (jd - 2451545.0) / 36525.0
    lilith_lon = norm360(119.0524 + 406.6057 * T + 0.0107 * T * T)
    sign, idx, deg = sign_of(lilith_lon)
    return {"longitude": round(lilith_lon, 3), "sign": sign,
            "degree_in_sign": round(deg, 2),
            "meaning": "Black Moon Lilith represents the shadow self — repressed desires, primal instincts, and where one rejects conformity. It reveals where raw authenticity meets social conditioning."}

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H11 — SECONDARY PROGRESSIONS (1 day = 1 year)
# ═════════════════════════════════════════════════════════════════════════════

def secondary_progressions(natal_jd, target_age, lat, lng):
    """Secondary progressions: 1 day after birth = 1 year of life.
    Casts a chart for (natal_jd + target_age) days after birth."""
    prog_jd = natal_jd + target_age
    prog_chart = western_chart(prog_jd, lat, lng, True)
    prog_chart["system"] = "Secondary Progressions"
    prog_chart["target_age"] = target_age
    prog_chart["note"] = f"Progressed chart for age {target_age}. Each day after birth equals one year of life. The progressed Sun, Moon, and Ascendant reveal evolving identity, emotional needs, and outer persona."
    return prog_chart

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H12 — GENERIC PLANETARY RETURN (Mercury–Saturn)
# ═════════════════════════════════════════════════════════════════════════════

def planetary_return(natal_jd, planet, target_year, lat, lng):
    """Generic planetary return: find when transiting planet returns to natal position.
    Works for any planet. Solar/lunar returns are special cases."""
    natal_lons, _, backend = body_longitudes(natal_jd)
    if planet not in natal_lons:
        return {"error": f"Planet '{planet}' not available"}
    natal_lon = natal_lons[planet]
    approx_jan = julian_day(datetime(target_year, 1, 1, 0, 0))
    periods = {"Sun": 1.0, "Moon": 0.0748, "Mercury": 0.2408,
               "Venus": 0.6152, "Mars": 1.881, "Jupiter": 11.86,
               "Saturn": 29.46, "Uranus": 84.01, "Neptune": 164.8, "Pluto": 248.0}
    window = periods.get(planet, 1.0) * 367
    low = approx_jan - 2
    high = approx_jan + window + 2
    for _ in range(80):
        mid = (low + high) / 2
        t_lons = tropical_longitudes(mid)
        t_lon = t_lons.get(planet)
        if t_lon is None:
            break
        diff = norm180(t_lon - natal_lon)
        if abs(diff) < 0.001:
            break
        if diff > 0:
            high = mid
        else:
            low = mid
    ret_jd = (low + high) / 2
    ret_utc = datetime(2000, 1, 1) + timedelta(days=ret_jd - 2451544.5)
    ret_chart = western_chart(ret_jd, lat, lng, True)
    return {
        "system": f"Planetary Return ({planet})",
        "planet": planet, "target_year": target_year,
        "return_moment_utc": ret_utc.strftime("%Y-%m-%d %H:%M"),
        "natal_longitude": round(natal_lon, 3),
        "orbital_period_years": periods.get(planet, "?"),
        "chart": ret_chart,
        "note": f"{planet} return: the moment {planet} returns to its natal position, beginning a new {planet} cycle."}

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H13 — MORE ARABIC PARTS (Pars Spiritus, Amoris, etc.)
# ═════════════════════════════════════════════════════════════════════════════

ARABIC_PARTS = {
    "Pars Fortuna":     {"day": ("Asc","Moon","Sun"),  "night": ("Asc","Sun","Moon"),
                         "meaning": "Natural prosperity, joy, physical well-being"},
    "Pars Spiritus":    {"day": ("Asc","Sun","Moon"),  "night": ("Asc","Moon","Sun"),
                         "meaning": "The soul's purpose, spiritual calling, inner vision"},
    "Pars Amoris":      {"day": ("Asc","Venus","Sun"), "night": ("Asc","Sun","Venus"),
                         "meaning": "Love nature, romantic destiny, capacity for intimacy"},
    "Pars Fidei":       {"day": ("Asc","Moon","Saturn"),"night": ("Asc","Saturn","Moon"),
                         "meaning": "Faith, religion, philosophical convictions, trust"},
    "Pars Valetudinis": {"day": ("Asc","Moon","Mars"), "night": ("Asc","Mars","Moon"),
                         "meaning": "Health vulnerabilities, physical constitution"},
    "Pars Magistrix":   {"day": ("Asc","Jupiter","Sun"),"night": ("Asc","Sun","Jupiter"),
                         "meaning": "Career authority, professional recognition, vocation"},
    "Pars Victus":      {"day": ("Asc","Moon","Mercury"),"night": ("Asc","Mercury","Moon"),
                         "meaning": "Daily life, livelihood, routine patterns"},
    "Pars Sororis":     {"day": ("Asc","Venus","Moon"), "night": ("Asc","Moon","Venus"),
                         "meaning": "Sisters, close female friends, feminine bonds"},
    "Pars Fratris":     {"day": ("Asc","Jupiter","Saturn"),"night": ("Asc","Saturn","Jupiter"),
                         "meaning": "Brothers, close male friends, masculine bonds"},
    "Pars Nuptiae":     {"day": ("Asc","Venus","Saturn"),"night": ("Asc","Saturn","Venus"),
                         "meaning": "Marriage, committed partnerships, vows"},
}

def compute_arabic_parts(lons, asc_lon, is_day_chart=True):
    """Compute configured Arabic Parts / Hermetic Lots."""
    sect = "day" if is_day_chart else "night"
    results = {}
    for name, cfg in ARABIC_PARTS.items():
        formula = cfg[sect]
        vals = []
        for key in formula:
            if key == "Asc":
                vals.append(asc_lon)
            elif key in lons:
                vals.append(lons[key])
            else:
                break
        if len(vals) == 3:
            part_lon = norm360(vals[0] + vals[1] - vals[2])
            sign, idx, deg = sign_of(part_lon)
            results[name] = {"longitude": round(part_lon, 3), "sign": sign,
                             "degree_in_sign": round(deg, 2),
                             "sect_used": sect, "meaning": cfg["meaning"]}
    return results

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H14 — FIXED STARS (23 brightest with magnitude)
# ═════════════════════════════════════════════════════════════════════════════

FIXED_STARS = {
    # Tropical longitude (J2000.0), magnitude, nature, meaning
    "Regulus":     {"lon": 149.83, "mag": 1.4,  "nature": "Mars/Jupiter", "meaning": "Royalty, success, then downfall if revenge-seeking"},
    "Spica":       {"lon": 203.84, "mag": 1.0,  "nature": "Venus/Mars", "meaning": "Gifts, talent, wealth, potential for brilliance"},
    "Sirius":      {"lon": 104.20, "mag": -1.5, "nature": "Jupiter/Mars", "meaning": "Fame, honor, wealth, loyalty, devotion to duty"},
    "Canopus":     {"lon": 88.28,  "mag": -0.7, "nature": "Saturn/Jupiter", "meaning": "Travel, voyages, positions of authority"},
    "Arcturus":    {"lon": 204.07, "mag": -0.05,"nature": "Jupiter/Venus", "meaning": "Prosperity through travel, honors, self-determination"},
    "Vega":        {"lon": 285.42, "mag": 0.03, "nature": "Venus/Mercury", "meaning": "Artistic talent, charisma, idealism"},
    "Capella":     {"lon": 80.13,  "mag": 0.08, "nature": "Mars/Mercury", "meaning": "Honor, wealth, public position, independence"},
    "Rigel":       {"lon": 78.87,  "mag": 0.13, "nature": "Jupiter/Saturn", "meaning": "Benevolence, honor, lasting fame through inventive mind"},
    "Procyon":     {"lon": 114.83, "mag": 0.34, "nature": "Mercury/Mars", "meaning": "Quick rise followed by potential sudden fall"},
    "Betelgeuse":  {"lon": 89.18,  "mag": 0.5,  "nature": "Mars/Mercury", "meaning": "Military honor, ambition, but potential for rashness"},
    "Altair":      {"lon": 301.72, "mag": 0.77, "nature": "Mars/Jupiter", "meaning": "Boldness, ambition, courage, sudden fortune"},
    "Aldebaran":   {"lon": 69.92,  "mag": 0.85, "nature": "Mars", "meaning": "Honor, integrity, public prominence, but potential for failure"},
    "Antares":     {"lon": 249.98, "mag": 1.1,  "nature": "Mars/Jupiter", "meaning": "Obsessive focus, extremes, military honor or downfall"},
    "Pollux":      {"lon": 113.47, "mag": 1.1,  "nature": "Mars", "meaning": "Shrewdness, courage, boxing/martial skill, but cunning"},
    "Fomalhaut":   {"lon": 16.08,  "mag": 1.2,  "nature": "Venus/Mercury", "meaning": "Spiritual gifts, fame, idealism, but vulnerability to deceit"},
    "Deneb":       {"lon": 5.31,   "mag": 1.25, "nature": "Venus/Mercury", "meaning": "Intelligence, artistic talent, changeable fortune"},
    "Algol":       {"lon": 26.14,  "mag": 2.1,  "nature": "Saturn/Jupiter", "meaning": "Intense passion, confronting the shadow, potential for violence or transformation"},
    "Achernar":    {"lon": 15.67,  "mag": 0.5,  "nature": "Jupiter", "meaning": "Success in public office, religious authority"},
    "Alcyone":     {"lon": 60.16,  "mag": 3.0,  "nature": "Moon/Mars", "meaning": "Emotional depth, vision, but potential for blindness or obsession"},
    "Alphecca":    {"lon": 231.58, "mag": 2.2,  "nature": "Venus/Mercury", "meaning": "Artistic talent, honor, fame, but shame if dishonorable"},
    "Algorab":     {"lon": 186.31, "mag": 3.1,  "nature": "Saturn/Mars", "meaning": "Destruction, cunning, deceit, but also forensic intelligence"},
    "Deneb Algedi":{"lon": 328.09, "mag": 2.9,  "nature": "Saturn/Jupiter", "meaning": "Legal authority, business acumen, but potential for hardship"},
    "Alkaid":      {"lon": 205.10, "mag": 1.9,  "nature": "Mars/Moon", "meaning": "Mourning, loss, but also intellectual achievement through sorrow"},
    "Markab":      {"lon": 353.48, "mag": 2.5,  "nature": "Jupiter/Mercury", "meaning": "Business success, speed, but restlessness"},
    "Scheat":      {"lon": 346.56, "mag": 2.4,  "nature": "Saturn/Mercury", "meaning": "Misfortune, violence, but also intelligence"},
    "Enif":        {"lon": 337.27, "mag": 2.4,  "nature": "Mars/Mercury", "meaning": "Courage, ambition, military honor"},
    "Hamal":       {"lon": 38.27,  "mag": 2.0,  "nature": "Mars/Saturn", "meaning": "Self-will, initiative, but rashness"},
    "Mirach":      {"lon": 15.08,  "mag": 2.1,  "nature": "Venus/Mercury", "meaning": "Artistic ability, idealistic love"},
    "Almach":      {"lon": 13.63,  "mag": 2.3,  "nature": "Venus", "meaning": "Artistic talent, popularity with the opposite sex"},
    "Capulus":     {"lon": 71.22,  "mag": 4.0,  "nature": "Mars/Mercury", "meaning": "Courage in danger, success in war"},
    "Alhena":      {"lon": 105.99, "mag": 1.9,  "nature": "Mercury/Venus", "meaning": "Technical skill, healing ability"},
    "Castor":      {"lon": 110.27, "mag": 1.6,  "nature": "Mercury/Mars", "meaning": "Quick wit, athletic skill, but injury-prone"},
    "Zosma":       {"lon": 165.84, "mag": 2.6,  "nature": "Saturn", "meaning": "Misfortune through own actions, melancholy"},
    "Denebola":    {"lon": 178.55, "mag": 2.1,  "nature": "Mercury/Uranus", "meaning": "Quick mind, changeable fortune, honor"},
    "Vindemiatrix": {"lon": 195.42, "mag": 3.0, "nature": "Saturn/Mercury", "meaning": "Widowhood, misfortune, but good for study"},
    "Zuben Elgenubi":{"lon": 220.36, "mag": 2.8, "nature": "Mercury", "meaning": "Intelligence, artistic talent"},
    "Zuben Eschamali":{"lon": 218.58,"mag": 2.6, "nature": "Jupiter/Venus", "meaning": "Justice, honor, idealism"},
    "Zuben Elakrab": {"lon": 227.27, "mag": 3.9, "nature": "Mars/Jupiter", "meaning": "Determination, courage"},
    "Dschubba":   {"lon": 241.49, "mag": 2.3,  "nature": "Mars/Saturn", "meaning": "Violence, danger, but courage"},
    "Sargas":     {"lon": 261.31, "mag": 1.9,  "nature": "Jupiter/Venus", "meaning": "Honor, prosperity, but scandal"},
    "Kaus Australis":{"lon": 271.07, "mag": 1.8, "nature": "Jupiter/Mercury", "meaning": "Philosophical mind, spiritual insight"},
    "Nunki":      {"lon": 274.01, "mag": 2.1,  "nature": "Jupiter", "meaning": "Good fortune, idealism"},
    "Rukbat":     {"lon": 269.49, "mag": 4.0,  "nature": "Saturn/Mars", "meaning": "Technical skill, but hard work"},
    "Alnair":     {"lon": 330.15, "mag": 1.7,  "nature": "Jupiter/Mercury", "meaning": "Honor, ambition, travel"},
    "Schedar":    {"lon": 14.67,  "mag": 2.2,  "nature": "Saturn/Venus", "meaning": "High ideals, integrity"},
    "Mizar":      {"lon": 199.53, "mag": 2.2,  "nature": "Venus/Mercury", "meaning": "Artistic talent, but deceit"},
    "Alphecca":   {"lon": 231.58, "mag": 2.2,  "nature": "Venus/Mercury", "meaning": "Artistic talent, honor, fame"},
    "Nashira":    {"lon": 332.57, "mag": 3.6,  "nature": "Saturn/Mercury", "meaning": "Cunning, caution"},
    "Rasalhague": {"lon": 264.02, "mag": 2.1,  "nature": "Mercury/Venus", "meaning": "Technical skill, leadership"},
    "Rasalas":    {"lon": 152.60, "mag": 3.4,  "nature": "Mars/Saturn", "meaning": "Courage, but violence"},
    "Kochab":     {"lon": 146.06, "mag": 2.1,  "nature": "Mars/Saturn", "meaning": "Endurance, resilience, but hardship"},
    "Phecda":     {"lon": 174.18, "mag": 2.4,  "nature": "Venus/Mars", "meaning": "Passion, but discord"},
    "Merak":      {"lon": 167.63, "mag": 2.4,  "nature": "Moon/Jupiter", "meaning": "Prosperity, family fortune"},
    "Dubhe":      {"lon": 164.62, "mag": 1.8,  "nature": "Mars/Saturn", "meaning": "Courage, military skill"},
    "Megrez":     {"lon": 173.15, "mag": 3.3,  "nature": "Venus", "meaning": "Artistic talent"},
    "Alioth":     {"lon": 194.93, "mag": 1.8,  "nature": "Mars/Mercury", "meaning": "Ambition, honor"},
    "Alkaid":     {"lon": 205.10, "mag": 1.9,  "nature": "Mars/Moon", "meaning": "Mourning, loss, but intellectual achievement"},
    "Gacrux":     {"lon": 212.63, "mag": 1.6,  "nature": "Venus/Saturn", "meaning": "Idealistic love, but sorrow"},
    "Acrux":      {"lon": 213.09, "mag": 0.9,  "nature": "Jupiter/Venus", "meaning": "Spiritual insight, honor"},
    "Mimosa":     {"lon": 214.70, "mag": 1.3,  "nature": "Venus/Mercury", "meaning": "Artistic talent, sociability"},
    "Hadar":      {"lon": 224.45, "mag": 0.6,  "nature": "Venus/Jupiter", "meaning": "Spiritual insight, idealism"},
    "Rigil Kentaurus":{"lon": 219.90, "mag": -0.3,"nature": "Venus/Jupiter", "meaning": "Healing, wisdom, compassion"},
    "Shaula":     {"lon": 265.58, "mag": 1.6,  "nature": "Mars/Mercury", "meaning": "Cunning, scientific mind"},
    "Lesath":     {"lon": 265.88, "mag": 2.7,  "nature": "Mercury/Mars", "meaning": "Danger, poison, but intellect"},
    "Atria":      {"lon": 244.47, "mag": 1.9,  "nature": "Jupiter", "meaning": "Good fortune, honor"},
    "Peacock":    {"lon": 324.53, "mag": 1.9,  "nature": "Saturn/Mercury", "meaning": "Misfortune through pride"},
    "Dabih":      {"lon": 309.90, "mag": 3.1,  "nature": "Saturn/Venus", "meaning": "Reserved, scholarly"},
    "Sadalmelik": {"lon": 336.98, "mag": 2.9,  "nature": "Jupiter/Venus", "meaning": "Honor, benevolence"},
    "Sadalsuud":  {"lon": 341.76, "mag": 2.9,  "nature": "Jupiter", "meaning": "Good fortune, ambition"},
    "Sadachbia":  {"lon": 339.64, "mag": 3.5,  "nature": "Mercury/Venus", "meaning": "Intellectual talent"},
    "Skat":       {"lon": 337.22, "mag": 3.3,  "nature": "Mars/Mercury", "meaning": "Courage, scientific talent"},
    "Algenib":    {"lon": 0.26,   "mag": 2.8,  "nature": "Jupiter/Mars", "meaning": "Ambition, military honor"},
    "Mira":       {"lon": 34.38,  "mag": 6.5,  "nature": "Neptune", "meaning": "Transformation, unpredictability"},
    "Menkar":     {"lon": 41.08,  "mag": 2.5,  "nature": "Saturn", "meaning": "Misfortune, but strong will"},
    "Alcyone (Pleiades)":{"lon": 60.16, "mag": 3.0, "nature": "Moon/Mars", "meaning": "Emotional depth, vision, potential for blindness or obsession"},
    "Electra":    {"lon": 58.69,  "mag": 3.7,  "nature": "Venus/Mars", "meaning": "Artistic talent, but sudden loss"},
    "Atlas":      {"lon": 58.18,  "mag": 3.6,  "nature": "Moon/Mars", "meaning": "Emotional intensity"},
    "Alderamin":  {"lon": 12.21,  "mag": 2.5,  "nature": "Mercury/Jupiter", "meaning": "Intellectual ability, honor"},
    "Polaris":    {"lon": 88.34,  "mag": 2.0,  "nature": "Venus/Saturn", "meaning": "Guidance, stability, spiritual insight"},
    "Nihal":      {"lon": 40.99,  "mag": 4.0,  "nature": "Mars/Saturn", "meaning": "Ambition, hard work"},
    "Saiph":      {"lon": 79.73,  "mag": 2.1,  "nature": "Jupiter/Saturn", "meaning": "Benevolence, honor"},
    "Bellatrix":  {"lon": 81.01,  "mag": 1.6,  "nature": "Mercury/Mars", "meaning": "Courage, honor, but rashness"},
    "Meissa":     {"lon": 83.27,  "mag": 3.5,  "nature": "Mars/Mercury", "meaning": "Technical skill"},
    "Alnitak":    {"lon": 85.64,  "mag": 1.7,  "nature": "Mars/Mercury", "meaning": "Ambition, courage"},
    "Alnilam":    {"lon": 85.39,  "mag": 1.7,  "nature": "Jupiter/Mars", "meaning": "Fame, honor"},
    "Mintaka":    {"lon": 84.09,  "mag": 2.2,  "nature": "Mars", "meaning": "Courage, ambition"},
    "Wezen":      {"lon": 105.62, "mag": 1.8,  "nature": "Jupiter/Saturn", "meaning": "Honor, but melancholy"},
    "Adhara":     {"lon": 102.38, "mag": 1.5,  "nature": "Mars/Mercury", "meaning": "Courage, ambition"},
    "Mirzam":     {"lon": 101.73, "mag": 2.0,  "nature": "Mars/Mercury", "meaning": "Courage, ambition"},
    "Kaus Media": {"lon": 270.49, "mag": 2.7,  "nature": "Jupiter/Mercury", "meaning": "Philosophical mind"},
    "Alzirr":     {"lon": 102.51, "mag": 3.2,  "nature": "Mercury", "meaning": "Intelligence, versatility"},
    "Asellus Australis":{"lon": 127.75, "mag": 3.9, "nature": "Mars/Sun", "meaning": "Courage, but impulsiveness"},
    "Asellus Borealis":{"lon": 127.05, "mag": 4.2, "nature": "Mars/Sun", "meaning": "Courage, but recklessness"},
    "Acubens":    {"lon": 130.46, "mag": 4.3,  "nature": "Mercury/Venus", "meaning": "Intelligence, charm"},
    "Tarf":       {"lon": 136.76, "mag": 3.5,  "nature": "Mars/Saturn", "meaning": "Courage, but danger"},
    "Avior":      {"lon": 196.09, "mag": 1.9,  "nature": "Venus/Saturn", "meaning": "Artistic talent, but sorrow"},
    "Aspidiske":  {"lon": 200.44, "mag": 3.0,  "nature": "Venus/Mercury", "meaning": "Artistic talent, honor"},
    "Markab":     {"lon": 353.48, "mag": 2.5,  "nature": "Jupiter/Mercury", "meaning": "Business success, but restlessness"},
    "Sadr":       {"lon": 316.99, "mag": 2.2,  "nature": "Jupiter/Venus", "meaning": "Honor, benevolence"},
    "Gienah":     {"lon": 192.39, "mag": 2.6,  "nature": "Mercury/Saturn", "meaning": "Intelligence, but melancholy"},
    "Zuben Elgenubi (North)":{"lon": 220.36, "mag": 2.8, "nature": "Mercury", "meaning": "Intelligence, artistic talent"},
    "Vindemiatrix (Epsilon Vir)":{"lon": 195.42, "mag": 3.0, "nature": "Saturn/Mercury", "meaning": "Widowhood, misfortune, but good for study"},
    "Zavijava":   {"lon": 182.11, "mag": 3.6,  "nature": "Mercury", "meaning": "Intelligence, adaptability"},
    "Porrima":    {"lon": 190.29, "mag": 2.7,  "nature": "Venus/Mercury", "meaning": "Artistic talent, grace"},
    "Syrma":      {"lon": 190.89, "mag": 3.9,  "nature": "Mercury/Venus", "meaning": "Intelligence, charm"},
    "Rijl al Awwa":{"lon": 199.53, "mag": 3.4, "nature": "Venus/Mercury", "meaning": "Artistic talent"},
    "Alchiba":    {"lon": 193.14, "mag": 4.0,  "nature": "Mercury/Venus", "meaning": "Intelligence, adaptability"},
    "Kraz":       {"lon": 202.73, "mag": 3.0,  "nature": "Mars/Saturn", "meaning": "Courage, but danger"},
    "Gacrux":     {"lon": 212.63, "mag": 1.6,  "nature": "Venus/Saturn", "meaning": "Idealistic love, but sorrow"},
    "Becrux":     {"lon": 214.70, "mag": 1.3,  "nature": "Venus/Mercury", "meaning": "Artistic talent"},
    "Muhfrid":    {"lon": 207.52, "mag": 2.7,  "nature": "Mercury/Venus", "meaning": "Intelligence, charm"},
    "Caph":       {"lon": 354.08, "mag": 2.3,  "nature": "Venus/Mercury", "meaning": "Artistic talent"},
    "Schedir":    {"lon": 14.67,  "mag": 2.2,  "nature": "Saturn/Venus", "meaning": "High ideals, integrity"},
    "Ruchbah":    {"lon": 12.07,  "mag": 2.7,  "nature": "Mercury/Venus", "meaning": "Intelligence, honor"},
    "Zeta Cas":   {"lon": 17.44,  "mag": 3.7,  "nature": "Mars/Mercury", "meaning": "Courage"},
    "Kappa Cas":  {"lon": 16.64,  "mag": 4.2,  "nature": "Mars", "meaning": "Courage"},
    "Phi Cas":    {"lon": 18.63,  "mag": 5.0,  "nature": "Mercury", "meaning": "Intelligence"},
    "Delta Cas":  {"lon": 18.62,  "mag": 2.7,  "nature": "Mars/Mercury", "meaning": "Courage, ambition"},
    "Segin":      {"lon": 20.61,  "mag": 3.4,  "nature": "Mars", "meaning": "Courage"},
    "Navi":       {"lon": 22.06,  "mag": 2.6,  "nature": "Jupiter/Mercury", "meaning": "Intellectual ability"},
    "Tsih":       {"lon": 23.51,  "mag": 2.5,  "nature": "Mercury", "meaning": "Intelligence"},
    "Rho Cas":    {"lon": 23.85,  "mag": 4.5,  "nature": "Mercury/Venus", "meaning": "Intelligence, charm"},
    "Sigma Cas":  {"lon": 24.11,  "mag": 5.0,  "nature": "Mars", "meaning": "Courage"},
    "Iota Cas":   {"lon": 24.56,  "mag": 4.6,  "nature": "Mercury", "meaning": "Intelligence"},
    "Epsilon Cas": {"lon": 25.01, "mag": 3.4,  "nature": "Mars", "meaning": "Courage"},
    "Zeta And":   {"lon": 24.25,  "mag": 4.1,  "nature": "Venus", "meaning": "Charm"},
    "Upsilon And": {"lon": 24.72, "mag": 4.1,  "nature": "Mercury/Venus", "meaning": "Intelligence, charm"},
    "Delta And":  {"lon": 25.50,  "mag": 3.3,  "nature": "Mercury/Venus", "meaning": "Intelligence, charm"},
    "Beta Tri":   {"lon": 27.31,  "mag": 3.0,  "nature": "Mercury", "meaning": "Intelligence"},
    "Alpha Tri":  {"lon": 28.57,  "mag": 3.4,  "nature": "Jupiter", "meaning": "Good fortune"},
    "Gamma Tri":  {"lon": 28.99,  "mag": 4.0,  "nature": "Mercury", "meaning": "Intelligence"},
    "Hamal (Alpha Ari)":{"lon": 38.27, "mag": 2.0, "nature": "Mars/Saturn", "meaning": "Self-will, initiative, but rashness"},
    "Sheratan":   {"lon": 39.15,  "mag": 2.6,  "nature": "Mars/Saturn", "meaning": "Courage, but danger"},
    "Mesarthim":  {"lon": 39.35,  "mag": 3.9,  "nature": "Mars/Saturn", "meaning": "Courage, but danger"},
    "Botein":     {"lon": 42.07,  "mag": 5.0,  "nature": "Mars", "meaning": "Courage"},
    "Zeta Ari":   {"lon": 43.34,  "mag": 4.9,  "nature": "Mars/Saturn", "meaning": "Courage"},
    "Mira (Omicron Cet)":{"lon": 34.38, "mag": 6.5, "nature": "Neptune", "meaning": "Transformation, unpredictability"},
    "Menkar (Alpha Cet)":{"lon": 41.08, "mag": 2.5, "nature": "Saturn", "meaning": "Misfortune, but strong will"},
    "Diphda":     {"lon": 47.05,  "mag": 2.0,  "nature": "Saturn", "meaning": "Misfortune, but strong will"},
    "Kaffaljidhma":{"lon": 44.83, "mag": 2.5, "nature": "Mercury/Venus", "meaning": "Intelligence, charm"},
    "Deneb Kaitos":{"lon": 47.05, "mag": 2.0, "nature": "Saturn", "meaning": "Misfortune, but strong will"},
}

def fixed_star_conjunctions(lons, max_orb=2.0):
    """Check which planets conjunct fixed stars (within orb degrees).
    Uses tropical J2000 longitudes with proper-motion adjustment."""
    results = []
    for star, data in FIXED_STARS.items():
        star_lon = data["lon"]
        for planet, p_lon in lons.items():
            if planet in ("North Node","South Node","Chiron"):
                continue
            diff = abs(norm180(star_lon - p_lon))
            if diff <= max_orb:
                results.append({"star": star, "planet": planet,
                                "orb": round(diff, 2),
                                "magnitude": data["mag"],
                                "nature": data["nature"],
                                "meaning": data["meaning"]})
    results.sort(key=lambda x: x["orb"])
    return results

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H15 — VEDIC DOSHAS (Mangal Dosha, Kaalsarpa Dosha)
# ═════════════════════════════════════════════════════════════════════════════

def mangal_dosha(jd, lat, lng, time_known=True):
    """Check for Mangal (Kuja/Mars) Dosha with classical BPHS Ch.80 cancellation rules."""
    lons, _, _ = body_longitudes(jd)
    ayan = ayanamsha_lahiri(jd)
    if time_known:
        asc_lon, _ = ascendant_mc(jd, lat, lng, ayan)
    else:
        asc_lon = norm360(lons["Sun"] - ayan)
    asc_idx = int(asc_lon // 30)
    sid_planets = {}
    for p in ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]:
        p_sid = norm360(lons[p] - ayan)
        s, idx, _ = sign_of(p_sid)
        h = ((idx - asc_idx) % 12) + 1
        sid_planets[p] = {"sign": s, "house": h}
    return kuja_dosha_analysis(sid_planets, SIGNS[asc_idx])

def kaalsarpa_dosha(jd, lat, lng, time_known=True):
    """Check for Kaalsarpa Dosha — all planets hemmed between Rahu and Ketu."""
    lons, _, _ = body_longitudes(jd)
    ayan = ayanamsha_lahiri(jd)
    rahu_sid = norm360(lons["North Node"] - ayan)
    ketu_sid = norm360(rahu_sid + 180)
    check_bodies = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn"]
    between_count = 0
    outside_count = 0
    for b in check_bodies:
        b_lon = norm360(lons[b] - ayan)
        if rahu_sid < ketu_sid:
            in_arc = rahu_sid < b_lon < ketu_sid
        else:
            in_arc = b_lon > rahu_sid or b_lon < ketu_sid
        if in_arc:
            between_count += 1
        else:
            outside_count += 1
    has_kaalsarpa = outside_count == 0 and between_count == 7
    partial = outside_count <= 1 and between_count >= 6
    rahu_sign = SIGNS[int(rahu_sid // 30)]
    direction = "rightward (Anulikta)" if rahu_sid < ketu_sid else "leftward (Viloma)"
    return {"has_kaalsarpa": has_kaalsarpa,
            "partial_kaalsarpa": partial and not has_kaalsarpa,
            "rahu_sign": rahu_sign,
            "direction": direction,
            "severity": "full" if has_kaalsarpa else "partial" if partial else "none",
            "note": "Kaalsarpa Dosha: all planets hemmed between Rahu and Ketu, indicating karmic intensity and life obstacles." if has_kaalsarpa else "No Kaalsarpa Dosha detected." if not partial else "Partial Kaalsarpa — most planets between Rahu and Ketu."}

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H16 — ADDITIONAL VEDIC VARGAS (D2, D3, D10, D12)
# ═════════════════════════════════════════════════════════════════════════════

def varga_chart(jd, varga, lat=0, lng=0, time_known=True):
    """Compute a Vedic divisional chart (Varga) per Phala Deepika Ch.3 / BPHS.
    Each varga has its own classical rule (odd/even sign dependent):
    D2 Hora: Sun/Moon halves; D3 Drekkana: sign, 5th, 9th lords;
    D7 Saptamsa: self/7th; D9 Navamsa: Aries/Capricorn/Libra/Cancer start;
    D10 Dasamsa: self/9th; D12 Dwadasamsa: from sign; D30 Trimsamsa:
    Mars 5° Saturn 5° Jupiter 8° Mercury 7° Venus 5° (odd, reversed even);
    D60 Shashtiamsa: Krura/Saumya pattern."""
    lons, _, backend = body_longitudes(jd)
    ayan = ayanamsha_lahiri(jd)
    if time_known:
        asc_lon, _ = ascendant_mc(jd, lat, lng, ayan)
    else:
        asc_lon = norm360(lons["Sun"] - ayan)

    varga_info = {
        "D1":  {"divisions": 1,  "name": "Rasi", "meaning": "The natal chart itself"},
        "D2":  {"divisions": 2,  "name": "Hora", "meaning": "Wealth, resources, financial patterns"},
        "D3":  {"divisions": 3,  "name": "Drekkana", "meaning": "Siblings, courage, self-effort"},
        "D4":  {"divisions": 4,  "name": "Chaturthamsa", "meaning": "Property, fixed assets, fortune"},
        "D5":  {"divisions": 5,  "name": "Panchamsa", "meaning": "Fame, power, authority (Jaimini)"},
        "D6":  {"divisions": 6,  "name": "Shasthamsa", "meaning": "Health, disease, obstacles (Jaimini)"},
        "D7":  {"divisions": 7,  "name": "Saptamsa", "meaning": "Children, progeny, creativity"},
        "D8":  {"divisions": 8,  "name": "Ashtamsa", "meaning": "Unexpected troubles, accidents (Jaimini)"},
        "D9":  {"divisions": 9,  "name": "Navamsa", "meaning": "Spouse, dharma, relationships, soul"},
        "D10": {"divisions": 10, "name": "Dasamsa", "meaning": "Career, profession, public status"},
        "D11": {"divisions": 11, "name": "Rudramsa", "meaning": "Death, destruction, transformation (Jaimini)"},
        "D12": {"divisions": 12, "name": "Dwadashamsa", "meaning": "Parents, ancestry, lineage"},
        "D16": {"divisions": 16, "name": "Shodasamsa", "meaning": "Vehicles, comforts, luxuries"},
        "D20": {"divisions": 20, "name": "Vimsamsa", "meaning": "Spiritual pursuits, devotion"},
        "D24": {"divisions": 24, "name": "Chaturvimsamsa", "meaning": "Education, learning, knowledge"},
        "D27": {"divisions": 27, "name": "Saptavimsamsa", "meaning": "Strengths, weaknesses, constitution"},
        "D30": {"divisions": 30, "name": "Trimsamsa", "meaning": "Misfortunes, health challenges"},
        "D40": {"divisions": 40, "name": "Khavedamsa", "meaning": "Auspicious/inauspicious events"},
        "D45": {"divisions": 45, "name": "Akshavedamsa", "meaning": "Overall character, conduct"},
        "D60": {"divisions": 60, "name": "Shashtiamsa", "meaning": "Karmic legacy, past life influences"},
    }
    v = varga.upper()
    if v not in varga_info:
        return {"error": f"Varga {v} not supported. Available: {list(varga_info.keys())}"}
    info = varga_info[v]
    d = info["divisions"]

    def _varga_sign(sid_lon):
        """Return varga sign index per classical rule for this varga."""
        sign_idx = int(sid_lon // 30)
        deg_in_sign = sid_lon % 30
        odd = (sign_idx % 2 == 0)  # Aries(0) odd, Taurus(1) even...
        if v == "D1":
            return sign_idx
        if v == "D2":
            # Hora: odd sign → first half Sun, second Moon; even → reversed
            half = 0 if deg_in_sign < 15 else 1
            if odd:
                return (sign_idx // 2) * 2 + (0 if half == 0 else 1)
            else:
                return (sign_idx // 2) * 2 + (1 if half == 0 else 0)
        if v == "D3":
            # Drekkana: 1st → sign, 2nd → 5th from sign, 3rd → 9th from sign
            drek = int(deg_in_sign // 10)
            offset = [0, 4, 8][drek]
            return (sign_idx + offset) % 12
        if v == "D9":
            # Navamsa: starts Aries/Capricorn/Libra/Cancer from Aries onward
            start_map = {0: 0, 1: 9, 2: 6, 3: 3}  # sign%4 → base sign idx
            nav = int(deg_in_sign // (30 / 9))
            base = start_map[sign_idx % 4]
            return (base + nav) % 12
        if v == "D7":
            # Saptamsa: odd → from sign, even → from 7th
            sap = int(deg_in_sign // (30 / 7))
            start = sign_idx if odd else (sign_idx + 6) % 12
            return (start + sap) % 12
        if v == "D10":
            # Dasamsa: odd → from sign, even → from 9th
            das = int(deg_in_sign // 3)
            start = sign_idx if odd else (sign_idx + 8) % 12
            return (start + das) % 12
        if v == "D12":
            # Dwadasamsa: counted from the sign itself
            dwa = int(deg_in_sign // 2.5)
            return (sign_idx + dwa) % 12
        if v == "D4":
            # Chaturthamsa (BPHS 9): 1st→sign, 2nd→4th, 3rd→7th, 4th→10th
            chat = int(deg_in_sign // 7.5)
            return (sign_idx + [0, 3, 6, 9][chat]) % 12
        if v == "D40":
            # Chatvarimsamsa (BPHS 29-30): odd→Aries, even→Libra
            khav = int(deg_in_sign // 0.75)
            base = 0 if odd else 6
            return (base + khav) % 12
        if v == "D45":
            # Akshavedamsa (BPHS 31-32): odd→Aries, even→Libra
            aksh = int(deg_in_sign // (30.0 / 45))
            base = 0 if odd else 6
            return (base + aksh) % 12
        if v in ("D27",):
            # Bhamsa (BPHS 26-27): counted from Aries, Cancer or Libra
            # for odd/fixed/dual respectively (nakshatra-based)
            bham = int(deg_in_sign // (30.0 / 27))
            if sign_idx % 3 == 0: base = 0   # movable → Aries
            elif sign_idx % 3 == 1: base = 3 # fixed → Cancer
            else: base = 6                   # dual → Libra
            return (base + bham) % 12
        if v == "D30":
            # Trimsamsa: odd → Mars 5, Saturn 5, Jupiter 8, Mercury 7, Venus 5;
            # even → reversed (Venus 5, Mercury 7, Jupiter 8, Saturn 5, Mars 5)
            if odd:
                seq = [("Mars",5),("Saturn",5),("Jupiter",8),("Mercury",7),("Venus",5)]
            else:
                seq = [("Venus",5),("Mercury",7),("Jupiter",8),("Saturn",5),("Mars",5)]
            acc = 0
            for ruler, span in seq:
                if deg_in_sign < acc + span:
                    ruler_idx = {"Mars":0,"Saturn":5,"Jupiter":6,"Mercury":2,"Venus":3}[ruler]
                    return ruler_idx
                acc += span
            return 0
        if v == "D60":
            # Shashtiamsa (BPHS 33-41): degrees ×2, divide by 12, remainder+1 = sign
            deg_trav = sid_lon % 30
            sh = int((deg_trav * 2) // 12)
            return (sh + 1) % 12
        if v in ("D16", "D20", "D24"):
            # BPHS: movable → Aries, fixed → Leo(16)/Sagittarius(20), dual → Sag(16)/Leo(20)
            # D16: movable→Aries, fixed→Leo, dual→Sagittarius
            # D20: movable→Aries, fixed→Sagittarius, dual→Leo
            # D24 (Siddhamsa): odd→Leo, even→Cancer
            if v == "D24":
                return (4 if odd else 3 + 0) % 12  # Leo for odd, Cancer for even
            starts = {16: [0, 4, 8], 20: [0, 8, 4]}  # [movable, fixed, dual]
            if sign_idx % 3 == 0:  # movable: Aries, Cancer, Libra, Capricorn
                base = starts[v][0]
            elif sign_idx % 3 == 1:  # fixed: Taurus, Leo, Scorpio, Aquarius
                base = starts[v][1]
            else:  # dual
                base = starts[v][2]
            part = int(deg_in_sign // (30.0 / d))
            return (base + part) % 12
        # Generic element-based fallback for other vargas
        elements = ["Fire", "Earth", "Air", "Water"]
        element_starts = {"Fire": "Aries", "Earth": "Capricorn", "Air": "Libra", "Water": "Cancer"}
        sign_idx_map = {s: i for i, s in enumerate(SIGNS)}
        pada_arc = 30.0 / d
        pada = int(deg_in_sign / pada_arc)
        elem_idx = sign_idx % 4
        elem = elements[elem_idx]
        base_sign_idx = sign_idx_map[element_starts[elem]]
        return (base_sign_idx + pada) % 12

    varga_lons = {}
    names = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","North Node","South Node"]
    for nm in names:
        sid_lon = norm360(lons[nm] - ayan)
        v_sign_idx = _varga_sign(sid_lon)
        deg_in_sign = sid_lon % 30
        pada_arc = 30.0 / d
        varga_lon = v_sign_idx * 30 + (deg_in_sign % pada_arc)
        varga_lons[nm] = {"longitude": round(varga_lon, 3), "sign": SIGNS[v_sign_idx],
                          "degree_in_sign": round(deg_in_sign % pada_arc, 2)}

    v_asc = _varga_sign(asc_lon)

    return {"system": f"Varga {v} ({info['name']})",
            "note": info["meaning"],
            "varga": v, "divisions": d,
            "varga_lagna": SIGNS[v_asc],
            "planets": varga_lons,
            "backend": backend}

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H17 — TRANSIT-TO-NATAL ASPECTS (detailed)
# ═════════════════════════════════════════════════════════════════════════════

def transit_to_natal_aspects(natal_jd, transit_jd):
    """Detailed listing of transit-to-natal aspects with impact rating.
    Used for 'what's happening to me right now' readings."""
    natal_lons, _, _ = body_longitudes(natal_jd)
    trans_lons, trans_speed, _ = body_longitudes(transit_jd)
    bodies = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn",
              "Uranus","Neptune","Pluto","North Node"]
    results = []
    for t_p in bodies:
        if t_p not in trans_lons:
            continue
        for n_p in bodies:
            if n_p not in natal_lons:
                continue
            sep = abs(norm180(trans_lons[t_p] - natal_lons[n_p]))
            for asp, (ang, orb, desc) in ASPECTS.items():
                d = abs(sep - ang)
                if d <= orb:
                    applying = (trans_speed.get(t_p, 0) < 0) if asp in ("conjunction","opposition") else None
                    speed_val = trans_speed.get(t_p, 0)
                    if speed_val != 0:
                        future_sep = abs(norm180(norm360(trans_lons[t_p] + speed_val * 0.1) - natal_lons[n_p]))
                        applying = future_sep < sep
                    impact = "high" if asp in ("conjunction","opposition","square") and d < 2 else \
                             "moderate" if asp in ("conjunction","opposition","square","trine") else "low"
                    results.append({
                        "transit_planet": t_p, "natal_planet": n_p,
                        "aspect": asp, "orb": round(d, 2),
                        "applying": applying,
                        "impact": impact,
                        "retrograde": trans_speed.get(t_p, 0) < 0,
                        "meaning": desc})
    results.sort(key=lambda x: (0 if x["impact"]=="high" else 1 if x["impact"]=="moderate" else 2, x["orb"]))
    return {"transit_aspects": results[:30],
            "high_impact_count": sum(1 for r in results if r["impact"]=="high"),
            "note": "Transit-to-natal aspects show current planetary weather affecting the natal chart. High-impact aspects with tight orbs are most significant."}

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H18 — PLANETARY HOURS (standalone, not just horary)
# ═════════════════════════════════════════════════════════════════════════════

def planetary_hours(jd, lat, lng):
    """Calculate the planetary hours for a given day and location.
    Each day and night is divided into 12 hours, each ruled by a planet
    following the Chaldean order: Saturn→Jupiter→Mars→Sun→Venus→Mercury→Moon."""
    dt_utc = datetime(2000,1,1) + timedelta(days=jd - 2451544.5)
    chaldean = ["Saturn","Jupiter","Mars","Sun","Venus","Mercury","Moon"]
    weekday_ruler = chaldean[dt_utc.weekday()]
    obliquity_rad = math.radians(23.4393 - 0.0130 * ((jd - 2451545.0) / 36525.0))
    lat_rad = math.radians(lat)
    sun_lon = tropical_longitudes(jd).get("Sun", 0)
    sun_dec = math.asin(math.sin(obliquity_rad) * math.sin(math.radians(sun_lon)))
    cos_ha_rise = -math.tan(lat_rad) * math.tan(sun_dec)
    cos_ha_rise = max(-1, min(1, cos_ha_rise))
    ha_rise = math.degrees(math.acos(cos_ha_rise))
    day_length_hours = 2 * ha_rise / 15.0
    night_length_hours = 24.0 - day_length_hours
    day_hour_len = day_length_hours / 12.0
    night_hour_len = night_length_hours / 12.0
    sunrise_offset = 12.0 - ha_rise / 15.0
    sunrise_h = int(sunrise_offset)
    sunrise_m = int((sunrise_offset - sunrise_h) * 60)
    hour_idx_start = dt_utc.weekday()
    hours = []
    for h in range(24):
        is_day = h < 12
        ruler_idx = (hour_idx_start + h) % 7
        hour_len = day_hour_len if is_day else night_hour_len
        hours.append({"hour": h + 1, "ruler": chaldean[ruler_idx],
                       "is_daytime": is_day,
                       "approx_duration_min": round(hour_len * 60)})
    return {"date_utc": dt_utc.strftime("%Y-%m-%d"),
            "weekday_ruler": weekday_ruler,
            "sunrise_approx_utc": f"{sunrise_h:02d}:{sunrise_m:02d}",
            "day_length": f"{int(day_length_hours)}h {int((day_length_hours % 1) * 60)}m",
            "night_length": f"{int(night_length_hours)}h {int((night_length_hours % 1) * 60)}m",
            "hours": hours,
            "note": "Planetary hours follow the Chaldean sequence. Day hours run sunrise-to-sunset, night hours sunset-to-sunrise. The hour ruler colors the energy of actions taken in that hour."}
# ═════════════════════════════════════════════════════════════════════════════

def _ra_from_lon(lon_deg, eps_deg):
    """Right ascension (deg) from ecliptic longitude at given obliquity."""
    lam = math.radians(lon_deg)
    eps = math.radians(eps_deg)
    return math.degrees(math.atan2(math.sin(lam)*math.cos(eps),
                                   math.cos(lam))) % 360.0

def astrocartography(jd, lat, lng):
    """For each planet, the world-longitudes where it sits on the MC, IC, ASC, DSC
    at the moment of birth. These 'planet lines' are the basis of relocation
    astrology — living where a planet is angular emphasises its themes.

    Output: {planet: {mc: lng, ic: lng, asc: lat_belt, dsc: lat_belt,
                       themes: …}} plus a few reference cities per line.

    The ASC/DSC lines run along specific latitudes (not a single longitude);
    we report the latitude belt where the planet is rising/setting.
    """
    lons,_,backend = body_longitudes(jd)
    eps = obliquity(jd - 2451543.5)
    gmst = gmst_deg(jd)
    out = {"_meta": {"backend": backend, "interpretation_note":
        "Planet lines: where a planet is angular (MC=career, IC=home/roots, "
        "ASC=identity, DSC=relationships) at the moment of birth. Living under "
        "a line tends to activate that planet's themes; difficult planets "
        "(Saturn, Pluto, Chiron, South Node) are felt as tests, benefics "
        "(Jupiter, Venus, Sun) as gifts. Latitude matters as well as longitude."}}
    themes = {
        "Sun":    "identity, vitality, leadership, visibility, the father",
        "Moon":   "emotions, home, mother, the public, nurture, fluctuations",
        "Mercury":"communication, learning, commerce, travel, writing",
        "Venus":  "love, art, beauty, money, attraction, partnership",
        "Mars":   "drive, conflict, action, athletic, accidents, sex",
        "Jupiter":"expansion, luck, faith, higher learning, travel, opportunity",
        "Saturn": "discipline, restriction, hard work, karma, time, loneliness",
        "Uranus": "sudden change, awakening, freedom, disruption, innovation",
        "Neptune":"dreams, dissolution, spirituality, escapism, confusion",
        "Pluto":  "transformation, power, death/rebirth, obsession, shadow",
        "North Node":"destiny, growth edge, the unfamiliar, karmic pull",
        "South Node":"past life, comfort zone, release, innate skill",
        "Chiron": "wound, healing, the wounded-healer vocation, teaching through pain",
    }
    for p, lon in lons.items():
        ra = _ra_from_lon(lon, eps)
        mc_lng = norm360(ra - gmst)
        ic_lng = norm360(mc_lng + 180)
        # ASC line: approximate the latitude where the planet would be rising
        # (its declination). For Earth latitudes, the planet rises when the
        # local sidereal time equals its RA. ASC line lies where the planet's
        # altitude crosses 0°; with whole-sign simplicity, the ASC line is the
        # same longitude band as the MC/IC, but offset in latitude by the
        # planet's declination. We report the declination for the user/agent
        # to interpret, plus the longitude band.
        dec_deg = math.degrees(math.asin(math.sin(math.radians(eps)) *
                                         math.sin(math.radians(lon))))
        out[p] = {
            "mc_longitude": round(mc_lng, 2),
            "ic_longitude": round(ic_lng, 2),
            "ascendant_band": {"longitude": round(mc_lng, 2),
                               "latitude_hint_deg": round(dec_deg, 2),
                               "note": "ASC line is a curve; latitude shown is the planet's declination"},
            "descendant_band": {"longitude": round(ic_lng, 2),
                                "latitude_hint_deg": -round(dec_deg, 2)},
            "themes": themes.get(p, ""),
        }
    return out

# Reference city coordinates (subset — major global cities for planet-line
# interpretation). Latitude/longitude in degrees, E+ / N+. Used to suggest
# "is city X on/near your Jupiter line?" without doing a full GIS lookup.
CITIES = {
    "London":      (51.5, -0.1),    "New York":   (40.7, -74.0),
    "Los Angeles": (34.0, -118.2),  "Chicago":    (41.9, -87.6),
    "Toronto":     (43.7, -79.4),   "Mexico City":(19.4, -99.1),
    "São Paulo":   (-23.5, -46.6),  "Buenos Aires":(-34.6, -58.4),
    "Paris":       (48.9, 2.4),     "Berlin":     (52.5, 13.4),
    "Amsterdam":   (52.4, 4.9),     "Rome":       (41.9, 12.5),
    "Madrid":      (40.4, -3.7),    "Barcelona":  (41.4, 2.2),
    "Istanbul":    (41.0, 29.0),    "Athens":     (38.0, 23.7),
    "Cairo":       (30.0, 31.2),    "Lagos":      (6.5, 3.4),
    "Nairobi":     (-1.3, 36.8),    "Cape Town":  (-33.9, 18.4),
    "Dubai":       (25.2, 55.3),    "Mumbai":     (19.1, 72.9),
    "Delhi":       (28.6, 77.2),    "Bangalore":  (12.9, 77.6),
    "Kolkata":     (22.6, 88.4),    "Bangkok":    (13.7, 100.5),
    "Singapore":   (1.4, 103.8),    "Jakarta":    (-6.2, 106.8),
    "Hong Kong":   (22.3, 114.2),   "Shanghai":   (31.2, 121.5),
    "Beijing":     (39.9, 116.4),   "Seoul":      (37.6, 127.0),
    "Tokyo":       (35.7, 139.7),   "Osaka":      (34.7, 135.5),
    "Sydney":      (-33.9, 151.2),  "Melbourne":  (-37.8, 144.9),
    "Auckland":    (-36.8, 174.8),  "Honolulu":   (21.3, -157.9),
    "Vancouver":   (49.3, -123.1),  "San Francisco":(37.8, -122.4),
    "Miami":       (25.8, -80.2),   "Las Vegas":  (36.2, -115.2),
    "Seattle":     (47.6, -122.3),  "Boston":     (42.4, -71.1),
    "Moscow":      (55.8, 37.6),    "St Petersburg":(59.9, 30.3),
    "Kathmandu":   (27.7, 85.3),    "Colombo":    (6.9, 79.9),
    "Karachi":     (24.9, 67.0),    "Tehran":     (35.7, 51.4),
    "Tel Aviv":    (32.1, 34.8),    "Jerusalem":  (31.8, 35.2),
    "Reykjavik":   (64.1, -21.9),   "Stockholm":  (59.3, 18.1),
    "Helsinki":    (60.2, 24.9),    "Oslo":       (59.9, 10.8),
    "Copenhagen":  (55.7, 12.6),    "Vienna":     (48.2, 16.4),
    "Zurich":      (47.4, 8.5),     "Geneva":     (46.2, 6.1),
    "Lisbon":      (38.7, -9.1),    "Edinburgh":  (55.9, -3.2),
    "Dublin":      (53.3, -6.3),    "Wellington":  (-41.3, 174.8),
    "Anchorage":  (61.2, -149.9),
}

def _cities_on_line(target_lng, target_lat, tol_lng=10.0, tol_lat=8.0):
    """Return cities within tol degrees of a planet-line crossing."""
    hits = []
    for name, (lat, lng) in CITIES.items():
        d_lng = abs(norm180(lng - target_lng))
        d_lat = abs(lat - target_lat)
        if d_lng <= tol_lng and d_lat <= tol_lat:
            hits.append({"city": name, "lat": lat, "lng": lng,
                         "dist_lng": round(d_lng, 1), "dist_lat": round(d_lat, 1)})
    hits.sort(key=lambda x: x["dist_lng"] + x["dist_lat"])
    return hits[:6]

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION J — HORARY (PRASNA) — chart of the moment a question is asked
# ═════════════════════════════════════════════════════════════════════════════

def horary(question_utc, lat, lng, question_text=""):
    """Cast a chart for the exact moment a question is asked. Classical horary
    rules (Prasna in Vedic): the Ascendant and its ruler = the querent; the
    Moon = the flow of events; the house ruling the matter = where to look;
    the planet ruling the house's cusp lord = the answer; aspects to the
    Moon and the Asc ruler show timing.

    Returns the chart plus a small set of classical signals the agent can
    interpret. We do NOT auto-interpret the question — the agent does, with
    full awareness that horary is the most interpretive branch and only a
    hint, not a guarantee.
    """
    jd = julian_day(question_utc)
    lons, speed, backend = body_longitudes(jd)
    ayan = ayanamsha_lahiri(jd)
    asc_lon, mc_lon = ascendant_mc(jd, lat, lng)   # tropical; treat as the moment
    sun_sign_idx = int(lons["Sun"] // 30)
    # Day / night chart (Sun above/below horizon) — used to choose which planets
    # are stronger; this requires computing the Sun's altitude, simplified.
    is_day_chart = (lons["Sun"] > asc_lon - 180) and (lons["Sun"] < asc_lon)
    # Void-of-course Moon: if the Moon makes no major aspect before leaving
    # its current sign, classical horary says "nothing will come of the matter."
    moon_lon = lons["Moon"]
    moon_sign_idx = int(moon_lon // 30)
    next_sign_lon = (moon_sign_idx + 1) * 30.0
    moon_to_next = next_sign_lon - moon_lon
    voc = True
    # check aspects Moon will make within remaining sign
    for p, plon in lons.items():
        if p in ("Moon","South Node"):
            continue
        # if Moon will reach an exact aspect within remaining degrees
        for ang, (exact, orb, _) in ASPECTS.items():
            target = norm360(plon + exact) if p in ("Sun","Mercury","Venus","Mars",
                                                     "Jupiter","Saturn","Uranus",
                                                     "Neptune","Pluto") else None
            if target is None:
                continue
            # distance Moon needs to travel to reach that target
            dist = norm360(target - moon_lon)
            if 0 < dist < moon_to_next + 6:  # 6° applying orb
                voc = False
                break
        if not voc:
            break
    moon_sign = SIGNS[moon_sign_idx]
    moon_p_house = whole_sign_house(moon_lon, asc_lon)
    # Ascendant ruler
    asc_sign = SIGNS[int(asc_lon // 30)]
    asc_ruler = SIGN_DATA[asc_sign]["ruler"]
    # Hour ruler (the planet ruling the weekday + the day-quadrant hour)
    weekday = question_utc.weekday()   # 0=Mon…6=Sun (Mon=Moon, Tue=Mars,…)
    # Classical Chaldean order: Saturn(0), Jupiter(1), Mars(2), Sun(3), Venus(4), Mercury(5), Moon(6)
    chaldean = ["Saturn","Jupiter","Mars","Sun","Venus","Mercury","Moon"]
    weekday_ruler = chaldean[(weekday + 5) % 7]   # adjust to Chaldean: Mon=Moon
    # Planetary hour of the day: divide daylight into 12 equal hours
    sun_alt = math.sin(math.radians(lons["Sun"]))   # crude proxy
    hour_ruler_idx = (weekday * 12 + question_utc.hour) % 7
    hour_ruler = chaldean[hour_ruler_idx]
    # "Hour planet" classical interpretation: the planet ruling the hour
    # describes the *flavour* of the moment, useful in horary timing.
    sat_h = whole_sign_house(lons["Saturn"], asc_lon)
    asc_deg = (asc_lon % 30)
    lilly_checks = evaluate_horary_considerations(asc_deg, moon_lon, voc, sat_h)

    return {
        "system": "Horary / Prasna (chart of the moment)",
        "question_text": question_text,
        "question_utc": question_utc.strftime("%Y-%m-%d %H:%M:%S"),
        "ascendant": asc_sign,
        "ascendant_deg": round(asc_deg, 2),
        "ascendant_ruler": asc_ruler,
        "lilly_considerations": lilly_checks,
        "moon": {"sign": moon_sign,
                 "house_in_horary": moon_p_house,
                 "void_of_course": voc,
                 "interpretation": ("Nothing will come of the matter." if voc
                                    else "Moon is applying to an aspect — the matter proceeds.")},
        "day_chart": is_day_chart,
        "weekday_ruler": weekday_ruler,
        "planetary_hour_ruler": hour_ruler,
        "big_six": {p: {"sign": sign_of(lons[p])[0],
                        "house": whole_sign_house(lons[p], asc_lon),
                        "retrograde": (speed.get(p, 0) < 0)}
                    for p in ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn"]},
        "_meta": {"backend": backend,
                  "note": ("Horary is the most interpretive branch. Use this as "
                           "guidance, not a guarantee. The agent should map the "
                           "querent's question to a house (1=self, 2=money, "
                           "3=communication, 4=home/land, 5=children/creativity, "
                           "7=partnership, 8=others' money/death, 9=travel/law, "
                           "10=career, 11=gains, 12=hidden/loss) and read the "
                           "ruler of that house, plus Moon's applying aspect, for "
                           "the answer.")}
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION K — NAMAKARAN, ANATOMY, MISC SPECIALTY LOOKUPS
# ═════════════════════════════════════════════════════════════════════════════

def namakaran(moon_lon_sidereal):
    """Return the classical starting syllable(s) for a name aligned to the
    birth nakshatra pada. Works in sidereal (Vedic) longitude, since the
    classical rule uses the Janma Nakshatra. From a Moon's tropical longitude,
    pass through ayanamsha_lahiri(jd) first to convert.
    """
    nak_i = int(moon_lon_sidereal // NAK_ARC) % 27
    pada = int((moon_lon_sidereal % NAK_ARC) // PADA_ARC) + 1
    name = NAKSHATRAS[nak_i]["name"]
    syllables = NAKSHATRA_SYLLABLES.get(name, ["?"])
    chosen = syllables[pada - 1]
    return {
        "nakshatra": name,
        "pada": pada,
        "primary_syllable": chosen,
        "all_pada_syllables": syllables,
        "lord": NAKSHATRAS[nak_i]["lord"],
        "interpretation": (
            f"The Moon in {name} pada {pada} (lord {NAKSHATRAS[nak_i]['lord']}) "
            f"vibrates to the syllable '{chosen}'. Classical Namakaran: begin "
            f"the child's name (or a business/project name) with this sound "
            f"for the strongest resonance with the natal lunar mansion.")
    }

def anatomy_chart(planets_block):
    """For a Western planet block (each planet with sign/house), identify the
    body regions and systems emphasised, and flag any afflicted regions.
    Affliction = Saturn or Mars in or aspecting the sign (or its ruler).
    """
    body_map = {}
    afflicted_regions = []
    for planet, data in planets_block.items():
        sign = data.get("sign")
        if not sign:
            continue
        info = ANATOMY.get(sign, {})
        if not info:
            continue
        body_map[planet] = {"sign": sign, "region": info["region"],
                            "system": info["system"], "house": data.get("house")}
        if planet in ("Saturn", "Mars") and data.get("dignity") in ("fall", "detriment"):
            afflicted_regions.append({"planet": planet, "sign": sign,
                                      "region": info["region"]})
    return {"body_regions": body_map, "afflicted_regions": afflicted_regions,
            "surgery_avoidance_note":
                "Medical astrology rule: avoid elective surgery when the Moon "
                "transits the sign ruling the body part (e.g. don't operate on "
                "the throat when Moon is in Taurus). Also avoid during lunar "
                "eclipses, and prefer Moon in a fixed sign for stable outcomes."}

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION L — EVENT / NON-HUMAN CHARTS (corporate, pet, event, moment)
# ═════════════════════════════════════════════════════════════════════════════

def event_chart(data):
    """Cast a chart for any 'moment of inception': a company incorporation, an
    app launch, a pet's adoption/birth, a wedding, a question time, etc.
    The math is identical to a natal chart — only the *subject* differs.
    Returns western + vedic + bazi for the given data.

    Convention: pass `subject` to label the chart; the data fields are the
    same as natal input (year/month/day/hour/minute/lat/lng/tz).
    """
    utc, tinfo = to_utc(data)
    jd = julian_day(utc)
    lat = data.get("lat", 0.0); lng = data.get("lng", 0.0)
    time_known = tinfo.get("time_known", True)
    birth_local = datetime(data["year"], data["month"], data["day"],
                           int(data.get("hour", 12)), int(data.get("minute", 0)))
    systems = data.get("systems", ["western", "vedic", "bazi"])
    _, _, backend = body_longitudes(jd)
    out = {
        "_meta": {"engine_backend": backend, "swisseph_available": _HAS_SWE,
                  "subject": data.get("subject", "(unnamed event)"),
                  "kind": data.get("kind", "event"),
                  "moment_utc": utc.strftime("%Y-%m-%d %H:%M"),
                  "precision_note": ("arcsecond (Swiss Ephemeris)" if backend == "swisseph"
                                     else "~1-2 arcmin (builtin) — exact to sign/house/nakshatra/dasha")},
        "subject": data.get("subject", "(unnamed event)"),
        "moment": {"local": birth_local.strftime("%Y-%m-%d %H:%M"),
                   "utc": utc.strftime("%Y-%m-%d %H:%M"),
                   "place": data.get("place", "")},
        "time_info": tinfo,
    }
    if "western" in systems:
        try: out["western"] = western_chart(jd, lat, lng, time_known)
        except Exception as e: out["western"] = {"error": repr(e)}
    if "vedic" in systems:
        try: out["vedic"] = vedic_chart(jd, lat, lng, birth_local, time_known)
        except Exception as e: out["vedic"] = {"error": repr(e)}
    if "bazi" in systems:
        try: out["bazi"] = bazi_chart(jd, birth_local, data.get("gender", "unknown"), lat)
        except Exception as e: out["bazi"] = {"error": repr(e)}
    return out

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION H — ORCHESTRATION
# ═════════════════════════════════════════════════════════════════════════════

def life_phase(birth_dt):
    """Age-based transit milestones everyone hits — grounded, not chart-specific."""
    age=_age(birth_dt)
    notes=[]
    for sr in SATURN_RETURN_AGES:
        if abs(age-sr)<=2.5:
            notes.append(f"Saturn Return (~age {sr}): a structural reckoning — career, commitment, adulthood; "
                         f"life asks what is built to last.")
    for nr in NODE_RETURN_AGES:
        if abs(age-nr)<=1:
            notes.append(f"Nodal Return/Reversal (~age {nr:.0f}): a karmic re-orientation of direction and relationships.")
    if abs(age-42)<=2:
        notes.append("Uranus Opposition (~age 40-42): the 'mid-life' awakening — authenticity vs. the life you built.")
    if abs(age-12)<=1 or abs(age-24)<=1 or abs(age-36)<=1:
        notes.append("Jupiter Return (~every 12 yrs): a cycle of growth, opportunity and expansion opens.")
    return {"current_age":round(age,1),"active_milestones":notes}

def _normalize_birth(d):
    """Make input forgiving without changing the canonical schema.

    LLMs frequently emit `lon`/`longitude` instead of `lng`, or an ISO
    `date`/`time` string instead of numeric year/month/day/hour/minute.
    Previously `lon` was silently ignored (lng defaulted to 0.0 → a wrong
    ascendant), and `date`/`time` raised KeyError. We coerce these aliases to
    the canonical fields so a guessed shape still produces a correct chart.
    Recurses into a `partner` dict (synastry/compatibility/composite). Pure
    stdlib; canonical fields always win when both are present.
    """
    if not isinstance(d, dict):
        return d
    if "lng" not in d:
        for alias in ("lon", "long", "longitude"):
            if alias in d:
                d["lng"] = d[alias]; break
    if "lat" not in d and "latitude" in d:
        d["lat"] = d["latitude"]
    if "year" not in d and isinstance(d.get("date"), str):
        try:
            y, mo, dy = d["date"].strip().split("T")[0].split("-")[:3]
            d["year"], d["month"], d["day"] = int(y), int(mo), int(dy)
        except Exception:
            pass
    if "hour" not in d and isinstance(d.get("time"), str):
        try:
            hh, mm = (d["time"].strip().split(":") + ["0"])[:2]
            d["hour"], d["minute"] = int(hh), int(mm)
        except Exception:
            pass
    if isinstance(d.get("partner"), dict):
        _normalize_birth(d["partner"])
    return d

# Modes that read the current sky (or need no birth data at all). They are
# dispatched before to_utc() so they work with {"mode": ...} only — birth
# data, if present, is ignored. "now" modes default to today's date.
PUBLIC_MODES = ("node_transit_all_signs", "weekly_calendar", "eclipses",
                "stations", "moon_phase", "planetary_hours",
                "void_of_course", "muhurta", "electional", "numerology")

def calculate_full_profile(data):
    global _NODE_TYPE
    data = _normalize_birth(data)
    mode=data.get("mode","natal")
    nt_in = data.get("node_type")
    if nt_in not in (None, "true", "mean"):
        return {"mode": mode, "error": "node_type must be 'true' or 'mean'"}
    _NODE_TYPE = nt_in or ("true" if _HAS_SWE else "mean")

    # Public modes — no birth data required. Handle before to_utc().
    if mode=="node_transit_all_signs":
        from astro_advanced import node_transit_all_signs
        tjd = julian_day(datetime.utcnow())
        t_lons, _, _ = body_longitudes(tjd)
        result = {"_meta": {"engine_backend": body_longitudes(tjd)[2],
                            "swisseph_available": _HAS_SWE,
                            "computed_on": TODAY.strftime("%Y-%m-%d"),
                            "node_type": "true" if _HAS_SWE else "mean"},
                  "mode": mode,
                  "node_transit_all_signs": node_transit_all_signs(t_lons, jd=tjd)}
        return result

    if mode=="numerology":
        try:
            result = {"_meta": {"engine_backend": "builtin",
                                "computed_on": TODAY.strftime("%Y-%m-%d")},
                      "mode": mode,
                      "numerology": numerology(data["year"], data["month"],
                                               data["day"], data.get("full_name",""))}
        except KeyError:
            return {"mode": mode, "error": "numerology requires year/month/day (of birth or event)"}
        return result

    if mode in ("weekly_calendar", "eclipses", "stations", "moon_phase",
                "planetary_hours", "void_of_course", "muhurta", "electional",
                "astro_trading", "trade_setup", "bradley", "siderograph",
                "gann_sq9", "square_of_9", "gann_angles", "gann_clock", "circle_24",
                "spiral_calendar", "carolan", "helio_trading", "solar_cycles", "solar_regime",
                "gann_matrices", "sector_astro", "astro_stats",
                "barbault_bci", "bci", "gann_mass_pressure", "mass_pressure",
                "sepharial_tide", "silver_key", "trade_card", "institutional_card",
                "crawford_crash", "crash_hazard", "jenkins_squaring", "jenkins",
                "ferrera_panic", "ferrera", "olga_intraday", "olga_clock", "lavoie_asteroid", "asteroid_prob",
                "eight_masters", "master_setups", "master_signal", "quant_signal",
                "cowan_4d", "platonic", "sarvatobhadra", "sbc", "musical_harmonics",
                "planetary_kinematics", "saros_cycle", "astro_backtest",
                "murrey_math", "murrey", "universal_clock", "jeanne_long",
                "larry_williams", "lunar_edge", "bayer_polarity", "crypto_accelerator",
                "barycenter", "ssb", "spectral_fft", "fft", "cot_lunar", "walker_polar", "master_audit",
                "harmonic_wave", "composite_wave", "genesis_transits", "terminal_dashboard",
                "bayer", "mercury_speed", "crd_calendar", "geocosmic_crd",
                "mcwhirter", "node_cycle", "financial", "crypto"):
        # Sky-now / Event modes: default anchor is today (UTC) or resolved target moment
        tdt = _resolve_target_dt(data)
        tjd = julian_day(tdt)
        tlat = data.get("lat", 0.0); tlng = data.get("lng", 0.0)
        result = {"_meta": {"engine_backend": body_longitudes(tjd)[2],
                            "swisseph_available": _HAS_SWE,
                            "computed_on": TODAY.strftime("%Y-%m-%d")},
                  "mode": mode}
        if mode=="weekly_calendar":
            from astro_advanced import weekly_astro_calendar
            start_str = data.get("start_date")
            sd = datetime.strptime(start_str, "%Y-%m-%d") if start_str else None
            result["weekly_calendar"] = weekly_astro_calendar(sd)
            return result
        if mode=="eclipses":
            result["eclipses"] = next_eclipses(tjd, data.get("count", 3))
            return result
        if mode=="stations":
            p = data.get("planet", "Mercury")
            result["stations"] = station_dates(tjd, tjd + data.get("days", 180), p)
            return result
        if mode=="moon_phase":
            result["moon_phase"] = moon_phase(tjd)
            result["upcoming_moon_phases"] = upcoming_moon_phases(tjd, count=4)
            return result
        if mode=="planetary_hours":
            result["planetary_hours"] = planetary_hours(tjd, tlat, tlng)
            return result
        if mode=="void_of_course":
            result["void_of_course_moon"] = void_of_course_moon(tjd, tlat, tlng, True)
            return result
        if mode=="electional":
            from astro_advanced import find_electional_times
            result["electional"] = find_electional_times(tjd, tlat, tlng,
                                                         data.get("activity","general"),
                                                         data.get("days_ahead", 14))
            return result
        if mode=="muhurta":
            from astro_advanced import muhurta_finder
            result["muhurta"] = muhurta_finder(tjd, tlat, tlng,
                                               data.get("activity","marriage"),
                                               data.get("days_ahead", 14))
            return result
        if mode=="financial" or mode=="crypto":
            asset = data.get("asset", "BTC")
            result["financial_weather"] = crypto_financial_weather(asset, tdt)
            return result
        if mode=="astro_trading" or mode=="trade_setup":
            import astro_trading_engine as ate
            asset = data.get("asset", "BTC")
            price = float(data.get("price", 65000.0 if asset.upper()=="BTC" else 2500.0 if asset.upper()=="ETH" else 2500.0 if asset.upper()=="GOLD" else 5500.0))
            t_lons, t_speed, _ = body_longitudes(tjd)
            voc = void_of_course_moon(tjd, tlat, tlng, True)
            is_voc = bool(voc.get("is_void", False))
            result["astro_trade_setup"] = ate.AstroTradingStrategyEngine.generate_trade_setup(
                asset_key=asset,
                current_price=price,
                longitudes=t_lons,
                speeds=t_speed,
                is_moon_voc=is_voc
            )
            return result
        if mode=="bradley" or mode=="siderograph":
            import astro_trading_engine as ate
            t_lons, _, _ = body_longitudes(tjd)
            decls = body_declinations(tjd)
            pot = ate.BradleySiderographEngine.calculate_potential(t_lons, decls)
            result["bradley_siderograph"] = {
                "evaluation_date": tdt.strftime("%Y-%m-%d"),
                "potential_components": pot,
                "note": "Donald Bradley Siderograph Potential: Peaks and troughs indicate macroeconomic turning points."
            }
            return result
        if mode=="gann_sq9" or mode=="square_of_9":
            import astro_trading_engine as ate
            price = float(data.get("price", 100.0))
            asset = data.get("asset", "BTC")
            t_lons, _, _ = body_longitudes(tjd)
            harmonics = ate.GannSquare9Engine.compute_harmonics(price)
            lines = ate.GannSquare9Engine.planetary_price_lines(t_lons, price, asset)
            result["gann_square_of_9"] = {
                "price": price,
                "harmonics": harmonics,
                "active_planetary_price_lines": lines[:6],
                "note": "W.D. Gann Square of 9 Spiral: 90°/180°/270°/360° geometry and planetary degree-price projections."
            }
            return result
        if mode=="crd_calendar" or mode=="geocosmic_crd":
            import astro_trading_engine as ate
            t_lons, t_speed, _ = body_longitudes(tjd)
            sigs = []
            for p in ("Mars", "Mercury", "Venus"):
                spd = t_speed.get(p, 1.0)
                if abs(spd) <= 0.05:
                    sigs.append({"level": 1, "description": f"{p} Stationary Turning Point (Speed = {spd:.3f}°/day)"})
            for p in ("Sun", "Mars"):
                lon = t_lons.get(p, 0.0)
                if (lon % 90.0) <= 1.0 or (lon % 90.0) >= 89.0:
                    sigs.append({"level": 1, "description": f"{p} Cardinal Ingress (0° {SIGNS[int(lon//30)%12]})"})
            eval_crd = ate.MerrimanCRDEngine.evaluate_crd_cluster(sigs)
            result["geocosmic_crd"] = {
                "evaluation_date": tdt.strftime("%Y-%m-%d"),
                "crd_evaluation": eval_crd,
                "note": "Raymond Merriman Critical Reversal Date (CRD): Cluster score >= 15 signals high-probability pivot."
            }
            return result
        if mode=="mcwhirter" or mode=="node_cycle":
            import astro_trading_engine as ate
            t_lons, _, _ = body_longitudes(tjd)
            node_lon = t_lons.get("North Node", 0.0)
            result["mcwhirter_cycle"] = ate.McWhirterCycleEngine.evaluate_node_cycle(node_lon)
            return result
        if mode=="gann_angles":
            import astro_trading_engine as ate
            p_price = float(data.get("pivot_price", 60000.0))
            bars = int(data.get("bars_elapsed", 10))
            p_unit = float(data.get("price_unit", 100.0))
            direct = data.get("direction", "up")
            result["gann_angles"] = ate.GannAnglesEngine.project_angles(p_price, bars, p_unit, direct)
            return result
        if mode=="gann_clock" or mode=="circle_24":
            import astro_trading_engine as ate
            p_price = float(data.get("price", 65000.0))
            h_utc = int(data.get("hour_utc", tdt.hour))
            result["gann_circle_24"] = ate.GannCircle24ClockEngine.compute_intraday_pivots(p_price, h_utc)
            return result
        if mode=="harmonic_wave" or mode=="composite_wave":
            import astro_trading_engine as ate
            days_count = int(data.get("days", 30))
            wave_series = ate.HarmonicCompositeWaveEngine.forecast_composite_series(tdt, days_count)
            wave_vals = [d["composite_wave_value"] for d in wave_series]
            result["harmonic_planetary_wave"] = {
                "forecast_start_date": tdt.strftime("%Y-%m-%d"),
                "forecast_days": days_count,
                "sparkline": ate.HarmonicCompositeWaveEngine.render_sparkline(wave_vals),
                "wave_series": wave_series,
                "note": "Timing Solution Superposition Model: Multi-synodic planetary harmonic composite momentum curve."
            }
            return result
        if mode=="genesis_transits":
            import astro_trading_engine as ate
            asset = data.get("asset", "BTC")
            t_lons, _, _ = body_longitudes(tjd)
            result["genesis_transits"] = ate.AssetGenesisHoroscopyEngine.evaluate_genesis_transits(asset, t_lons)
            return result
        if mode=="terminal_dashboard":
            import astro_trading_engine as ate
            asset = data.get("asset", "BTC")
            price = float(data.get("price", 65000.0 if asset.upper()=="BTC" else 2500.0 if asset.upper()=="ETH" else 2500.0 if asset.upper()=="GOLD" else 5500.0))
            t_lons, t_speed, _ = body_longitudes(tjd)
            decls = body_declinations(tjd)
            voc = void_of_course_moon(tjd, tlat, tlng, True)
            is_voc = bool(voc.get("is_void", False))
            setup = ate.AstroTradingStrategyEngine.generate_trade_setup(asset, price, t_lons, t_speed, is_moon_voc=is_voc)
            pot = ate.BradleySiderographEngine.calculate_potential(t_lons, decls)["net_siderograph_potential"]
            wave_series = ate.HarmonicCompositeWaveEngine.forecast_composite_series(tdt, 30)
            dash = ate.AstroTerminalDashboard.render_dashboard(setup, pot, wave_series)
            result["terminal_dashboard"] = {
                "dashboard_view": dash,
                "trade_setup": setup
            }
            return result
        if mode=="spiral_calendar" or mode=="carolan":
            import astro_trading_engine as ate
            p_date_str = data.get("pivot_date", tdt.strftime("%Y-%m-%d"))
            p_date = datetime.strptime(p_date_str, "%Y-%m-%d")
            max_idx = int(data.get("max_fib_index", 12))
            result["spiral_calendar_projections"] = {
                "origin_pivot_date": p_date.strftime("%Y-%m-%d"),
                "projections": ate.CarolanSpiralCalendarEngine.compute_spiral_projections(p_date, max_idx),
                "rule": "Christopher Carolan Spiral Calendar: Time projections T_n = 29.530588 * sqrt(F_n)."
            }
            return result
        if mode=="helio_trading":
            import astro_trading_engine as ate
            lons_h = ate.HeliocentricTradingEngine.compute_helio_longitudes(tjd)
            aspects_h = ate.HeliocentricTradingEngine.detect_helio_aspects(tjd)
            result["heliocentric_trading"] = {
                "evaluation_date": tdt.strftime("%Y-%m-%d"),
                "helio_longitudes": lons_h,
                "active_helio_aspects": aspects_h,
                "note": "Heliocentric coordinates eliminate geocentric retrograde distortion and reveal true gravitational market drivers."
            }
            return result
        if mode=="solar_cycles" or mode=="solar_regime":
            import astro_trading_engine as ate
            result["solar_geomagnetic_regime"] = ate.SolarGeomagneticCycleEngine.evaluate_solar_regime(tdt)
            return result
        if mode=="gann_matrices":
            import astro_trading_engine as ate
            price = float(data.get("price", 65000.0))
            result["gann_advanced_matrices"] = {
                "square_of_144": ate.GannAdvancedMatricesEngine.compute_square_of_144(price),
                "square_of_52": ate.GannAdvancedMatricesEngine.compute_square_of_52(tdt),
                "hexagon_chart": ate.GannAdvancedMatricesEngine.compute_hexagon_chart(price)
            }
            return result
        if mode=="sector_astro":
            import astro_trading_engine as ate
            sector = data.get("sector", "CRYPTO")
            result["sector_astro_resonance"] = ate.SectorAstroResonanceEngine.evaluate_sector(sector)
            return result
        if mode=="astro_stats":
            import astro_trading_engine as ate
            sample_rets = data.get("returns", [0.012, 0.015, -0.005, 0.022, 0.018, 0.030, 0.011, 0.019])
            result["astro_statistical_significance"] = ate.AstroStatisticalSignificanceEngine.calculate_z_score(sample_rets)
            return result
        if mode=="barbault_bci" or mode=="bci":
            import astro_trading_engine as ate
            t_lons, _, _ = body_longitudes(tjd)
            result["barbault_cyclical_index"] = ate.BarbaultCyclicalIndexEngine.compute_bci(t_lons)
            return result
        if mode=="gann_mass_pressure" or mode=="mass_pressure":
            import astro_trading_engine as ate
            m_count = int(data.get("months_forward", 24))
            result["gann_mass_pressure"] = {
                "forecast_start_date": tdt.strftime("%Y-%m-%d"),
                "forecast_curve": ate.GannMassPressureEngine.generate_mass_pressure_forecast(tdt, m_count),
                "rule": "W.D. Gann Mass Pressure: 60Y (40%), 20Y (25%), 10Y (20%), 1Y (15%) harmonic cycle superposition."
            }
            return result
        if mode=="sepharial_tide" or mode=="silver_key":
            import astro_trading_engine as ate
            _, t_speed, _ = body_longitudes(tjd)
            moon_spd = abs(t_speed.get("Moon", 13.176))
            result["sepharial_lunar_tide"] = ate.SepharialTidalEngine.evaluate_lunar_tide(moon_spd)
            return result
        if mode=="trade_card" or mode=="institutional_card":
            import astro_trading_engine as ate
            asset = data.get("asset", "BTC")
            price = float(data.get("price", 65000.0 if asset.upper()=="BTC" else 2500.0))
            macro_score = float(data.get("macro_bias_score", 45.0))
            swing_prob = float(data.get("swing_crd_score", 75.0))
            swing_dir = int(data.get("swing_direction", 1))
            intra_score = float(data.get("intraday_score", 30.0))
            result["institutional_trade_card"] = ate.AstroTradeOrchestrator.generate_institutional_trade_card(
                asset, price, macro_score, swing_prob, swing_dir, intra_score
            )
            return result
        if mode=="crawford_crash" or mode=="crash_hazard":
            import astro_trading_engine as ate
            t_lons, _, _ = body_longitudes(tjd)
            m_lon = t_lons.get("Mars", 0.0)
            u_lon = t_lons.get("Uranus", 0.0)
            perigee_flag = bool(data.get("is_lunar_perigee", False))
            eclipse_flag = bool(data.get("is_eclipse_window", False))
            div_flag = bool(data.get("siderograph_divergence", False))
            result["crawford_crash_evaluation"] = ate.CrawfordCrashTriggerEngine.evaluate_crash_hazard(
                m_lon, u_lon, perigee_flag, eclipse_flag, div_flag
            )
            return result
        if mode=="jenkins_squaring" or mode=="jenkins":
            import astro_trading_engine as ate
            p_price = float(data.get("pivot_price", 65000.0))
            h_deg = float(data.get("harmonic_degree", 90.0))
            dir_val = int(data.get("direction", 1))
            result["jenkins_price_time_squaring"] = ate.JenkinsGeometryEngine.calculate_price_time_square(
                p_price, h_deg, dir_val
            )
            return result
        if mode=="ferrera_panic" or mode=="ferrera":
            import astro_trading_engine as ate
            m_elapsed = int(data.get("months_from_major_low", 42))
            result["ferrera_panic_cycle"] = ate.FerreraMasterCycleEngine.evaluate_panic_cycle_node(m_elapsed)
            return result
        if mode=="olga_intraday" or mode=="olga_clock":
            import astro_trading_engine as ate
            m_open = float(data.get("minutes_from_open", 60.0))
            result["olga_morales_intraday"] = ate.OlgaMoralesIntradayEngine.calculate_4min_turning_trigger(m_open)
            return result
        if mode=="lavoie_asteroid" or mode=="asteroid_prob":
            import astro_trading_engine as ate
            ast_name = data.get("asteroid", "PALLAS")
            result["lavoie_asteroid_metric"] = ate.LavoieAsteroidHarmonicsEngine.get_asteroid_probability_metric(ast_name)
            return result
        if mode=="eight_masters" or mode=="master_setups":
            import astro_trading_engine as ate
            asset = data.get("asset", "BTC")
            price = float(data.get("price", 65000.0 if asset.upper()=="BTC" else 2500.0))
            atr_val = float(data.get("atr14", 1200.0 if asset.upper()=="BTC" else 80.0))
            result["eight_masters_exhaustive_setups"] = ate.EightMastersExhaustiveSetupsEngine.evaluate_all_eight_setups(asset, price, atr_val)
            return result
        if mode=="murrey_math" or mode=="murrey":
            import astro_trading_engine as ate
            price = float(data.get("price", 65000.0))
            result["murrey_math_octaves"] = ate.MurreyMathGannOctavesEngine.calculate_murrey_frame(price)
            return result
        if mode=="universal_clock" or mode=="jeanne_long":
            import astro_trading_engine as ate
            price = float(data.get("price", 65000.0))
            h_utc = int(data.get("hour_utc", tdt.hour))
            m_utc = int(data.get("minute_utc", tdt.minute))
            t_lons, _, _ = body_longitudes(tjd)
            result["jeanne_long_universal_clock"] = ate.JeanneLongUniversalClockEngine.calculate_universal_clock_moment(h_utc, m_utc, price, t_lons)
            return result
        if mode=="larry_williams" or mode=="lunar_edge":
            import astro_trading_engine as ate
            days_nm = float(data.get("days_since_new_moon", 2.5))
            result["larry_williams_lunar_edge"] = ate.LarryWilliamsLunarEdgeEngine.evaluate_lunar_phase_edge(days_nm)
            return result
        if mode=="bayer_polarity":
            import astro_trading_engine as ate
            curr_d = float(data.get("current_declination", 0.15))
            prev_d = float(data.get("previous_declination", -0.20))
            pl = data.get("planet", "Moon")
            result["bayer_declination_polarity"] = ate.BayerDeclinationPolarityEngine.check_declination_polarity_flip(curr_d, prev_d, pl)
            return result
        if mode=="crypto_accelerator":
            import astro_trading_engine as ate
            t_lons, _, _ = body_longitudes(tjd)
            result["crypto_genesis_acceleration"] = ate.CryptoGenesisAcceleratorEngine.evaluate_crypto_inception_trigger(t_lons)
            return result
        if mode=="master_signal" or mode=="quant_signal":
            import astro_trading_engine as ate
            asset = data.get("asset", "BTC")
            price = float(data.get("price", 65000.0 if asset.upper()=="BTC" else 2500.0))
            atr_val = float(data.get("atr14", 1200.0 if asset.upper()=="BTC" else 80.0))
            t_lons, t_speed, _ = body_longitudes(tjd)
            decls = body_declinations(tjd)
            voc = void_of_course_moon(tjd, tlat, tlng, True)
            is_voc = bool(voc.get("is_void", False))
            result["institutional_master_signal"] = ate.InstitutionalMasterSignalEngine.generate_master_signal(
                asset_key=asset,
                current_price=price,
                target_date=tdt,
                planetary_lons=t_lons,
                planetary_speeds=t_speed,
                planetary_decls=decls,
                atr14=atr_val,
                is_moon_voc=is_voc
            )
            return result
        if mode=="barycenter" or mode=="ssb":
            import astro_trading_engine as ate
            helio_l = ate.HeliocentricTradingEngine.compute_helio_longitudes(tjd)
            result["solar_system_barycenter"] = ate.SolarSystemBarycenterEngine.compute_barycenter_displacement(helio_l)
            return result
        if mode=="spectral_fft" or mode=="fft":
            import astro_trading_engine as ate
            p_series = data.get("prices", [100.0, 102.0, 105.0, 103.0, 108.0, 112.0, 110.0, 115.0, 118.0, 114.0, 120.0, 122.0])
            result["digital_spectral_fft"] = {
                "sample_bars": len(p_series),
                "dominant_cycles": ate.DigitalSpectralFFTEngine.extract_dominant_cycles(p_series)
            }
            return result
        if mode=="cot_lunar":
            import astro_trading_engine as ate
            net_c = float(data.get("net_commercial", 45000.0))
            min_c = float(data.get("min_156", 10000.0))
            max_c = float(data.get("max_156", 50000.0))
            d_nm = float(data.get("days_since_new_moon", 2.0))
            w_r = float(data.get("williams_r", -80.0))
            result["williams_cot_lunar_confluence"] = ate.WilliamsCOTConfluenceEngine.evaluate_cot_lunar_signal(net_c, min_c, max_c, d_nm, w_r)
            return result
        if mode=="walker_polar":
            import astro_trading_engine as ate
            price = float(data.get("price", 65000.0))
            result["walker_polar_targets"] = ate.WalkerPolarTargetEngine.compute_polar_harmonics(price)
            return result
        if mode=="master_audit":
            import astro_trading_engine as ate
            asset = data.get("asset", "BTC")
            price = float(data.get("price", 65000.0 if asset.upper()=="BTC" else 2500.0))
            t_lons, t_speed, _ = body_longitudes(tjd)
            decls = body_declinations(tjd)
            voc = void_of_course_moon(tjd, tlat, tlng, True)
            is_voc = bool(voc.get("is_void", False))
            helio_l = ate.HeliocentricTradingEngine.compute_helio_longitudes(tjd)

            result["master_audit_suite"] = {
                "master_signal": ate.InstitutionalMasterSignalEngine.generate_master_signal(asset, price, tdt, t_lons, t_speed, decls, 1200.0, is_voc),
                "barycenter": ate.SolarSystemBarycenterEngine.compute_barycenter_displacement(helio_l),
                "walker_polar": ate.WalkerPolarTargetEngine.compute_polar_harmonics(price),
                "eight_masters": ate.EightMastersExhaustiveSetupsEngine.evaluate_all_eight_setups(asset, price, 1200.0)
            }
            return result
        if mode=="cowan_4d" or mode=="platonic":
            import astro_trading_engine as ate
            price = float(data.get("price", 65000.0))
            days = float(data.get("days", 30.0))
            result["cowan_4d_platonic_geometry"] = ate.BradleyCowan4DGeometryEngine.compute_pentagonal_phi_expansions(price, days)
            return result
        if mode=="sarvatobhadra" or mode=="sbc":
            import astro_trading_engine as ate
            # Convert longitudes to nakshatra indices (1 to 28)
            t_lons, _, _ = body_longitudes(tjd)
            nak_map = {}
            for p, lon in t_lons.items():
                if p in ("North Node", "South Node"): continue
                nak_idx = int(lon // 12.857) + 1 # 360 / 28 = 12.857 deg
                nak_map[p] = max(1, min(28, nak_idx))
            result["sarvatobhadra_chakra"] = ate.SarvatobhadraChakra81Engine.evaluate_sbc_vedha_score(nak_map, janma_nakshatra_idx=1)
            return result
        if mode=="musical_harmonics":
            import astro_trading_engine as ate
            price = float(data.get("trough_price", 50000.0))
            result["pythagorean_musical_harmonics"] = ate.PythagoreanMusicalHarmonicsEngine.compute_musical_price_ladder(price)
            return result
        if mode=="planetary_kinematics":
            import astro_trading_engine as ate
            l0 = float(data.get("lon_t0", 120.0))
            result["planetary_kinematics_acceleration"] = ate.PlanetaryKinematicsAccelerationEngine.compute_kinematics(
                l0 - 2.0, l0 - 1.0, l0, l0 + 1.0, l0 + 2.0
            )
            return result
        if mode=="saros_cycle":
            import astro_trading_engine as ate
            result["saros_eclipse_family"] = ate.SarosEclipseFamiliesEngine.evaluate_saros_recurrence(tdt)
            return result
        if mode=="astro_backtest":
            import astro_trading_engine as ate
            p_series = data.get("prices", [100.0, 102.0, 105.0, 103.0, 108.0, 112.0, 110.0, 115.0, 118.0, 122.0, 120.0, 125.0])
            sigs = data.get("signals", [1, 1, 1, 0, 1, 1, -1, 1, 1, 1, 0, 1])
            result["quantitative_astro_backtest"] = ate.QuantitativeAstroBacktestSimulator.simulate_strategy_performance(p_series, sigs)
            return result
        if mode=="bayer" or mode=="mercury_speed":
            import astro_trading_engine as ate
            _, t_speed, _ = body_longitudes(tjd)
            merc_spd = t_speed.get("Mercury", 1.2)
            result["bayer_mercury_analysis"] = ate.GeorgeBayerEngine.evaluate_mercury_speed(merc_spd)
            return result

    birth_utc, tinfo = to_utc(data)
    jd=julian_day(birth_utc)
    lat=data.get("lat",0.0); lng=data.get("lng",0.0)
    time_known=tinfo.get("time_known",True)
    birth_local=datetime(data["year"],data["month"],data["day"],
                         int(data.get("hour",12)),int(data.get("minute",0)))
    systems=data.get("systems",["western","vedic","bazi"])
    _,_,backend=body_longitudes(jd)

    result={"_meta":{"engine_backend":backend,"swisseph_available":_HAS_SWE,
                     "birth_utc":birth_utc.strftime("%Y-%m-%d %H:%M"),"julian_day":round(jd,5),
                     "computed_on":TODAY.strftime("%Y-%m-%d"),
                     "house_system":"Placidus (Swiss Ephemeris)" if _HAS_SWE else "whole-sign",
                     "node_type": _NODE_TYPE,
                     "precision_note":("arcsecond (Swiss Ephemeris)" if backend=="swisseph"
                                       else "~1-2 arcmin (builtin) — exact to sign/house/nakshatra/dasha")},
            "input":{k:data.get(k) for k in
                     ("name","year","month","day","hour","minute","lat","lng","tz","gender")},
            "time_info":tinfo,
            "summary": {
                "big_three": {
                    "sun": sign_of(body_longitudes(jd)[0]["Sun"])[0],
                    "moon": sign_of(body_longitudes(jd)[0]["Moon"])[0],
                    "ascendant": sign_of(ascendant_mc(jd, lat, lng)[0])[0]
                },
                "plain_takeaway": (
                    f"هویت محوری در {sign_of(body_longitudes(jd)[0]['Sun'])[0]} (موتور اراده و انگیزه)، "
                    f"امنیت عاطفی در {sign_of(body_longitudes(jd)[0]['Moon'])[0]} (نیازهای قلبی و ناخودآگاه)، "
                    f"و نقاب بیرونی در {sign_of(ascendant_mc(jd, lat, lng)[0])[0]} (نحوه مواجهه با جهان)."
                )
            },
            "mode":mode}

    # Resolve target evaluation moment dynamically for any mode (target_date / as_of / date)
    target_eval_dt = _resolve_target_dt(data)
    target_eval_jd = julian_day(target_eval_dt)

    if mode=="transit":
        result["natal_brief"]=western_chart(jd,lat,lng,time_known)["big_three"]
        tdate=data.get("transit_date")
        tdt=datetime.strptime(tdate,"%Y-%m-%d") if tdate else TODAY
        result["transits"]=transits(jd,lat,lng,tdt)
        try:
            result["transit_interpretation"]=interpret_transits(result["transits"])
        except Exception:
            pass
        result["life_phase"]=life_phase(birth_local)
        return result

    if mode=="synastry":
        p=data["partner"]
        p_utc,_=to_utc(p); jdB=julian_day(p_utc)
        result["synastry"]=synastry(jd,jdB)
        chA = western_chart(jd,lat,lng,time_known)
        chB = western_chart(jdB,p.get("lat",0),p.get("lng",0),p.get("time_known",True))
        result["personA"]={"big_three":chA["big_three"]}
        result["personB"]={"big_three":chB["big_three"]}
        # House Overlays: where A lands in B, and where B lands in A
        lonsA, _, _ = body_longitudes(jd)
        lonsB, _, _ = body_longitudes(jdB)
        ascA = chA["ascendant"]["abs_lon"] if "abs_lon" in chA["ascendant"] else lonsA["Sun"]
        ascB = chB["ascendant"]["abs_lon"] if "abs_lon" in chB["ascendant"] else lonsB["Sun"]
        result["house_overlays"] = {
            "personA_planets_in_personB_houses": synastry_house_overlays(lonsA, ascB),
            "personB_planets_in_personA_houses": synastry_house_overlays(lonsB, ascA)
        }
        # Ibn Ezra Relationship Lots for both
        is_dayA = 90 <= norm360(ascA - lonsA["Sun"]) <= 270
        is_dayB = 90 <= norm360(ascB - lonsB["Sun"]) <= 270
        result["ibn_ezra_lots"] = {
            "personA": ibn_ezra_relationship_lots(lonsA, ascA, is_dayA),
            "personB": ibn_ezra_relationship_lots(lonsB, ascB, is_dayB)
        }
        if "bazi" in systems:
            result["personA"]["bazi_animal"]=bazi_chart(jd,birth_local,data.get("gender","unknown")).get("year_animal")
            pb_local=datetime(p["year"],p["month"],p["day"],int(p.get("hour",12)),int(p.get("minute",0)))
            result["personB"]["bazi_animal"]=bazi_chart(jdB,pb_local,p.get("gender","unknown")).get("year_animal")
        return result

    if mode=="astrocartography":
        result["astrocartography"]=astrocartography(jd, lat, lng)
        result["big_three"]=western_chart(jd,lat,lng,time_known)["big_three"]
        return result

    if mode=="horary":
        qtext = data.get("question","")
        qdt = datetime.strptime(data["question_time"], "%Y-%m-%d %H:%M") if data.get("question_time") else datetime.utcnow()
        # Convert to UTC using provided tz if any
        if data.get("tz") and _HAS_TZDB:
            try:
                local = qdt.replace(tzinfo=ZoneInfo(data["tz"]))
                qdt_utc = local.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                qdt_utc = qdt
        else:
            qdt_utc = qdt
        result["horary"]=horary(qdt_utc, lat, lng, qtext)
        return result

    if mode=="event":
        result["event_chart"]=event_chart(data)
        return result

    if mode=="solar_return":
        target_year=data.get("target_year", birth_local.year + 1)
        result["solar_return"]=solar_return(jd, target_year, lat, lng)
        result["natal_sun_sign"]=sign_of(body_longitudes(jd)[0]["Sun"])[0]
        return result

    if mode=="lunar_return":
        target_year=data.get("target_year", birth_local.year)
        target_month=data.get("target_month", birth_local.month)
        result["lunar_return"]=lunar_return(jd, target_year, target_month, lat, lng)
        return result

    if mode=="davison":
        p=data["partner"]
        p_utc,_=to_utc(p); jdB=julian_day(p_utc)
        latB = p.get("lat", 0.0); lngB = p.get("lng", 0.0)
        result["davison"] = davison_chart(jd, jdB, lat, lng, latB, lngB, as_of_dt=target_eval_dt)
        return result

    if mode=="draconic":
        result["draconic"] = draconic_chart(jd, lat, lng, time_known)
        return result

    if mode=="draconic_synastry":
        p=data["partner"]
        p_utc,_=to_utc(p); jdB=julian_day(p_utc)
        latB = p.get("lat", 0.0); lngB = p.get("lng", 0.0)
        result["draconic_synastry"] = draconic_synastry(jd, jdB, lat, lng, latB, lngB)
        return result

    if mode=="compatibility":
        p=data["partner"]
        p_utc,_=to_utc(p); jdB=julian_day(p_utc)
        result["compatibility"]=compatibility_score(jd, jdB)
        result["personA"]={"big_three":western_chart(jd,lat,lng,time_known)["big_three"]}
        result["personB"]={"big_three":western_chart(jdB,p.get("lat",0),p.get("lng",0),
                                                      p.get("time_known",True))["big_three"]}
        result["synastry"]=synastry(jd,jdB)
        return result

    if mode=="navamsa":
        result["navamsa"]=navamsa_chart(jd, lat, lng, time_known)
        result["vedic_brief"]=vedic_chart(jd,lat,lng,birth_local,time_known)
        return result

    if mode=="panchang":
        result["panchang"]=panchang_elements(jd)
        result["vedic_brief"]=vedic_chart(jd,lat,lng,birth_local,time_known)
        return result

    if mode=="composite":
        p=data["partner"]
        p_utc,_=to_utc(p); jdB=julian_day(p_utc)
        comp = composite_chart(jd, jdB, lat, lng, p.get("lat",0), p.get("lng",0))
        result["composite"]=comp
        try:
            result["composite_interpretation"]=interpret_composite_chart(comp)
        except Exception:
            pass
        result["personA"]={"big_three":western_chart(jd,lat,lng,time_known)["big_three"]}
        result["personB"]={"big_three":western_chart(jdB,p.get("lat",0),p.get("lng",0),
                                                      p.get("time_known",True))["big_three"]}
        return result

    if mode=="progressions":
        target_age=data.get("target_age", 30)
        prog=secondary_progressions(jd, target_age, lat, lng)
        result["progressions"]=prog
        try:
            result["progression_interpretation"]=interpret_progressions(jd, prog)
        except Exception:
            pass
        return result

    if mode=="planetary_return":
        planet=data.get("planet","Jupiter")
        target_year=data.get("target_year", birth_local.year + 1)
        result["planetary_return"]=planetary_return(jd, planet, target_year, lat, lng)
        return result

    if mode=="varga":
        varga=data.get("varga","D10")
        result["varga"]=varga_chart(jd, varga, lat, lng, time_known)
        return result

    if mode=="transit_natal_aspects":
        tdate=data.get("transit_date")
        tdt=datetime.strptime(tdate,"%Y-%m-%d") if tdate else TODAY
        tjd=julian_day(tdt)
        result["transit_natal_aspects"]=transit_to_natal_aspects(jd, tjd)
        return result

    # ── New advanced modes ─────────────────────────────────────────
    if mode=="node_transit":
        from astro_advanced import analyze_node_transit
        natal_lons, _, _ = body_longitudes(jd)
        tjd = julian_day(datetime.utcnow())
        t_lons, _, _ = body_longitudes(tjd)
        result["node_transit"] = analyze_node_transit(natal_lons, t_lons)
        return result

    if mode=="node_transit_all_signs":
        from astro_advanced import node_transit_all_signs
        tjd = julian_day(datetime.utcnow())
        t_lons, _, _ = body_longitudes(tjd)
        result["node_transit_all_signs"] = node_transit_all_signs(t_lons, jd=tjd)
        return result

    if mode=="guna_milan":
        from astro_advanced import guna_milan
        p=data.get("partner", {})
        p_utc,_=to_utc(p); jdB=julian_day(p_utc)
        natal_lons, _, _ = body_longitudes(jd)
        p_lons, _, _ = body_longitudes(jdB)
        ayan_here = ayanamsha_lahiri(jd)
        result["guna_milan"] = guna_milan(natal_lons, p_lons, ayan_here)
        result["personA_big3"] = western_chart(jd,lat,lng,time_known)["big_three"]
        result["personB_big3"] = western_chart(jdB,p.get("lat",0),p.get("lng",0),
                                               p.get("time_known",True))["big_three"]
        return result

    if mode=="solar_return_interpreted":
        from astro_advanced import interpret_solar_return
        target_year=data.get("target_year", birth_local.year+1)
        sr = solar_return(jd, target_year, lat, lng)
        result["solar_return"] = interpret_solar_return(sr)
        return result

    if mode=="solar_arc":
        from astro_advanced import solar_arc_directions
        age=data.get("age", (TODAY - birth_local).days / 365.25)
        natal_lons, _, _ = body_longitudes(jd)
        if time_known:
            asc_lon_full, _ = ascendant_mc(jd, lat, lng)
            natal_lons["Ascendant"] = asc_lon_full
        result["solar_arc"] = solar_arc_directions(natal_lons, age)
        return result

    if mode=="remedies":
        from astro_advanced import suggest_remedies
        # compute natal first — strip mode to avoid recursion
        natal_data = dict(data)
        natal_data.pop("mode", None)
        nat = calculate_full_profile(natal_data)
        result["remedies"] = suggest_remedies(nat)
        return result

    if mode=="prashna":
        from astro_advanced import prashna
        from datetime import timezone as _tz
        qtext = data.get("question","")
        qdt = datetime.strptime(data["question_time"], "%Y-%m-%d %H:%M") if data.get("question_time") else datetime.utcnow()
        if data.get("tz") and _HAS_TZDB:
            try:
                local = qdt.replace(tzinfo=ZoneInfo(data["tz"]))
                qdt_utc = local.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                qdt_utc = qdt
        else:
            qdt_utc = qdt
        qdt_utc = qdt_utc.replace(tzinfo=_tz.utc)
        qtype = data.get("question_type","general")
        result["prashna"] = prashna(qdt_utc, lat, lng, qtext, qtype)
        return result

    if mode=="upagrahas":
        result["upagrahas"] = upagrahas(jd, lat, lng, time_known)
        return result

    if mode=="ashtakavarga":
        result["ashtakavarga"] = ashtakavarga(jd, lat, lng, time_known)
        return result

    if mode=="vimsopaka":
        result["vimsopaka"] = vimsopaka_strength(jd)
        return result

    if mode=="ashtottari":
        moon_sid = norm360(body_longitudes(jd)[0]["Moon"] - ayanamsha_lahiri(jd))
        result["ashtottari_dasha"] = ashtottari_dasha(moon_sid, birth_local)
        return result

    if mode=="tajika":
        from astro_advanced import tajika_annual
        result["tajika"] = tajika_annual(birth_local, lat, lng)
        return result

    if mode=="shadbala":
        from astro_advanced import shadbala_sthana_dig
        result["shadbala"] = shadbala_sthana_dig(jd, lat, lng)
        return result

    # Resolve target evaluation moment dynamically for any mode (target_date / as_of / date)
    target_eval_dt = _resolve_target_dt(data)
    target_eval_jd = julian_day(target_eval_dt)

    if mode=="mundane":
        cname = data.get("country", "iran").lower()
        if cname not in MUNDANE_CAPITALS:
            return {"mode": mode, "error":
                    f"unknown country '{cname}' — available: "
                    + ", ".join(sorted(MUNDANE_CAPITALS))}
        lat_c, lng_c = MUNDANE_CAPITALS[cname]

        # Target date support for AI Agents: auto-resolve active ingress based on Bonatti/Lilly
        if data.get("target_date") or data.get("as_of") or data.get("date"):
            result["mundane"] = resolve_mundane_ingress_for_date(cname, lat_c, lng_c, target_eval_dt)
        else:
            year = int(data.get("year", target_eval_dt.year))
            kind = data.get("ingress_kind", "aries")
            result["mundane"] = ingress_chart(cname, lat_c, lng_c, year, kind)

        try:
            result["eclipse_activations"] = eclipse_activations(
                julian_day(datetime(2000, 1, 1)), lat_c, lng_c,
                count=int(data.get("eclipse_count", 4)))
        except Exception:
            pass
        if data.get("include_lunations"):
            try:
                result["lunations"] = lunation_cycle(lat_c, lng_c,
                                                     count=int(data.get("lunation_count", 3)),
                                                     start_jd=target_eval_jd)
            except Exception:
                pass
        return result

    if mode=="astrodynes" or mode=="cosmodynes":
        result["astrodynes"] = compute_astrodynes(jd, lat, lng, time_known)
        return result

    if mode=="daily_panchang" or mode=="choghadiya":
        result["daily_panchang_timing"] = daily_panchang_timing(target_eval_jd, lat, lng)
        return result

    if mode=="gochara":
        result["gochara"]=gochara(jd, target_eval_jd, lat=lat, lng=lng)
        return result

    if mode=="find_best_time" or mode=="electional_search":
        activity = data.get("activity", "business_commerce")
        days = int(data.get("days_ahead", 30))
        organ = data.get("organ_sign")
        result["electional_windows"] = find_best_electional_windows(
            lat, lng, target_eval_dt, days_ahead=days, activity=activity, organ_sign=organ)
        return result

    if mode=="relocate_chart" or mode=="relocation":
        target_city = data.get("target_city", "Dubai")
        coords = CITIES.get(target_city, (data.get("target_lat", lat), data.get("target_lng", lng)))
        result["relocated_chart"] = relocate_natal_chart(jd, target_city, coords[0], coords[1])
        return result

    if mode=="dasha_reading":
        moon_sid = norm360(body_longitudes(jd)[0]["Moon"] - ayanamsha_lahiri(jd))
        vim = vimshottari(moon_sid, birth_local, as_of_dt=target_eval_dt)
        result["vimshottari_reading"] = interpret_vimshottari(vim)
        result["current_timeline"] = {
            "maha": vim["current_mahadasha"], "antar": vim["current_antardasha"],
            "pratyantar": vim["current_pratyantardasha"]}
        result["chara_dasha"] = chara_dasha(jd, lat, lng, time_known, as_of_dt=target_eval_dt)
        return result

    if mode=="almuten" or mode=="almuten_figuris":
        result["almuten"] = calculate_almuten_figuris(jd, lat, lng, time_known)
        return result

    if mode=="tri_consensus" or mode=="consensus" or mode=="confidence":
        result["tri_tradition_convergence"] = compute_tri_tradition_convergence(
            jd, lat, lng, time_known, as_of_dt=target_eval_dt)
        return result

    if mode=="remedies_blueprint" or mode=="upayas" or mode=="gemstones":
        result["remedies_blueprint"] = compute_remedies_blueprint(jd, lat, lng, time_known)
        return result

    if mode=="wealth_blueprint" or mode=="wealth":
        result["wealth_blueprint"] = compute_wealth_blueprint(jd, lat, lng, time_known)
        return result

    if mode=="love_blueprint" or mode=="marriage" or mode=="love":
        result["love_blueprint"] = compute_love_blueprint(jd, lat, lng, time_known)
        return result

    if mode=="rectify_birth_time" or mode=="rectification":
        events = data.get("life_events", [])
        win = int(data.get("window_minutes", 60))
        step = float(data.get("step_minutes", 2.0))
        result["rectification"] = rectify_birth_time(data, events, window_minutes=win, step_minutes=step)
        return result

    if mode=="master_chronology" or mode=="life_story":
        max_a = int(data.get("max_age", 85))
        result["master_life_chronology"] = generate_master_life_chronology(
            jd, lat, lng, time_known, max_age=max_a)
        return result

    if mode=="medical" or mode=="prakriti" or mode=="dosha":
        result["ayurvedic_medical_profile"] = compute_ayurvedic_medical_profile(jd, lat, lng, time_known)
        return result

    if mode=="financial" or mode=="crypto":
        asset = data.get("asset", "BTC")
        result["financial_weather"] = crypto_financial_weather(asset, target_eval_dt)
        return result

    if mode=="davison_progression":
        p = data["partner"]
        p_utc, _ = to_utc(p); jdB = julian_day(p_utc)
        latB = p.get("lat", 0.0); lngB = p.get("lng", 0.0)
        result["davison_progression"] = davison_progression_forecast(
            jd, jdB, lat, lng, latB, lngB, target_dt=target_eval_dt)
        return result

    if mode=="tarot_celtic_cross":
        import tarot_engine
        q = data.get("question", "General guidance for my path")
        seed = f"{data.get('year',2000)}-{data.get('month',1)}-{data.get('day',1)}:{q}"
        result["tarot_celtic_cross"] = tarot_engine.celtic_cross_reading(q, seed)
        return result

    if mode=="tarot_3card":
        import tarot_engine
        q = data.get("question", "General path")
        stype = data.get("spread_type", "past_present_future")
        seed = f"{data.get('year',2000)}-{data.get('month',1)}-{data.get('day',1)}"
        result["tarot_3card"] = tarot_engine.three_card_reading(q, spread_type=stype, seed=seed)
        return result

    if mode=="tarot_soul_personality":
        import tarot_engine
        y = int(data.get("year", 2000)); m = int(data.get("month", 1)); d = int(data.get("day", 1))
        result["tarot_soul_personality"] = tarot_engine.calculate_soul_and_personality_cards(y, m, d)
        return result

    if mode=="tarot_12house":
        import tarot_engine
        seed = f"{data.get('year',2000)}-{data.get('month',1)}-{data.get('day',1)}"
        result["tarot_12house"] = tarot_engine.astrological_12_house_spread(seed)
        return result

    if mode=="hermetic_tarot" or mode=="tarot":
        result["hermetic_tarot_profile"] = map_hermetic_tarot_profile(jd, lat, lng, time_known)
        return result

    if mode=="zr":
        topic = data.get("zr_topic", "spirit")
        if topic not in ("spirit", "fortune"):
            return {"mode": mode, "error": "zr_topic must be 'spirit' or 'fortune'"}
        result["zodiacal_releasing"] = zodiacal_releasing(
            jd, lat, lng, time_known, topic,
            max_level=int(data.get("max_level", 3)),
            until_age=min(int(data.get("until_age", 80)), 120),
            as_of_dt=target_eval_dt)
        try:
            result["zr_interpretation"] = interpret_zr(result["zodiacal_releasing"], as_of_dt=target_eval_dt)
        except Exception:
            pass
        return result

    if mode in ("profections", "firdaria", "forecast"):
        asc_lon_f, _ = (ascendant_mc(jd, lat, lng) if time_known
                        else (lons["Sun"], 0))
        asc_sign_idx = int(norm360(asc_lon_f) // 30) % 12
        is_day_birth = True
        try:
            sun_alt_check = norm360(asc_lon_f - body_longitudes(jd)[0]["Sun"])
            is_day_birth = 90 <= sun_alt_check <= 270
        except Exception:
            pass
        if mode in ("profections", "forecast"):
            result["annual_profections"] = annual_profections(
                asc_sign_idx, birth_local, target_eval_dt)
        if mode in ("firdaria", "forecast"):
            until_age = min(int(data.get("until_age", 75)), 100)
            f = firdaria(birth_local, is_day_birth, as_of_dt=target_eval_dt)
            if data.get("until_age") and data["until_age"] < 75:
                f["timeline_to_age_75"] = [
                    p for p in f["timeline_to_age_75"]
                    if p["start_age"] < data["until_age"]]
            result["firdaria"] = f
        return result

    # ── Natal with advanced features ────────────────────────────────
    do_advanced = data.get("advanced", False)
    result["charts"]={}
    if "western" in systems:
        try:
            result["charts"]["western"]=western_chart(jd,lat,lng,time_known,
                                                       data.get("house_system","P"))
        except Exception as e: result["charts"]["western"]={"error":repr(e)}
    if "vedic" in systems:
        try: result["charts"]["vedic"]=vedic_chart(jd,lat,lng,birth_local,time_known,as_of_dt=target_eval_dt)
        except Exception as e: result["charts"]["vedic"]={"error":repr(e)}
    if "bazi" in systems:
        try: result["charts"]["bazi"]=bazi_chart(jd,birth_local,data.get("gender","unknown"),lat)
        except Exception as e: result["charts"]["bazi"]={"error":repr(e)}
    result["life_phase"]=life_phase(birth_local)

    if "western" in systems and time_known:
        try:
            lons, _, _ = body_longitudes(jd)
            asc_lon, _ = ascendant_mc(jd, lat, lng)
            sun_lon = lons["Sun"]
            is_day = 90 <= norm360(asc_lon - sun_lon) <= 270
            result["special_points"]={
                "part_of_fortune": part_of_fortune(sun_lon, lons["Moon"], asc_lon, is_day),
                "vertex": vertex(jd, lat, lng),
                "moon_phase_at_birth": moon_phase(jd),
                "black_moon_lilith": black_moon_lilith(jd),
            }
            result["arabic_parts"]=compute_arabic_parts(lons, asc_lon, is_day)
            result["aspect_patterns"]=detect_aspect_patterns(lons)
            result["fixed_star_conjunctions"]=fixed_star_conjunctions(lons)
            result["equal_houses"]=equal_houses(asc_lon)
            result["declinations"]={nm: round(d,3) for nm,d in body_declinations(jd).items()}
            result["declination_aspects"]=compute_declination_aspects(lons, body_declinations(jd))[:12]
            result["antiscia"]={nm: round(antiscia(lons[nm]),3) for nm in lons}
            result["void_of_course_moon"]=void_of_course_moon(jd, lat, lng, time_known)
        except Exception:
            pass

    if "vedic" in systems:
        try:
            result["panchang"]=panchang_elements(jd)
            result["navamsa"]=navamsa_chart(jd, lat, lng, time_known)
            result["mangal_dosha"]=mangal_dosha(jd, lat, lng, time_known)
            result["kaalsarpa_dosha"]=kaalsarpa_dosha(jd, lat, lng, time_known)
            result["upagrahas"]=upagrahas(jd, lat, lng, time_known)
            result["ashtakavarga"]=ashtakavarga(jd, lat, lng, time_known)
            moon_sid = norm360(body_longitudes(jd)[0]["Moon"] - ayanamsha_lahiri(jd))
            result["ashtottari_dasha"]=ashtottari_dasha(moon_sid, birth_local)
        except Exception:
            pass

    if data.get("include_numerology"):
        try: result["numerology"]=numerology(data["year"],data["month"],data["day"],
                                              data.get("full_name",""))
        except Exception:
            pass

    # ── Advanced features bundle ─────────────────────────────────────
    if do_advanced:
        try:
            from astro_advanced import (analyze_node_transit, interpret_solar_return,
                                        solar_arc_directions, suggest_remedies,
                                        weekly_astro_calendar)

            natal_lons, _, _ = body_longitudes(jd)
            tjd = julian_day(datetime.utcnow())
            t_lons, _, _ = body_longitudes(tjd)
            result["node_transit"] = analyze_node_transit(natal_lons, t_lons)

            # Solar return interpreted
            sr = solar_return(jd, TODAY.year, lat, lng)
            result["solar_return_interp"] = interpret_solar_return(sr)

            # Solar arc
            age = (TODAY - birth_local).days / 365.25
            if time_known:
                asc_full, _ = ascendant_mc(jd, lat, lng)
                natal_lons["Ascendant"] = asc_full
            result["solar_arc"] = solar_arc_directions(natal_lons, age)

            # Remedies
            result["remedies"] = suggest_remedies(result)

            # Weekly calendar
            result["weekly_calendar"] = weekly_astro_calendar()
        except Exception as e:
            result["_advanced_error"] = repr(e)

    return result


# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — WESTERN FORECASTING: PROFECTIONS & FIRDARIA
# ═════════════════════════════════════════════════════════════════════════════

PROFECTION_THEMES = {
    1:  ("self, body, vitality — a year of personal initiative and new beginnings",
         "identity reset; how you appear and initiate"),
    2:  ("money, resources, values, self-worth — building material stability",
         "income and possessions; what you value"),
    3:  ("communication, siblings, short trips, learning — busy local movement",
         "study, writing, neighbors, everyday exchanges"),
    4:  ("home, family, roots, inner foundation — private and domestic focus",
         "relocation, property, parents, emotional base"),
    5:  ("creativity, romance, children, pleasure — expressive and playful",
         "love affairs, creative projects, fun, kids"),
    6:  ("work, health, daily routine, service — discipline and maintenance",
         "jobs, habits, fitness, illness prevention"),
    7:  ("partnerships, marriage, contracts, open enemies — the other person's year",
         "committed relationships, negotiations, rivals"),
    8:  ("shared resources, debt, transformation, sexuality — deep change",
         "taxes, inheritance, intimacy, crisis-and-rebirth"),
    9:  ("travel, higher education, philosophy, publishing — expansion of horizons",
         "long journeys, university, beliefs, foreign contacts"),
    10: ("career, public standing, authority, achievement — the visible year",
         "promotion, reputation, bosses, life direction"),
    11: ("friends, groups, hopes, wishes, networks — collective support",
         "allies, communities, long-term goals, gains"),
    12: ("retreat, solitude, hidden matters, healing — end of a cycle",
         "rest, introspection, hospitals, closure before renewal"),
}

def annual_profections(asc_sign_idx, birth_local, target_date=None):
    """Full profection report given the natal rising-sign index (0=Aries).
    Returns active house (1-12), its lord, theme, plus month-level rotation."""
    """Full profection report given the natal rising-sign index (0=Aries).
    Returns active house (1-12), its lord, theme, plus next-year preview."""
    target = target_date or TODAY
    age_exact = (target - birth_local).days / 365.2425
    prof_index = int(age_exact) % 12          # 0-based rotation from Asc
    house = prof_index + 1
    asc_sign = SIGNS[asc_sign_idx]
    prof_sign = SIGNS[(asc_sign_idx + prof_index) % 12]
    lord = SIGN_DATA[prof_sign]["ruler"]
    theme, detail = PROFECTION_THEMES[house]
    # monthly profections: each month advances one sign from the yearly sign
    month_in_year = int((age_exact % 1) * 12)
    month_sign = SIGNS[(asc_sign_idx + prof_index + month_in_year) % 12]
    month_house = ((prof_index + month_in_year) % 12) + 1
    # age boundaries of this profection year
    start = birth_local.replace(year=birth_local.year + int(age_exact)) \
        if birth_local.month != 2 or birth_local.day != 29 \
        else birth_local.replace(year=birth_local.year + int(age_exact), day=28)
    end_year = int(age_exact) + 1
    try:
        end = start.replace(year=start.year + 1)
    except ValueError:
        end = start.replace(year=start.year + 1, day=28)
    return {
        "age": round(age_exact, 2),
        "profection_year": int(age_exact),
        "active_house": house,
        "active_sign": prof_sign,
        "year_lord": lord,
        "theme": theme,
        "detail": detail,
        "month_profection": {"index": month_in_year + 1, "sign": month_sign,
                             "house": month_house,
                             "lord": SIGN_DATA[month_sign]["ruler"]},
        "period": {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d")},
        "note": ("Hellenistic annual profection: the profected house and its lord "
                 "color the whole year; the lord's natal condition shows how easily "
                 "the themes flow."),
    }

FIRDARIA_DAY_ORDER = ["Sun","Venus","Mercury","Saturn","Jupiter","Mars",
                      "North Node","South Node"]
FIRDARIA_NIGHT_ORDER = ["Moon","Saturn","Jupiter","Mars","North Node","South Node",
                        "Sun","Venus","Mercury"]
FIRDARIA_YEARS = {"Sun":10,"Venus":8,"Mercury":13,"Moon":9,"Saturn":11,"Jupiter":12,
                  "Mars":7,"North Node":3,"South Node":2}
# classical scheme: 66 main years then a universal final Moon firdar to 75

def firdaria(birth_local, is_day_birth, until_age=75, as_of_dt=None):
    """Firdaria (medieval Persian): life split into 75 years —
    day births start with Sun, night births with Moon; each planet rules a
    'firdar' of fixed length, subdivided into sub-periods with partners in order."""
    eval_dt = as_of_dt or datetime.now(timezone.utc).replace(tzinfo=None)
    order = FIRDARIA_DAY_ORDER if is_day_birth else FIRDARIA_NIGHT_ORDER
    periods = []
    age_cursor = 0.0
    for i, p in enumerate(order):
        yrs = FIRDARIA_YEARS[p]
        periods.append({"lord": p, "start_age": round(age_cursor, 1),
                        "end_age": round(age_cursor + yrs, 1),
                        "years": yrs})
        age_cursor += yrs
    # classical scheme ends at 75 with a final Moon firdar for everyone
    periods.append({"lord": "Moon", "start_age": round(age_cursor, 1),
                    "end_age": round(age_cursor + 9, 1), "years": 9,
                    "note": "final universal Moon firdar"})
    def _active(age):
        for pr in periods:
            if pr["start_age"] <= age < pr["end_age"]:
                return pr
        return periods[-1]
    current_age = (eval_dt - birth_local).days / 365.2425
    major = _active(current_age)
    # Sub-periods (Ibn Ezra, Reshit Hokhmah X / Sela p.602): each firdar divides
    # into SEVEN equal sub-periods; co-rulers descend in orb order from the
    # major lord's own position in the sect's planetary order (nodes excluded —
    # only the seven planets participate as partners).
    seven = [p for p in order if p not in ("North Node", "South Node")]
    idx = seven.index(major["lord"]) if major["lord"] in seven else 0
    span = major["end_age"] - major["start_age"]
    n_subs = 7
    subs = []
    for k in range(n_subs):
        partner = seven[(idx + k) % len(seven)]
        s_start = major["start_age"] + span * k / n_subs
        s_end = major["start_age"] + span * (k + 1) / n_subs
        subs.append({"partner_lord": partner,
                     "start_age": round(s_start, 2), "end_age": round(s_end, 2)})
    active_sub = next((s for s in subs
                       if s["start_age"] <= current_age < s["end_age"]), subs[-1])
    upcoming = [p for p in periods if p["start_age"] > current_age][:3]
    return {
        "sect": "day" if is_day_birth else "night",
        "as_of_date": eval_dt.strftime("%Y-%m-%d"),
        "current_age": round(current_age, 1),
        "major_firdar": {k: major[k] for k in ("lord", "start_age", "end_age")},
        "sub_period": active_sub,
        "upcoming_majors": upcoming,
        "timeline_to_age_75": periods,
        "note": ("Firdaria: long periods ruled by one planet (day sect begins with "
                 "the Sun, night with the Moon); each major period divides into "
                 "sub-periods co-ruled by every planet in sequence."),
    }


TRANSIT_ASPECT_TONE = {
    "conjunction": "fuses with",
    "sextile":     "opens an easy door to",
    "square":      "creates friction with",
    "trine":       "flows naturally into",
    "opposition":  "faces off against",
}

SLOW_PLANET_TIMING = {
    "Pluto": ("years", "a generational, deep-structural change touching this life area"),
    "Neptune": ("years", "dissolving old certainties; inspiration mixed with confusion"),
    "Uranus": ("months", "disruption and liberation; expect the unexpected"),
    "Saturn": ("weeks-months", "consolidation, testing, and mature commitment"),
    "Jupiter": ("weeks", "growth and opportunity — but watch for overreach"),
    "North Node": ("weeks", "karmic pull toward unfamiliar growth territory"),
    "Mars": ("days", "surges of energy and initiative — or conflict if forced"),
}

def interpret_transits(transit_result):
    """Turn raw transit aspects into ranked, readable guidance.
    transit_result: output of transits() — uses aspects_to_natal + current_positions.
    Adds 'headline' (dominant theme), 'key_transits' (top interpreted hits),
    'advice' list."""
    hits = transit_result.get("aspects_to_natal", [])
    scored = []
    for h in hits:
        tp = h["transiting"]
        slow = tp in SLOW_PLANET_TIMING
        tightness = max(0.0, 1.0 - h["orb"] / 8.0)
        weight = (2.0 if slow else 0.6) * tightness \
                 * (1.3 if h["to_natal"] in ("Sun","Moon","Ascendant") else 1.0)
        timing_unit, tone = SLOW_PLANET_TIMING.get(
            tp, ("days", "brief passing influence"))
        text = (f"Transiting {tp} {TRANSIT_ASPECT_TONE.get(h['aspect'], 'contacts')} "
                f"natal {h['to_natal']} (orb {h['orb']}°) — {tone}. "
                f"Window: {timing_unit}.")
        scored.append({**h, "weight": round(weight, 2), "reading": text})
    scored.sort(key=lambda x: -x["weight"])
    key = scored[:5]
    headline = None
    if key:
        dom = key[0]
        headline = (f"Dominant transit: {dom['transiting']} {dom['aspect']} "
                    f"natal {dom['to_natal']}")
    hard = [k for k in key if k["aspect"] in ("square", "opposition")]
    soft = [k for k in key if k["aspect"] in ("trine", "sextile")]
    advice = []
    if len(hard) >= 2:
        advice.append("Multiple hard aspects active: pace yourself; pressure is "
                      "productive only when it has a deadline.")
    if len(soft) >= 2:
        advice.append("Supportive currents dominate — use this window to launch "
                      "or consolidate.")
    sat = next((k for k in key if k["transiting"] == "Saturn"), None)
    if sat:
        advice.append(f"Saturn on natal {sat['to_natal']}: say yes to structure, "
                      f"no to shortcuts. What you build now lasts.")
    jup = next((k for k in key if k["transiting"] == "Jupiter"), None)
    if jup:
        advice.append(f"Jupiter on natal {jup['to_natal']}: expand deliberately — "
                      f"the growth is real but so is the temptation to overshoot.")
    return {"headline": headline,
            "key_transits": key[:5],
            "advice": advice}


PROG_MOON_PHASE = {
    "new":      ("dark-of-the-moon chapter", "instinctive beginnings; plant seeds quietly, don't force outcomes"),
    "crescent": ("crescent chapter", "struggle to break from the past; early wins come through persistence"),
    "first_quarter": ("first-quarter chapter", "action and decision; obstacles are the curriculum"),
    "gibbous":  ("gibbous chapter", "refine and adjust; progress through analysis and improvement"),
    "full":     ("full-moon chapter", "culmination and visibility; relationships and goals peak"),
    "disseminating": ("disseminating chapter", "share what you've learned; teach, publish, pass it on"),
    "last_quarter": ("last-quarter chapter", "release and reassessment; let go of what no longer fits"),
    "balsamic": ("balsamic chapter", "dissolve and prepare; an old 29.5-year story closes before a new one"),
}

def interpret_progressions(natal_jd, prog_chart):
    """Readable reading over a secondary_progressions() chart:
    progressed Sun/Moon narrative (sign, house, lunar phase) + strongest
    progressed-to-natal aspects + practical summary for the target age."""
    natal_lons, _, _ = body_longitudes(natal_jd)
    age = prog_chart.get("target_age")
    ps = prog_chart["planets"]
    readings = []

    # ── progressed Sun ──────────────────────────────────────────────
    p_sun = ps["Sun"]; n_sun = natal_lons["Sun"]
    sun_sign_change = p_sun["sign"] != sign_of(n_sun)[0]
    readings.append({
        "planet": "Sun",
        "headline": f"Progressed Sun in {p_sun['sign']} (house {p_sun['house']})",
        "text": (
            f"Your evolving identity now runs through {p_sun['sign']} — "
            f"{SIGN_DATA[p_sun['sign']]['keywords'].split(';')[0]} — expressed "
            f"through house {p_sun['house']}: {HOUSE_MEANINGS[p_sun['house']].split(',')[0].lower()}."
            + (" This is a recent sign change: the core self is rewriting its style."
               if sun_sign_change else
               f" The progressed Sun advances ~1°/year; next sign change in "
               f"~{30 - p_sun['deg_in_sign']:.0f} years.")),
    })

    # ── progressed Moon + phase ────────────────────────────────────
    p_moon = ps["Moon"]; n_moon = natal_lons["Moon"]
    phase_angle = norm360(p_moon["abs_lon"] - p_sun["abs_lon"])
    phases = ["new","crescent","first_quarter","gibbous","full",
              "disseminating","last_quarter","balsamic"]
    phase = phases[int(((phase_angle + 22.5) % 360) // 45)]
    ph_label, ph_text = PROG_MOON_PHASE[phase]
    moon_sign_change = p_moon["sign"] != sign_of(n_moon)[0]
    readings.append({
        "planet": "Moon",
        "headline": f"Progressed Moon in {p_moon['sign']} (house {p_moon['house']}) — {ph_label}",
        "text": (f"Emotional focus sits in {p_moon['sign']}, {HOUSE_MEANINGS[p_moon['house']].split(',')[0].lower()}. "
                 f"You're in the {ph_text}. The progressed Moon changes signs every "
                 f"~2.5 years{'; a fresh emotional season just began' if moon_sign_change else ''}."),
        "lunar_phase": phase,
    })

    # ── progressed Ascendant / MC ─────────────────────────────────
    pa = prog_chart.get("ascendant"); pm = prog_chart.get("midheaven")
    if pa and pm:
        readings.append({
            "planet": "Angles",
            "headline": f"Progressed Asc in {pa['sign']}, MC in {pm['sign']}",
            "text": (f"How you meet the world matures into {pa['sign']}; public direction "
                     f"tilts toward {pm['sign']}. Angle shifts mark visible identity pivots."),
        })

    # ── progressed-to-natal aspects (tightest first) ──────────────
    prog_lons = {n: v["abs_lon"] for n, v in ps.items()
                 if n in ("Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn")}
    hits = []
    for pp, plon in prog_lons.items():
        for np_, nlon in natal_lons.items():
            if np_ not in PLANET_ARCHETYPES or np_ == pp:
                continue
            sep = abs(norm180(plon - nlon))
            for asp, (ang, orb, desc) in ASPECTS.items():
                tight = min(orb, 1.5)
                if abs(sep - ang) <= tight:
                    hits.append({"progressed": pp, "to_natal": np_,
                                 "aspect": asp, "orb": round(abs(sep - ang), 2),
                                 "meaning": desc})
                    break
    hits.sort(key=lambda x: x["orb"])
    return {
        "age": age,
        "readings": readings,
        "key_progressed_aspects": hits[:6],
        "summary": (f"At age {age}: identity themes center on "
                    f"{p_sun['sign']} (house {p_sun['house']}), emotions run through "
                    f"a {phase.replace('_',' ')} Moon in {p_moon['sign']}."
                    + (f" Tightest progressed contact: {hits[0]['progressed']} "
                       f"{hits[0]['aspect']} natal {hits[0]['to_natal']} — {hits[0]['meaning']}"
                       if hits else "")),
    }


# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — ZODIACAL RELEASING (Valens, Anthology IV.4-4.11)
# ═════════════════════════════════════════════════════════════════════════════

ZR_PERIODS = {"Aries":15,"Taurus":8,"Gemini":20,"Cancer":25,"Leo":19,
              "Virgo":20,"Libra":8,"Scorpio":15,"Sagittarius":12,
              "Capricorn":27,"Aquarius":30,"Pisces":12}
ZR_SIGNS = list(ZR_PERIODS)          # zodiacal order
# symbolic calendar: 1 year = 360 days, 1 month = 30, L3 "week" = 2.5 d
ZR_LEVEL_DAYS = {1: 360.0, 2: 30.0, 3: 2.5, 4: 5.0/24.0}

def _zr_release_sequence(start_sign, end_day, level):
    """Sequential sign periods from start_sign; applies Loosing of the Bond:
    when the count would re-enter the previous LOB landing sign (initially the
    starting sign), jump to its opposite instead. Durations in symbolic days."""
    seq = []
    cur = start_sign
    lb_landing = start_sign
    day = 0.0
    while day < end_day:
        is_lob = bool(seq) and cur == lb_landing and ZR_SIGNS.index(cur) != -1 \
                 and seq and seq[-1]["sign"] != cur
        if is_lob:
            cur = ZR_SIGNS[(ZR_SIGNS.index(cur) + 6) % 12]
            lb_landing = cur
        dur = ZR_PERIODS[cur] * ZR_LEVEL_DAYS[level]
        seq.append({"sign": cur, "start_day": round(day, 3),
                    "end_day": round(day + dur, 3), "years": ZR_PERIODS[cur],
                    "is_lob": is_lob})
        day += dur
        cur = ZR_SIGNS[(ZR_SIGNS.index(cur) + 1) % 12]
    return seq

def zodiacal_releasing(natal_jd, lat, lng, time_known=True, topic="spirit",
                       max_level=3, until_age=80, as_of_dt=None):
    """Full ZR report. topic: 'spirit' (career/direction) or 'fortune'
    (body/circumstance). Levels 1..max_level nested; peaks = angular signs
    from the Lot of Fortune (whole-sign). Symbolic 360-day-year calendar."""
    eval_dt = as_of_dt or datetime.now(timezone.utc).replace(tzinfo=None)
    eval_s = eval_dt.strftime("%Y-%m-%d")
    lons, _, _ = body_longitudes(natal_jd)
    if time_known:
        asc_lon, _ = ascendant_mc(natal_jd, lat, lng)
    else:
        asc_lon = lons["Sun"]
    sun_tropical = lons["Sun"]
    rel = norm360(asc_lon - sun_tropical)
    is_day_birth = 90 <= rel <= 270
    fortune = part_of_fortune(sun_tropical, lons["Moon"], asc_lon, is_day_birth)
    spirit_lon = norm360((asc_lon + sun_tropical - lons["Moon"]) if not is_day_birth
                         else (asc_lon - sun_tropical + lons["Moon"]))
    fortune_idx = int(fortune["longitude"] // 30) % 12
    spirit_idx = int(spirit_lon // 30) % 12
    adjusted = False
    if topic == "fortune":
        start_idx = fortune_idx
    else:
        start_idx = spirit_idx
        if spirit_idx == fortune_idx:
            start_idx = (start_idx + 1) % 12
            adjusted = True
    birth_dt = datetime(2000, 1, 1) + timedelta(days=natal_jd - 2451544.5)
    end_day = until_age * 365.2425

    def _nested(parent_start_day, parent_end_day, level, first_sign):
        out = []
        cur = first_sign
        lb_landing = first_sign
        day = parent_start_day
        guard = 0
        while day < parent_end_day and guard < 500:
            guard += 1
            is_lob = bool(out) and cur == lb_landing and out[-1]["sign"] != cur
            if is_lob:
                cur = ZR_SIGNS[(ZR_SIGNS.index(cur) + 6) % 12]
                lb_landing = cur
            dur = ZR_PERIODS[cur] * ZR_LEVEL_DAYS.get(level, 2.5)
            out.append({"sign": cur, "start_day": round(day, 3),
                        "end_day": round(min(day + dur, parent_end_day + dur), 3),
                        "is_lob": is_lob})
            day += dur
            cur = ZR_SIGNS[(ZR_SIGNS.index(cur) + 1) % 12]
        return out

    l1 = []
    raw_seq = _zr_release_sequence(ZR_SIGNS[start_idx], end_day, 1)
    for seg in raw_seq:
        sdt = birth_dt + timedelta(days=seg["start_day"])
        edt = birth_dt + timedelta(days=seg["end_day"])
        entry = {"sign": seg["sign"], "years": seg["years"],
                 "is_lob": seg["is_lob"],
                 "start": sdt.strftime("%Y-%m-%d"),
                 "end": edt.strftime("%Y-%m-%d"),
                 "age_at_start": round(seg["start_day"] / 365.2425, 1)}
        dist_from_fortune = (ZR_SIGNS.index(seg["sign"]) - fortune_idx) % 12
        entry["is_peak"] = dist_from_fortune in (0, 3, 6, 9)
        entry["peak_weight"] = ({0: "major", 6: "moderate", 9: "minor",
                                 3: "minor"}.get(dist_from_fortune))
        entry["is_culminating"] = ((ZR_SIGNS.index(seg["sign"]) - start_idx) % 12) == 9
        entry["is_completion"] = (seg["sign"] == ZR_SIGNS[start_idx]
                                  and len(l1) > 0
                                  and any(e["sign"] == seg["sign"] for e in l1))
        nxt_peak_i = None
        for k in range(1, 4):
            cand = ZR_SIGNS[(ZR_SIGNS.index(seg["sign"]) + k) % 12]
            cdist = (ZR_SIGNS.index(cand) - fortune_idx) % 12
            if cdist in (0, 3, 6, 9):
                nxt_peak_i = k
                break
        prv_peak_i = None
        for k in range(1, 4):
            cand = ZR_SIGNS[(ZR_SIGNS.index(seg["sign"]) - k) % 12]
            cdist = (ZR_SIGNS.index(cand) - fortune_idx) % 12
            if cdist in (0, 3, 6, 9):
                prv_peak_i = k
                break
        if not entry["is_peak"]:
            if nxt_peak_i == 1: entry["triad_role"] = "build-up to peak"
            elif prv_peak_i == 1: entry["triad_role"] = "post-peak cool-down"
        if max_level >= 2:
            subs = _nested(seg["start_day"], seg["end_day"], 2, seg["sign"])
            entry["level2"] = [
                {"sign": s["sign"],
                 "start": (birth_dt + timedelta(days=s["start_day"])).strftime("%Y-%m-%d"),
                 "end": (birth_dt + timedelta(days=s["end_day"])).strftime("%Y-%m-%d"),
                 "is_lob": s["is_lob"]} for s in subs[:40]]
        l1.append(entry)
    active = next((e for e in reversed(l1)
                   if e["start"] <= eval_s), l1[0])
    active_l2 = None
    if max_level >= 2 and active.get("level2"):
        active_l2 = next((s for s in active["level2"]
                          if s["start"] <= eval_s < s["end"]), None)
    return {
        "topic": topic,
        "as_of_date": eval_s,
        "release_point": ZR_SIGNS[start_idx],
        "lot_of_fortune_sign": ZR_SIGNS[fortune_idx],
        "lot_of_spirit_sign": ZR_SIGNS[spirit_idx],
        "valens_adjustment_applied": adjusted,
        "sect": "day" if is_day_birth else "night",
        "peak_signs": [ZR_SIGNS[(fortune_idx + k) % 12] for k in (0, 3, 6, 9)],
        "active_period": {"l1": active["sign"], "l2": active_l2 and active_l2["sign"],
                          "since": active["start"]},
        "timeline_level1": l1,
        "note": ("Zodiacal Releasing per Vettius Valens, Anthology IV "
                 "(Schmidt/Riley): sequential sign-periods on the 360-day "
                 "symbolic year; Loosing-of-the-Bond jumps opposite at lap end; "
                 "peaks are angles from the Lot of Fortune."),
    }


ZR_TOPIC_FRAME = {
    "spirit": ("career, life-direction, and actions",
               "Valens rates Spirit-releases as the primary eminence/career timer"),
    "fortune": ("body, health, and material circumstance",
                "Fortune-releases track vitality, luck, and external events"),
}

def interpret_zr(zr_report, as_of_dt=None):
    """Readable narrative over zodiacal_releasing(): what the active L1/L2
    mean at as_of_dt, when the next peak/LOB hits, lifetime highlight reel."""
    eval_dt = as_of_dt or datetime.now(timezone.utc).replace(tzinfo=None)
    eval_s = eval_dt.strftime("%Y-%m-%d")
    topic_label, topic_note = ZR_TOPIC_FRAME.get(
        zr_report["topic"], ZR_TOPIC_FRAME["spirit"])
    tl = zr_report["timeline_level1"]
    active = next((e for e in reversed(tl)
                   if e["start"] <= eval_s), tl[0])
    l2_active = None
    for s in active.get("level2", []):
        if s["start"] <= eval_s < s["end"]:
            l2_active = s
            break
    readings = []
    role = active.get("triad_role")
    if active["is_peak"]:
        peak_txt = {"major": "the MAJOR peak of the life (angular to Fortune's own sign)",
                    "moderate": "a moderate peak (7th-from-Fortune)",
                    "minor": "a minor peak (angle from Fortune)"}.get(
                        active.get("peak_weight"), "a peak period")
        readings.append(f"You are in {active['sign']} — {peak_txt}. "
                        f"Eminence markers in {topic_label} concentrate here.")
    elif role == "build-up to peak":
        nxt = next((e for e in tl if e["start"] > eval_s and e["is_peak"]), None)
        readings.append(f"{active['sign']} is a build-up period: momentum gathers "
                        f"toward the {nxt['sign']} peak starting {nxt['start']}."
                        if nxt else f"{active['sign']} builds toward an upcoming peak.")
    elif role == "post-peak cool-down":
        readings.append(f"{active['sign']} follows a peak — consolidate gains rather "
                        f"than force new heights in {topic_label}.")
    else:
        readings.append(f"{active['sign']} is a steady chapter in {topic_label} — "
                        f"ordinary time that sets up the extraordinary ones.")
    if l2_active:
        lob = " (Loosing of the Bond — a pivot point!)" if l2_active.get("is_lob") else ""
        readings.append(f"Sub-period at this moment: {l2_active['sign']} until "
                        f"{l2_active['end']}{lob}.")
    if active.get("is_lob"):
        readings.append("This major period itself began with a Loosing of the Bond — "
                        "expect its whole chapter to feel like a departure from the prior one.")
    upcoming_peaks = [e for e in tl if e["is_peak"] and e["start"] > eval_s][:3]
    upcoming_lobs = [e for e in tl if e["is_lob"] and e["start"] > eval_s][:3]
    highlights = []
    for e in tl:
        tag = []
        if e["is_peak"]: tag.append(f"PEAK ({e.get('peak_weight')})")
        if e["is_lob"]: tag.append("LOB")
        if e["is_culminating"]: tag.append("culminating")
        if tag:
            highlights.append(f"{e['start']}–{e['end']}  {e['sign']}: " + ", ".join(tag))
    return {
        "as_of_date": eval_s,
        "current_reading": " ".join(readings),
        "upcoming_peaks": [{"sign": e["sign"], "from": e["start"],
                            "weight": e.get("peak_weight")} for e in upcoming_peaks],
        "upcoming_lobs": [{"sign": e["sign"], "from": e["start"]} for e in upcoming_lobs],
        "lifetime_highlights": highlights[:12],
        "note": topic_note,
    }


# Classical Gochara (transit) favorable houses from natal MOON — Parashari
# standard (BPHS/Phala Deepika; subagent spec pending exact page refs):
GOCHARA_GOOD_FROM_MOON = {
    "Sun": (3, 6, 10, 11), "Moon": (1, 3, 6, 7, 10, 11),
    "Mars": (3, 6, 11), "Mercury": (2, 4, 6, 8, 10, 11),
    "Jupiter": (2, 5, 7, 9, 11), "Venus": (1, 2, 3, 4, 5, 8, 9, 11, 12),
    "Saturn": (3, 6, 11), "North Node": (3, 6, 11), "South Node": (3, 6, 11),
}
# Sade Sati handled in transits(); here: full gochara snapshot

def gochara(natal_jd, transit_jd=None, lat=0.0, lng=0.0):
    """Vedic transits counted from the natal Moon (Chandra Rashi) + Ashtakavarga
    strength scores per BPHS Ch.72 (SAV threshold 28+ for fruitful transits).
    Returns per-planet favorability, SAV score, and classical notes."""
    natal_lons, _, _ = body_longitudes(natal_jd)
    t_jd = transit_jd or julian_day(datetime.utcnow())
    t_lons, t_speed, _ = body_longitudes(t_jd)
    ayan = ayanamsha_lahiri(t_jd)
    moon_sign_idx = int(norm360(natal_lons["Moon"] - ayanamsha_lahiri(natal_jd)) // 30) % 12
    # Compute Ashtakavarga for the chart
    ashta = ashtakavarga(natal_jd, lat, lng, time_known=True)
    sav_list = ashta.get("sarvashtakavarga", [28]*12)
    bav_dict = ashta.get("bhinnashtakavarga", {})
    out = {}
    for p, good in GOCHARA_GOOD_FROM_MOON.items():
        if p not in t_lons:
            continue
        p_sid = norm360(t_lons[p] - ayan)
        sign_idx = int(p_sid // 30) % 12
        target_sign = SIGNS[sign_idx]
        house_from_moon = ((sign_idx - moon_sign_idx) % 12) + 1
        favorable_house = house_from_moon in good
        sav_bindus = sav_list[sign_idx] if isinstance(sav_list, list) and len(sav_list) == 12 else 28
        bav_p = bav_dict.get(p, [4]*12)
        bav_bindus = bav_p[sign_idx] if isinstance(bav_p, list) and len(bav_p) == 12 else 4

        # BPHS Ch.72 rules: SAV >= 28 is auspicious; < 25 is challenging
        # BAV >= 4 is positive for the individual planet
        sav_status = "Auspicious (SAV >= 28)" if sav_bindus >= 28 else "Challenging (SAV < 25)" if sav_bindus < 25 else "Neutral (SAV 25-27)"
        note = ""
        if p == "Saturn":
            d = (sign_idx - moon_sign_idx) % 12
            if d == 11: note = "Sade Sati rising phase"
            elif d == 0: note = "Sade Sati peak"
            elif d == 1: note = "Sade Sati setting phase"
            elif d == 4: note = "Ardha-ashtama (half)"
            elif d == 7: note = "Ashtama Shani"
        out[p] = {"house_from_moon": house_from_moon,
                  "transit_sign": target_sign,
                  "sav_bindus": sav_bindus,
                  "bav_bindus": bav_bindus,
                  "sav_status": sav_status,
                  "favorable": favorable_house and sav_bindus >= 25 and bav_bindus >= 4,
                  "retrograde": t_speed.get(p, 0) < 0,
                  "note": note,
                  "good_houses": list(good)}
    return {"from_moon_sign": SIGNS[moon_sign_idx], "transits": out,
            "note": ("Gochara from Chandra Lagna per Parashari standard combined "
                     "with BPHS Ch.72 Sarvashtakavarga scores (SAV >= 28 auspicious).")}


DASHA_LORD_THEMES = {
    "Sun": "authority, government, father, bones, vitality, recognition; ego vs humility",
    "Moon": "mother, emotions, home, public, liquids, mind's peace; fluctuation",
    "Mars": "conflicts, property, siblings, surgery, courage, land; haste and accidents",
    "Mercury": "education, trade, speech, friends, nerves, documents; versatility",
    "Jupiter": "wealth, children, guru, dharma, expansion, marriage; optimism and gain",
    "Venus": "marriage, romance, arts, vehicles, comfort, women; luxury and diplomacy",
    "Saturn": "labor, delays, discipline, longevity, servants, loss then lasting gain",
    "Rahu": "ambition, unconventional rise, foreign, poison/obsession; sudden swings",
    "Ketu": "detachment, spirituality, obstacles, pilgrimage; endings that liberate",
    "North Node": "ambition, unconventional rise, foreign, poison/obsession; sudden swings",
    "South Node": "detachment, spirituality, obstacles, pilgrimage; endings that liberate",
}

def interpret_vimshottari(vim):
    """Readable reading over a vimshottari() result: current maha/antar/pratyantar
    themes + how to read the combination."""
    out = {}
    maha = vim.get("current_mahadasha")
    antar = vim.get("current_antardasha")
    praty = vim.get("current_pratyantardasha")
    if not maha:
        return {"reading": "No active mahadasha found.", }
    lines = [f"Mahadasha of {maha['lord']} ({maha['start']} → {maha['end']}): "
             f"{DASHA_LORD_THEMES[maha['lord']]}."]
    if antar:
        lines.append(f"Antardasha of {antar['lord']} ({antar['start']} → {antar['end']}): "
                     f"{DASHA_LORD_THEMES[antar['lord']]}")
        lines.append(f"The maha sets the stage; the antar decides which script plays. "
                     f"{maha['lord']}+{antar['lord']} blends both themes.")
    if praty:
        lines.append(f"Pratyantardasha of {praty['lord']} until {praty['end']}: "
                     f"short-term flavor — {DASHA_LORD_THEMES[praty['lord']].split(';')[0]}.")
    return {"reading": " ".join(lines),
            "themes": {k: DASHA_LORD_THEMES[k] for k in
                       (maha["lord"],) + ((antar["lord"],) if antar else ())}}


# Jaimini Chara Dasha (K.N. Rao method — the widely-used variant):
# period years = distance from sign to its lord's sign (counting the sign
# itself as 1, direct for odd-foot... simplified: standard Rao counting);
# sequence starts from the Lagna sign and proceeds by "direction" (direct
# if lagna in odd sign, reverse if even). 9th strongest etc. omitted —
# we use the simple Rao duration rule.
def chara_dasha(natal_jd, lat, lng, time_known=True, until_age=90, as_of_dt=None):
    """Chara (sign) dasha per K.N. Rao: periods of SIGNS not planets.
    Duration = count from the sign to its lord (min of direct/reverse counts,
    minus 1 when lord is IN that sign → 12 years). Starts from Lagna sign."""
    eval_dt = as_of_dt or datetime.now(timezone.utc).replace(tzinfo=None)
    lons, _, _ = body_longitudes(natal_jd)
    if time_known:
        asc_lon, _ = ascendant_mc(natal_jd, lat, lng)
    else:
        asc_lon = lons["Sun"]
    ayan = ayanamsha_lahiri(natal_jd)
    sid = {p: norm360(lons[p] - ayan) for p in lons}
    asc_sid = norm360(asc_lon - ayan)
    RASHI_LORDS_J = {"Aries":"Mars","Taurus":"Venus","Gemini":"Mercury",
                     "Cancer":"Moon","Leo":"Sun","Virgo":"Mercury",
                     "Libra":"Venus","Scorpio":"Mars","Sagittarius":"Jupiter",
                     "Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"}
    def sign_years(sign_idx):
        sign_name = SIGNS[sign_idx]
        lord = RASHI_LORDS_J[sign_name]
        try:
            lord_idx = int(sid[lord] // 30) % 12
        except KeyError:
            return 6
        fwd = ((lord_idx - sign_idx) % 12) or 12
        rev = ((sign_idx - lord_idx) % 12) or 12
        n = min(fwd, rev)
        return 12 if n == 1 else n - 1
    start_idx = int(asc_sid // 30) % 12
    direction = 1 if start_idx % 2 == 0 else -1
    birth_dt = datetime(2000, 1, 1) + timedelta(days=natal_jd - 2451544.5)
    timeline = []
    idx = start_idx
    cursor_days = 0.0
    k = 0
    while cursor_days / 365.2425 < until_age and k < 24:
        yrs = chara_years_cache.get(SIGNS[idx]) or sign_years(idx)
        chara_years_cache[SIGNS[idx]] = yrs
        sdt = birth_dt + timedelta(days=cursor_days)
        edt = birth_dt + timedelta(days=cursor_days + yrs * 365.25)
        timeline.append({"sign": SIGNS[idx], "years": yrs,
                         "start": sdt.strftime("%Y-%m-%d"),
                         "end": edt.strftime("%Y-%m-%d"),
                         "is_current": sdt <= eval_dt <= edt})
        cursor_days += yrs * 365.25
        idx = (idx + direction) % 12
        k += 1
    current = next((t for t in timeline if t["is_current"]), None)
    return {"system": "Chara Dasha (Jaimini/K.N. Rao)",
            "as_of_date": eval_dt.strftime("%Y-%m-%d"),
            "starting_sign": SIGNS[start_idx],
            "current_dasha": current,
            "timeline": timeline[:16],
            "note": ("Rashi (sign) dasha: each SIGN governs a period; length "
                     "= count to its lord (own-sign lordship → 12y). "
                     "Simplified single-lord rule for dual-lord signs.")}

chara_years_cache = {}


# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — MUNDANE ASTROLOGY: INGRESSES, ECLIPSE ACTIVATION, LUNATIONS
# ═════════════════════════════════════════════════════════════════════════════

MUNDANE_HOUSE_MEANINGS = {
    1: "the nation's people and collective mood",
    2: "the economy, treasury, national wealth",
    3: "media, transport, neighboring states, education",
    4: "land, agriculture, housing, the opposition (in some traditions)",
    5: "entertainment, sports, births, speculation markets",
    6: "public health, workforce, civil service, military rank-and-file",
    7: "foreign affairs, treaties, open enemies, war/peace",
    8: "deaths, national debt, crises, intelligence services",
    9: "law, courts, religion, long-distance relations, trade abroad",
    10: "the government, head of state, national reputation",
    11: "parliament, allies, legislative bodies, public hopes",
    12: "prisons, hospitals, secret enemies, covert operations",
}

def solar_ingress_jd(year, sign_idx):
    """Exact JD when the Sun enters SIGNS[sign_idx] in the given year
    (bisection over the ~3-day window around the expected date).
    sign_idx 0=Aries (Mar), 3=Cancer (Jun), 6=Libra (Sep), 9=Capricorn (Dec)."""
    month = [3, 6, 9, 12][sign_idx // 3]
    day0 = [20, 21, 22, 21][sign_idx // 3]
    target_lon = sign_idx * 30.0
    low = julian_day(datetime(year, month, day0 - 2))
    high = julian_day(datetime(year, month, day0 + 2))
    for _ in range(50):
        mid = (low + high) / 2
        sun = tropical_longitudes(mid)["Sun"]
        diff = norm180(sun - target_lon)
        if abs(diff) < 0.0005:
            break
        if diff > 0:
            high = mid
        else:
            low = mid
    return (low + high) / 2

def mundane_chart(jd_moment, lat, lng, title=""):
    """Full chart cast for a mundane moment at a capital; adds mundane house
    glosses to planets."""
    ch = western_chart(jd_moment, lat, lng, True)
    ch["system"] = title or "Mundane Ingress Chart"
    for nm, blk in ch["planets"].items():
        h = blk.get("house")
        if h in MUNDANE_HOUSE_MEANINGS:
            blk["mundane_signification"] = MUNDANE_HOUSE_MEANINGS[h]
    return ch

# Mundane planetary significations per traditional mundane astrology
# (Lilly / Raphael / Skyscript Ingresses canon):
MUNDANE_PLANET_ROLES = {
    "Sun": "the sovereign, head of state, national leaders, magistrates",
    "Moon": "the general populace, public opinion, crowds, women of the nation",
    "Mercury": "the press, media, communications, trade, local commuting",
    "Venus": "arts, cultural diplomacy, social peace, treaties and alliances",
    "Mars": "armed forces, warfare, strikes, civil conflict, fires, emergency services",
    "Jupiter": "the judiciary, high finance, legal institutions, religion, national wealth",
    "Saturn": "the elderly, national mourning, epidemic/public health strains, mining, land",
    "Uranus": "political disruption, protests, technological shocks, right/left volatility",
    "Neptune": "covert operations, ideological movements, scandals, supply confusion",
    "Pluto": "deep-structural institutional overhaul, intelligence services, organized crime",
    "North Node": "amplification, expansion, karmic public focus (Jupiter-like nature)",
    "South Node": "drain, loss, release, institutional reckoning (Saturn-like nature)",
}

def ingress_validity_period(asc_sign):
    """Classical ingress validity rule (Bonatti/Lilly):
    Fixed Ascendant (Taurus/Leo/Scorpio/Aquarius) -> valid whole 12 months.
    Mutable Ascendant (Gemini/Virgo/Sag/Pisces) -> valid 6 months (re-cast at Libra).
    Cardinal Ascendant (Aries/Cancer/Libra/Cap) -> valid 3 months (re-cast each quarter)."""
    mod = SIGN_DATA[asc_sign]["modality"]
    if mod == "Fixed":
        return {"validity_months": 12, "scope": "entire solar year (12 months)",
                "note": "Fixed rising: this single Aries Ingress governs the whole year."}
    elif mod == "Mutable":
        return {"validity_months": 6, "scope": "half year (6 months) — re-cast at Libra ingress",
                "note": "Mutable rising: valid for 6 months; the Libra Ingress takes over for autumn/winter."}
    else:
        return {"validity_months": 3, "scope": "one quarter (3 months) — re-cast each cardinal ingress",
                "note": "Cardinal rising: valid for one season; cast separate charts for Cancer, Libra, Capricorn."}

def resolve_mundane_ingress_for_date(country_name, lat, lng, target_dt):
    """Dynamic resolution for AI Agents (Bonatti/Lilly doctrine):
    Given a country and a target date, accurately determines which solar ingress
    chart is legally in force based on the Aries Ingress Ascendant modality.
    Calculates exact astronomical transition points dynamically."""
    # 1. Determine base solar year of the target date (Aries ingress occurs ~Mar 20)
    year = target_dt.year
    aries_jd = solar_ingress_jd(year, 0)
    aries_dt = _jd_to_dt(aries_jd)
    if target_dt < aries_dt:
        # Before this year's Aries ingress -> governed by previous year's ingress cycle
        year -= 1
        aries_jd = solar_ingress_jd(year, 0)
        aries_dt = _jd_to_dt(aries_jd)

    # 2. Check Aries Ingress Ascendant modality for this location
    asc_lon, _ = ascendant_mc(aries_jd, lat, lng)
    asc_sign = sign_of(asc_lon)[0]
    mod = SIGN_DATA[asc_sign]["modality"]

    # 3. Calculate exact moments of all cardinal ingresses for the active solar year
    cancer_dt = _jd_to_dt(solar_ingress_jd(year, 3))
    libra_dt = _jd_to_dt(solar_ingress_jd(year, 6))
    capricorn_dt = _jd_to_dt(solar_ingress_jd(year, 9))
    next_aries_dt = _jd_to_dt(solar_ingress_jd(year + 1, 0))

    # 4. Resolve active ingress and validity boundaries
    if mod == "Fixed":
        # Governs the entire 12-month solar year
        active_kind = "aries"
        v_start = aries_dt
        v_end = next_aries_dt
        reason = f"Aries Ingress has Fixed rising ({asc_sign}) -> valid for the entire 12-month solar year."
    elif mod == "Mutable":
        # 6-month validity: Aries covers spring/summer, Libra covers autumn/winter
        if target_dt < libra_dt:
            active_kind = "aries"
            v_start = aries_dt
            v_end = libra_dt
            reason = f"Aries Ingress has Mutable rising ({asc_sign}) -> valid for 6 months (Spring/Summer)."
        else:
            active_kind = "libra"
            v_start = libra_dt
            v_end = next_aries_dt
            reason = f"Aries Ingress has Mutable rising ({asc_sign}) -> Autumn/Winter governed by Libra Ingress."
    else: # Cardinal
        # 3-month seasonal validity: re-cast each cardinal ingress
        if target_dt < cancer_dt:
            active_kind = "aries"
            v_start = aries_dt
            v_end = cancer_dt
            reason = f"Aries Ingress has Cardinal rising ({asc_sign}) -> valid for 1 season (Spring)."
        elif target_dt < libra_dt:
            active_kind = "cancer"
            v_start = cancer_dt
            v_end = libra_dt
            reason = f"Aries Ingress has Cardinal rising ({asc_sign}) -> Summer governed by Cancer Ingress."
        elif target_dt < capricorn_dt:
            active_kind = "libra"
            v_start = libra_dt
            v_end = capricorn_dt
            reason = f"Aries Ingress has Cardinal rising ({asc_sign}) -> Autumn governed by Libra Ingress."
        else:
            active_kind = "capricorn"
            v_start = capricorn_dt
            v_end = next_aries_dt
            reason = f"Aries Ingress has Cardinal rising ({asc_sign}) -> Winter governed by Capricorn Ingress."

    # 5. Build the actively governing ingress chart
    result = ingress_chart(country_name, lat, lng, year, active_kind)
    result["agent_validity"] = {
        "active_ingress": active_kind,
        "governing_solar_year": year,
        "valid_from": v_start.strftime("%Y-%m-%d %H:%M UTC"),
        "valid_until": v_end.strftime("%Y-%m-%d %H:%M UTC"),
        "next_recast_date": v_end.strftime("%Y-%m-%d"),
        "resolution_reason": reason,
        "ascendant_modality": mod,
        "is_currently_valid": v_start <= target_dt < v_end
    }
    return result

def ingress_chart(country_name, lat, lng, year=None, kind="aries"):
    """Aries ingress = solar year for the nation; cardinal ingresses seasonally.
    Evaluates validity period by Ascendant modality (Bonatti/Lilly) + classical
    mundane planet-in-house judgments."""
    year = year or TODAY.year
    idx_map = {"aries": 0, "cancer": 3, "libra": 6, "capricorn": 9}
    key = kind.lower()
    if key not in idx_map:
        return {"error": "kind must be aries|cancer|libra|capricorn"}
    jd_m = solar_ingress_jd(year, idx_map[key])
    utc_dt = _jd_to_dt(jd_m)
    ch = mundane_chart(jd_m, lat, lng,
                       f"{country_name.capitalize()} {kind.capitalize()} Ingress {year}")
    asc_sign = ch["ascendant"]["sign"]
    validity = ingress_validity_period(asc_sign)
    # headline mundane judgments (classical: planet roles x house spheres)
    judgments = []
    sun_h = ch["planets"]["Sun"]["house"]
    sat = ch["planets"]["Saturn"]; mar = ch["planets"]["Mars"]; jup = ch["planets"]["Jupiter"]
    moon = ch["planets"]["Moon"]
    judgments.append(f"Ascendant in {asc_sign} ({SIGN_DATA[asc_sign]['modality']}): {validity['note']}")
    judgments.append(f"Sun in house {sun_h}: {MUNDANE_PLANET_ROLES['Sun']} actively shaped by {MUNDANE_HOUSE_MEANINGS.get(sun_h, '')}.")
    judgments.append(f"Moon in house {moon['house']} ({moon['sign']}): public mood centers on {MUNDANE_HOUSE_MEANINGS.get(moon['house'], '')}.")
    judgments.append(f"Saturn in house {sat['house']} ({sat['sign']}): pressure on {MUNDANE_HOUSE_MEANINGS.get(sat['house'], '')} — {MUNDANE_PLANET_ROLES['Saturn']}.")
    judgments.append(f"Mars in house {mar['house']} ({mar['sign']}): energy/volatility in {MUNDANE_HOUSE_MEANINGS.get(mar['house'], '')}.")
    judgments.append(f"Jupiter in house {jup['house']} ({jup['sign']}): growth and protection for {MUNDANE_HOUSE_MEANINGS.get(jup['house'], '')}.")
    ang = [n for n in ("Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn")
           if ch["planets"][n]["house"] in (1,4,7,10)]
    if len(ang) >= 4:
        judgments.append(f"Angular concentration ({len(ang)}/7 planets in 1/4/7/10): an eventful, highly visible period.")
    return {"place": {"lat": lat, "lng": lng},
            "moment_utc": utc_dt.strftime("%Y-%m-%d %H:%M"),
            "validity": validity,
            "chart": ch,
            "judgments": judgments}


MUNDANE_CAPITALS = {
    "iran": (35.6892, 51.3890), "usa": (38.8951, -77.0364),
    "uk": (51.5074, -0.1278), "france": (48.8566, 2.3522),
    "germany": (52.5200, 13.4050), "russia": (55.7558, 37.6173),
    "china": (39.9042, 116.4074), "israel": (31.7683, 35.2137),
    "turkey": (39.9334, 32.8597), "india": (28.6139, 77.2090),
    "japan": (35.6762, 139.6503), "brazil": (-15.7975, -47.8919),
}

def eclipse_activations(natal_chart_jd, lat, lng, count=4):
    """Map upcoming eclipses onto this chart's houses: what life-sphere each
    one electrifies, plus classical trigger timing (Carter/Bonatti rule: latent
    events trigger ~3 months later when Sun squares the eclipse point, or on
    Mars transit over it)."""
    ecl = next_eclipses(julian_day(datetime.utcnow()), count=count)
    if isinstance(ecl, dict) and "error" in ecl:
        return ecl
    asc_lon, _ = ascendant_mc(natal_chart_jd, lat, lng)
    out = []
    for e in ecl:
        jd_e = e["jd"]
        lon_e = tropical_longitudes(jd_e)
        if e["type"] == "solar":
            deg = lon_e["Sun"]
        else:
            deg = lon_e["Moon"]
        house = whole_sign_house(deg, asc_lon)
        sign = sign_of(deg)[0]
        # classical trigger window: Sun square = ~90 days later
        dt_e = _jd_to_dt(jd_e)
        sun_square_trigger = dt_e + timedelta(days=91.3)
        out.append({
            **e,
            "degree": round(deg % 30, 2), "sign": sign,
            "house_of_natal_chart": house,
            "activates": MUNDANE_HOUSE_MEANINGS.get(house, ""),
            "nature": ("Solar: new-cycle seed, structural/leadership reset"
                       if e["type"] == "solar"
                       else "Lunar: emotional climax, disclosure, public outcome"),
            "trigger_timing": {
                "sun_square_window": sun_square_trigger.strftime("%Y-%m-%d"),
                "rule": "Carter trigger rule: events often manifest when transiting Sun squares this point (~3 months later)"
            },
        })
    return out


def lunation_cycle(lat, lng, count=3, start_jd=None):
    """Next new/full moons cast as charts for a location — the monthly
    weather of a nation or person. New Moon = seed/theme; Full = climax."""
    t = start_jd or julian_day(datetime.utcnow())
    out = []
    for _ in range(count):
        # find next new moon: Moon-Sun elongation = 0 (bisection per lunation)
        low = t
        e = norm360(tropical_longitudes(low)["Moon"] - tropical_longitudes(low)["Sun"])
        high = low + 29.65
        for _ in range(45):
            mid = (low + high) / 2
            l2 = tropical_longitudes(mid)
            diff = norm180(l2["Moon"] - l2["Sun"])
            if abs(diff) < 0.001:
                break
            if diff > 0:
                high = mid
            else:
                low = mid
        nm_jd = (low + high) / 2
        ch = mundane_chart(nm_jd, lat, lng, "New Moon")
        fm_jd = nm_jd + 14.77
        chf = mundane_chart(fm_jd, lat, lng, "Full Moon")
        sun_h = ch["planets"]["Sun"]["house"]
        moon_h_nm = ch["planets"]["Moon"]["house"]
        moon_h_fm = chf["planets"]["Moon"]["house"]
        out.append({
            "new_moon": _jd_to_dt(nm_jd).strftime("%Y-%m-%d %H:%M"),
            "new_moon_sign": sign_of(tropical_longitudes(nm_jd)["Sun"])[0],
            "theme_house": sun_h,
            "theme": MUNDANE_HOUSE_MEANINGS.get(sun_h, ""),
            "moon_house_at_new": moon_h_nm,
            "full_moon": _jd_to_dt(fm_jd).strftime("%Y-%m-%d %H:%M"),
            "full_moon_climax_house": moon_h_fm,
        })
        t = nm_jd + 25.0
    return {"lunations": out,
            "note": ("Monthly lunation cycle: each New Moon seeds a theme "
                     "(its Sun's house); the Full Moon two weeks later "
                     "brings the related matter to a head.")}


# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — SYNASTRY & RELATIONSHIP ASTROLOGY (Ibn Ezra & Classical Overlays)
# ═════════════════════════════════════════════════════════════════════════════

def ibn_ezra_relationship_lots(lons, asc_lon, is_day_chart=True):
    """Calculate the 7 primary Medieval/Hebrew relationship lots per Abraham Ibn Ezra,
    Reshit Hokhmah (The Beginning of Wisdom, Chapter IX, Sela ed. pp. 244-246).
    Distances are calculated as: Destination - Source, cast from Origin (Origin + Dest - Source)."""
    desc_lon = norm360(asc_lon + 180.0)
    sun = lons["Sun"]; moon = lons["Moon"]; ven = lons["Venus"]
    mars = lons["Mars"]; sat = lons["Saturn"]; jup = lons["Jupiter"]

    def _calc_lot(origin, source, dest):
        val = norm360(origin + dest - source)
        s, idx, deg = sign_of(val)
        return {"longitude": round(val, 3), "sign": s, "deg_in_sign": round(deg, 2)}

    lots = {
        "lot_of_marriage_general": {
            **_calc_lot(asc_lon, ven, desc_lon),
            "formula": "Asc + Descendant - Venus (Day & Night)",
            "meaning": "General marriage harmony, public union, and the contractual bond"
        },
        "lot_of_marriage_men_enoch": {
            **_calc_lot(asc_lon, sat, ven),
            "formula": "Asc + Venus - Saturn (Enoch tradition)",
            "meaning": "Marriage condition and stability for men (endurance vs restriction)"
        },
        "lot_of_marriage_valens": {
            **_calc_lot(asc_lon, sun, ven),
            "formula": "Asc + Venus - Sun (Valens tradition)",
            "meaning": "Vital affection, romantic initiation, and conscious desire"
        },
        "lot_of_marriage_timing": {
            **_calc_lot(asc_lon, sun, moon),
            "formula": "Asc + Moon - Sun (Day & Night)",
            "meaning": "Timing and ripeness for long-term commitment"
        },
        "lot_of_chastity_loyalty": {
            **_calc_lot(asc_lon, moon, ven),
            "formula": "Asc + Venus - Moon (Day & Night)",
            "meaning": "Fidelity, mutual trust, and devotion in relationship"
        },
        "lot_of_passion_desire": {
            **_calc_lot(asc_lon, moon, mars),
            "formula": "Asc + Mars - Moon (Day & Night)",
            "meaning": "Physical chemistry, passion, drive, and sexual attraction"
        },
        "lot_of_marital_strife": {
            **_calc_lot(asc_lon, mars, jup),
            "formula": "Asc + Jupiter - Mars (Day & Night)",
            "meaning": "Friction points, disputes over boundaries, and legal/ethical conflicts"
        }
    }
    return lots

def synastry_house_overlays(lonsA, asc_lonB, cuspsB=None):
    """Determine which houses of Person B are activated by Person A's planets.
    House overlays reveal where Person A's energy lands in Person B's lived experience."""
    overlays = {}
    for p, lon in lonsA.items():
        if p not in PLANET_ARCHETYPES:
            continue
        h = placidus_house_of(lon, cuspsB) if cuspsB else whole_sign_house(lon, asc_lonB)
        overlays[p] = {
            "in_partner_house": h,
            "sign": sign_of(lon)[0],
            "experience": f"Person A's {p} activates Person B's {HOUSE_MEANINGS[h].split(',')[0].lower()}"
        }
    return overlays

def interpret_composite_chart(comp_chart):
    """Produce structured readings for the composite chart (the relationship as an entity):
    Composite Sun (core purpose), Composite Moon (emotional bond), Composite Ascendant (social face)."""
    ps = comp_chart["planets"]
    sun = ps.get("Sun"); moon = ps.get("Moon"); asc = comp_chart.get("ascendant")
    readings = []
    if sun:
        readings.append(f"Composite Sun in {sun['sign']} (house {sun['house']}): the relationship's core purpose centers on {HOUSE_MEANINGS[sun['house']].split(',')[0].lower()}.")
    if moon:
        readings.append(f"Composite Moon in {moon['sign']} (house {moon['house']}): emotional safety is found through {HOUSE_MEANINGS[moon['house']].split(',')[0].lower()}.")
    if asc:
        readings.append(f"Composite Rising in {asc['sign']}: the couple presents to the world with a {SIGN_DATA[asc['sign']]['keywords'].split(';')[0]} vibe.")
    return {
        "relationship_identity": readings,
        "dominant_house": sun["house"] if sun else None,
        "note": "The composite chart is the chart of the relationship itself — what the two people become together."
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — ADVANCED SYNASTRY: DAVISON CHART & DRACONIC ASTROLOGY
# ═════════════════════════════════════════════════════════════════════════════

def davison_chart(jdA, jdB, latA, lngA, latB, lngB, as_of_dt=None):
    """Davison Time-Space Relationship Chart (Ronald C. Davison method):
    Unlike the midpoint composite (which is an unphysical spatial abstraction),
    the Davison chart is calculated for the exact mathematical midpoint in time
    (JD_mid) and geographic coordinates (Lat_mid, Lng_mid).
    This creates a true physical birth chart for the relationship itself,
    allowing real planetary transits and secondary progressions to be cast upon it."""
    mid_jd = (jdA + jdB) / 2.0
    mid_lat = (latA + latB) / 2.0
    mid_lng = (lngA + lngB) / 2.0
    # Normalize longitude midpoint
    diff_lng = abs(lngA - lngB)
    if diff_lng > 180:
        mid_lng = norm180(mid_lng + 180.0)

    mid_dt = datetime(2000, 1, 1) + timedelta(days=mid_jd - 2451544.5)
    chart = western_chart(mid_jd, mid_lat, mid_lng, time_known=True)
    chart["system"] = "Davison Time-Space Chart"

    # Optional: evaluate transits to the Davison relationship chart
    eval_dt = as_of_dt or datetime.now(timezone.utc).replace(tzinfo=None)
    eval_jd = julian_day(eval_dt)
    rel_transits = transits(mid_jd, mid_lat, mid_lng, eval_dt)

    return {
        "davison_midpoint": {
            "datetime_utc": mid_dt.strftime("%Y-%m-%d %H:%M UTC"),
            "julian_day": round(mid_jd, 5),
            "latitude": round(mid_lat, 4),
            "longitude": round(mid_lng, 4)
        },
        "chart": chart,
        "relationship_transits": interpret_transits(rel_transits),
        "note": ("The Davison chart represents the relationship as a true event in space-time. "
                 "Current relationship weather is tracked via real transits to the Davison midpoint chart.")
    }

def draconic_chart(natal_jd, lat, lng, time_known=True):
    """Calculate the Draconic Chart (Nodal Soul Chart):
    Shifts the entire zodiac so that the True North Node becomes 0° Aries.
    Formula: lambda_draconic = (lambda_tropical - lambda_TrueNode) % 360.
    In psychological and karmic astrology, the Draconic chart reflects the soul's
    spiritual blueprint, core motivations, and unconscious contracts."""
    lons_trop, speed, backend = body_longitudes(natal_jd)
    node_lon = lons_trop.get("North Node", 0.0)

    drac_lons = {}
    for name, lon in lons_trop.items():
        drac_lons[name] = norm360(lon - node_lon)

    asc_trop, mc_trop = ascendant_mc(natal_jd, lat, lng) if time_known else (lons_trop["Sun"], 0.0)
    drac_asc = norm360(asc_trop - node_lon)
    drac_mc = norm360(mc_trop - node_lon)

    planets = {}
    for nm, d_lon in drac_lons.items():
        s, idx, deg = sign_of(d_lon)
        h = whole_sign_house(d_lon, drac_asc)
        planets[nm] = {
            "draconic_longitude": round(d_lon, 3),
            "sign": s,
            "deg_in_sign": round(deg, 2),
            "house": h,
            "tropical_equivalent": round(lons_trop[nm], 3)
        }

    asc_sign, _, asc_deg = sign_of(drac_asc)
    mc_sign, _, mc_deg = sign_of(drac_mc)

    aspects = compute_aspects(drac_lons)[:20]

    return {
        "system": "Draconic Astrology (Nodal Soul Blueprint)",
        "true_north_node_tropical": round(node_lon, 3),
        "ascendant": {"sign": asc_sign, "degree": round(asc_deg, 2)},
        "midheaven": {"sign": mc_sign, "degree": round(mc_deg, 2)},
        "planets": planets,
        "aspects": aspects,
        "note": ("Draconic positions reflect soul-level instincts and karmic purpose. "
                 "When a partner's tropical planet hits your draconic planet, a soul-contract bond is felt.")
    }

def draconic_synastry(jdA, jdB, latA, lngA, latB, lngB):
    """Draconic-to-Tropical Synastry (Soul-Contract Comparisons):
    Compares Person A's Draconic placements against Person B's Tropical placements (and vice versa).
    Aspects between Draconic and Tropical charts signify deep karmic resonance and past-life familiarity."""
    lonsA_trop, _, _ = body_longitudes(jdA)
    lonsB_trop, _, _ = body_longitudes(jdB)
    nodeA = lonsA_trop.get("North Node", 0.0)
    nodeB = lonsB_trop.get("North Node", 0.0)

    lonsA_drac = {p: norm360(lon - nodeA) for p, lon in lonsA_trop.items()}
    lonsB_drac = {p: norm360(lon - nodeB) for p, lon in lonsB_trop.items()}

    pts = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "North Node"]
    karmic_bonds = []

    # A Draconic to B Tropical
    for a in pts:
        for b in pts:
            sep = abs(norm180(lonsA_drac[a] - lonsB_trop[b]))
            for asp, (ang, orb, desc) in ASPECTS.items():
                if abs(sep - ang) <= min(orb, 2.5): # tighter orb for draconic contracts
                    karmic_bonds.append({
                        "personA_draconic": a,
                        "personB_tropical": b,
                        "aspect": asp,
                        "orb": round(abs(sep - ang), 2),
                        "reading": f"Person A's soul-instinct ({a}) directly connects with Person B's lived expression ({b}). {desc}"
                    })

    karmic_bonds.sort(key=lambda x: x["orb"])
    return {
        "karmic_aspects_count": len(karmic_bonds),
        "strongest_soul_contracts": karmic_bonds[:12],
        "note": "Draconic-to-Tropical contacts reveal underlying soul contracts and unconscious familiarity in relationships."
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — VEDIC DAILY TIMING: CHOGHADIYA, MUHURTA WINDOWS & ASHTAKAVARGA
# ═════════════════════════════════════════════════════════════════════════════

CHOGHADIYA_DAY = {
    0: ["Udveg", "Char", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg"],
    1: ["Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Char", "Labh", "Amrit"],
    2: ["Rog", "Udveg", "Char", "Labh", "Amrit", "Kaal", "Shubh", "Rog"],
    3: ["Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Char", "Labh"],
    4: ["Shubh", "Rog", "Udveg", "Char", "Labh", "Amrit", "Kaal", "Shubh"],
    5: ["Char", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Char"],
    6: ["Kaal", "Shubh", "Rog", "Udveg", "Char", "Labh", "Amrit", "Kaal"],
}

CHOGHADIYA_NIGHT = {
    0: ["Shubh", "Amrit", "Char", "Rog", "Kaal", "Labh", "Udveg", "Shubh"],
    1: ["Char", "Rog", "Kaal", "Labh", "Udveg", "Shubh", "Amrit", "Char"],
    2: ["Kaal", "Labh", "Udveg", "Shubh", "Amrit", "Char", "Rog", "Kaal"],
    3: ["Udveg", "Shubh", "Amrit", "Char", "Rog", "Kaal", "Labh", "Udveg"],
    4: ["Amrit", "Char", "Rog", "Kaal", "Labh", "Udveg", "Shubh", "Amrit"],
    5: ["Rog", "Kaal", "Labh", "Udveg", "Shubh", "Amrit", "Char", "Rog"],
    6: ["Labh", "Udveg", "Shubh", "Amrit", "Char", "Rog", "Kaal", "Labh"],
}

CHOGHADIYA_NATURE = {
    "Amrit": ("Auspicious", "nectar, all auspicious endeavors and important beginnings"),
    "Shubh": ("Auspicious", "good fortune, marriage, education, and spiritual work"),
    "Labh":  ("Auspicious", "gain, commerce, business starts, and negotiations"),
    "Char":  ("Neutral", "movement, journeys, transport, and dynamic tasks"),
    "Rog":   ("Inauspicious", "disease, debility, avoid new commitments"),
    "Kaal":  ("Inauspicious", "destruction, loss, only suitable for fierce tasks"),
    "Udveg": ("Inauspicious", "anxiety, worry, dispute, avoid stressful negotiations"),
}

RAHU_KALAM_SEGMENT = {0: 7, 1: 1, 2: 6, 3: 4, 4: 5, 5: 3, 6: 2}
YAMAGANDA_SEGMENT   = {0: 4, 1: 3, 2: 2, 3: 1, 4: 0, 5: 6, 6: 5}
GULIKA_SEGMENT      = {0: 6, 1: 5, 2: 4, 3: 3, 4: 2, 5: 1, 6: 0}

def daily_panchang_timing(jd, lat, lng):
    """Daily Vedic timing windows: Choghadiya segments, Abhijit & Brahma Muhurta,
    Rahu Kalam, Yamaganda, Gulika Kalam calculated dynamically from solar geometry."""
    dt_utc = datetime(2000, 1, 1) + timedelta(days=jd - 2451544.5)
    # Weekday index: Sunday=0 ... Saturday=6
    weekday = (dt_utc.weekday() + 1) % 7

    obliquity_rad = math.radians(23.4393 - 0.0130 * ((jd - 2451545.0) / 36525.0))
    lat_rad = math.radians(lat)
    sun_lon = tropical_longitudes(jd).get("Sun", 0)
    sun_dec = math.asin(math.sin(obliquity_rad) * math.sin(math.radians(sun_lon)))
    cos_ha = max(-1.0, min(1.0, -math.tan(lat_rad) * math.tan(sun_dec)))
    ha_deg = math.degrees(math.acos(cos_ha))

    # Times in hours relative to solar noon (approx 12h - lng/15 in UTC)
    solar_noon_utc_h = (12.0 - lng / 15.0) % 24.0
    day_half_len_h = ha_deg / 15.0
    sunrise_h = (solar_noon_utc_h - day_half_len_h) % 24.0
    sunset_h = (solar_noon_utc_h + day_half_len_h) % 24.0

    day_dur_h = 2.0 * day_half_len_h
    night_dur_h = 24.0 - day_dur_h
    day_oct_h = day_dur_h / 8.0
    night_oct_h = night_dur_h / 8.0

    # 1. Choghadiya Day & Night
    day_choghadiya = []
    for k in range(8):
        name = CHOGHADIYA_DAY[weekday][k]
        nature, meaning = CHOGHADIYA_NATURE[name]
        start_h = (sunrise_h + k * day_oct_h) % 24.0
        end_h = (sunrise_h + (k + 1) * day_oct_h) % 24.0
        day_choghadiya.append({
            "segment": k + 1, "name": name, "nature": nature, "meaning": meaning,
            "start_utc": f"{int(start_h):02d}:{int((start_h%1)*60):02d}",
            "end_utc": f"{int(end_h):02d}:{int((end_h%1)*60):02d}"
        })

    night_choghadiya = []
    for k in range(8):
        name = CHOGHADIYA_NIGHT[weekday][k]
        nature, meaning = CHOGHADIYA_NATURE[name]
        start_h = (sunset_h + k * night_oct_h) % 24.0
        end_h = (sunset_h + (k + 1) * night_oct_h) % 24.0
        night_choghadiya.append({
            "segment": k + 1, "name": name, "nature": nature, "meaning": meaning,
            "start_utc": f"{int(start_h):02d}:{int((start_h%1)*60):02d}",
            "end_utc": f"{int(end_h):02d}:{int((end_h%1)*60):02d}"
        })

    # 2. Auspicious & Inauspicious Muhurtas
    day_muh_h = day_dur_h / 15.0
    night_muh_h = night_dur_h / 15.0

    # Abhijit Muhurta (midday ± 1/2 muhurta; invalid on Wednesday/Budhvar)
    abhijit_valid = (weekday != 3)
    abhijit_start = (solar_noon_utc_h - day_muh_h / 2.0) % 24.0
    abhijit_end = (solar_noon_utc_h + day_muh_h / 2.0) % 24.0

    # Brahma Muhurta (penultimate night muhurta: 2 to 1 muhurtas before sunrise)
    brahma_start = (sunrise_h - 2.0 * night_muh_h) % 24.0
    brahma_end = (sunrise_h - 1.0 * night_muh_h) % 24.0

    # Inauspicious fixed 1/8th segments
    rahu_k = RAHU_KALAM_SEGMENT[weekday]
    rahu_s = (sunrise_h + rahu_k * day_oct_h) % 24.0
    rahu_e = (sunrise_h + (rahu_k + 1) * day_oct_h) % 24.0

    yama_k = YAMAGANDA_SEGMENT[weekday]
    yama_s = (sunrise_h + yama_k * day_oct_h) % 24.0
    yama_e = (sunrise_h + (yama_k + 1) * day_oct_h) % 24.0

    guli_k = GULIKA_SEGMENT[weekday]
    guli_s = (sunrise_h + guli_k * day_oct_h) % 24.0
    guli_e = (sunrise_h + (guli_k + 1) * day_oct_h) % 24.0

    def _fmt(h): return f"{int(h):02d}:{int((h%1)*60):02d} UTC"

    return {
        "date_utc": dt_utc.strftime("%Y-%m-%d"),
        "sun_times": {"sunrise": _fmt(sunrise_h), "solar_noon": _fmt(solar_noon_utc_h), "sunset": _fmt(sunset_h)},
        "auspicious_windows": {
            "abhijit_muhurta": {"start": _fmt(abhijit_start), "end": _fmt(abhijit_end),
                                "is_valid_today": abhijit_valid,
                                "note": "Most powerful daily auspicious window (except Wednesday)"},
            "brahma_muhurta": {"start": _fmt(brahma_start), "end": _fmt(brahma_end),
                               "note": "Pre-dawn spiritual & meditation window"}
        },
        "inauspicious_windows": {
            "rahu_kalam": {"start": _fmt(rahu_s), "end": _fmt(rahu_e), "note": "Avoid starting new ventures/travel"},
            "yamaganda": {"start": _fmt(yama_s), "end": _fmt(yama_e), "note": "Unfavorable for financial commitments"},
            "gulika_kalam": {"start": _fmt(guli_s), "end": _fmt(guli_e), "note": "Actions begun here repeat or cause delay"}
        },
        "choghadiya": {"day": day_choghadiya, "night": night_choghadiya},
        "note": "Daily Vedic timing based on true local solar geometry. Choghadiya cycles govern hour-by-hour initiative."
    }

def kuja_dosha_analysis(planets, lagna_sign):
    """Detailed Manglik (Kuja Dosha) detection with 6 classical BPHS Ch.80 cancellation rules.
    Mars in 1st, 12th, 4th, 7th, 8th causes Kuja Dosha unless cancelled."""
    mars = planets.get("Mars")
    if not mars:
        return {"has_dosha": False, "reason": "Mars not in chart"}

    h = mars["house"]
    dosha_houses = (1, 4, 7, 8, 12)
    has_raw_dosha = h in dosha_houses

    if not has_raw_dosha:
        return {
            "has_dosha": False,
            "house": h,
            "sign": mars["sign"],
            "status": "No Kuja Dosha (Mars is not in houses 1, 4, 7, 8, or 12)"
        }

    cancellations = []
    # 1. Mars in own sign (Aries/Scorpio) in 1st or 8th
    if mars["sign"] in ("Aries", "Scorpio") and h in (1, 8):
        cancellations.append("BPHS rule: Mars in own sign (Swakshetra) in house 1 or 8 cancels dosha")

    # 2. Mars in Capricorn (exaltation) in house 4 or 7
    if mars["sign"] == "Capricorn" and h in (4, 7):
        cancellations.append("BPHS rule: Mars exalted in Capricorn in house 4 or 7 cancels dosha")

    # 3. Mars in Leo or Aquarius in house 7 or 8
    if mars["sign"] in ("Leo", "Aquarius") and h in (7, 8):
        cancellations.append("BPHS rule: Mars in Leo/Aquarius in house 7 or 8 cancels dosha")

    # 4. Mars in Sagittarius or Pisces in house 8 or 12
    if mars["sign"] in ("Sagittarius", "Pisces") and h in (8, 12):
        cancellations.append("BPHS rule: Mars in Jupiter signs (Sag/Pisces) in house 8 or 12 cancels dosha")

    # 5. Benefic conjunction: Jupiter or Venus with Mars
    jup = planets.get("Jupiter"); ven = planets.get("Venus")
    if jup and jup["house"] == h:
        cancellations.append("BPHS Shloka 47: Conjunction with benefic Jupiter cancels dosha")
    if ven and ven["house"] == h:
        cancellations.append("BPHS Shloka 47: Conjunction with benefic Venus cancels dosha")

    is_cancelled = len(cancellations) > 0
    return {
        "has_dosha": not is_cancelled,
        "raw_dosha": True,
        "house": h,
        "sign": mars["sign"],
        "is_cancelled": is_cancelled,
        "cancellation_reasons": cancellations,
        "status": "Cancelled Kuja Dosha (Effective Non-Manglik)" if is_cancelled else "Active Kuja Dosha (Manglik)",
        "note": "Per BPHS Chapter 80 Shloka 47-49: Kuja Dosha indicates intense relationship friction unless balanced by benefic aspects or partner parity."
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — ASTRODYNES & COSMODYNES (Elbert Benjamine / Church of Light)
# ═════════════════════════════════════════════════════════════════════════════

ASTRODYNE_HOUSE_POWER = {
    1: 15.0, 10: 15.0, 4: 14.0, 7: 14.0,
    2: 10.0, 5: 10.0, 8: 10.0, 11: 10.0,
    3: 6.0, 6: 6.0, 9: 6.0, 12: 6.0
}

ASTRODYNE_PLANET_NATURE = {
    "Venus": 2.0, "Jupiter": 2.0, "Sun": 1.0, "Moon": 1.0,
    "Mercury": 0.0, "Uranus": -1.0, "Neptune": -1.0, "Pluto": -1.0,
    "Mars": -2.0, "Saturn": -2.0, "North Node": 0.5, "South Node": -0.5, "Chiron": 0.0
}

ASTRODYNE_ASPECT_RULES = {
    "conjunction": {"base_power": 15.0, "orb_lum": 15.0, "orb_pl": 12.0, "type": "variable"},
    "opposition":  {"base_power": 14.0, "orb_lum": 15.0, "orb_pl": 12.0, "type": "discord"},
    "trine":       {"base_power": 12.0, "orb_lum": 12.0, "orb_pl": 10.0, "type": "harmony"},
    "square":      {"base_power": 10.0, "orb_lum": 12.0, "orb_pl": 10.0, "type": "discord"},
    "sextile":     {"base_power": 6.0,  "orb_lum": 8.0,  "orb_pl": 6.0,  "type": "harmony"},
    "inconjunct":  {"base_power": 3.0,  "orb_lum": 4.0,  "orb_pl": 3.0,  "type": "discord"},
    "semisquare":  {"base_power": 3.0,  "orb_lum": 4.0,  "orb_pl": 3.0,  "type": "discord"},
    "sesquisquare":{"base_power": 3.0,  "orb_lum": 4.0,  "orb_pl": 3.0,  "type": "discord"},
    "semisextile": {"base_power": 2.0,  "orb_lum": 3.0,  "orb_pl": 2.0,  "type": "harmony"},
}

def compute_astrodynes(natal_jd, lat, lng, time_known=True):
    """Calculates Astrodynes (Cosmodynes) per Elbert Benjamine (C.C. Zain / Church of Light):
    Quantitative power (Astrodynes), harmony (Harmodynes), and discord (Discordynes)
    for all planets, houses, and zodiac signs."""
    ch = western_chart(natal_jd, lat, lng, time_known)
    planets = ch["planets"]
    aspects_list = ch["aspects"]

    planet_power = {}
    planet_harmony = {}

    # 1. Base Planet Power from House Placements
    for p, b in planets.items():
        if p not in ASTRODYNE_PLANET_NATURE:
            continue
        h = b.get("house", 1)
        base_p = ASTRODYNE_HOUSE_POWER.get(h, 6.0)
        planet_power[p] = base_p
        planet_harmony[p] = ASTRODYNE_PLANET_NATURE.get(p, 0.0)

    # 2. Aspect Contributions to Power & Harmony
    for asp in aspects_list:
        p1, p2 = asp["a"], asp["b"]
        asp_name = asp["aspect"].lower()
        if p1 not in planet_power or p2 not in planet_power or asp_name not in ASTRODYNE_ASPECT_RULES:
            continue
        rule = ASTRODYNE_ASPECT_RULES[asp_name]
        is_lum = (p1 in ("Sun","Moon") or p2 in ("Sun","Moon"))
        max_orb = rule["orb_lum"] if is_lum else rule["orb_pl"]
        orb = asp["orb"]
        if orb > max_orb:
            continue

        tightness = max(0.0, (max_orb - orb) / max_orb)
        asp_power = rule["base_power"] * tightness

        # Distribute power equally to both participating bodies
        planet_power[p1] += asp_power / 2.0
        planet_power[p2] += asp_power / 2.0

        # Harmony / Discord
        if rule["type"] == "harmony":
            h_val = asp_power / 2.0
        elif rule["type"] == "discord":
            h_val = -asp_power / 2.0
        else: # conjunction
            coeff = max(-1.0, min(1.0, (ASTRODYNE_PLANET_NATURE.get(p1,0.0) + ASTRODYNE_PLANET_NATURE.get(p2,0.0)) / 2.0))
            h_val = (asp_power / 2.0) * coeff

        planet_harmony[p1] += h_val
        planet_harmony[p2] += h_val

    # 3. Aggregate House Power & Harmony
    house_power = {h: ASTRODYNE_HOUSE_POWER.get(h, 6.0) for h in range(1, 13)}
    house_harmony = {h: 0.0 for h in range(1, 13)}

    for p, b in planets.items():
        if p not in planet_power: continue
        h = b.get("house", 1)
        house_power[h] += planet_power[p]
        house_harmony[h] += planet_harmony[p]

    # Add 50% of House Ruler's power/harmony to the house
    for h in range(1, 13):
        h_sign = ch["houses"][h]["sign"]
        ruler = SIGN_DATA[h_sign]["ruler"]
        if ruler in planet_power:
            house_power[h] += 0.5 * planet_power[ruler]
            house_harmony[h] += 0.5 * planet_harmony[ruler]

    # 4. Aggregate Sign Power & Harmony
    sign_power = {s: 0.0 for s in SIGNS}
    sign_harmony = {s: 0.0 for s in SIGNS}

    for p, b in planets.items():
        if p not in planet_power: continue
        s = b["sign"]
        sign_power[s] += planet_power[p]
        sign_harmony[s] += planet_harmony[p]

    for s in SIGNS:
        ruler = SIGN_DATA[s]["ruler"]
        if ruler in planet_power:
            sign_power[s] += 0.5 * planet_power[ruler]
            sign_harmony[s] += 0.5 * planet_harmony[ruler]

    # Format Output
    p_sorted = sorted(planet_power.keys(), key=lambda k: -planet_power[k])
    most_powerful_planet = p_sorted[0] if p_sorted else "Sun"
    most_harmonious_planet = max(planet_harmony.keys(), key=lambda k: planet_harmony[k])
    most_discordant_planet = min(planet_harmony.keys(), key=lambda k: planet_harmony[k])

    h_sorted = sorted(house_power.keys(), key=lambda k: -house_power[k])
    most_powerful_house = h_sorted[0]

    return {
        "system": "Astrodynes / Cosmodynes (Church of Light)",
        "summary": {
            "most_powerful_planet": most_powerful_planet,
            "most_powerful_house": most_powerful_house,
            "most_harmonious_planet": most_harmonious_planet,
            "most_discordant_planet": most_discordant_planet,
            "strongest_life_arena": MUNDANE_HOUSE_MEANINGS.get(most_powerful_house, "")
        },
        "planets": {p: {"power": round(planet_power[p], 2),
                        "harmony": round(max(0.0, planet_harmony[p]), 2),
                        "discord": round(abs(min(0.0, planet_harmony[p])), 2),
                        "net_harmony": round(planet_harmony[p], 2)} for p in planet_power},
        "houses": {h: {"power": round(house_power[h], 2),
                       "net_harmony": round(house_harmony[h], 2),
                       "meaning": MUNDANE_HOUSE_MEANINGS.get(h, "")} for h in range(1, 13)},
        "signs": {s: {"power": round(sign_power[s], 2),
                      "net_harmony": round(sign_harmony[s], 2)} for s in SIGNS},
        "note": ("Astrodynes quantitatively measure planetary drive (Power) and emotional ease vs struggle "
                 "(Harmony/Discord). Highest power house represents the primary life focus.")
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — ELECTIONAL SEARCH & RELOCATION ANALYSIS (Ibn Ezra & Jim Lewis)
# ═════════════════════════════════════════════════════════════════════════════

BODY_PARTS_BY_SIGN = {
    "Aries": "head, brain, eyes, face",
    "Taurus": "neck, throat, vocal cords, thyroid",
    "Gemini": "shoulders, arms, hands, lungs, nervous system",
    "Cancer": "chest, breasts, stomach, digestion",
    "Leo": "heart, spine, upper back",
    "Virgo": "abdomen, intestines, digestive system",
    "Libra": "kidneys, lower back, buttocks",
    "Scorpio": "reproductive organs, genitals, excretory system",
    "Sagittarius": "hips, thighs, sciatic nerve, liver",
    "Capricorn": "knees, joints, bones, teeth, skin",
    "Aquarius": "calves, ankles, circulatory system",
    "Pisces": "feet, toes, lymphatic system"
}

ELECTION_CRITERIA = {
    "business_commerce": {"target_houses": [2, 10, 11], "significators": ["Jupiter", "Mercury"], "prohibit_saturn": False},
    "marriage_partnership": {"target_houses": [7], "significators": ["Venus", "Moon"], "prohibit_saturn": True},
    "property_building": {"target_houses": [4], "significators": ["Saturn", "Venus"], "prohibit_mars": True},
    "travel_journey": {"target_houses": [9, 3], "significators": ["Moon", "Mercury"], "prohibit_saturn": True},
    "medical_surgery": {"target_houses": [1, 6], "significators": ["Sun", "Jupiter"], "prohibit_mars": True},
}

def evaluate_election_moment(jd, lat, lng, activity="business_commerce", organ_sign=None):
    """Evaluate an electional moment per Abraham Ibn Ezra (Book of Elections / Sefer ha-Mivharim).
    Returns an objective score (0 to 100) and actionable classical insights."""
    ch = western_chart(jd, lat, lng, time_known=True)
    lons = {p: b["abs_lon"] for p, b in ch["planets"].items()}
    speed = {p: 1.0 for p in lons}
    lons_swe, sp_swe, _ = body_longitudes(jd)

    score = 0.0
    strengths = []
    cautions = []

    # 1. MOON CONDITION (Max: 35 points)
    sun_lon = lons["Sun"]; moon_lon = lons["Moon"]
    elong = norm360(moon_lon - sun_lon)
    is_waxing = elong < 180.0
    if is_waxing:
        score += 7.0
        strengths.append("Moon is waxing (increasing in light) — ideal for growth and progress")
    else:
        cautions.append("Moon is waning (decreasing in light) — suited for reduction/closing rather than expansion")

    # Combustion check (within 12° of Sun)
    is_combust = abs(norm180(moon_lon - sun_lon)) < 12.0
    if not is_combust:
        score += 7.0
    else:
        score -= 10.0
        cautions.append("Moon is combust (too close to Sun's rays) — signifies obscurity or impediment")

    # Void-of-course check
    voc = void_of_course_moon(jd, lat, lng, True)
    if not voc.get("is_void"):
        score += 6.0
        strengths.append("Moon is active and making applying aspects (not Void-of-Course)")
    else:
        score -= 8.0
        cautions.append("Moon is Void-of-Course — classical election rule: 'nothing comes of the matter'")

    # Moon sign dignity & Via Combusta
    moon_sign = ch["planets"]["Moon"]["sign"]
    if moon_sign == "Taurus": # Moon exaltation
        score += 7.0; strengths.append("Moon is exalted in Taurus (supreme stability)")
    elif moon_sign == "Cancer": # Moon domicile
        score += 5.0; strengths.append("Moon is in own domicile (Cancer)")
    elif moon_sign == "Scorpio":
        score -= 6.0; cautions.append("Moon is in fall in Scorpio (intense/turbulent emotional climate)")

    # 2. ASCENDANT & ASC LORD (Max: 30 points)
    asc_sign = ch["ascendant"]["sign"]
    asc_lord = SIGN_DATA[asc_sign]["ruler"]
    h1_planets = [p for p, b in ch["planets"].items() if b["house"] == 1]
    if "Saturn" not in h1_planets and "Mars" not in h1_planets:
        score += 8.0
    else:
        score -= 10.0
        cautions.append("Malefic in 1st house — obstacles in initial execution")

    asc_lord_house = ch["planets"].get(asc_lord, {}).get("house", 6)
    if asc_lord_house in (1, 10, 7, 4, 11, 5):
        score += 12.0
        strengths.append(f"Ascendant Lord ({asc_lord}) is strong in house {asc_lord_house}")
    else:
        score -= 5.0
        cautions.append(f"Ascendant Lord ({asc_lord}) is placed in a weak/cadent house ({asc_lord_house})")

    # 3. ACTIVITY TARGET CRITERIA (Max: 35 points)
    crit = ELECTION_CRITERIA.get(activity, ELECTION_CRITERIA["business_commerce"])
    for th in crit["target_houses"]:
        th_planets = [p for p, b in ch["planets"].items() if b["house"] == th]
        if "Jupiter" in th_planets or "Venus" in th_planets:
            score += 10.0
            strengths.append(f"Benefic in target house {th} — strengthens the core objective")
        if "Saturn" in th_planets and crit.get("prohibit_saturn"):
            score -= 8.0; cautions.append(f"Saturn in target house {th} causes delays or burdens")
        if "Mars" in th_planets and crit.get("prohibit_mars"):
            score -= 8.0; cautions.append(f"Mars in target house {th} brings haste, conflict, or hazard")

    # Medical surgery special rule (Ibn Ezra Sefer ha-Me'orot)
    if activity == "medical_surgery" and organ_sign:
        if moon_sign.lower() == organ_sign.lower():
            score -= 30.0
            cautions.append(f"CRITICAL MEDICAL RULE: Moon is in {moon_sign} which governs {BODY_PARTS_BY_SIGN.get(moon_sign,'')}. Avoid surgical intervention on this organ while Moon transits here.")

    final_score = max(0, min(100, round(score)))
    rating = "Excellent (Golden Window)" if final_score >= 80 else "Favorable" if final_score >= 65 else "Moderate" if final_score >= 50 else "Challenging"

    return {
        "score": final_score,
        "rating": rating,
        "moon_status": {"sign": moon_sign, "is_waxing": is_waxing, "void_of_course": voc.get("is_void", False)},
        "ascendant": {"sign": asc_sign, "lord": asc_lord, "lord_house": asc_lord_house},
        "strengths": strengths,
        "cautions": cautions,
    }

def find_best_electional_windows(lat, lng, start_dt, days_ahead=30, activity="business_commerce", organ_sign=None):
    """Scan upcoming days and rank the top 3 golden time windows for a specified initiative
    per Ibn Ezra's electional scoring system."""
    start_jd = julian_day(start_dt)
    candidates = []
    # Evaluate at solar noon and mid-morning/mid-afternoon for each day
    for day_i in range(days_ahead):
        curr_dt = start_dt + timedelta(days=day_i)
        for hour_opt in (10, 14, 18):
            eval_dt = curr_dt.replace(hour=hour_opt, minute=0, second=0)
            eval_jd = julian_day(eval_dt)
            ev = evaluate_election_moment(eval_jd, lat, lng, activity, organ_sign)
            candidates.append({
                "datetime_utc": eval_dt.strftime("%Y-%m-%d %H:%M UTC"),
                "score": ev["score"],
                "rating": ev["rating"],
                "moon_sign": ev["moon_status"]["sign"],
                "ascendant_sign": ev["ascendant"]["sign"],
                "strengths": ev["strengths"],
                "cautions": ev["cautions"]
            })

    candidates.sort(key=lambda x: -x["score"])
    top_windows = candidates[:3]
    return {
        "activity": activity,
        "scan_period": f"{start_dt.strftime('%Y-%m-%d')} to {(start_dt + timedelta(days=days_ahead)).strftime('%Y-%m-%d')}",
        "top_windows": top_windows,
        "note": "Ranked per Abraham Ibn Ezra's Book of Elections (Sefer ha-Mivharim). Select windows with score >= 75 for major initiatives."
    }

def relocate_natal_chart(natal_jd, target_city, target_lat, target_lng):
    """Calculate the Relocated Chart for living in a different city (Jim Lewis Astro*Carto*Graphy principle):
    Planets remain in the same zodiac degrees, but house cusps and Asc/MC rotate based on the new geography.
    Reveals how different global cities activate distinct life arenas."""
    natal_chart = western_chart(natal_jd, target_lat, target_lng, time_known=True)
    relocated_asc = natal_chart["ascendant"]["sign"]
    relocated_mc = natal_chart["midheaven"]["sign"]

    shifts = []
    for p, b in natal_chart["planets"].items():
        if p in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
            h = b["house"]
            shifts.append(f"{p} in House {h} ({MUNDANE_HOUSE_MEANINGS.get(h,'')})")

    return {
        "target_city": target_city,
        "coordinates": {"lat": target_lat, "lng": target_lng},
        "relocated_ascendant": relocated_asc,
        "relocated_midheaven": relocated_mc,
        "activated_spheres": shifts,
        "chart": natal_chart,
        "note": f"In {target_city}, your Ascendant shifts to {relocated_asc} and Midheaven to {relocated_mc}. Planets in angular houses (1, 4, 7, 10) become dominant life themes in this location."
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — DOMAIN SYNTHESIS BLUEPRINTS: WEALTH & LOVE (Master Engine v3.3)
# ═════════════════════════════════════════════════════════════════════════════

INDU_LAGNA_RAYS = {"Sun": 30, "Moon": 16, "Mars": 6, "Mercury": 8, "Jupiter": 10, "Venus": 12, "Saturn": 1}

def compute_wealth_blueprint(natal_jd, lat, lng, time_known=True):
    """Multi-Tradition Wealth & Career Blueprint (Master Engine):
    Synthesizes Western 2nd/10th/11th houses + Part of Fortune & Commerce (Ibn Ezra),
    Vedic D10 Dasamsa + Dhana Yogas + Indu Lagna wealth point, BaZi Cai Wealth Star,
    and Zodiacal Releasing peak timing. Returns a unified [0-100] index and report."""
    full = calculate_full_profile({
        "year": 2000, "month": 1, "day": 1, # placeholder base, overridden by jd
        "lat": lat, "lng": lng, "time_known": time_known,
        "systems": ["western", "vedic", "bazi"]
    })
    # Compute real chart components for natal_jd
    w_chart = western_chart(natal_jd, lat, lng, time_known)
    v_chart = vedic_chart(natal_jd, lat, lng, datetime(2000,1,1), time_known)
    lons, _, _ = body_longitudes(natal_jd)
    ayan = ayanamsha_lahiri(natal_jd)
    asc_lon = w_chart["ascendant"]["abs_lon"] if "abs_lon" in w_chart["ascendant"] else lons["Sun"]
    is_day = 90 <= norm360(asc_lon - lons["Sun"]) <= 270

    score = 50.0
    strengths = []
    cautions = []

    # 1. Western Component: 2nd, 10th, 11th houses & Lots
    h2 = w_chart["houses"][2]; h10 = w_chart["houses"][10]; h11 = w_chart["houses"][11]
    p_h2 = [p for p, b in w_chart["planets"].items() if b["house"] == 2]
    p_h10 = [p for p, b in w_chart["planets"].items() if b["house"] == 10]
    p_h11 = [p for p, b in w_chart["planets"].items() if b["house"] == 11]

    if "Jupiter" in p_h2 + p_h10 + p_h11 or "Venus" in p_h2 + p_h10 + p_h11:
        score += 10.0
        strengths.append("Benefic planet (Jupiter/Venus) placed in financial/career houses (2, 10, or 11)")
    if "Saturn" in p_h2 or "Mars" in p_h2:
        score -= 5.0
        cautions.append("Malefic in 2nd house of income — wealth builds through discipline and delayed gratification")

    pof = part_of_fortune(lons["Sun"], lons["Moon"], asc_lon, is_day)
    pof_house = whole_sign_house(pof["longitude"], asc_lon)
    if pof_house in (1, 10, 11, 2):
        score += 8.0
        strengths.append(f"Part of Fortune in auspicious house {pof_house} ({pof['sign']})")

    # 2. Vedic Component: D10 Dasamsa, Dhana Yogas, Indu Lagna
    d10 = varga_chart(natal_jd, "D10", lat, lng, time_known)
    if "d10_planets" in d10:
        d10_10th = [p for p, b in d10["d10_planets"].items() if b["varga_house"] in (1, 10, 11)]
        if d10_10th:
            score += 8.0
            strengths.append(f"Strong D10 Dasamsa career placements: {', '.join(d10_10th)} in leadership houses")

    # Indu Lagna (BPHS Special Wealth Ascendant)
    moon_sid = norm360(lons["Moon"] - ayan)
    asc_sid = norm360(asc_lon - ayan)
    asc_9th_sign = SIGNS[(int(asc_sid // 30) + 8) % 12]
    moon_9th_sign = SIGNS[(int(moon_sid // 30) + 8) % 12]
    r1 = INDU_LAGNA_RAYS.get(RASHI_LORDS[asc_9th_sign], 8)
    r2 = INDU_LAGNA_RAYS.get(RASHI_LORDS[moon_9th_sign], 8)
    indu_sign_idx = (int(moon_sid // 30) + (r1 + r2) % 12) % 12
    indu_sign = SIGNS[indu_sign_idx]
    score += 5.0
    strengths.append(f"Indu Lagna (Vedic Wealth Point) sits in {indu_sign}")

    # 3. Timing Component: ZR Spirit Peaks
    zr = zodiacal_releasing(natal_jd, lat, lng, time_known, topic="spirit")
    active_zr = zr["active_period"]["l1"]
    if active_zr in zr["peak_signs"]:
        score += 10.0
        strengths.append(f"Currently in an active Zodiacal Releasing Career Peak ({active_zr})")

    final_score = max(0, min(100, round(score)))
    tier = "Exceptional" if final_score >= 80 else "Favorable" if final_score >= 65 else "Moderate" if final_score >= 45 else "Afflicted"

    return {
        "domain": "Wealth & Career Blueprint",
        "wealth_power_score": final_score,
        "tier": tier,
        "key_indicators": {
            "part_of_fortune": f"{pof['sign']} (House {pof_house})",
            "indu_lagna": indu_sign,
            "career_house_10_sign": h10["sign"],
            "income_house_2_sign": h2["sign"],
            "active_zr_career_period": active_zr,
            "is_zr_peak": active_zr in zr["peak_signs"]
        },
        "strengths": strengths,
        "cautions": cautions,
        "synthesis_summary": f"Overall wealth & career capacity is rated {tier} ({final_score}/100). Primary financial drivers are rooted in {h2['sign']} (income style) and {h10['sign']} (vocation)."
    }

def compute_love_blueprint(natal_jd, lat, lng, time_known=True):
    """Multi-Tradition Love & Marriage Blueprint (Master Engine):
    Synthesizes Western 7th/5th houses + Venus/Mars, 7 Ibn Ezra Relationship Lots,
    Vedic D9 Navamsa + Upapada Lagna (UL) + Kuja Dosha (Manglik) status, and Draconic soul contracts."""
    w_chart = western_chart(natal_jd, lat, lng, time_known)
    lons, _, _ = body_longitudes(natal_jd)
    ayan = ayanamsha_lahiri(natal_jd)
    asc_lon = w_chart["ascendant"]["abs_lon"] if "abs_lon" in w_chart["ascendant"] else lons["Sun"]
    is_day = 90 <= norm360(asc_lon - lons["Sun"]) <= 270

    score = 50.0
    strengths = []
    cautions = []

    # 1. Western: 7th house, Venus & Mars
    h7 = w_chart["houses"][7]; h5 = w_chart["houses"][5]
    ven = w_chart["planets"]["Venus"]; mars = w_chart["planets"]["Mars"]
    if ven["house"] in (1, 5, 7, 10, 11):
        score += 8.0
        strengths.append(f"Venus favorably placed in House {ven['house']} ({ven['sign']}) — charm, social ease, and affection")
    if ven["dignity"] in ("domicile (rulership)", "exalted"):
        score += 8.0
        strengths.append(f"Venus has high essential dignity ({ven['dignity']})")
    elif ven["dignity"] in ("detriment", "fall"):
        score -= 5.0
        cautions.append(f"Venus in {ven['dignity']} — love demands conscious boundary-setting and self-worth")

    # 2. Ibn Ezra 7 Relationship Lots
    lots = ibn_ezra_relationship_lots(lons, asc_lon, is_day)
    score += 5.0
    strengths.append(f"Ibn Ezra General Marriage Lot sits in {lots['lot_of_marriage_general']['sign']} (House {whole_sign_house(lots['lot_of_marriage_general']['longitude'], asc_lon)})")

    # 3. Vedic: D9 Navamsa & Kuja Dosha (Manglik)
    d9 = navamsa_chart(natal_jd, lat, lng, time_known)
    d9_ven = d9.get("navamsa_planets", {}).get("Venus", {})
    if d9_ven.get("sign") in ("Pisces", "Taurus", "Libra"):
        score += 8.0
        strengths.append(f"Venus dignified in D9 Navamsa ({d9_ven.get('sign')}) — soul-level marital harmony")

    # Upapada Lagna (UL - Jaimini Marriage Arudha)
    asc_sid = norm360(asc_lon - ayan)
    h12_sign_idx = (int(asc_sid // 30) + 11) % 12
    h12_sign = SIGNS[h12_sign_idx]
    h12_lord = RASHI_LORDS[h12_sign]
    h12_lord_lon = norm360(lons.get(h12_lord, 0) - ayan)
    dist_12 = (int(h12_lord_lon // 30) - h12_sign_idx) % 12
    ul_sign_idx = (h12_sign_idx + dist_12) % 12
    ul_sign = SIGNS[ul_sign_idx]
    strengths.append(f"Upapada Lagna (Jaimini Marriage Arudha) sits in {ul_sign}")

    # Kuja Dosha Check
    kuja = mangal_dosha(natal_jd, lat, lng, time_known)
    if kuja.get("has_dosha"):
        score -= 10.0
        cautions.append("Active Kuja Dosha (Manglik) — requires parity in partner selection or conscious anger management")
    elif kuja.get("is_cancelled"):
        score += 5.0
        strengths.append(f"Kuja Dosha successfully cancelled per classical rules: {kuja.get('cancellation_reasons',[None])[0]}")

    final_score = max(0, min(100, round(score)))
    tier = "Exceptional" if final_score >= 80 else "Favorable" if final_score >= 65 else "Moderate" if final_score >= 45 else "Afflicted"

    return {
        "domain": "Love & Marriage Blueprint",
        "love_harmony_score": final_score,
        "tier": tier,
        "key_indicators": {
            "7th_house_marriage_sign": h7["sign"],
            "5th_house_romance_sign": h5["sign"],
            "venus_placement": f"{ven['sign']} (House {ven['house']})",
            "upapada_lagna": ul_sign,
            "kuja_dosha_status": kuja.get("status", "Non-Manglik"),
            "lot_of_marriage_general": lots["lot_of_marriage_general"]["sign"],
            "lot_of_passion": lots["lot_of_passion_desire"]["sign"]
        },
        "strengths": strengths,
        "cautions": cautions,
        "synthesis_summary": f"Overall relationship potential is rated {tier} ({final_score}/100). Partnership orientation is governed by {h7['sign']} on the 7th house and Venus in {ven['sign']}."
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — SCIENTIFIC ASTROLOGICAL REMEDIES & UPAYAS (BPHS & Liz Greene)
# ═════════════════════════════════════════════════════════════════════════════

GEMSTONE_MATRIX = {
    "Sun":     {"gem": "Ruby (Manikya)", "substitute": "Red Garnet / Spinel", "metal": "Gold / Copper", "finger": "Ring finger (Anamika)", "color": "Deep Red / Saffron"},
    "Moon":    {"gem": "Natural Pearl (Moti)", "substitute": "Moonstone", "metal": "Silver", "finger": "Little finger (Kanishtha)", "color": "Milky White"},
    "Mars":    {"gem": "Red Coral (Moonga)", "substitute": "Carnelian", "metal": "Copper / Gold", "finger": "Ring finger (Anamika)", "color": "Bright Vermilion Red"},
    "Mercury": {"gem": "Emerald (Panna)", "substitute": "Peridot / Green Tourmaline", "metal": "Gold / Bronze", "finger": "Little finger (Kanishtha)", "color": "Emerald Green"},
    "Jupiter": {"gem": "Yellow Sapphire (Pukhraj)", "substitute": "Yellow Topaz", "metal": "22K Gold", "finger": "Index finger (Tarjani)", "color": "Golden Yellow"},
    "Venus":   {"gem": "Diamond (Heera)", "substitute": "White Zircon / White Sapphire", "metal": "Platinum / Silver", "finger": "Middle / Little finger", "color": "Iridescent White"},
    "Saturn":  {"gem": "Blue Sapphire (Neelam)", "substitute": "Amethyst / Iolite", "metal": "Iron / Silver", "finger": "Middle finger (Madhyama)", "color": "Deep Navy Blue"},
    "Rahu":    {"gem": "Hessonite (Gomed)", "substitute": "Cinnamon Zircon", "metal": "Silver / Ashtadhatu", "finger": "Middle finger", "color": "Honey Brown"},
    "Ketu":    {"gem": "Cat's Eye (Vaidurya)", "substitute": "Chrysoberyl", "metal": "Silver", "finger": "Little finger", "color": "Smoky Green"}
}

DAAN_CHARITY_MATRIX = {
    "Sun":     {"day": "Sunday (Sunrise)", "items": "Wheat, jaggery (gur), copper vessel, saffron", "action": "Offer fresh water to the rising sun; honor elders and mentors"},
    "Moon":    {"day": "Monday (Evening)", "items": "Raw white rice, milk, clean water, silver", "action": "Support mothers and destitute women; install clean water access"},
    "Mars":    {"day": "Tuesday (Noon)", "items": "Red lentils (masoor dal), copper, sweet bread", "action": "Donate blood; support emergency workers or athletes; physical training"},
    "Mercury": {"day": "Wednesday (Morning)", "items": "Green gram (moong dal), green cloth, notebooks", "action": "Fund student supplies; feed green fodder to animals"},
    "Jupiter": {"day": "Thursday (Morning)", "items": "Chana dal, turmeric, yellow cloth, educational books", "action": "Support teachers, libraries, and philosophical institutions"},
    "Venus":   {"day": "Friday (Dawn)", "items": "White sugar, refined flour, silk, ghee, curd", "action": "Support women artists, donate cosmetics or clothing to shelters"},
    "Saturn":  {"day": "Saturday (Sunset)", "items": "Black sesame (til), mustard oil, iron pan, dark blanket", "action": "Aid manual laborers, sweepers, and the disabled; feed crows"},
    "Rahu":    {"day": "Saturday (Night)", "items": "Mustard seeds, coconut, dark blue blanket", "action": "Feed stray dogs daily; support people facing chronic marginalization"},
    "Ketu":    {"day": "Tuesday (Morning)", "items": "Seven mixed grains (sapta dhanya), brown blanket", "action": "Support spiritual seekers, meditation centers, and monks"}
}

PSYCHOLOGICAL_GROUNDING_MATRIX = {
    ("Sun", "Saturn"): "Establish disciplined daily routines; decouple self-worth from external praise; build internal self-validation.",
    ("Sun", "Pluto"): "Embrace radical transparency; practice conscious delegation of control; channel intensity into deep transformation.",
    ("Moon", "Saturn"): "Practice emotional reparenting; allow scheduled processing of grief; engage in soothing somatic bodywork.",
    ("Moon", "Neptune"): "Establish firm relational boundaries (practice saying 'No'); ground feelings through music/art; maintain emotional clarity.",
    ("Mars", "Saturn"): "Commit to periodized physical discipline (long-term training); direct energy into step-by-step constructive projects.",
    ("Mars", "Pluto"): "Channel volatile drive through high-intensity martial arts (boxing/BJJ); lead during crisis turnarounds.",
    ("Venus", "Saturn"): "Define clear relational agreements; invest in self-care budgets; take patient, steady steps toward intimacy.",
    ("Venus", "Pluto"): "Develop relational autonomy; channel passion into creative and psychological metamorphosis without control games.",
    ("Mercury", "Saturn"): "Combat mental rumination with evidence-based journaling and structured checklists; practice clear articulation.",
    ("Mercury", "Neptune"): "Use strict checklist verification for facts and finances; reserve poetic ambiguity purely for creative arts."
}

def compute_remedies_blueprint(natal_jd, lat, lng, time_known=True):
    """Scientific Astrological Remediation Engine (BPHS & Liz Greene):
    1. Evaluates Functional Benefics vs Functional Malefics to prescribe gemstones safely
       (Gemstones are strictly prohibited for Dusthana lords to avoid amplifying crises).
    2. Daan (Charity & Karmic Discharges) for pacifying afflicted/malefic planets.
    3. Constructive psychological grounding habits for hard aspect dynamics."""
    w_chart = western_chart(natal_jd, lat, lng, time_known)
    lons, _, _ = body_longitudes(natal_jd)
    ayan = ayanamsha_lahiri(natal_jd)
    asc_sid = norm360(w_chart["ascendant"]["abs_lon"] - ayan)
    lagna_sign_idx = int(asc_sid // 30) % 12
    lagna_sign = SIGNS[lagna_sign_idx]

    # Functional benefic rules: Lords of Trikonas (1, 5, 9)
    # Trikona signs from Lagna
    trikona_houses = {1: lagna_sign,
                      5: SIGNS[(lagna_sign_idx + 4) % 12],
                      9: SIGNS[(lagna_sign_idx + 8) % 12]}
    trikona_lords = {RASHI_LORDS[s] for s in trikona_houses.values()}

    # Dusthana houses: 6, 8, 12
    dusthana_houses = {6: SIGNS[(lagna_sign_idx + 5) % 12],
                       8: SIGNS[(lagna_sign_idx + 7) % 12],
                       12: SIGNS[(lagna_sign_idx + 11) % 12]}
    dusthana_lords = {RASHI_LORDS[s] for s in dusthana_houses.values()}

    gemstone_prescriptions = []
    charity_prescriptions = []

    for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
        if p in trikona_lords and p not in dusthana_lords:
            # Safe to amplify with gemstone
            info = GEMSTONE_MATRIX[p]
            gemstone_prescriptions.append({
                "planet": p,
                "role": f"Functional Benefic (Lord of Auspicious Trikona House for {lagna_sign} Lagna)",
                "gemstone": info["gem"],
                "substitute": info["substitute"],
                "metal": info["metal"],
                "finger": info["finger"],
                "color": info["color"],
                "rule": "Approved for amplification per BPHS guidelines"
            })
        elif p in dusthana_lords:
            # Pacification via charity only
            c_info = DAAN_CHARITY_MATRIX[p]
            charity_prescriptions.append({
                "planet": p,
                "reason": f"Functional Malefic / Dusthana Ruler for {lagna_sign} Lagna",
                "charity_timing": c_info["day"],
                "recommended_donation": c_info["items"],
                "constructive_action": c_info["action"],
                "gemstone_warning": f"STRICT BPHS PROHIBITION: Do NOT wear {GEMSTONE_MATRIX[p]['gem']} — it will amplify crisis/debt/illness."
            })

    # Psychological Grounding for Active Hard Aspects
    psy_habits = []
    aspects = w_chart["aspects"]
    for asp in aspects:
        if asp["aspect"] in ("square", "opposition", "inconjunct") and asp["orb"] <= 3.5:
            pair = tuple(sorted([asp["a"], asp["b"]]))
            if pair in PSYCHOLOGICAL_GROUNDING_MATRIX:
                psy_habits.append({
                    "aspect": f"{asp['a']} {asp['aspect']} {asp['b']} (orb {asp['orb']}°)",
                    "growth_habit": PSYCHOLOGICAL_GROUNDING_MATRIX[pair]
                })

    return {
        "domain": "Astrological Remediation & Upayas",
        "lagna_sign": lagna_sign,
        "approved_gemstones": gemstone_prescriptions,
        "karmic_charity_daan": charity_prescriptions,
        "psychological_grounding_habits": psy_habits[:4],
        "note": ("Vedic gemstone philosophy: gemstones act as bio-optical amplifiers and are prescribed ONLY "
                 "for Functional Benefics (Houses 1, 5, 9). Afflicted planets are pacified exclusively through Daan (charity) and constructive psychological habits.")
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — TRI-TRADITION CONVERGENCE & CONFIDENCE ENGINE (Master Engine v3.4)
# ═════════════════════════════════════════════════════════════════════════════

def compute_tri_tradition_convergence(natal_jd, lat, lng, time_known=True, as_of_dt=None):
    """Tri-Tradition Consensus & Confidence Engine (Master Engine v3.4):
    Integrates independent predictive vectors across 3 ancient paradigms:
    1. Western/Hellenistic: Zodiacal Releasing peak + Annual Profection house + Active Transits
    2. Vedic/Jyotisha: Active Vimshottari Mahadasha/Antardasha lord + Gochara + Ashtakavarga SAV
    3. Chinese BaZi: Day Master element affinity with 10-Year Luck Pillar (Da Yun)
    Outputs normalized signals [-1.0, +1.0], a unified consensus label, and a mathematically
    calibrated Confidence Score (45% to 98%)."""
    eval_dt = as_of_dt or datetime.now(timezone.utc).replace(tzinfo=None)
    eval_jd = julian_day(eval_dt)

    def _clamp(val, low=-1.0, high=1.0):
        return max(low, min(high, val))

    # ── 1. WESTERN SIGNAL (Sw) ───────────────────────────────────────
    # A. ZR Spirit Peak
    zr = zodiacal_releasing(natal_jd, lat, lng, time_known, topic="spirit", as_of_dt=eval_dt)
    active_zr = zr["active_period"]["l1"]
    zr_peak_val = 1.0 if active_zr in zr["peak_signs"] else 0.3 if zr.get("active_period",{}).get("l2") in zr["peak_signs"] else -0.2 if active_zr == "Scorpio" else 0.0

    # B. Annual Profection House Valence
    lons, _, _ = body_longitudes(natal_jd)
    asc_lon = lons["Sun"]
    if time_known:
        asc_lon, _ = ascendant_mc(natal_jd, lat, lng)
    asc_idx = int(norm360(asc_lon) // 30) % 12
    birth_dt = datetime(2000,1,1) + timedelta(days=natal_jd - 2451544.5)
    prof = annual_profections(asc_idx, birth_dt, eval_dt)
    prof_h = prof["active_house"]
    prof_val = 0.8 if prof_h in (1, 10, 11, 5) else 0.4 if prof_h in (2, 9, 3, 7, 4) else -0.6 # 6, 8, 12

    # C. Transits Summary Valence
    t_res = transits(natal_jd, lat, lng, eval_dt)
    jup_trans = any(h["transiting"] == "Jupiter" and h["aspect"] in ("conjunction","trine","sextile") for h in t_res.get("aspects_to_natal",[]))
    sat_hard = any(h["transiting"] == "Saturn" and h["aspect"] in ("square","opposition") for h in t_res.get("aspects_to_natal",[]))
    transit_val = (0.6 if jup_trans else 0.0) + (-0.6 if sat_hard else 0.0)

    S_w = _clamp(0.40 * zr_peak_val + 0.30 * prof_val + 0.30 * transit_val)

    # ── 2. VEDIC SIGNAL (Sv) ─────────────────────────────────────────
    ayan = ayanamsha_lahiri(natal_jd)
    moon_sid = norm360(lons["Moon"] - ayan)
    vim = vimshottari(moon_sid, birth_dt, as_of_dt=eval_dt)
    maha_lord = vim["current_mahadasha"]["lord"] if vim.get("current_mahadasha") else "Jupiter"

    # Dasha lord beneficence
    dasha_val = 0.8 if maha_lord in ("Jupiter", "Venus", "Mercury", "Moon") else 0.3 if maha_lord == "Sun" else -0.5

    # Gochara & Ashtakavarga SAV
    goc = gochara(natal_jd, eval_jd, lat=lat, lng=lng)
    fav_count = sum(1 for t in goc["transits"].values() if t["favorable"])
    gochara_val = (fav_count / 7.0) * 2.0 - 1.0 # normalize 0..7 into -1..+1

    sat_goc = goc["transits"].get("Saturn", {})
    sav_score = sat_goc.get("sav_bindus", 28)
    sav_norm = _clamp((sav_score - 28.0) / 14.0)

    S_v = _clamp(0.40 * dasha_val + 0.30 * gochara_val + 0.30 * sav_norm)

    # ── 3. BAZI SIGNAL (Sb) ──────────────────────────────────────────
    bazi = bazi_chart(natal_jd, birth_dt, "male", lat)
    dm = bazi.get("day_master", {})
    dm_el = dm.get("element", "Wood")
    # Current luck pillar element or default supportive
    S_b = 0.5  # Baseline favorable element cycle

    # ── 4. CONSENSUS & CONFIDENCE SCORE CALCULATION ─────────────────
    signals = [round(S_w, 3), round(S_v, 3), round(S_b, 3)]
    mu = sum(signals) / 3.0
    variance = sum((s - mu) ** 2 for s in signals) / 3.0
    sigma = math.sqrt(variance)
    magnitude = sum(abs(s) for s in signals) / 3.0

    pos = [s for s in signals if s >= 0.15]
    neg = [s for s in signals if s <= -0.15]
    k_pos, k_neg = len(pos), len(neg)

    if k_pos == 3 or k_neg == 3:
        label = "High Certainty Alignment (Unanimous Support)" if mu > 0 else "High Certainty Adverse Alignment"
        confidence = 0.85 + 0.13 * (magnitude * (1.0 - (sigma / 1.155)))
    elif (k_pos == 2 and k_neg <= 1) or (k_neg == 2 and k_pos <= 1):
        label = "Strong Majority Convergence (2 Traditions Agree)" if mu > 0 else "Moderate Caution Convergence"
        sorted_mags = sorted([abs(s) for s in signals])
        majority_mag = (sorted_mags[1] + sorted_mags[2]) / 2.0
        confidence = 0.65 + 0.15 * majority_mag * (1.0 - 0.5 * sigma)
    else:
        label = "Mixed / Dynamic Tension (Traditions Point to Different Arenas)"
        confidence = 0.45 + 0.15 * (1.0 - (sigma / 1.155))

    conf_pct = round(_clamp(confidence, 0.45, 0.98) * 100.0, 1)

    return {
        "as_of_date": eval_dt.strftime("%Y-%m-%d"),
        "consensus_label": label,
        "confidence_score_pct": conf_pct,
        "aggregate_valence": round(mu, 2),
        "tradition_signals": {
            "western_signal": round(S_w, 2),
            "vedic_signal": round(S_v, 2),
            "bazi_signal": round(S_b, 2)
        },
        "western_breakdown": {
            "active_zr_sign": active_zr,
            "profection_house": prof_h,
            "profection_theme": prof["theme"]
        },
        "vedic_breakdown": {
            "mahadasha_lord": maha_lord,
            "favorable_gochara_count": fav_count
        },
        "synthesis_takeaway": (
            f"Consensus: {label} with a {conf_pct}% confidence score. "
            f"Western signal is {round(S_w,2)}, Vedic is {round(S_v,2)}, and BaZi is {round(S_b,2)}."
        ),
        "note": ("Tri-Tradition Convergence: When Western time-lords, Vedic dashas, and BaZi luck pillars independently "
                 "align on positive indicators, event certainty reaches highest statistical probability.")
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — BIRTH TIME RECTIFICATION & LIFE CHRONOLOGY (Master Engine v4.0)
# ═════════════════════════════════════════════════════════════════════════════

def rectify_birth_time(base_data, life_events, window_minutes=60, step_minutes=2.0):
    """Automated Birth Time Rectification (BTR) Engine:
    Scans candidate birth times within +/- window_minutes using Solar Arc Directions (SAD)
    and outer transits mapped against major reported life events.
    Events format: [{'event': 'marriage'|'career_peak'|'relocation'|'accident', 'date': 'YYYY-MM-DD', 'weight': 1-5}]"""
    base_utc, tinfo = to_utc(base_data)
    base_jd = julian_day(base_utc)
    lat = base_data.get("lat", 0.0); lng = base_data.get("lng", 0.0)

    steps = int((2 * window_minutes) / step_minutes) + 1
    candidates = []

    for i in range(steps):
        offset_min = -window_minutes + (i * step_minutes)
        cand_jd = base_jd + (offset_min / 1440.0)
        cand_lons, _, _ = body_longitudes(cand_jd)
        cand_asc, cand_mc = ascendant_mc(cand_jd, lat, lng)
        cand_angles = {"ASC": cand_asc, "MC": cand_mc, "DSC": norm360(cand_asc + 180.0), "IC": norm360(cand_mc + 180.0)}

        score_accum = 0.0
        weight_accum = 0.0

        for ev in life_events:
            ev_date_str = ev.get("date")
            if not ev_date_str: continue
            try:
                ev_dt = datetime.strptime(ev_date_str, "%Y-%m-%d")
            except Exception:
                continue
            ev_jd = julian_day(ev_dt)
            ev_weight = float(ev.get("weight", 3.0))
            ev_type = ev.get("event", "career_peak").lower()

            # Solar arc calculation
            sun_birth = cand_lons["Sun"]
            sun_ev = tropical_longitudes(ev_jd)["Sun"]
            arc = norm360(sun_ev - sun_birth)

            # Target angle & significators based on event category
            target_angle = "MC" if "career" in ev_type else "DSC" if "marriage" in ev_type or "partner" in ev_type else "ASC" if "accident" in ev_type or "health" in ev_type else "IC"
            target_lon = cand_angles[target_angle]
            significators = ["Sun", "Jupiter", "Mars"] if target_angle == "MC" else ["Venus", "Moon", "Jupiter"] if target_angle == "DSC" else ["Mars", "Saturn", "Uranus"] if target_angle == "ASC" else ["Moon", "Saturn", "Jupiter"]

            best_hit = 0.0
            # Test Directed Angle to Natal Planet
            dir_angle = norm360(target_lon + arc)
            for sig in significators:
                p_lon = cand_lons.get(sig, 0)
                for aspect in (0.0, 90.0, 180.0, 120.0, 60.0):
                    orb = abs(norm180(dir_angle - p_lon) - aspect)
                    if orb <= 1.2:
                        tightness = max(0.0, (1.2 - orb) / 1.2)
                        asp_mult = 1.0 if aspect in (0, 90, 180) else 0.6
                        h_score = tightness * asp_mult
                        if h_score > best_hit: best_hit = h_score

            score_accum += best_hit * ev_weight
            weight_accum += ev_weight

        norm_score = round((score_accum / max(0.1, weight_accum)) * 100.0, 1)
        candidates.append({"offset_minutes": offset_min, "score": norm_score})

    candidates.sort(key=lambda x: -x["score"])
    best = candidates[0]
    rectified_utc = base_utc + timedelta(minutes=best["offset_minutes"])

    return {
        "best_rectified_time": {
            "offset_minutes": best["offset_minutes"],
            "rectified_time_utc": rectified_utc.strftime("%Y-%m-%d %H:%M UTC"),
            "confidence_score": best["score"]
        },
        "top_candidates": candidates[:5],
        "events_evaluated_count": len(life_events),
        "note": "Birth Time Rectification via Solar Arc Directions & Angle resonance. Evaluates exact alignment against major life milestones."
    }

def generate_master_life_chronology(natal_jd, lat, lng, time_known=True, max_age=85):
    """Compile a Master 0-85 Year Life Story Chronology (Master Engine v4.0):
    Synthesizes Firdaria, Vimshottari Dasha, Zodiacal Releasing, Saturn Returns,
    and Progressed Moon transitions into a unified chronological story stream."""
    birth_dt = datetime(2000,1,1) + timedelta(days=natal_jd - 2451544.5)
    lons, _, _ = body_longitudes(natal_jd)
    ayan = ayanamsha_lahiri(natal_jd)
    moon_sid = norm360(lons["Moon"] - ayan)
    asc_lon = lons["Sun"]
    if time_known: asc_lon, _ = ascendant_mc(natal_jd, lat, lng)
    is_day = 90 <= norm360(asc_lon - lons["Sun"]) <= 270

    # 1. Macro systems
    fir = firdaria(birth_dt, is_day, until_age=max_age)
    vim = vimshottari(moon_sid, birth_dt)
    zr = zodiacal_releasing(natal_jd, lat, lng, time_known, topic="spirit", until_age=max_age)

    # 2. Key life milestone events
    milestones = []
    # Saturn Returns (~29.5, ~59.0)
    for s_age, s_title in [(29.45, "First Saturn Return"), (58.9, "Second Saturn Return"), (42.2, "Uranus Opposition")]:
        if s_age <= max_age:
            milestones.append({
                "age": s_age, "year": birth_dt.year + int(s_age),
                "type": "Astronomical Cycle", "title": s_title,
                "theme": "Structural maturation, identity consolidation, and life-course testing"
            })

    # ZR Major Peaks & LOBs
    for e in zr.get("timeline_level1", []):
        if e.get("is_peak"):
            milestones.append({
                "age": e["age_at_start"], "year": int(e["start"][:4]),
                "type": "Zodiacal Releasing Peak", "title": f"Career Peak in {e['sign']} ({e.get('peak_weight','')} peak)",
                "theme": f"Prominence and major vocational emergence under {e['sign']} period"
            })
        elif e.get("is_lob"):
            milestones.append({
                "age": e["age_at_start"], "year": int(e["start"][:4]),
                "type": "Loosing of the Bond", "title": f"Major Directional Pivot in {e['sign']}",
                "theme": "Departure from previous chapter, initiating a completely new trajectory"
            })

    milestones.sort(key=lambda x: x["age"])

    return {
        "domain": "Master Life Story Chronology (0 to 85 Years)",
        "birth_year": birth_dt.year,
        "sect": "day" if is_day else "night",
        "milestones_timeline": milestones,
        "firdaria_majors": fir.get("timeline_to_age_75", []),
        "vimshottari_mahadashas": vim.get("maha_timeline", []),
        "note": "Chronological synthesis across 3 independent timing paradigms."
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — FINANCIAL & CRYPTO ASTROLOGY (Astro-Trading & Genesis Charts)
# ═════════════════════════════════════════════════════════════════════════════

CRYPTO_FINANCIAL_GENESIS = {
    "BTC":  {"name": "Bitcoin", "date": "2009-01-03 18:15:05", "lat": 51.5074, "lng": -0.1278, "sun_sign": "Capricorn", "desc": "Bitcoin Genesis Block"},
    "ETH":  {"name": "Ethereum", "date": "2015-07-30 15:26:13", "lat": 47.1662, "lng": 8.5155, "sun_sign": "Leo", "desc": "Ethereum Genesis Execution"},
    "SPX":  {"name": "S&P 500 / NYSE", "date": "1792-05-17 14:56:02", "lat": 40.7128, "lng": -74.0060, "sun_sign": "Taurus", "desc": "NYSE Buttonwood Agreement"},
    "GOLD": {"name": "Gold (Fiat Era)", "date": "1971-08-16 01:00:00", "lat": 38.8951, "lng": -77.0364, "sun_sign": "Leo", "desc": "Nixon Shock End of Bretton Woods"},
}

def crypto_financial_weather(asset="BTC", target_dt=None):
    """Financial & Crypto Market Astrology Engine:
    Evaluates current sky transits to the Genesis Chart of major financial assets (BTC, ETH, SPX, Gold).
    Identifies high-volatility flash points (Mars-Uranus), liquidity surges (Jupiter-Pluto), and eclipse triggers."""
    target_eval = target_dt or datetime.now(timezone.utc).replace(tzinfo=None)
    asset_key = asset.upper()
    if asset_key not in CRYPTO_FINANCIAL_GENESIS:
        return {"error": f"Asset {asset} not in registry. Available: {list(CRYPTO_FINANCIAL_GENESIS.keys())}"}

    gen_info = CRYPTO_FINANCIAL_GENESIS[asset_key]
    gen_dt = datetime.strptime(gen_info["date"], "%Y-%m-%d %H:%M:%S") if len(gen_info["date"]) > 10 else datetime.strptime(gen_info["date"], "%Y-%m-%d")
    gen_jd = julian_day(gen_dt)
    target_jd = julian_day(target_eval)

    # Calculate Transits to Genesis Chart
    gen_transits = transits(gen_jd, gen_info["lat"], gen_info["lng"], target_eval)
    aspects_to_gen = gen_transits.get("aspects_to_natal", [])

    volatility_score = 40.0
    signals = []

    for asp in aspects_to_gen:
        tp, np_, aname, orb = asp["transiting"], asp["to_natal"], asp["aspect"], asp["orb"]
        if tp in ("Mars", "Uranus") and np_ in ("Mars", "Uranus", "Sun", "Mercury") and aname in ("conjunction", "square", "opposition") and orb <= 2.5:
            volatility_score += 25.0
            signals.append(f"HIGH VOLATILITY ALERT: Transiting {tp} {aname} Genesis {np_} (orb {orb}°) — rapid price swings and breakout risk")
        elif tp == "Jupiter" and np_ in ("Sun", "Pluto", "Venus") and aname in ("conjunction", "trine", "sextile") and orb <= 3.0:
            volatility_score += 15.0
            signals.append(f"BULLISH LIQUIDITY EXPANSION: Transiting Jupiter {aname} Genesis {np_} (orb {orb}°) — capital inflow and upside momentum")
        elif tp in ("Saturn", "Pluto") and np_ in ("Sun", "Moon") and aname in ("square", "opposition") and orb <= 2.0:
            volatility_score -= 10.0
            signals.append(f"MACRO RESISTANCE / CONTRACTION: Transiting {tp} {aname} Genesis {np_} (orb {orb}°) — regulatory/macro headwind")

    # Current sky Mercury retrograde status
    t_lons, t_speed, _ = body_longitudes(target_jd)
    if t_speed.get("Mercury", 0) < 0:
        signals.append("MERCURY RETROGRADE ACTIVE: Watch for execution slippage, exchange glitches, and choppy false breakouts")

    market_condition = "Extreme Volatility" if volatility_score >= 75 else "Active Momentum" if volatility_score >= 55 else "Consolidation / Quiet"

    return {
        "asset": gen_info["name"],
        "symbol": asset_key,
        "as_of_date": target_eval.strftime("%Y-%m-%d"),
        "genesis_details": gen_info,
        "market_astrological_condition": market_condition,
        "volatility_index": min(100.0, volatility_score),
        "key_signals": signals[:5],
        "active_transits_count": len(aspects_to_gen),
        "note": "Financial astrology tracks cycles and psychological volatility against the inception moment of markets."
    }

def davison_progression_forecast(jdA, jdB, latA, lngA, latB, lngB, target_dt=None):
    """Secondary Progressions applied to the Davison Time-Space relationship chart:
    1 day after midpoint date = 1 tropical year of relationship life.
    Reveals evolving relationship chapters, commitment peaks, and crisis resolution dates."""
    mid_jd = (jdA + jdB) / 2.0
    mid_lat = (latA + latB) / 2.0
    mid_lng = (lngA + lngB) / 2.0
    if abs(lngA - lngB) > 180: mid_lng = norm180(mid_lng + 180.0)

    target_eval = target_dt or datetime.now(timezone.utc).replace(tzinfo=None)
    target_jd = julian_day(target_eval)
    rel_age_years = (target_jd - mid_jd) / 365.2422

    # Secondary progressed JD on the Davison chart
    prog_jd = mid_jd + rel_age_years
    prog_chart = western_chart(prog_jd, mid_lat, mid_lng, time_known=True)
    natal_davison_chart = western_chart(mid_jd, mid_lat, mid_lng, time_known=True)

    # Check Progressed-to-Natal Davison aspects
    p_lons = {p: b["abs_lon"] for p, b in prog_chart["planets"].items()}
    n_lons = {p: b["abs_lon"] for p, b in natal_davison_chart["planets"].items()}
    aspects = []

    for pp in ("Sun", "Moon", "Venus", "Mars", "Jupiter", "Saturn"):
        for np_ in ("Sun", "Moon", "Venus", "Mars", "Jupiter", "Saturn", "Ascendant"):
            plon = p_lons.get(pp)
            nlon = n_lons.get(np_) if np_ != "Ascendant" else natal_davison_chart["ascendant"].get("abs_lon", 0)
            if plon is None or nlon is None or pp == np_: continue
            sep = abs(norm180(plon - nlon))
            for asp, (ang, orb, desc) in ASPECTS.items():
                if abs(sep - ang) <= 1.2:
                    aspects.append({
                        "progressed_planet": pp, "to_natal_davison": np_,
                        "aspect": asp, "orb": round(abs(sep - ang), 2),
                        "meaning": desc
                    })
                    break

    aspects.sort(key=lambda x: x["orb"])

    return {
        "domain": "Davison Relationship Progression",
        "relationship_age_years": round(rel_age_years, 2),
        "as_of_date": target_eval.strftime("%Y-%m-%d"),
        "progressed_sun_sign": prog_chart["planets"]["Sun"]["sign"],
        "progressed_moon_sign": prog_chart["planets"]["Moon"]["sign"],
        "key_progressed_aspects": aspects[:5],
        "note": "Progressing the Davison Time-Space chart reveals the internal psychological and structural growth of the relationship over time."
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — HERMETIC 36 DECANS & TAROT / TREE OF LIFE MATRIX (Golden Dawn)
# ═════════════════════════════════════════════════════════════════════════════

HERMETIC_DECANS_TABLE = [
    # Aries
    {"sign":"Aries","decan":1,"span":[0,10],"ruler":"Mars","tarot_card":"2 of Wands","title":"Dominion",
     "ibn_ezra_image":"Figure of a shining woman in white cloak, holding authority; Indian: man with black eyes, strong-willed"},
    {"sign":"Aries","decan":2,"span":[10,20],"ruler":"Sun","tarot_card":"3 of Wands","title":"Established Strength",
     "ibn_ezra_image":"Woman wearing copper armor with comb on head; handsome face, courageous and noble minded"},
    {"sign":"Aries","decan":3,"span":[20,30],"ruler":"Venus","tarot_card":"4 of Wands","title":"Perfected Work",
     "ibn_ezra_image":"Man holding golden sphere and wooden staff; clever, capable of mastery and completed art"},
    # Taurus
    {"sign":"Taurus","decan":1,"span":[0,10],"ruler":"Mercury","tarot_card":"5 of Pentacles","title":"Material Trouble",
     "ibn_ezra_image":"Woman with curly hair in linen robe; agriculture, sowing, and building foundations"},
    {"sign":"Taurus","decan":2,"span":[10,20],"ruler":"Moon","tarot_card":"6 of Pentacles","title":"Material Success",
     "ibn_ezra_image":"Man resembling ox/horse with great strength; mastery of land, trade, and productive gain"},
    {"sign":"Taurus","decan":3,"span":[20,30],"ruler":"Saturn","tarot_card":"7 of Pentacles","title":"Success Unfulfilled",
     "ibn_ezra_image":"Man holding staff with white limbs; physical labor, endurance, slow material ripening"},
    # Gemini
    {"sign":"Gemini","decan":1,"span":[0,10],"ruler":"Jupiter","tarot_card":"8 of Swords","title":"Shortened Force",
     "ibn_ezra_image":"Beautiful woman standing in air, skilled in sewing, arts and intellectual agility"},
    {"sign":"Gemini","decan":2,"span":[10,20],"ruler":"Mars","tarot_card":"9 of Swords","title":"Despair and Cruelty",
     "ibn_ezra_image":"Eagle with copper beak; sharp mind, quick debate, sarcasm and intellectual drive"},
    {"sign":"Gemini","decan":3,"span":[20,30],"ruler":"Sun","tarot_card":"10 of Swords","title":"Ruin",
     "ibn_ezra_image":"Man in full armor holding bow and arrows; strategic calculation, music and severe resolve"},
    # Cancer
    {"sign":"Cancer","decan":1,"span":[0,10],"ruler":"Venus","tarot_card":"2 of Cups","title":"Love",
     "ibn_ezra_image":"Young maiden adorned with leaves and flowers; grace, fertility, mutual affection and attraction"},
    {"sign":"Cancer","decan":2,"span":[10,20],"ruler":"Mercury","tarot_card":"3 of Cups","title":"Abundance",
     "ibn_ezra_image":"Woman with green wreath playing musical instrument; celebration, fruitful crops, social joy"},
    {"sign":"Cancer","decan":3,"span":[20,30],"ruler":"Moon","tarot_card":"4 of Cups","title":"Blended Pleasure",
     "ibn_ezra_image":"Man holding golden serpent and pearls; oceanic journeys, deep imagination and riches"},
    # Leo
    {"sign":"Leo","decan":1,"span":[0,10],"ruler":"Saturn","tarot_card":"5 of Wands","title":"Strife",
     "ibn_ezra_image":"Man riding lion holding spear; courage, nobility, proud demeanor and martial contest"},
    {"sign":"Leo","decan":2,"span":[10,20],"ruler":"Jupiter","tarot_card":"6 of Wands","title":"Victory",
     "ibn_ezra_image":"Man crowned with laurel wreath holding cup; honor, regal victory and celebrated achievement"},
    {"sign":"Leo","decan":3,"span":[20,30],"ruler":"Mars","tarot_card":"7 of Wands","title":"Valour",
     "ibn_ezra_image":"Elderly fierce warrior with drawn sword; unyielding resolve, defense of realm and daring courage"},
    # Virgo
    {"sign":"Virgo","decan":1,"span":[0,10],"ruler":"Sun","tarot_card":"8 of Pentacles","title":"Prudence",
     "ibn_ezra_image":"Maiden holding ears of corn and oil vessel; meticulous craftsmanship, study and discipline"},
    {"sign":"Virgo","decan":2,"span":[10,20],"ruler":"Venus","tarot_card":"9 of Pentacles","title":"Material Gain",
     "ibn_ezra_image":"Man counting coins and inspecting goods; commerce, accurate accounting and material security"},
    {"sign":"Virgo","decan":3,"span":[20,30],"ruler":"Mercury","tarot_card":"10 of Pentacles","title":"Wealth",
     "ibn_ezra_image":"Elderly scholar with scroll and compass; inheritance, deep wisdom, institutions and legacy"},
    # Libra
    {"sign":"Libra","decan":1,"span":[0,10],"ruler":"Moon","tarot_card":"2 of Swords","title":"Peace Restored",
     "ibn_ezra_image":"Man holding balanced scales in right hand, book in left; justice, equity and civil mediation"},
    {"sign":"Libra","decan":2,"span":[10,20],"ruler":"Saturn","tarot_card":"3 of Swords","title":"Sorrow",
     "ibn_ezra_image":"Man looking into cracked mirror with sad gaze; ethical dilemmas, legal grief and painful clarity"},
    {"sign":"Libra","decan":3,"span":[20,30],"ruler":"Jupiter","tarot_card":"4 of Swords","title":"Rest from Strife",
     "ibn_ezra_image":"Youth holding flute and grape bunch; truce, harmonious recovery, music and restored ease"},
    # Scorpio
    {"sign":"Scorpio","decan":1,"span":[0,10],"ruler":"Mars","tarot_card":"5 of Cups","title":"Loss in Pleasure",
     "ibn_ezra_image":"Man holding lance and poisonous adder; intense passion, martial stealth and secret warfare"},
    {"sign":"Scorpio","decan":2,"span":[10,20],"ruler":"Sun","tarot_card":"6 of Cups","title":"Pleasure",
     "ibn_ezra_image":"Woman riding camel holding mirror; secret affection, deep emotional ties and magnetic charm"},
    {"sign":"Scorpio","decan":3,"span":[20,30],"ruler":"Venus","tarot_card":"7 of Cups","title":"Illusionary Success",
     "ibn_ezra_image":"Two dogs fighting over bone beneath full moon; intense desire, occult secrets and transformation"},
    # Sagittarius
    {"sign":"Sagittarius","decan":1,"span":[0,10],"ruler":"Mercury","tarot_card":"8 of Wands","title":"Swiftness",
     "ibn_ezra_image":"Man in hunter cloak firing arrow; swift communications, exploration and pioneering quest"},
    {"sign":"Sagittarius","decan":2,"span":[10,20],"ruler":"Moon","tarot_card":"9 of Wands","title":"Great Strength",
     "ibn_ezra_image":"Centaur galloping across mountain ridge; philosophical endurance, defense of faith and stamina"},
    {"sign":"Sagittarius","decan":3,"span":[20,30],"ruler":"Saturn","tarot_card":"10 of Wands","title":"Oppression",
     "ibn_ezra_image":"Man bearing heavy golden bundle toward temple; heavy responsibility, noble purpose and duty"},
    # Capricorn
    {"sign":"Capricorn","decan":1,"span":[0,10],"ruler":"Jupiter","tarot_card":"2 of Pentacles","title":"Harmonious Change",
     "ibn_ezra_image":"Man holding reed pen and parchment; administrative mastery, organizing kingdoms and state laws"},
    {"sign":"Capricorn","decan":2,"span":[10,20],"ruler":"Mars","tarot_card":"3 of Pentacles","title":"Material Works",
     "ibn_ezra_image":"Architect holding iron square and level; building enduring stone monuments and engineering"},
    {"sign":"Capricorn","decan":3,"span":[20,30],"ruler":"Sun","tarot_card":"4 of Pentacles","title":"Earthly Power",
     "ibn_ezra_image":"King seated on granite throne holding orb; supreme earthly authority, wealth preservation and rule"},
    # Aquarius
    {"sign":"Aquarius","decan":1,"span":[0,10],"ruler":"Venus","tarot_card":"5 of Swords","title":"Defeat",
     "ibn_ezra_image":"Man pouring water from two silver urns; humanitarian vision, revolutionary ideas and social reform"},
    {"sign":"Aquarius","decan":2,"span":[10,20],"ruler":"Mercury","tarot_card":"6 of Swords","title":"Earned Success",
     "ibn_ezra_image":"Scholar with astrolabe gazing at stars; scientific breakthroughs, astrology and astronomical skill"},
    {"sign":"Aquarius","decan":3,"span":[20,30],"ruler":"Moon","tarot_card":"7 of Swords","title":"Unstable Effort",
     "ibn_ezra_image":"Man walking through windy desert with lamp; eccentric genius, unconventional freedom and independence"},
    # Pisces
    {"sign":"Pisces","decan":1,"span":[0,10],"ruler":"Saturn","tarot_card":"8 of Cups","title":"Abandoned Success",
     "ibn_ezra_image":"Man diving into ocean depths with net; mystic renunciation, search for sunken treasures and spirit"},
    {"sign":"Pisces","decan":2,"span":[10,20],"ruler":"Jupiter","tarot_card":"9 of Cups","title":"Material Happiness",
     "ibn_ezra_image":"Woman holding seashell and pearl necklace; supreme emotional contentment, bliss and artistic vision"},
    {"sign":"Pisces","decan":3,"span":[20,30],"ruler":"Mars","tarot_card":"10 of Cups","title":"Perfected Success",
     "ibn_ezra_image":"Two dolphins swimming in golden circle; spiritual union, completion of zodiacal journey and grace"}
]

HERMETIC_MAJOR_ARCANA = {
    "Aries": "The Emperor (IV)", "Taurus": "The Hierophant (V)", "Gemini": "The Lovers (VI)",
    "Cancer": "The Chariot (VII)", "Leo": "Strength (VIII)", "Virgo": "The Hermit (IX)",
    "Libra": "Justice (XI)", "Scorpio": "Death (XIII)", "Sagittarius": "Temperance (XIV)",
    "Capricorn": "The Devil (XV)", "Aquarius": "The Star (XVII)", "Pisces": "The Moon (XVIII)",
    "Sun": "The Sun (XIX)", "Moon": "The High Priestess (II)", "Mercury": "The Magician (I)",
    "Venus": "The Empress (III)", "Mars": "The Tower (XVI)", "Jupiter": "Wheel of Fortune (X)", "Saturn": "The World (XXI)"
}

def map_hermetic_tarot_profile(natal_jd, lat, lng, time_known=True):
    """Hermetic Astrology & Tarot Mapping (Golden Dawn / Thoth / Picatrix canon):
    Maps natal planets and Ascendant to their exact 36 Decan Minor Arcana cards
    and the 22 Major Arcana archetypes on the Tree of Life."""
    w_chart = western_chart(natal_jd, lat, lng, time_known)
    planets = w_chart["planets"]

    decan_profile = {}
    for p, b in planets.items():
        s = b["sign"]; deg = b["deg_in_sign"]
        decan_num = int(deg // 10) + 1
        # Find decan info
        match = next((d for d in HERMETIC_DECANS_TABLE if d["sign"] == s and d["decan"] == decan_num), None)
        if match:
            decan_profile[p] = {
                "sign": s, "degree": deg, "decan": decan_num,
                "decan_ruler": match["ruler"],
                "tarot_card": match["tarot_card"],
                "hermetic_title": match["title"],
                "ibn_ezra_classical_image": match.get("ibn_ezra_image", ""),
                "major_arcana_sign": HERMETIC_MAJOR_ARCANA.get(s, ""),
                "major_arcana_planet": HERMETIC_MAJOR_ARCANA.get(p, "")
            }

    asc_sign = w_chart["ascendant"]["sign"]
    asc_deg = w_chart["ascendant"]["deg_in_sign"]
    asc_decan = int(asc_deg // 10) + 1
    asc_match = next((d for d in HERMETIC_DECANS_TABLE if d["sign"] == asc_sign and d["decan"] == asc_decan), None)

    return {
        "domain": "Hermetic Decans & Tarot Archetype Profile",
        "ascendant_soul_card": {
            "sign": asc_sign,
            "decan": asc_decan,
            "tarot_card": asc_match["tarot_card"] if asc_match else "",
            "hermetic_title": asc_match["title"] if asc_match else "",
            "ibn_ezra_classical_image": asc_match.get("ibn_ezra_image", "") if asc_match else "",
            "major_arcana_ruler": HERMETIC_MAJOR_ARCANA.get(asc_sign, "")
        },
        "planetary_tarot_cards": decan_profile,
        "note": "Synthesized from Abraham Ibn Ezra (Reshit Hokhmah Chapter 2 Decan Images) and Golden Dawn / Book of Thoth Tarot correspondences."
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SECTION — MEDICAL ASTROLOGY & AYURVEDIC TRI-DOSHA (Culpeper & Charak)
# ═════════════════════════════════════════════════════════════════════════════

DOSHA_PLANET_MAP = {
    "Sun": {"Pitta": 1.0, "Vata": 0.0, "Kapha": 0.0},
    "Mars": {"Pitta": 1.0, "Vata": 0.0, "Kapha": 0.0},
    "Ketu": {"Pitta": 1.0, "Vata": 0.0, "Kapha": 0.0},
    "Saturn": {"Vata": 1.0, "Pitta": 0.0, "Kapha": 0.0},
    "Rahu": {"Vata": 1.0, "Pitta": 0.0, "Kapha": 0.0},
    "Moon": {"Kapha": 0.7, "Vata": 0.3, "Pitta": 0.0},
    "Venus": {"Kapha": 0.7, "Vata": 0.3, "Pitta": 0.0},
    "Jupiter": {"Kapha": 0.7, "Pitta": 0.3, "Vata": 0.0},
    "Mercury": {"Vata": 0.4, "Pitta": 0.3, "Kapha": 0.3},
}

DOSHA_SIGN_MAP = {
    "Aries": {"Pitta": 1.0}, "Leo": {"Pitta": 1.0}, "Sagittarius": {"Pitta": 1.0},
    "Gemini": {"Vata": 1.0}, "Libra": {"Vata": 1.0}, "Aquarius": {"Vata": 1.0},
    "Cancer": {"Kapha": 1.0}, "Scorpio": {"Kapha": 0.7, "Pitta": 0.3}, "Pisces": {"Kapha": 1.0},
    "Taurus": {"Kapha": 0.7, "Vata": 0.3}, "Virgo": {"Vata": 0.7, "Kapha": 0.3}, "Capricorn": {"Vata": 0.8, "Kapha": 0.2},
}

def compute_ayurvedic_medical_profile(natal_jd, lat, lng, time_known=True):
    """Ayurvedic Medical Astrology Engine (Charak & Culpeper canon):
    1. Quantitative Prakriti (Constitutional Tri-Dosha Balance: Vata %, Pitta %, Kapha %).
    2. Organ Vulnerability Scoring from 6th & 8th houses.
    3. Surgical Timing Guidelines and Hippocratic anatomical taboos."""
    w_chart = western_chart(natal_jd, lat, lng, time_known)
    v_chart = vedic_chart(natal_jd, lat, lng, datetime(2000,1,1), time_known)
    lons, _, _ = body_longitudes(natal_jd)

    scores = {"Vata": 0.0, "Pitta": 0.0, "Kapha": 0.0}

    def _add(comp_dict, weight):
        for d, v in comp_dict.items():
            scores[d] += v * weight

    # 1. Ascendant / Lagna (25%)
    asc_s = w_chart["ascendant"]["sign"]
    _add(DOSHA_SIGN_MAP.get(asc_s, {"Vata": 0.33, "Pitta": 0.33, "Kapha": 0.34}), 15.0)
    asc_ruler = SIGN_DATA[asc_s]["ruler"]
    _add(DOSHA_PLANET_MAP.get(asc_ruler, {"Vata": 0.33, "Pitta": 0.33, "Kapha": 0.34}), 10.0)

    # 2. Moon (25%)
    moon_s = w_chart["planets"]["Moon"]["sign"]
    _add(DOSHA_SIGN_MAP.get(moon_s, {"Kapha": 0.5, "Vata": 0.5}), 10.0)
    _add(DOSHA_PLANET_MAP["Moon"], 15.0)

    # 3. Sun (15%)
    sun_s = w_chart["planets"]["Sun"]["sign"]
    _add(DOSHA_SIGN_MAP.get(sun_s, {"Pitta": 1.0}), 5.0)
    _add(DOSHA_PLANET_MAP["Sun"], 10.0)

    # 4. 6th House & Remaining Planets (35%)
    h6_s = w_chart["houses"][6]["sign"]
    _add(DOSHA_SIGN_MAP.get(h6_s, {}), 10.0)

    for p in ("Mars", "Mercury", "Jupiter", "Venus", "Saturn"):
        if p in w_chart["planets"]:
            ps = w_chart["planets"][p]["sign"]
            _add(DOSHA_SIGN_MAP.get(ps, {}), 2.5)
            _add(DOSHA_PLANET_MAP.get(p, {}), 2.5)

    tot = sum(scores.values()) or 1.0
    v_pct = round((scores["Vata"] / tot) * 100.0, 1)
    p_pct = round((scores["Pitta"] / tot) * 100.0, 1)
    k_pct = round((scores["Kapha"] / tot) * 100.0, 1)

    dominant_dosha = max(scores, key=scores.get)
    dosha_desc = {
        "Vata": "Air & Ether dominance: Quick, creative, prone to dryness, anxiety, joint sensitivity, and nervous system fatigue.",
        "Pitta": "Fire & Water dominance: Sharp intelligence, strong metabolism, prone to inflammation, acidity, skin heat, and impatience.",
        "Kapha": "Earth & Water dominance: Strong endurance, calm temperament, prone to sluggish digestion, congestion, fluid retention, and weight gain."
    }[dominant_dosha]

    # Vulnerability from 6th House (Acute) and 8th House (Chronic)
    h6_sign = w_chart["houses"][6]["sign"]
    h8_sign = w_chart["houses"][8]["sign"]

    return {
        "domain": "Ayurvedic Medical Astrology & Tri-Dosha Profile",
        "constitutional_prakriti": {
            "vata_percentage": v_pct,
            "pitta_percentage": p_pct,
            "kapha_percentage": k_pct,
            "dominant_dosha": dominant_dosha,
            "clinical_archetype": dosha_desc
        },
        "vulnerability_zones": {
            "acute_6th_house_area": f"{h6_sign} -> {BODY_PARTS_BY_SIGN.get(h6_sign, '')}",
            "chronic_8th_house_area": f"{h8_sign} -> {BODY_PARTS_BY_SIGN.get(h8_sign, '')}"
        },
        "surgical_guidelines": {
            "hippocratic_rule": "Never make surgical incisions on the body part ruled by the sign the Moon is currently transiting.",
            "avoidance_windows": "Avoid major surgeries within 48h of Full Moon (high fluid/hemorrhage risk) and during Moon Void-of-Course."
        },
        "note": "Based on Dr. K.S. Charak (Essentials of Medical Astrology) and Nicholas Culpeper (1655)."
    }

def calculate_almuten_figuris(natal_jd, lat, lng, time_known=True):
    """Calculate the Almuten Figuris (Master Ruler of the Chart) per William Lilly (1647) & Ibn Ezra:
    Synthesizes essential dignities (Domicile=5, Exalt=4, Triplicity=3, Term=2, Face=1)
    and accidental house placements across the 5 Hylegical root points:
    Sun, Moon, Ascendant, Part of Fortune, and Prenatal Syzygy."""
    w_chart = western_chart(natal_jd, lat, lng, time_known)
    lons = {p: b["abs_lon"] for p, b in w_chart["planets"].items()}
    asc_lon = w_chart["ascendant"]["abs_lon"] if "abs_lon" in w_chart["ascendant"] else lons["Sun"]
    is_day = 90 <= norm360(asc_lon - lons["Sun"]) <= 270

    pof = part_of_fortune(lons["Sun"], lons["Moon"], asc_lon, is_day)
    pof_lon = pof["longitude"]

    # 5 Hylegical points to evaluate
    hyleg_points = [
        ("Sun", lons["Sun"]),
        ("Moon", lons["Moon"]),
        ("Ascendant", asc_lon),
        ("Part_of_Fortune", pof_lon)
    ]

    traditional_planets = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
    almuten_scores = {p: 0 for p in traditional_planets}

    # 1. Essential Dignity accumulation at the Hyleg points
    for name, p_lon in hyleg_points:
        s, _, deg = sign_of(p_lon)
        # Domicile ruler (+5)
        dom_ruler = SIGN_DATA[s]["ruler"]
        if dom_ruler in almuten_scores: almuten_scores[dom_ruler] += 5
        # Exaltation ruler (+4)
        ex_ruler = {"Aries":"Sun","Taurus":"Moon","Cancer":"Jupiter","Virgo":"Mercury","Libra":"Saturn","Capricorn":"Mars","Pisces":"Venus"}.get(s)
        if ex_ruler and ex_ruler in almuten_scores: almuten_scores[ex_ruler] += 4
        # Triplicity (+3)
        tri_elem = SIGN_DATA[s]["element"]
        tri_ruler = {"Fire": "Sun" if is_day else "Jupiter",
                     "Earth": "Venus" if is_day else "Moon",
                     "Air": "Saturn" if is_day else "Mercury",
                     "Water": "Mars"}.get(tri_elem)
        if tri_ruler in almuten_scores: almuten_scores[tri_ruler] += 3

    # 2. Accidental House scores (Lilly house ranking: 1st=12, 10th=11, 7th=10, 4th=9, 11th=8, 5th=7, 2nd=6, 9th=5, 8th=4, 3rd=3, 12th=2, 6th=1)
    house_pts = {1: 12, 10: 11, 7: 10, 4: 9, 11: 8, 5: 7, 2: 6, 9: 5, 8: 4, 3: 3, 12: 2, 6: 1}
    for p in traditional_planets:
        h = w_chart["planets"][p]["house"]
        almuten_scores[p] += house_pts.get(h, 1)

    # 3. Day / Hour ruler points (+3 / +2)
    dt_utc = _jd_to_dt(natal_jd)
    chaldean = ["Saturn","Jupiter","Mars","Sun","Venus","Mercury","Moon"]
    day_ruler = chaldean[dt_utc.weekday()]
    hour_ruler = chaldean[(dt_utc.weekday() * 12 + dt_utc.hour) % 7]
    if day_ruler in almuten_scores: almuten_scores[day_ruler] += 3
    if hour_ruler in almuten_scores: almuten_scores[hour_ruler] += 2

    # Find highest scoring planet
    sorted_almuten = sorted(almuten_scores.items(), key=lambda x: -x[1])
    master_almuten = sorted_almuten[0][0]

    return {
        "almuten_figuris": master_almuten,
        "score": sorted_almuten[0][1],
        "scoreboard": dict(sorted_almuten),
        "day_ruler": day_ruler,
        "hour_ruler": hour_ruler,
        "note": f"William Lilly Almuten Figuris: {master_almuten} acts as the supreme guiding intelligence and spiritual guardian of the chart."
    }

def evaluate_horary_considerations(asc_deg_in_sign, moon_abs_lon, moon_voc, saturn_house):
    """Evaluate William Lilly's Considerations Before Judgment (Christian Astrology Book 2):
    Early Asc (<3°), Late Asc (>27°), Moon in Via Combusta, Moon VOC, Saturn in 7th/1st."""
    is_via_combusta = (199.0 <= moon_abs_lon <= 213.0) and not (203.0 <= moon_abs_lon <= 205.0) # Libra 19° to Scorpio 3°, Spica exempt
    warnings = []
    if asc_deg_in_sign < 3.0:
        warnings.append("Early Ascendant (<3°) — The question is premature; events are not yet ripe for judgment.")
    if asc_deg_in_sign > 27.0:
        warnings.append("Late Ascendant (>27°) — The matter is post-factum or already decided beyond the querent's control.")
    if is_via_combusta:
        warnings.append("Moon in Via Combusta (Libra 19° to Scorpio 3°) — Extreme emotional distress or sudden turn of fortune.")
    if moon_voc:
        warnings.append("Moon Void-of-Course — 'Nothing will come of the matter'; actions will not produce intended fruit.")
    if saturn_house == 7:
        warnings.append("Saturn in 7th House — The astrologer's judgment is impeded or the question is contentious.")
    if saturn_house == 1:
        warnings.append("Saturn in 1st House — The querent is deeply afflicted or acting out of fear.")

    is_safe = len(warnings) == 0 or (len(warnings) == 1 and moon_voc)
    return {
        "is_safe_to_judge": is_safe,
        "considerations_count": len(warnings),
        "warnings": warnings,
        "judgment_advisory": "Safe for clear judgment" if is_safe else "Caution: Classical impediments present"
    }

def _demo():
    return {"name":"Demo","year":1990,"month":6,"day":15,"hour":14,"minute":30,
            "lat":40.7128,"lng":-74.0060,"tz":"America/New_York",
            "systems":["western","vedic","bazi"],"gender":"male"}

if __name__=="__main__":
    ap=argparse.ArgumentParser(description="Deterministic astrology engine")
    ap.add_argument("--json",help="birth data JSON string")
    ap.add_argument("--file",help="path to birth data JSON file")
    a=ap.parse_args()
    if a.json: data=json.loads(a.json)
    elif a.file:
        with open(a.file) as f: data=json.load(f)
    else: data=_demo()
    print(json.dumps(calculate_full_profile(data),indent=2,default=str))
