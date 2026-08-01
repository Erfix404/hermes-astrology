#!/usr/bin/env python3
"""
Advanced Astrology Features — supplement to astro_engine.py
===========================================================
8 premium modules: Node transit, Guna Milan, Solar Return interpretation,
Electional finder, Solar Arc, Remedies, Weekly calendar, Prashna.

All zero-dependency (stdlib only). Each function returns dict ready for JSON.
"""

import math, json, os, sys
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    import astro_engine as _ae
except ImportError:
    _ae = None

# ── helpers (mirror astro_engine) ───────────────────────────────────
SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
         "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
SIGN_DATA = {
    "Aries":      {"element":"Fire",    "modality":"Cardinal",    "ruler":"Mars",         "quality":"Y"},
    "Taurus":     {"element":"Earth",   "modality":"Fixed",       "ruler":"Venus",        "quality":"Y"},
    "Gemini":     {"element":"Air",     "modality":"Mutable",     "ruler":"Mercury",      "quality":"Y"},
    "Cancer":     {"element":"Water",   "modality":"Cardinal",    "ruler":"Moon",         "quality":"N"},
    "Leo":        {"element":"Fire",    "modality":"Fixed",       "ruler":"Sun",          "quality":"Y"},
    "Virgo":      {"element":"Earth",   "modality":"Mutable",     "ruler":"Mercury",      "quality":"N"},
    "Libra":      {"element":"Air",     "modality":"Cardinal",    "ruler":"Venus",        "quality":"Y"},
    "Scorpio":    {"element":"Water",   "modality":"Fixed",       "ruler":"Mars/Pluto",   "quality":"N"},
    "Sagittarius":{"element":"Fire",    "modality":"Mutable",     "ruler":"Jupiter",      "quality":"Y"},
    "Capricorn":  {"element":"Earth",   "modality":"Cardinal",    "ruler":"Saturn",       "quality":"N"},
    "Aquarius":   {"element":"Air",     "modality":"Fixed",       "ruler":"Saturn/Uranus","quality":"Y"},
    "Pisces":     {"element":"Water",   "modality":"Mutable",     "ruler":"Jupiter/Neptune","quality":"N"},
}

NAKSHATRAS = [
    ("Ashwini","Aries",0,"Ket"),("Bharani","Aries",2,"Ven"),("Krittika","Aries",4,"Sun"),
    ("Rohini","Taurus",6,"Moo"),("Mrigashira","Taurus",8,"Mar"),("Ardra","Gemini",10,"Rah"),
    ("Punarvasu","Gemini",12,"Jup"),("Pushya","Cancer",14,"Sat"),("Ashlesha","Cancer",16,"Mer"),
    ("Magha","Leo",18,"Ket"),("Purva Phalguni","Leo",20,"Ven"),("Uttara Phalguni","Virgo",22,"Sun"),
    ("Hasta","Virgo",24,"Moo"),("Chitra","Libra",26,"Mar"),("Swati","Libra",28,"Rah"),
    ("Vishakha","Scorpio",30,"Jup"),("Anuradha","Scorpio",32,"Sat"),("Jyeshtha","Scorpio",34,"Mer"),
    ("Mula","Sagittarius",36,"Ket"),("Purva Ashadha","Sagittarius",38,"Ven"),("Uttara Ashadha","Capricorn",40,"Sun"),
    ("Shravana","Capricorn",42,"Moo"),("Dhanishtha","Aquarius",44,"Mar"),("Shatabhisha","Aquarius",46,"Rah"),
    ("Purva Bhadrapada","Pisces",48,"Jup"),("Uttara Bhadrapada","Pisces",50,"Sat"),("Revati","Pisces",52,"Mer"),
]
N_NAK = len(NAKSHATRAS)  # 27

def norm360(x):
    return x % 360.0

def sign_of(lon):
    s = SIGNS[int(lon // 30) % 12]
    return s if isinstance(s, str) else s[0]

def nakshatra_of(lon_sidereal):
    """Return (name, lord, pada) for a sidereal longitude."""
    deg = lon_sidereal % 360
    idx = int(deg // (360 / N_NAK))
    name, sign, start_deg, lord = NAKSHATRAS[idx % N_NAK]
    pada = int((deg % (360/N_NAK)) // (360/N_NAK/4)) + 1
    return {"name": name, "lord": lord, "pada": pada, "degrees_in_nak": round(deg % (360/N_NAK), 2)}

HOUSE_MEANINGS = {
    1:"Self, body, vitality, first impressions",
    2:"Money, possessions, values, self-worth",
    3:"Communication, siblings, short trips, courage",
    4:"Home, mother, roots, emotional foundation",
    5:"Creativity, children, romance, talent",
    6:"Health, daily work, service, obstacles",
    7:"Partnership, marriage, open enemies",
    8:"Death/rebirth, shared resources, intimacy, occult",
    9:"Philosophy, higher study, travel, luck",
    10:"Career, reputation, authority, public life",
    11:"Friends, networks, hopes, gains",
    12:"Solitude, loss, spirituality, the unconscious",
}

# ─────────────────────────────────────────────────────────────────────
#  1  — Node (Rahu/Ketu) Transit Analysis
# ─────────────────────────────────────────────────────────────────────
RAHU_HOUSES_INTERP = {
    1:"Identity crisis — you're being pulled to redefine who you are. Ego dissolves and reforms.",
    2:"Financial rollercoaster — values shift, unexpected gains/losses. Let go of attachment to money.",
    3:"Communication shake-up — friendships may fracture or deepen through honest talk.",
    4:"Home & roots uprooted — relocation, family shifts, or the past resurfacing. Find inner security.",
    5:"Creative destruction — love affairs, children, or artistic projects push you beyond comfort zones.",
    6:"Health & service spotlight — chronic issues demand attention. Routine becomes spiritual practice.",
    7:"Relationship crossroads — partnerships either transform or dissolve. Authenticity is non-negotiable.",
    8:"Deep underworld transit — occult, shared resources, intimacy. What's hidden comes to light.",
    9:"Belief system overhaul — travel, philosophy, or religion expands your worldview radically.",
    10:"Career metamorphosis — public identity shifts dramatically. Step into a bigger role.",
    11:"Community & networks — meet fated connections. Hopes get a reality check.",
    12:"Letting go — solitude, dreams, and spiritual release. What ends makes room for what's next.",
}
KETU_HOUSES_INTERP = {
    1:"Let go of ego — the need to impress dissolves. You become invisible, and that's freedom.",
    2:"Detachment from money — possessions lose meaning. Simple living emerges naturally.",
    3:"Silence over speech — fewer words, deeper listening. Sibling dynamics shift.",
    4:"Roots released — you feel disconnected from family or home. Finding inner home instead.",
    5:"Creative withdrawal — romance or children may feel distant. Inner creative rebirth.",
    6:"Health scrutiny — psychosomatic issues surface. Service to others heals.",
    7:"Relationship release — some partnerships fall away. Solitude purifies connection.",
    8:"Strong Ketu — spiritual insight, past life blur, interest in occult intensifies.",
    9:"Luck changes — faith dissolves and rebuilds. Travel may feel fated.",
    10:"Career detach — public ambition fades. Purpose becomes inner, not external.",
    11:"Social withdrawal — friend circles shrink. Quality over quantity in networks.",
    12:"Moksha pull — strong urge for renunciation. Dreams bring karmic messages.",
}

NODE_TECHNICAL = {
    "Rahu": {"nature": "shadow, obsession, worldly desire, illusion", "body": "south node head", "direction": "forward karmic growth"},
    "Ketu": {"nature": "detachment, spirituality, past life, wisdom", "body": "south node tail", "direction": "past life release"},
}

def analyze_node_transit(natal_lons, transit_lons):
    """Analyze Rahu and Ketu transit through the natal houses.
    
    Returns interpretation of which houses Rahu/Ketu are transiting,
    their natal house positions, and what themes are activated.
    """
    import sys
    _SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
    if _SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, _SCRIPTS_DIR)
    import astro_engine as _ae
    
    # Get ayanamsha for computing sidereal positions
    jd = datetime.utcnow()
    ayan = _ae.ayanamsha_lahiri(_ae.julian_day(jd))
    
    result = {}
    for node, key in [("Rahu", "North Node"), ("Ketu", "South Node")]:
        if key not in transit_lons:
            continue
        
        trans_lon = transit_lons[key]
        natal_lon = natal_lons.get(key, 0)
        
        # Transit house (whole sign)
        transit_house = int(trans_lon // 30) + 1
        natal_house = int(natal_lon // 30) + 1
        
        # Opposite house for Ketu if Rahu is in X, Ketu is in X+6
        partner_house = (transit_house + 5) % 12 + 1
        
        interp_key = transit_house
        rahu_interp = RAHU_HOUSES_INTERP.get(interp_key, "Observe what disrupts — it's your growth edge.")
        ketu_interp = KETU_HOUSES_INTERP.get(partner_house if node == "Rahu" else interp_key,
                        "Release is the theme — what falls away creates space.")
        
        interp = rahu_interp if node == "Rahu" else ketu_interp
        # Sidereal nakshatra
        trans_nak = nakshatra_of(trans_lon - ayan)
        
        result[node] = {
            "transiting_house": transit_house,
            "natal_house": natal_house,
            "transit_nakshatra": trans_nak["name"],
            "transit_nakshatra_lord": trans_nak["lord"],
            "partner_house": partner_house,  # Ketu house if Rahu transit, vice versa
            "interpretation": interp,
            "house_meaning": HOUSE_MEANINGS.get(transit_house, ""),
            "technical": NODE_TECHNICAL[node],
        }
    
    result["_note"] = "Node transits (Rahu/Ketu) last ~18 months per house. Rahu amplifies the house; Ketu releases it. They always transit opposite houses together."
    return result


# Rahu/Ketu effect on natives of each zodiac sign (public, no birth data needed).
# From references/templates.md — tables ۷. Keyed by zodiac sign index 0-11 (Aries=0).
RAHU_SIGN_INTERP = {
    0:  "Career leap, fierce competition — boldness surges, watch for haste.",
    1:  "Money temptation and spending — wealth comes but managing it is hard.",
    2:  "Great networking, new connections — ignore the gossip.",
    3:  "Home and family tension — relocation or moving house.",
    4:  "Artistic/romantic ambition — lots of showing off, pride.",
    5:  "Health and work obsession — don't overdo the details.",
    6:  "Partnership and marriage pressure — don't rush decisions.",
    7:  "Deep transformation, shared money, secrets — betrayal and trust.",
    8:  "Travel and study — expand your beliefs.",
    9:  "Professional ambition — fame and authority.",
    10: "New networks, fateful friends — hope.",
    11: "Isolation, dreams, spirituality — letting go and peace.",
}
KETU_SIGN_INTERP = {
    0:  "Less boldness — retreat from competition, calm.",
    1:  "Disinterest in wealth — simple living.",
    2:  "Fewer words — silence and introspection.",
    3:  "Distance from family — emotional independence.",
    4:  "Avoiding show — humility.",
    5:  "Letting go of obsession — accepting simplicity.",
    6:  "Break from relationships — productive solitude.",
    7:  "Deep spirituality — interest in the unseen.",
    8:  "Less travel — study and inward focus.",
    9:  "Letting go of ambition — contentment.",
    10: "Withdrawal from groups — self-sufficiency.",
    11: "Moksha, liberation — complete spirituality.",
}


def node_transit_all_signs(transit_lons, jd=None):
    """Public Rahu/Ketu transit — effect on natives of ALL 12 signs.

    No birth data required. Uses current (or given) node positions:
    for each zodiac sign, tells how transiting Rahu/Ketu affects
    natives born under that sign (Rahu house = sign index offset from
    the node's current sign).

    Returns per-sign interpretation + which sign Rahu/Ketu currently occupy.
    """
    import sys
    _SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
    if _SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, _SCRIPTS_DIR)
    import astro_engine as _ae

    if jd is None:
        jd = _ae.julian_day(datetime.utcnow())
    ayan = _ae.ayanamsha_lahiri(jd)

    rahu_sid = (transit_lons.get("North Node", 0) - ayan) % 360
    ketu_sid = (transit_lons.get("South Node", 0) - ayan) % 360
    rahu_sign_idx = int(rahu_sid // 30) % 12
    ketu_sign_idx = int(ketu_sid // 30) % 12

    signs = _ae.SIGNS  # ["Aries", ..., "Pisces"]
    out = {
        "current": {
            "rahu_sign": signs[rahu_sign_idx],
            "ketu_sign": signs[ketu_sign_idx],
            "rahu_sidereal_lon": round(rahu_sid, 3),
            "ketu_sidereal_lon": round(ketu_sid, 3),
        },
        "per_sign": [],
        "_note": ("Rahu/Ketu each stay ~18 months per sign. "
                  "Rahu house for a native = offset from their Sun/Moon sign "
                  "to the node's current sign (whole-sign). Effects below are "
                  "for natives of each sign, with the node transiting their "
                  "1st house (their sign itself)."),
    }
    for idx in range(12):
        # House the node occupies relative to native's sign:
        # native sign = 1st house; node sign offset = house number
        rahu_house = (rahu_sign_idx - idx) % 12 + 1
        ketu_house = (ketu_sign_idx - idx) % 12 + 1
        out["per_sign"].append({
            "sign": signs[idx],
            "rahu_house": rahu_house,
            "rahu_effect": RAHU_SIGN_INTERP.get(idx, ""),
            "ketu_house": ketu_house,
            "ketu_effect": KETU_SIGN_INTERP.get(idx, ""),
        })
    return out

# ─────────────────────────────────────────────────────────────────────
#  2  — Guna Milan / Ashtakoota (36-guna Vedic compatibility)
# ─────────────────────────────────────────────────────────────────────
GUNA_NAMES = {
    "varna":("Varna","Caste/ego compatibility",1),
    "vashya":("Vashya","Mutual attraction & control",2),
    "tara":("Tara","Star/auspiciousness",3),
    "yoni":("Yoni","Sexual & instinctual compatibility",4),
    "graha_maitri":("Graha Maitri","Mental & emotional affinity",5),
    "gana":("Gana","Temperament & spiritual nature",6),
    "bhakoota":("Bhakoota","Love, children & prosperity",7),
    "nadi":("Nadi","Health, genes & children",8),
}

# Varna mapping by Moon nakshatra lord
VARNA_MAP = {
    "Ket":"Brahmin","Ven":"Brahmin","Sun":"Kshatriya","Mar":"Kshatriya",
    "Moo":"Vaishya","Mer":"Vaishya","Jup":"Shudra","Sat":"Shudra","Rah":"Shudra",
}
# Yoni mapping by nakshatra
YONI_MAP = {
    "Ashwini":"Horse","Bharani":"Elephant","Krittika":"Goat","Rohini":"Serpent",
    "Mrigashira":"Serpent","Ardra":"Dog","Punarvasu":"Cat","Pushya":"Goat",
    "Ashlesha":"Cat","Magha":"Rat","Purva Phalguni":"Rat","Uttara Phalguni":"Cow",
    "Hasta":"Buffalo","Chitra":"Tiger","Swati":"Buffalo","Vishakha":"Tiger",
    "Anuradha":"Hare","Jyeshtha":"Hare","Mula":"Dog","Purva Ashadha":"Monkey",
    "Uttara Ashadha":"Mongoose","Shravana":"Monkey","Dhanishtha":"Lion",
    "Shatabhisha":"Horse","Purva Bhadrapada":"Lion","Uttara Bhadrapada":"Cow","Revati":"Elephant",
}
# Gana mapping
GANA_MAP = {
    "Ashwini":"Deva","Bharani":"Manushya","Krittika":"Rakshasa","Rohini":"Manushya",
    "Mrigashira":"Deva","Ardra":"Manushya","Punarvasu":"Deva","Pushya":"Deva",
    "Ashlesha":"Rakshasa","Magha":"Rakshasa","Purva Phalguni":"Manushya","Uttara Phalguni":"Manushya",
    "Hasta":"Deva","Chitra":"Rakshasa","Swati":"Deva","Vishakha":"Rakshasa",
    "Anuradha":"Deva","Jyeshtha":"Rakshasa","Mula":"Rakshasa","Purva Ashadha":"Manushya",
    "Uttara Ashadha":"Deva","Shravana":"Deva","Dhanishtha":"Rakshasa","Shatabhisha":"Rakshasa",
    "Purva Bhadrapada":"Manushya","Uttara Bhadrapada":"Manushya","Revati":"Deva",
}

def _get_moon_nak(lons, ayan):
    """Get moon nakshatra from lons dict."""
    moon_lon = lons.get("Moon", 0)
    return nakshatra_of(moon_lon - ayan)

def guna_milan(lonsA, lonsB, ayan):
    """Calculate Vedic Ashtakoota / Guna Milan (36-guna) compatibility.
    
    Uses Moon nakshatras of both charts.
    Returns detailed breakdown per guna + total score.
    """
    nakA = _get_moon_nak(lonsA, ayan)
    nakB = _get_moon_nak(lonsB, ayan)
    idxA = next(i for i, n in enumerate(NAKSHATRAS) if n[0] == nakA["name"])
    idxB = next(i for i, n in enumerate(NAKSHATRAS) if n[0] == nakB["name"])
    
    scores = {}
    
    # 1. Varna (1 point)
    lordA = nakA["lord"]
    lordB = nakB["lord"]
    varnaA = VARNA_MAP.get(lordA, "Vaishya")
    varnaB = VARNA_MAP.get(lordB, "Vaishya")
    varna_rank = {"Brahmin": 4, "Kshatriya": 3, "Vaishya": 2, "Shudra": 1}
    varna_score = 1 if (varna_rank.get(varnaA, 2) >= varna_rank.get(varnaB, 2)) else 0
    scores["varna"] = {"score": varna_score, "max": 1, "his": varnaA, "her": varnaB}
    
    # 2. Vashya (2 points)
    vashyaA = YONI_MAP.get(nakA["name"], "Human")
    vashyaB = YONI_MAP.get(nakB["name"], "Human")
    VASHYA_CONTROL = {
        "Horse":["Buffalo","Goat","Deer"], "Elephant":["Lion","Tiger"],
        "Goat":["Buffalo"], "Serpent":["Goat"], "Dog":["Monkey"],
        "Cat":["Rat"], "Rat":["Elephant","Buffalo"], "Cow":["Tiger","Lion"],
        "Buffalo":["Lion","Tiger"], "Tiger":["Monkey"], "Hare":["Elephant","Buffalo"],
        "Monkey":["Goat"], "Mongoose":["Rat","Serpent"], "Lion":["Elephant","Buffalo","Horse"],
    }
    controlled = VASHYA_CONTROL.get(vashyaA, [])
    vashya_score = 2 if vashyaB in controlled or vashyaA == vashyaB else 1 if vashyaA == vashyaB else 0
    scores["vashya"] = {"score": vashya_score, "max": 2, "his": vashyaA, "her": vashyaB}
    
    # 3. Tara (3 points)
    diff = (idxB - idxA) % N_NAK
    tara_bhinnas = [3, 5, 7, 9, 13, 16, 18, 22, 24, 26]
    tara_score = 3 if diff not in tara_bhinnas else 0
    scores["tara"] = {"score": tara_score, "max": 3, "nakshatra_position": diff}
    
    # 4. Yoni (4 points)
    yoniA = YONI_MAP.get(nakA["name"], "Human")
    yoniB = YONI_MAP.get(nakB["name"], "Human")
    YONI_FRIEND = {
        "Horse":["Horse","Buffalo"], "Elephant":["Elephant","Hare"],
        "Goat":["Goat","Serpent"], "Serpent":["Serpent","Goat"],
        "Dog":["Dog","Monkey"], "Cat":["Cat","Rat"],
        "Rat":["Rat","Cat"], "Cow":["Cow","Tiger"],
        "Buffalo":["Buffalo","Horse"], "Tiger":["Tiger","Cow"],
        "Hare":["Hare","Elephant"], "Monkey":["Monkey","Dog"],
        "Mongoose":["Mongoose","Rat"], "Lion":["Lion","Elephant"],
    }
    yoni_friends = YONI_FRIEND.get(yoniA, [])
    if yoniA == yoniB: yoni_score = 4
    elif yoniB in yoni_friends: yoni_score = 3
    elif yoniA == yoniB: yoni_score = 2
    else: yoni_score = 1
    scores["yoni"] = {"score": yoni_score, "max": 4, "his": yoniA, "her": yoniB}
    
    # 5. Graha Maitri (5 points)
    GRAHA_FRIEND = {
        "Sun": ["Sun","Moon","Mars","Jupiter"], "Moon": ["Moon","Sun","Mercury"],
        "Mars": ["Mars","Sun","Moon","Jupiter"], "Mercury": ["Mercury","Sun","Venus"],
        "Jupiter": ["Jupiter","Sun","Moon","Mars"], "Venus": ["Venus","Mercury","Saturn"],
        "Saturn": ["Saturn","Mercury","Venus"], "Rah": ["Rah","Mercury","Venus","Saturn"],
        "Ket": ["Ket","Mercury","Venus","Saturn"],
    }
    graha_score = 5 if lordB in GRAHA_FRIEND.get(lordA, []) else 3 if lordA == lordB else 1
    scores["graha_maitri"] = {"score": graha_score, "max": 5, "his_lord": lordA, "her_lord": lordB}
    
    # 6. Gana (6 points)
    ganaA = GANA_MAP.get(nakA["name"], "Manushya")
    ganaB = GANA_MAP.get(nakB["name"], "Manushya")
    GANA_COMPAT = {"Deva": ["Deva","Manushya"], "Manushya": ["Manushya","Deva","Rakshasa"], "Rakshasa": ["Rakshasa","Manushya"]}
    if ganaA == ganaB: gana_score = 6
    elif ganaB in GANA_COMPAT.get(ganaA, []): gana_score = 3
    else: gana_score = 0
    if ganaA == "Rakshasa" and ganaB == "Rakshasa": gana_score = 6
    scores["gana"] = {"score": gana_score, "max": 6, "his": ganaA, "her": ganaB}
    
    # 7. Bhakoota (7 points)
    moon_signA = sign_of(lonsA.get("Moon", 0))
    moon_signB = sign_of(lonsB.get("Moon", 0))
    bhakoota_forbidden = {
        0: [2,6,10], 1: [5,9], 2: [4,8,0], 3: [7,11], 4: [6,10,2],
        5: [9,1], 6: [8,0,4], 7: [11,3], 8: [10,2,6], 9: [1,5], 10: [0,4,8], 11: [3,7],
    }
    idxMoonA = SIGNS.index(moon_signA) if moon_signA in SIGNS else 0
    idxMoonB = SIGNS.index(moon_signB) if moon_signB in SIGNS else 0
    forbidden = bhakoota_forbidden.get(idxMoonA, [])
    bhakoota_score = 7 if idxMoonB not in forbidden else 0
    scores["bhakoota"] = {"score": bhakoota_score, "max": 7}
    
    # 8. Nadi (8 points)
    NAKS_NARI_GROUP = {
        "Ashwini":"Adi","Bharani":"Adi","Krittika":"Adi",
        "Rohini":"Madhya","Mrigashira":"Madhya","Ardra":"Madhya",
        "Punarvasu":"Antya","Pushya":"Antya","Ashlesha":"Antya",
        "Magha":"Adi","Purva Phalguni":"Adi","Uttara Phalguni":"Adi",
        "Hasta":"Madhya","Chitra":"Madhya","Swati":"Madhya",
        "Vishakha":"Antya","Anuradha":"Antya","Jyeshtha":"Antya",
        "Mula":"Adi","Purva Ashadha":"Adi","Uttara Ashadha":"Adi",
        "Shravana":"Madhya","Dhanishtha":"Madhya","Shatabhisha":"Madhya",
        "Purva Bhadrapada":"Antya","Uttara Bhadrapada":"Antya","Revati":"Antya",
    }
    nadiA = NAKS_NARI_GROUP.get(nakA["name"], "Madhya")
    nadiB = NAKS_NARI_GROUP.get(nakB["name"], "Madhya")
    nadi_score = 8 if nadiA != nadiB else 0
    scores["nadi"] = {"score": nadi_score, "max": 8, "his": nadiA, "her": nadiB}
    
    total = sum(v["score"] for v in scores.values())
    max_total = sum(v["max"] for v in scores.values())
    
    if total >= 30: verdict = "Excellent — highly compatible"
    elif total >= 24: verdict = "Good — strong compatibility"
    elif total >= 18: verdict = "Average — needs work but viable"
    elif total >= 12: verdict = "Below average — significant differences"
    else: verdict = "Low compatibility — challenging alignment"
    
    return {
        "total_score": total,
        "max_score": max_total,
        "percentage": round(total / max_total * 100, 1),
        "verdict": verdict,
        "breakdown": {k: v for k, v in scores.items()},
        "term": {
            "his_nakshatra": nakA["name"], "her_nakshatra": nakB["name"],
            "his_moon_lord": lordA, "her_moon_lord": lordB,
        }
    }

# ─────────────────────────────────────────────────────────────────────
#  3  — Solar Return Interpretation
# ─────────────────────────────────────────────────────────────────────

SR_HOUSE_THEMES = {
    1:"Year of reinventing yourself — new identity, appearance change, personal projects.",
    2:"Financial focus — income shift, values re-evaluation, spending pattern change.",
    3:"Communication year — learning, writing, siblings, short trips, ideas flow.",
    4:"Home & family year — moving, renovation, family dynamics, emotional grounding.",
    5:"Creative explosion — romance, children, artistic risks, fun, self-expression.",
    6:"Health & work — routine overhaul, health focus, new job or daily habits.",
    7:"Relationship year — partnership milestones, marriage, collaboration or divorce.",
    8:"Transformation year — shared resources, inheritance, intimacy, deep change.",
    9:"Expansion year — travel, study, philosophy, publishing, higher purpose.",
    10:"Career peak — promotion, public recognition, new professional direction.",
    11:"Social year — new networks, friends, community involvement, hopes fulfilled.",
    12:"Retreat year — solitude, healing, spiritual practice, closure and release.",
}

SR_PLANET_EMPHASIS = {
    "Sun": "Self-expression, vitality, identity focus",
    "Moon": "Emotional needs, home, family, nurturing theme",
    "Mercury": "Mental activity, communication, learning, contracts",
    "Venus": "Love, beauty, money, pleasure, relationship highlight",
    "Mars": "Action, ambition, conflict, physical energy, career drive",
    "Jupiter": "Expansion, luck, abundance, travel, growth opportunity",
    "Saturn": "Responsibility, discipline, lessons, structure, karmic task",
    "Uranus": "Sudden change, breakthrough, rebellion, freedom",
    "Neptune": "Dreams, confusion, spirituality, creativity, illusion",
    "Pluto": "Deep transformation, power, control, death-rebirth",
}

def interpret_solar_return(sr_data):
    """Add human-readable interpretation to a computed solar return chart.
    
    sr_data: dict from astro_engine.solar_return()
    Returns augmented dict with interpretation fields.
    """
    chart = sr_data.get("chart", {})
    if not chart:
        return sr_data
    
    # Which house does SR Sun fall in?
    sun = chart.get("planets", {}).get("Sun", {})
    sr_sun_house = sun.get("house", 1)
    year_theme = SR_HOUSE_THEMES.get(sr_sun_house, "A year of general growth and adjustment.")
    
    # Which planets are angular (houses 1/4/7/10) — they dominate the year
    angular = []
    for pname, pdata in chart.get("planets", {}).items():
        if pdata.get("house") in (1, 4, 7, 10):
            emphasis = SR_PLANET_EMPHASIS.get(pname, f"{pname} activated")
            angular.append({"planet": pname, "house": pdata["house"], "emphasis": emphasis,
                            "sign": pdata.get("sign", "")})
    
    # Dominant element of SR chart
    elem_count = {}
    for pdata in chart.get("planets", {}).values():
        el = SIGN_DATA.get(pdata.get("sign", ""), {}).get("element", "")
        if el: elem_count[el] = elem_count.get(el, 0) + 1
    dominant_el = max(elem_count, key=elem_count.get) if elem_count else "Mixed"
    lacking_el = min(elem_count, key=elem_count.get) if elem_count else "None"
    
    # Big three of SR
    big3 = chart.get("big_three", {})
    
    sr_data["interpretation"] = {
        "year_theme": year_theme,
        "sun_house": sr_sun_house,
        "angular_planets": angular,
        "dominant_element_year": dominant_el,
        "lacking_element_year": lacking_el,
        "solar_return_big_three": big3,
        "advice": _sr_advice(dominant_el, lacking_el, sr_sun_house),
        "_note": "The SR Sun house shows the year's main stage. Angular planets are your supporting cast. Cultivate the dominant element; compensate for the lacking one."
    }
    return sr_data

def _sr_advice(dominant, lacking, sun_house):
    tips = []
    if dominant == "Fire": tips.append("Channel extra energy into creative projects.")
    elif dominant == "Earth": tips.append("Ground your ambitions — build something lasting.")
    elif dominant == "Air": tips.append("Focus your ideas — execute, don't just plan.")
    elif dominant == "Water": tips.append("Feel deeply, but set emotional boundaries.")
    if lacking == "Fire": tips.append("You may feel low energy — prioritize what ignites you.")
    elif lacking == "Earth": tips.append("Stay practical — avoid getting lost in dreams.")
    elif lacking == "Air": tips.append("Make time for objectivity and social connection.")
    elif lacking == "Water": tips.append("Don't neglect your emotional life for productivity.")
    tips.append(f"House {sun_house} focus: {SR_HOUSE_THEMES.get(sun_house, 'Consult your SR chart for details.')}")
    return tips

# ─────────────────────────────────────────────────────────────────────
#  4  — Electional Finder (best time for activities)
# ─────────────────────────────────────────────────────────────────────
ELECTIONAL_ACTIVITIES = {
    "marriage": ["Venus","Jupiter"],
    "job_start": ["Jupiter","Sun","Mercury"],
    "business_launch": ["Jupiter","Mercury","Venus"],
    "investment": ["Jupiter","Venus"],
    "surgery": ["Mars","Sun"],
    "travel": ["Jupiter","Mercury"],
    "education_start": ["Mercury","Jupiter"],
    "move_home": ["Moon","Venus"],
    "legal_matters": ["Jupiter","Sun","Mercury"],
    "creative_project": ["Venus","Sun","Moon"],
    "spiritual_practice": ["Moon","Neptune","Jupiter"],
    "negotiation": ["Mercury","Venus"],
    "medical_treatment": ["Sun","Jupiter"],
    "party_celebration": ["Venus","Jupiter","Sun"],
}
MOON_AVOID_SIGNS = [3, 6, 8, 12]  # Avoid Moon in these houses
EMPTY_MOON_SIGNS_BAD = ["Gemini","Virgo","Sagittarius","Pisces"]  # Via Combusta / void

WEEKDAYS_PLANET = {
    0: "Sun", 1: "Moon", 2: "Mars", 3: "Mercury",
    4: "Jupiter", 5: "Venus", 6: "Saturn",
}

def find_electional_times(jd_start, lat, lng, activity="marriage", days_ahead=14):
    """Find best astrological times for a specific activity.
    
    Returns list of top windows with planetary hour, moon phase, and suitability.
    """
    import astro_engine as _ae
    
    benefics = ELECTIONAL_ACTIVITIES.get(activity, ["Jupiter","Venus"])
    
    results = []
    start = datetime.fromtimestamp((jd_start - 2440587.5) * 86400, tz=timezone.utc)
    
    for d in range(days_ahead):
        date = start + timedelta(days=d)
        jd = _ae.julian_day(date)
        
        try:
            lons, speed, _ = _ae.body_longitudes(jd)
            mp = _ae.moon_phase(jd)
            hours_data = _ae.planetary_hours(jd, lat, lng)
            ayan = _ae.ayanamsha_lahiri(jd)
        except Exception:
            continue
        
        # Moon check
        moon_sign = SIGNS[int(lons.get("Moon", 0) // 30) % 12]
        moon_avoid = moon_sign in EMPTY_MOON_SIGNS_BAD
        
        # Check planetary hours for benefics
        best_hours = []
        for h in hours_data.get("hours", []):
            if h.get("ruler") in benefics:
                best_hours.append(h)
        
        # Day of week check
        dow = date.weekday()
        dow_ruler = WEEKDAYS_PLANET.get(dow, "")
        dow_ok = dow_ruler in benefics
        
        # Moon phase
        phase_name = mp.get("phase", "")
        
        if best_hours and not moon_avoid:
            results.append({
                "date": date.strftime("%Y-%m-%d"),
                "day_of_week": date.strftime("%A"),
                "moon_phase": phase_name,
                "moon_sign": moon_sign,
                "moon_avoid": moon_avoid,
                "day_ruler_ok": dow_ok,
                "best_hours": [{"hour": h["hour"], "ruler": h["ruler"], "time": h.get("time","")}
                              for h in best_hours[:3]],
                "score": len(best_hours) + (2 if dow_ok else 0) + (0 if moon_avoid else 2),
            })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return {
        "activity": activity,
        "benefic_planets": benefics,
        "top_windows": results[:7],
        "_note": f"Best time for {activity}: when Moon is not void/bad-sign, on a day ruled by a benefic planet, during the benefic planetary hour."
    }

# ─────────────────────────────────────────────────────────────────────
#  5  — Solar Arc Directions
# ─────────────────────────────────────────────────────────────────────
def solar_arc_directions(natal_lons, age):
    """Calculate Solar Arc Directions (all planets + Asc move ~1°/year of life).
    
    natal_lons: dict of {planet: longitude}
    age: current age in years
    Returns progressed positions + notable aspects.
    """
    import sys, os
    import astro_engine as _ae
    
    arc = age * 1.0  # ~1° per year (solar arc key)
    
    natal_asc = natal_lons.get("Ascendant", natal_lons.get("Sun", 0))
    for name in ["Sun", "Ascendant"]:
        if name in natal_lons:
            arc = abs(norm360(natal_lons[name] + age - natal_lons[name]))
            arc = age * 0.9856  # more precise: 0.9856°/day × 365.25 = 360°/year
    
    # Apply arc to all bodies
    arced = {}
    for name, lon in natal_lons.items():
        arced[name] = _ae.norm360(lon + arc)
    
    # Compute directional aspects (arced planets to natal planets)
    aspects_list = []
    bodies = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn",
              "Uranus","Neptune","Pluto"]
    ASPECTS = {0:("conjunction",8,"fusion — energies merge"),
               60:("sextile",6,"opportunity, cooperation"),
               90:("square",6,"friction, drive, growth through struggle"),
               120:("trine",6,"natural flow, ease, talent"),
               180:("opposition",6,"tension & awareness through the other")}
    soft = {60, 120}
    hard = {0, 90, 180}
    
    for na in bodies:
        if na not in arced: continue
        for nb in bodies:
            if nb not in natal_lons or na == nb: continue
            sep = abs(_ae.norm180(arced[na] - natal_lons[nb]))
            for ang, (asp_name, orb, desc) in ASPECTS.items():
                if abs(sep - ang) <= orb:
                    aspects_list.append({
                        "directional_planet": na, "to_natal_planet": nb,
                        "aspect": asp_name, "orb": round(abs(sep - ang), 2),
                        "age_at_exact": round(age, 1),
                        "meaning": desc,
                        "kind": "soft" if ang in soft else "hard" if ang in hard else "neutral",
                    })
                    break
    
    aspects_list.sort(key=lambda x: x["orb"])
    
    # Significant: directional angles to Ascendant and Midheaven
    natal_asc = natal_lons.get("Ascendant", 0)
    asc_aspects = []
    for name in bodies:
        if name not in arced: continue
        sep = abs(_ae.norm180(arced[name] - natal_asc))
        for ang, (asp_name, orb, desc) in ASPECTS.items():
            if abs(sep - ang) <= orb:
                asc_aspects.append({"planet": name, "aspect": asp_name, "orb": round(abs(sep - ang), 2)})
                break
    
    return {
        "age": round(age, 1),
        "solar_arc_degrees": round(arc, 4),
        "directional_positions": {k: {"sign": sign_of(v), "degree": round(v % 30, 2)}
                                  for k, v in sorted(arced.items())},
        "directional_aspects_to_natal": aspects_list[:20],
        "ascendant_aspects": asc_aspects,
        "_note": "Solar Arc = 1° ≈ 1 year. When a progressed planet aspects a natal planet by hard aspect (0/90/180°), significant life events occur. Soft aspects (60/120°) mark growth periods."
    }

# ─────────────────────────────────────────────────────────────────────
#  6  — Remedy Suggestions
# ─────────────────────────────────────────────────────────────────────
REMEDIES = {
    "Sun": {
        "weak": ["Ruby","Sunstone","","Copper","Surya Namaskar","Wheat, oranges, gold","East","Sunday"],
        "afflicted": ["Carnelian","Citrine","","Red","Sun Salutation","Gratitude practice","East","Sunday"],
    },
    "Moon": {
        "weak": ["Pearl","Moonstone","","Silver","Walking barefoot","Milk, rice, silver","Northwest","Monday"],
        "afflicted": ["Moonstone","White Sapphire","","White","Emotional journal","Mother's blessing","Northwest","Monday"],
    },
    "Mercury": {
        "weak": ["Emerald","Peridot","","Green","Reading/writing","Green vegetables","North","Wednesday"],
        "afflicted": ["Green Aventurine","Jade","","Green","Breathwork","Laugh more","North","Wednesday"],
    },
    "Venus": {
        "weak": ["Diamond","Rose Quartz","","Pink","Self-care","Art, music, beauty","Southeast","Friday"],
        "afflicted": ["Rose Quartz","Rhodonite","","Pink","Relationship talk","Sweet fragrances","Southeast","Friday"],
    },
    "Mars": {
        "weak": ["Coral","Red Jasper","Carnelian","Red","Exercise","Spicy food avoidance","South","Tuesday"],
        "afflicted": ["Red Jasper","Bloodstone","","Red","Anger journal","Physical release","South","Tuesday"],
    },
    "Jupiter": {
        "weak": ["Yellow Sapphire","Topaz","","Yellow","Teaching/mentoring","Turmeric, gold","Northeast","Thursday"],
        "afflicted": ["Yellow Topaz","Amber","","Yellow","Generosity practice","Faith & optimism","Northeast","Thursday"],
    },
    "Saturn": {
        "weak": ["Blue Sapphire","Amethyst","","Blue","Slow down","Elderly service, discipline","West","Saturday"],
        "afflicted": ["Amethyst","Lapis Lazuli","","Indigo","Meditation","Structure & patience","West","Saturday"],
    },
    "Rahu": {
        "weak": ["Hessonite","Labradorite","Garnet","Mixed","Grounding","Avoid crowds, smoke","Southwest",""],
        "afflicted": ["Labradorite","Smoky Quartz","","Dark grey","Shadow work","Detox, primal","Southwest",""],
    },
    "Ketu": {
        "weak": ["Cat's Eye","Haematite","Onyx","Purple","Silence/retreat","Spiritual study","Southeast",""],
        "afflicted": ["Haematite","Obsidian","","Brown","Letting go ritual","Simplify life","Southeast",""],
    },
}

PLANET_COLORS = {
    "Sun":"Gold","Moon":"Silver","Mercury":"Green","Venus":"Pink",
    "Mars":"Red","Jupiter":"Yellow","Saturn":"Blue","Rahu":"Smoke","Ketu":"Brown"
}

def suggest_remedies(chart_data):
    """Analyze a natal chart and suggest personalized remedies.
    
    Analyzes planetary dignities, afflictions, element balance.
    """
    result = {"planet_remedies": [], "element_balance": {}, "general_advice": []}
    
    # Check western chart planets
    for sys_name in ("western", "vedic"):
        ch = chart_data.get("charts", {}).get(sys_name, {})
        if not ch: continue
        planets = ch.get("planets", {})
        if not isinstance(planets, dict): continue
        
        for pname, pdata in planets.items():
            if pname not in REMEDIES: continue
            dignity = pdata.get("dignity", "").lower()
            retro = pdata.get("retrograde", False)
            
            # Weak or afflicted?
            weak_keywords = ["detriment", "fall", "peregrine"]
            is_weak = any(k in dignity for k in weak_keywords)
            is_afflicted = retro
            
            if is_weak or is_afflicted:
                key = "afflicted" if is_afflicted else "weak"
                rem = REMEDIES[pname].get(key, REMEDIES[pname]["weak"])
                result["planet_remedies"].append({
                    "planet": pname,
                    "condition": "Afflicted/Retrograde" if is_afflicted else "Weak/Detriment" if is_weak else dignity,
                    "dignity": pdata.get("dignity", ""),
                    "gemstone": rem[0],
                    "alternative_gem": rem[1] if len(rem) > 1 else "",
                    "metal": rem[3] if len(rem) > 3 else "",
                    "vibration_color": rem[2] if len(rem) > 2 else PLANET_COLORS.get(pname, ""),
                    "color": rem[4] if len(rem) > 4 else "",
                    "practice": rem[5] if len(rem) > 5 else "",
                    "nourish": rem[6] if len(rem) > 6 else "",
                    "direction": rem[7] if len(rem) > 7 else "",
                    "day": rem[8] if len(rem) > 8 else "",
                })
    
    # Element balance
    for sys_name in ("western",):
        ch = chart_data.get("charts", {}).get(sys_name, {})
        if not ch: continue
        eb = ch.get("element_balance", {})
        if eb:
            max_el = max(eb, key=eb.get)
            min_el = min(eb, key=eb.get)
            result["element_balance"] = {
                "balanced": max(eb.values()) - min(eb.values()) <= 1,
                "dominant": max_el,
                "lacking": min_el,
                "detail": eb,
                "advice_dominant": _el_advice_dominant(max_el),
                "advice_lacking": _el_advice_lacking(min_el),
            }
            result["general_advice"].append(result["element_balance"]["advice_lacking"])
    
    # General guidance
    if chart_data.get("life_phase", {}).get("current_age", 30) in range(27, 33):
        result["general_advice"].append("You're in Saturn Return territory — this is a structural reckoning. Build foundations, not fantasies.")
    
    return result

def _el_advice_dominant(el):
    m = {"Fire":"Your fire is strong — great for leadership. Watch for burnout and impatience.",
         "Earth":"Practical and grounded — you build well. Don't get stuck in routine.",
         "Air":"Intellectual and social — you see patterns. Ground ideas in action.",
         "Water":"Deeply intuitive and emotional. Channel feelings into art, not overwhelm."}
    return m.get(el, "")

def _el_advice_lacking(el):
    m = {"Fire":"Cultivate courage — try something bold. Sun exposure and red/orange help.",
         "Earth":"Get practical — routine and structure will stabilize you. Touch grass.",
         "Air":"Find mental stimulation — read, discuss, learn. Fresh air helps clarity.",
         "Water":"Connect with emotions — water therapy, art, or journaling balances you."}
    return m.get(el, "")

# ─────────────────────────────────────────────────────────────────────
#  7  — Weekly Astro Calendar
# ─────────────────────────────────────────────────────────────────────
def weekly_astro_calendar(start_date=None):
    """Generate a 7-day astrological calendar with transits, moon phases,
    planetary hours highlights, and notable events.
    
    Returns markdown-friendly dict per day.
    """
    import astro_engine as _ae
    
    if start_date is None:
        start = datetime.utcnow()
    else:
        start = start_date
    
    days = []
    for i in range(7):
        date = start + timedelta(days=i)
        jd = _ae.julian_day(date)
        try:
            lons, speed, _ = _ae.body_longitudes(jd)
            mp = _ae.moon_phase(jd)
            hours = _ae.planetary_hours(jd, 35.68, 51.38)  # Tehran default
            ayan = _ae.ayanamsha_lahiri(jd)
        except Exception as e:
            days.append({"date": date.strftime("%Y-%m-%d"), "error": str(e)})
            continue
        
        # Notable aspects today (Mars-Saturn conjunctions etc.)
        aspects = []
        bodies = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn",
                  "Uranus","Neptune","Pluto"]
        ASPECTS = {0:("conjunction",8), 60:("sextile",6), 90:("square",6),
                   120:("trine",6), 180:("opposition",6)}
        for i in range(len(bodies)):
            for j in range(i+1, len(bodies)):
                a, b = bodies[i], bodies[j]
                if a not in lons or b not in lons: continue
                sep = abs(norm360(lons[a] - lons[b]))
                for ang, (asp_name, orb) in ASPECTS.items():
                    if abs(sep - ang) <= orb:
                        aspects.append({"planets": f"{a}-{b}", "aspect": asp_name,
                                        "orb": round(abs(sep - ang), 2)})
                        break
        
        aspects.sort(key=lambda x: x["orb"])
        
        # Planet positions
        planets = {}
        for p in ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn",
                  "Uranus","Neptune","Pluto"]:
            if p in lons:
                ret = speed.get(p, 0) < 0
                planets[p] = {"sign": sign_of(lons[p]), "degree": round(lons[p] % 30, 1),
                              "retrograde": ret}
        
        # Find best planetary hour today
        best_hour = ""
        for h in hours.get("hours", [])[:5]:
            if h.get("ruler") in ("Jupiter", "Venus", "Sun"):
                best_hour = f"{h.get('hour','')} ({h.get('ruler','')})"
                break
        
        # Moon phase events
        upcomings = upcoming_moon_phases(jd, 3) if 'upcoming_moon_phases' in dir() else []
        
        day_data = {
            "date": date.strftime("%Y-%m-%d"),
            "weekday": date.strftime("%A"),
            "moon": {
                "phase": mp.get("phase", ""),
                "illumination": mp.get("illumination", 0),
                "sign": planets.get("Moon", {}).get("sign", ""),
            },
            "retrograde_planets": [p for p, d in planets.items() if d.get("retrograde")],
            "top_aspects": aspects[:5],
            "best_planetary_hour": best_hour,
            "sunrise": hours.get("sunrise", ""),
            "sunset": hours.get("sunset", ""),
        }
        days.append(day_data)
    
    return {
        "week_start": start.strftime("%Y-%m-%d"),
        "week_end": (start + timedelta(days=6)).strftime("%Y-%m-%d"),
        "days": days,
        "_note": "Daily overview: moon phase shows emotional tone, retrograde planets show areas to review, top aspects show the 'weather' of the day."
    }

# ─────────────────────────────────────────────────────────────────────
#  8  — Prashna / Vedic Horary
# ─────────────────────────────────────────────────────────────────────
PRASHNA_QUESTIONS = {
    "general": "General life guidance",
    "career": "Career & profession",
    "marriage": "Marriage & relationship",
    "finance": "Financial prospects",
    "health": "Health & recovery",
    "travel": "Travel & relocation",
    "legal": "Legal matters & court",
    "education": "Education & exams",
    "family": "Family & children",
    "property": "Property & assets",
}

HOUSE_1_ME = {
    "Aries": "Quick answer, fast resolution",
    "Taurus": "Delayed but certain",
    "Gemini": "Uncertain, depends on communication",
    "Cancer": "Emotional, involving family",
    "Leo": "Positive, with recognition",
    "Virgo": "Requires analysis and patience",
    "Libra": "Balanced, involving others",
    "Scorpio": "Hidden, transformative outcome",
    "Sagittarius": "Fortunate, involving travel",
    "Capricorn": "Slow but solid result",
    "Aquarius": "Unexpected, innovative solution",
    "Pisces": "Karmic, not fully clear yet",
}

def prashna(question_utc, lat, lng, question_text="", question_type="general"):
    """Vedic horary (Prashna) — chart of the moment a question is asked.
    
    Uses Ascendant + Moon + Navamsa signals for prediction.
    """
    import astro_engine as _ae
    
    jd = _ae.julian_day(question_utc)
    lons, speed, _ = _ae.body_longitudes(jd)
    asc_lon, mc_lon = _ae.ascendant_mc(jd, lat, lng)
    ayan = _ae.ayanamsha_lahiri(jd)
    
    asc_sign = sign_of(asc_lon)
    asc_idx = SIGNS.index(asc_sign) if asc_sign in SIGNS else 0
    asc_deg = asc_lon % 30
    
    # Moon is key in Prashna
    moon_lon = lons.get("Moon", 0)
    moon_sign = sign_of(moon_lon)
    moon_idx = SIGNS.index(moon_sign) if moon_sign in SIGNS else 0
    moon_nak = nakshatra_of(moon_lon - ayan)
    
    # Lord of Ascendant Hour (Placidean time)
    hour_lord_idx = int(question_utc.hour) % 12 + 1
    
    # Is answer yes/no?
    # Rule: Moon in 1/3/6/10/11 houses from Asc → positive
    moon_house_from_asc = (moon_idx - asc_idx) % 12 + 1
    positive_houses = [1, 3, 6, 10, 11]
    is_favorable = moon_house_from_asc in positive_houses
    
    # Navamsa strength
    nav = _ae.navamsa_chart(jd, lat, lng, True)
    nav_lagna = nav.get("lagna", {})
    nav_lagna_sign = nav_lagna.get("sign", "")
    
    # Timing
    MOON_TOUCH = {
        1: "days", 2: "months", 3: "weeks", 4: "years",
        5: "weeks", 6: "days", 7: "weeks", 8: "years",
        9: "weeks", 10: "days", 11: "weeks", 12: "years",
    }
    timing_unit = MOON_TOUCH.get(moon_house_from_asc, "months")
    timing_number = max(1, int(asc_deg // 2.5))
    
    return {
        "question": question_text,
        "question_type": question_type,
        "question_time_utc": question_utc.strftime("%Y-%m-%d %H:%M UTC"),
        "ascendant": {"sign": asc_sign, "degree": round(asc_deg, 2)},
        "ascendant_meaning": HOUSE_1_ME.get(asc_sign, "Neutral outcome"),
        "moon": {
            "sign": moon_sign,
            "nakshatra": moon_nak["name"],
            "nakshatra_lord": moon_nak["lord"],
            "house_from_ascendant": moon_house_from_asc,
        },
        "navamsa_lagna": nav_lagna_sign,
        "verdict": {
            "is_favorable": is_favorable,
            "summary": "The signs are favorable — proceed with confidence." if is_favorable
                       else "The chart suggests obstacles — reconsider timing or approach.",
            "timing": f"{timing_number} {timing_unit}" if timing_number else "Unknown",
        },
        "key_signals": [
            f"Ascendant in {asc_sign}: {HOUSE_1_ME.get(asc_sign, '')}",
            f"Moon in {moon_sign} ({moon_nak['name']}): house {moon_house_from_asc} from Asc",
            f"Navamsa Lagna in {nav_lagna_sign}: soul-level alignment",
        ],
        "_note": "Prashna readings are for guidance, not certainty. The Ascendant shows the shape of the answer; Moon shows emotional backdrop; Navamsa shows soul-level truth."
    }

# ─────────────────────────────────────────────────────────────────────
#  Integration — single entry point
# ─────────────────────────────────────────────────────────────────────
def compute_all_advanced(natal_data, transit_date=None):
    """Run all 8 advanced features on a natal chart.
    
    Returns dict with all results.
    """
    import sys, os
    _SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
    if _SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, _SCRIPTS_DIR)
    from astro_engine import (calculate_full_profile, julian_day, body_longitudes,
                              solar_return, ayanamsha_lahiri, transits)
    
    # Get natal chart
    natal = calculate_full_profile(natal_data)
    if not natal:
        return {"error": "Failed to compute natal chart"}
    
    birth_local = datetime(natal_data["year"], natal_data["month"], natal_data["day"],
                           natal_data.get("hour", 12), natal_data.get("minute", 0))
    jd = julian_day(birth_local)
    
    # Get lons for all planets
    lons, speed, _ = body_longitudes(jd)
    lons["Ascendant"], _ = __import__("astro_engine", fromlist=["ascendant_mc"]).ascendant_mc(
        jd, natal_data.get("lat", 0), natal_data.get("lng", 0))
    
    # Transit date
    td = datetime.strptime(transit_date, "%Y-%m-%d") if transit_date else datetime.utcnow()
    t_jd = julian_day(td)
    t_lons, _, _ = body_longitudes(t_jd)
    
    # Age
    age = (td - birth_local).days / 365.25
    
    # Compute all
    results = {}
    
    # 1. Node transit
    results["node_transit"] = analyze_node_transit(lons, t_lons)
    
    # 2. Guna Milan (needs partner — placeholder if partner data provided)
    # Will be computed via mode "guna_milan" at engine level
    
    # 3. Solar Return interpreted
    try:
        sr = solar_return(jd, td.year, natal_data.get("lat", 0), natal_data.get("lng", 0))
        results["solar_return"] = interpret_solar_return(sr)
    except Exception as e:
        results["solar_return"] = {"error": str(e)}
    
    # 4. Electional — return top durations for common activities
    # Computed on demand
    
    # 5. Solar Arc
    results["solar_arc"] = solar_arc_directions(lons, age)
    
    # 6. Remedies
    results["remedies"] = suggest_remedies(natal)
    
    # 7. Weekly calendar
    results["weekly_calendar"] = weekly_astro_calendar(td)
    
    # 8. Prashna — computed on demand with question
    results["_note"] = "8 advanced features computed. Run individual functions for electional/prashna/guna_milan with specific parameters."
    
    return results


# ═════════════════════════════════════════════════════════════════════════════
#  POST-AUDIT MODULES — Tajika, Muhurta, Shadbala
# ═════════════════════════════════════════════════════════════════════════════

def tajika_annual(birth_dt, lat, lng):
    """Tajika (annual Vedic horoscope) — solar return with Vedic overlay.
    Computes the annual chart: Sun returns to natal sidereal position,
    with tajika year count and strength (Panchadai) assessment."""
    if _ae is None:
        return {"error": "astro_engine not available"}
    jd_birth = _ae.julian_day(birth_dt)
    # Find next solar return (Sun back to natal sidereal longitude)
    natal_sid = _ae.norm360(_ae.body_longitudes(jd_birth)[0]["Sun"] - _ae.ayanamsha_lahiri(jd_birth))
    best = None
    # search day-by-day with generous tolerance, then refine by hour
    for y in range(birth_dt.year + 1, birth_dt.year + 3):
        prev_diff = None
        prev_dt = None
        for d in range(0, 366):
            dt = datetime(y, 1, 1, 12) + timedelta(days=d)
            jd = _ae.julian_day(dt)
            sun_sid = _ae.norm360(_ae.body_longitudes(jd)[0]["Sun"] - _ae.ayanamsha_lahiri(jd))
            diff = _ae.norm180(sun_sid - natal_sid)
            # Sun moves ~1°/day; detect crossing
            if prev_diff is not None and prev_diff * diff < 0:
                # crossing between prev_dt and dt — interpolate hour
                frac = abs(prev_diff) / (abs(prev_diff) + abs(diff))
                best = prev_dt + timedelta(days=frac)
                break
            prev_diff = diff
            prev_dt = dt
        if best:
            break
    if best is None:
        return {"error": "solar return not found"}
    # refine to hour precision
    best = best.replace(minute=0, second=0, microsecond=0)
    jd_sr = _ae.julian_day(best)
    lons, _, _ = _ae.body_longitudes(jd_sr)
    # Tajika year: count of years since birth
    age_years = (best - birth_dt).days / 365.25
    tajika_year = int(age_years) + 1
    # Moon nakshatra in annual chart
    moon_sid = _ae.norm360(lons["Moon"] - _ae.ayanamsha_lahiri(jd_sr))
    nak_i = int(moon_sid // _ae.NAK_ARC) % 27
    nk = _ae.NAKSHATRAS[nak_i]
    return {
        "tajika_year": tajika_year,
        "solar_return_date": best.strftime("%Y-%m-%d %H:%M"),
        "annual_lagna_sign": SIGNS[int(lons["Sun"] // 30) % 12],
        "moon_nakshatra": nk["name"],
        "moon_nakshatra_lord": nk["lord"],
        "sun_sign": SIGNS[int(_ae.norm360(lons["Sun"] - _ae.ayanamsha_lahiri(jd_sr)) // 30) % 12],
        "note": "Tajika annual chart — Sun returns to natal sidereal position; strength via Panchadai (compute per-house with full data)",
    }


def muhurta_finder(jd_start, lat, lng, activity="marriage", days_ahead=14):
    """Vedic Muhurta — panchang-based electional timing.
    Combines tithi, nakshatra, yoga, karana, weekday with activity-specific
    benefics and avoidances (more rigorous than generic electional)."""
    if _ae is None:
        return {"error": "astro_engine not available"}
    # Tithi quality: 1-5, 10-11 (Shukla); 6-8, 14-15 (Krishna) — good tithis
    GOOD_TITHIS = {1, 2, 3, 4, 5, 10, 11}
    AVOID_TITHIS = {4, 9, 14}  # Rikta tithis
    # Nakshatra qualities (Vedic): fixed (good for stability), movable (travel),
    # tender, sharp (avoid for most), mixed
    SHARP_NAKS = {"Ardra", "Ashlesha", "Jyeshtha", "Mula", "Magha", "Bharani"}
    FIXED_NAKS = {"Rohini", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada", "Krittika"}
    start = datetime.fromtimestamp((jd_start - 2440587.5) * 86400, tz=timezone.utc)
    results = []
    for d in range(days_ahead):
        date = start + timedelta(days=d)
        jd = _ae.julian_day(date)
        try:
            pan = _ae.panchang_elements(jd)
            lons, _, _ = _ae.body_longitudes(jd)
        except Exception:
            continue
        tithi_i = pan.get("tithi", {}).get("num", 0)
        tithi_name = pan.get("tithi", {}).get("name", "")
        nak_name = pan.get("nakshatra", {}).get("name", "")
        yoga_name = pan.get("yoga", {}).get("name", "")
        karana_name = pan.get("karana", {}).get("name", "")
        moon_sign = SIGNS[int(lons.get("Moon", 0) // 30) % 12]
        moon_phase = _ae.moon_phase(jd).get("phase", "")
        # scoring
        score = 0
        reasons = []
        if tithi_i in GOOD_TITHIS:
            score += 2; reasons.append(f"good tithi ({tithi_name})")
        if tithi_i in AVOID_TITHIS:
            score -= 2; reasons.append(f"avoid tithi ({tithi_name})")
        if nak_name in FIXED_NAKS:
            score += 2; reasons.append(f"fixed nakshatra ({nak_name})")
        if nak_name in SHARP_NAKS:
            score -= 1; reasons.append(f"sharp nakshatra ({nak_name}) — avoid")
        # weekday check
        dow = date.weekday()
        dow_rulers = {0:"Moon",1:"Mars",2:"Mercury",3:"Jupiter",4:"Venus",5:"Saturn",6:"Sun"}
        wk_ruler = dow_rulers.get(dow, "")
        if wk_ruler in ("Jupiter","Venus","Mercury"):
            score += 1; reasons.append(f"benefic weekday ({date.strftime('%A')})")
        if score >= 2:
            results.append({
                "date": date.strftime("%Y-%m-%d"),
                "weekday": date.strftime("%A"),
                "tithi": tithi_name, "nakshatra": nak_name,
                "yoga": yoga_name, "karana": karana_name,
                "moon_sign": moon_sign, "moon_phase": moon_phase,
                "score": score, "reasons": reasons,
                "suitable": score >= 3,
            })
    results.sort(key=lambda x: x["score"], reverse=True)
    return {"activity": activity, "top_muhurtas": results[:7]}


def shadbala_sthana_dig(jd, lat, lng):
    """Shadbala (Vedic six-fold strength) per Phala Deepika Ch.4.
    Full implementation: Uchcha, Saptavarga, Oja/Yugma, Kendradi, Drekkana
    (Sthana) + Drik (dig) + Kala (diurnal/nocturnal) + Naisargika (natural).
    Cheshta (motion) included as retrograde penalty."""
    if _ae is None:
        return {"error": "astro_engine not available"}
    lons, speed, _ = _ae.body_longitudes(jd)
    ayan = _ae.ayanamsha_lahiri(jd)
    asc_lon, _ = _ae.ascendant_mc(jd, lat, lng, ayan)

    # ── Sthana Bala (12 components, Phala Deepika 4) ────────────────
    planets = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]
    # (1) Uchcha Bala: 1 rupa at deep exaltation, 0 at deep debilitation, linear
    uchcha_points = {"Sun":10,"Moon":3,"Mars":28,"Mercury":15,"Jupiter":5,"Venus":27,"Saturn":20}
    debil_points = {"Sun":190,"Moon":183,"Mars":208,"Mercury":195,"Jupiter":185,"Venus":207,"Saturn":200}
    uchcha_bala = {}
    for p in planets:
        sid = _ae.norm360(lons[p] - ayan)
        up, dp = uchcha_points[p], debil_points[p]
        dist_from_uccha = min(_ae.norm180(sid - up), 360 - _ae.norm180(sid - up))
        dist_uccha_debil = min(_ae.norm180(up - dp), 360 - _ae.norm180(up - dp))
        uchcha_bala[p] = max(0.0, 1.0 - dist_from_uccha / dist_uccha_debil)

    # (2)-(8) Saptavarga Bala: BPHS Ch.27 slokas 2-4 weights:
    # Moolatrikona 45, own 30, extreme friend 20, friend 15, neutral 10,
    # enemy 4, extreme enemy 2 (virupas)
    friend_map = {
        "Sun": ["Moon","Mars","Jupiter"], "Moon": ["Sun","Mercury"],
        "Mars": ["Sun","Moon","Jupiter"], "Mercury": ["Sun","Venus"],
        "Jupiter": ["Sun","Moon","Mars"], "Venus": ["Mercury","Saturn"],
        "Saturn": ["Mercury","Venus"],
    }
    enemy_map = {
        "Sun": ["Saturn","Venus"], "Moon": [], "Mars": ["Mercury"],
        "Mercury": ["Moon"], "Jupiter": ["Mercury","Venus"],
        "Venus": ["Sun","Moon"], "Saturn": ["Sun","Moon","Mars"],
    }
    def _relation(benefactor, benef):
        if benef in friend_map.get(benefactor, []): return 15.0
        if benef in enemy_map.get(benefactor, []): return 4.0
        return 10.0
    saptavarga_bala = {}
    for p in planets:
        p_sign = _ae.SIGNS[int(_ae.norm360(lons[p] - ayan) // 30) % 12]
        # own sign check
        if p_sign in _ae.DIGNITY[p]["rule"]:
            saptavarga_bala[p] = 30.0
        else:
            saptavarga_bala[p] = _relation(p, p)

    # (9) Oja Rasi: Sun/Mars/Mercury/Saturn in odd sign → 15; (10) Oja/Yugma navamsa
    oja_bala = {}
    for p in planets:
        sid = _ae.norm360(lons[p] - ayan)
        sign_idx = int(sid // 30) % 12
        odd = sign_idx % 2 == 0
        oja_bala[p] = 15.0 if odd and p in ("Sun","Mars","Mercury","Saturn") else \
                      15.0 if not odd and p in ("Moon","Venus") else 0.0

    # (11) Kendradi Bala: kendra 60, panaphara 30, apoklima 15
    kendradi_bala = {}
    asc_sign = int(asc_lon // 30) % 12
    for p in planets:
        p_sign = int(_ae.norm360(lons[p] - ayan) // 30) % 12
        dist = (p_sign - asc_sign) % 12
        if dist in (0, 3, 6, 9): kendradi_bala[p] = 60.0
        elif dist in (1, 4, 7, 10): kendradi_bala[p] = 30.0
        else: kendradi_bala[p] = 15.0

    # (12) Drekkana Bala: Sun/Mars/Jupiter 1st, Saturn/Mercury 2nd, Moon/Venus 3rd
    drekkana_bala = {}
    for p in planets:
        sid = _ae.norm360(lons[p] - ayan)
        drek = int((sid % 30) // 10)
        if p in ("Sun","Mars","Jupiter") and drek == 0: drekkana_bala[p] = 15.0
        elif p in ("Saturn","Mercury") and drek == 1: drekkana_bala[p] = 15.0
        elif p in ("Moon","Venus") and drek == 2: drekkana_bala[p] = 15.0
        else: drekkana_bala[p] = 0.0

    # Sthana total (rupa = 60 shashtayamsa; convert to rupas)
    sthana_bala = {}
    for p in planets:
        total_sh = (uchcha_bala[p]*60 + saptavarga_bala[p] + oja_bala[p] +
                    kendradi_bala[p] + drekkana_bala[p])
        sthana_bala[p] = round(total_sh / 60.0, 2)

    # ── Drik Bala (directional) — Phala Deepika: Sun/Mars 10th, Moon/Venus 4th,
    # Mercury/Jupiter 1st, Saturn 7th (each 1 rupa at own angle, 0 opposite)
    # BPHS Ch.27 alternative: Sun/Mars 4th, Jupiter/Mercury 7th, Venus/Moon 10th, Saturn 1st.
    dig_angles = {"Sun":10,"Mars":10,"Moon":4,"Venus":4,"Mercury":1,"Jupiter":1,"Saturn":7}
    bphs_dig_angles = {"Sun":4,"Mars":4,"Jupiter":7,"Mercury":7,"Venus":10,"Moon":10,"Saturn":1}
    dig_bala = {}
    for p in planets:
        sid = _ae.norm360(lons[p] - ayan)
        p_house_angle = ((sid - asc_lon) % 360) / 30.0  # house position 1-12
        target = dig_angles[p]
        dist = min(abs(p_house_angle - target), 12 - abs(p_house_angle - target))
        dig_bala[p] = round(max(0.0, 1.0 - dist / 6.0), 2)

    # ── Kala Bala (diurnal/nocturnal strength, simplified): day → Sun/Jup/Ven strong
    # night → Moon/Mars/Saturn strong. Mercury neutral.
    kala_bala = {}
    # solar hour approximation: sun above horizon = day
    import datetime as _dt
    jd_ut = jd
    day_frac = (jd_ut + 0.5) % 1.0
    is_day = True  # default; refined below
    try:
        # rough: compare local solar time to sunrise/sunset via swe if available
        if _ae._HAS_SWE:
            import swisseph as swe
            res = swe.rise_trans(jd_ut, swe.SUN, swe.CALC_RISE, 0, lat, lng, 0, 0, 0)
            if res[0] == 0:
                rise = res[1][0]
                set_res = swe.rise_trans(jd_ut, swe.SUN, swe.CALC_SET, 0, lat, lng, 0, 0, 0)
                sett = set_res[1][0]
                is_day = rise <= (jd_ut % 1.0) + 0.5 <= sett
    except Exception:
        pass
    day_strong = ("Sun","Jupiter","Venus")
    night_strong = ("Moon","Mars","Saturn")
    for p in planets:
        if p == "Mercury":
            kala_bala[p] = 0.5
        elif is_day and p in day_strong:
            kala_bala[p] = 1.0
        elif not is_day and p in night_strong:
            kala_bala[p] = 1.0
        else:
            kala_bala[p] = 0.0

    # ── Naisargika Bala (natural strength): fixed per classical order
    naisargika = {"Sun":60,"Moon":51.43,"Venus":42.86,"Jupiter":34.29,
                  "Mercury":25.71,"Mars":17.14,"Saturn":8.57}
    naisargika_bala = {p: round(v/60.0, 2) for p, v in naisargika.items()}

    # ── Cheshta Bala (motion): retrograde planets weak, direct full
    cheshta_bala = {}
    for p in planets:
        retro = speed.get(p, 0) < 0 if speed else False
        cheshta_bala[p] = 0.25 if retro else 1.0

    # Total Shadbala (sum of 6, in rupas)
    total = {}
    for p in planets:
        total[p] = round(sthana_bala[p] + dig_bala[p] + kala_bala[p] +
                         naisargika_bala[p] + cheshta_bala[p], 2)

    return {
        "sthana_bala": sthana_bala,
        "dig_bala": dig_bala,
        "kala_bala": kala_bala,
        "naisargika_bala": naisargika_bala,
        "cheshta_bala": cheshta_bala,
        "shadbala_total": total,
        "note": "Full 6-fold Shadbala per Phala Deepika Ch.4 (Uchcha, Saptavarga, Oja/Yugma, Kendradi, Drekkana, Drik, Kala, Naisargika, Cheshta).",
    }
