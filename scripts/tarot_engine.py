#!/usr/bin/env python3
"""Canonical Rider-Waite-Smith (RWS) 78-Card Tarot Suite & Astrological Spreads Engine.
Based on:
- Arthur Edward Waite, The Pictorial Key to the Tarot (1910)
- Golden Dawn Book T (Elemental Dignities & Decan Mapping)
- Mary K. Greer, Tarot for Your Self (Soul & Personality Cards)
Zero dependencies — pure Python.
"""

from typing import Dict, List, Optional, Tuple, Any
import hashlib
import json

# =====================================================================
# 1. 22 MAJOR ARCANA (0 to 21)
# =====================================================================

MAJOR_ARCANA_RWS = {
    0: {"name": "The Fool", "number": 0, "hebrew": "Aleph", "element": "Air", "astrology": "Air (Uranus)",
        "upright": "Pure potential, leap of faith, spontaneous beginnings, original innocence",
        "reversed": "Recklessness, foolish risk, paralysis, naive vulnerability",
        "symbolism": "White rose of purity, cliff edge of manifest leap, small companion dog, yellow sky of divine intellect"},
    1: {"name": "The Magician", "number": 1, "hebrew": "Beth", "element": "Air", "astrology": "Mercury",
        "upright": "Conscious will, focused manifestation, channeling above to below, mastery",
        "reversed": "Manipulation, trickery, abuse of talent, misdirected power",
        "symbolism": "Lemniscate crown, right hand wand to sky / left to earth, table with 4 elemental tools"},
    2: {"name": "The High Priestess", "number": 2, "hebrew": "Gimel", "element": "Water", "astrology": "Moon",
        "upright": "Intuition, hidden wisdom, unconscious mind, esoteric mysteries",
        "reversed": "Secrets revealed, repressed intuition, superficiality, emotional coldness",
        "symbolism": "Boaz and Jachin pillars, pomegranate veil, crescent moon at feet, partially hidden scroll"},
    3: {"name": "The Empress", "number": 3, "hebrew": "Daleth", "element": "Earth", "astrology": "Venus",
        "upright": "Fertility, creative abundance, nature's nurture, sensory pleasure",
        "reversed": "Creative block, smothering overprotection, barrenness, material dependency",
        "symbolism": "Crown of 12 twelve-pointed stars, wheat field, shield with Venus glyph, flowing waterfall"},
    4: {"name": "The Emperor", "number": 4, "hebrew": "Heh", "element": "Fire", "astrology": "Aries",
        "upright": "Structural authority, temporal sovereignty, paternal order, stability",
        "reversed": "Tyranny, rigidity, loss of control, failed leadership, dogma",
        "symbolism": "Cubic stone throne with 4 ram heads, armor under red robe, ankh scepter and globe"},
    5: {"name": "The Hierophant", "number": 5, "hebrew": "Vav", "element": "Earth", "astrology": "Taurus",
        "upright": "Tradition, spiritual orthodoxy, mentorship, institutional doctrine",
        "reversed": "Blind conformity, dogmatic rigidity, spiritual hypocrisy, rebellion",
        "symbolism": "Triple papal crown, triple cross staff, crossed keys of St. Peter, two tonsured priests"},
    6: {"name": "The Lovers", "number": 6, "hebrew": "Zayin", "element": "Air", "astrology": "Gemini",
        "upright": "Union of opposites, moral choice, values alignment, soul partnership",
        "reversed": "Disharmony, values clash, destructive choices, fractured bond",
        "symbolism": "Archangel Raphael blessing Adam & Eve, Tree of Life & Tree of Knowledge with serpent"},
    7: {"name": "The Chariot", "number": 7, "hebrew": "Cheth", "element": "Water", "astrology": "Cancer",
        "upright": "Triumph of disciplined will, directed momentum, conquest over duality",
        "reversed": "Aggression, loss of control, lack of direction, hubris",
        "symbolism": "Black & white sphinxes in repose, starry blue canopy on 4 pillars, armor with lunar crescents"},
    8: {"name": "Strength", "number": 8, "hebrew": "Teth", "element": "Fire", "astrology": "Leo",
        "upright": "Compassion over animal instinct, inner fortitude, gentle mastery",
        "reversed": "Raw animal fury, self-doubt, cowardice, abuse of brute power",
        "symbolism": "Woman in white crowned with lemniscate gently closing lion's jaw, floral garlands"},
    9: {"name": "The Hermit", "number": 9, "hebrew": "Yod", "element": "Earth", "astrology": "Virgo",
        "upright": "Soul-searching, solitude, inner illumination, guiding wisdom",
        "reversed": "Isolation, lonely alienation, stubborn withdrawal, refusing wise counsel",
        "symbolism": "Cloaked sage on snowy summit, lantern containing 6-pointed Seal of Solomon, staff"},
    10: {"name": "Wheel of Fortune", "number": 10, "hebrew": "Kaph", "element": "Fire", "astrology": "Jupiter",
         "upright": "Karmic cycles, turning points, sudden opportunity, cosmic law",
         "reversed": "Bad luck, resistance to inevitable change, downward spiral",
         "symbolism": "YHVH & TARO/ROTA wheel, 4 winged creatures reading books in corners, Hermanubis and Typhon"},
    11: {"name": "Justice", "number": 11, "hebrew": "Lamed", "element": "Air", "astrology": "Libra",
         "upright": "Karmic cause and effect, objective truth, ethical clarity, legal equity",
         "reversed": "Injustice, dishonesty, bias, dodging accountability, legal defeat",
         "symbolism": "Upright double-edged sword in right hand, balanced golden scales in left, stone pillars"},
    12: {"name": "The Hanged Man", "number": 12, "hebrew": "Mem", "element": "Water", "astrology": "Water (Neptune)",
         "upright": "Surrender, spiritual pause, paradox, voluntary sacrifice, new perspective",
         "reversed": "Useless martyrdom, ego resistance, stagnation, materialistic blindness",
         "symbolism": "Suspended upside-down by one ankle from living Tau cross, free leg forming 4, golden halo"},
    13: {"name": "Death", "number": 13, "hebrew": "Nun", "element": "Water", "astrology": "Scorpio",
         "upright": "Radical metamorphosis, profound ending, clearing the old, transition",
         "reversed": "Fear of change, clinging to dead forms, stagnation, delayed transition",
         "symbolism": "Skeletal knight in black armor on white horse, 5-petaled Mystic Rose banner, rising sun"},
    14: {"name": "Temperance", "number": 14, "hebrew": "Samekh", "element": "Fire", "astrology": "Sagittarius",
         "upright": "Alchemy, moderation, synthesis of extremes, patient healing",
         "reversed": "Imbalance, excess, clashing extremes, lack of harmony, haste",
         "symbolism": "Archangel pouring water between 2 golden chalices, one foot on earth / one in water, mountain path"},
    15: {"name": "The Devil", "number": 15, "hebrew": "Ayin", "element": "Earth", "astrology": "Capricorn",
         "upright": "Bondage to illusion, materialism, shadow self, unhealthy obsessions",
         "reversed": "Liberation, breaking chains, confronting the shadow, awakening",
         "symbolism": "Baphomet-like beast on half-cube altar, downward torch, male and female chained loosely"},
    16: {"name": "The Tower", "number": 16, "hebrew": "Peh", "element": "Fire", "astrology": "Mars",
         "upright": "Sudden collapse of false constructs, breakthrough via crisis, divine flash",
         "reversed": "Averting necessary breakdown, trapped in ruins, prolonged suffering",
         "symbolism": "Lightning bolt striking crown from stone tower, flames from windows, figures falling"},
    17: {"name": "The Star", "number": 17, "hebrew": "Tzaddi", "element": "Air", "astrology": "Aquarius",
         "upright": "Hope, spiritual renewal, sublime inspiration, peace, cosmic alignment",
         "reversed": "Despair, loss of faith, cynicism, ungrounded fantasy",
         "symbolism": "Naked maiden pouring water onto earth (5 streams) and pool, 8-pointed golden star with 7 smaller stars"},
    18: {"name": "The Moon", "number": 18, "hebrew": "Qoph", "element": "Water", "astrology": "Pisces",
         "upright": "Deep unconscious, deception, primal fear, psychic mirage, fluctuating moods",
         "reversed": "Truth unveiled, dispelling delusions, overcoming irrational terror",
         "symbolism": "Full moon shedding yods, dog & wolf howling, crayfish crawling from dark pool toward towers"},
    19: {"name": "The Sun", "number": 19, "hebrew": "Resh", "element": "Fire", "astrology": "Sun",
         "upright": "Radiant joy, conscious vitality, enlightenment, absolute triumph",
         "reversed": "Temporary eclipse of optimism, sunburn/conceit, delayed success",
         "symbolism": "Beaming sun with 21 rays, naked child with red feather riding white horse, 4 sunflowers"},
    20: {"name": "Judgement", "number": 20, "hebrew": "Shin", "element": "Fire", "astrology": "Fire (Pluto)",
         "upright": "Spiritual resurrection, awakening, higher calling, redemption",
         "reversed": "Self-doubt, ignoring calling, harsh self-criticism, fear of evaluation",
         "symbolism": "Archangel Gabriel sounding golden trumpet with cross banner, naked souls rising from sea graves"},
    21: {"name": "The World", "number": 21, "hebrew": "Tav", "element": "Earth", "astrology": "Saturn",
         "upright": "Completion of Great Work, cosmic integration, wholeness, liberation",
         "reversed": "Incompletion, lack of closure, shortcuts, delayed culmination",
         "symbolism": "Dancing figure draped in purple scarf with two wands, oval laurel wreath, 4 Cherubim in corners"}
}

# =====================================================================
# 2. 56 MINOR ARCANA (40 Pips + 16 Courts)
# =====================================================================

SUITS_ELEMENTS = {
    "Wands": "Fire",
    "Cups": "Water",
    "Swords": "Air",
    "Pentacles": "Earth"
}

MINOR_PIPS_RWS = {
    # ACES
    "Ace of Wands": {"suit": "Wands", "number": 1, "element": "Fire", "title": "Root of the Powers of Fire",
                     "upright": "Creative spark, primal inspiration, masculine initiative, drive", "reversed": "Lack of motivation, false start, burnout, creative block"},
    "Ace of Cups": {"suit": "Cups", "number": 1, "element": "Water", "title": "Root of the Powers of Water",
                    "upright": "Unconditional love, spiritual receptivity, emotional overflow", "reversed": "Emotional depletion, blocked heart, sorrow, suppressed intimacy"},
    "Ace of Swords": {"suit": "Swords", "number": 1, "element": "Air", "title": "Root of the Powers of Air",
                      "upright": "Mental clarity, radical truth, piercing intellect, breakthrough", "reversed": "Mental cruelty, confusion, misuse of authority, chaos"},
    "Ace of Pentacles": {"suit": "Pentacles", "number": 1, "element": "Earth", "title": "Root of the Powers of Earth",
                         "upright": "Tangible opportunity, material seed, prosperity, physical manifestation", "reversed": "Missed investment, greed, material instability, poor foundation"},

    # 36 DECAN PIPS (2-10)
    "2 of Wands": {"suit": "Wands", "number": 2, "decan": "Aries 1", "astrology": "Mars in Aries", "title": "Lord of Dominion",
                   "upright": "Strategic planning, commanding vision, world in hand", "reversed": "Hesitation, fear of unknown, bad planning"},
    "3 of Wands": {"suit": "Wands", "number": 3, "decan": "Aries 2", "astrology": "Sun in Aries", "title": "Lord of Established Strength",
                   "upright": "Enterprise underway, commerce, expansion, ships arriving", "reversed": "Logistics delays, frustration, dashed hopes"},
    "4 of Wands": {"suit": "Wands", "number": 4, "decan": "Aries 3", "astrology": "Venus in Aries", "title": "Lord of Perfected Work",
                   "upright": "Celebration, homecoming, harmony, community sanctuary", "reversed": "Transient joy, family tension, canceled gathering"},
    "5 of Wands": {"suit": "Wands", "number": 5, "decan": "Leo 1", "astrology": "Saturn in Leo", "title": "Lord of Strife",
                   "upright": "Competition, clashing egos, creative mock battle, friction", "reversed": "Harmony restored, conflict avoidance, malice"},
    "6 of Wands": {"suit": "Wands", "number": 6, "decan": "Leo 2", "astrology": "Jupiter in Leo", "title": "Lord of Victory",
                   "upright": "Public acclaim, triumph, recognition, riding in glory", "reversed": "Fall from grace, arrogance, denied recognition"},
    "7 of Wands": {"suit": "Wands", "number": 7, "decan": "Leo 3", "astrology": "Mars in Leo", "title": "Lord of Valour",
                   "upright": "Holding the high ground, defending position against odds", "reversed": "Overwhelmed, yielding ground, defensive exhaustion"},
    "8 of Wands": {"suit": "Wands", "number": 8, "decan": "Sagittarius 1", "astrology": "Mercury in Sagittarius", "title": "Lord of Swiftness",
                   "upright": "Rapid momentum, swift communication, speed, clear path", "reversed": "Delays, scattered haste, misdirected panic"},
    "9 of Wands": {"suit": "Wands", "number": 9, "decan": "Sagittarius 2", "astrology": "Moon in Sagittarius", "title": "Lord of Great Strength",
                   "upright": "Battle-tested resilience, final defensive boundary, grit", "reversed": "Paranoia, chronic defensiveness, giving up at the end"},
    "10 of Wands": {"suit": "Wands", "number": 10, "decan": "Sagittarius 3", "astrology": "Saturn in Sagittarius", "title": "Lord of Oppression",
                    "upright": "Crushing burden, overcommitment, exhaustion from duty", "reversed": "Dropping the load, delegating, burnout breakdown"},

    "2 of Cups": {"suit": "Cups", "number": 2, "decan": "Cancer 1", "astrology": "Venus in Cancer", "title": "Lord of Love",
                  "upright": "Soul union, mutual attraction, balanced partnership", "reversed": "Broken rapport, imbalance, miscommunication"},
    "3 of Cups": {"suit": "Cups", "number": 3, "decan": "Cancer 2", "astrology": "Mercury in Cancer", "title": "Lord of Abundance",
                  "upright": "Friendship, communal celebration, joy, creative harvest", "reversed": "Gossip, overindulgence, exclusion, third-party strain"},
    "4 of Cups": {"suit": "Cups", "number": 4, "decan": "Cancer 3", "astrology": "Moon in Cancer", "title": "Lord of Blended Pleasure",
                  "upright": "Apathy, emotional withdrawal, contemplation, boredom", "reversed": "Reawakening, seizing newly offered opportunities"},
    "5 of Cups": {"suit": "Cups", "number": 5, "decan": "Scorpio 1", "astrology": "Mars in Scorpio", "title": "Lord of Loss in Pleasure",
                  "upright": "Mourning spilled cups, emotional grief, remorse", "reversed": "Turning to remaining cups, acceptance, moving forward"},
    "6 of Cups": {"suit": "Cups", "number": 6, "decan": "Scorpio 2", "astrology": "Sun in Scorpio", "title": "Lord of Pleasure",
                  "upright": "Nostalgia, sweet childhood memories, innocent reunion", "reversed": "Living in the past, childish clinging, outgrowing roots"},
    "7 of Cups": {"suit": "Cups", "number": 7, "decan": "Scorpio 3", "astrology": "Venus in Scorpio", "title": "Lord of Illusionary Success",
                  "upright": "Illusions, daydreaming, paralyzing temptation, fantasies", "reversed": "Clarity of vision, dispelling fog, decisive focus"},
    "8 of Cups": {"suit": "Cups", "number": 8, "decan": "Pisces 1", "astrology": "Saturn in Pisces", "title": "Lord of Abandoned Success",
                  "upright": "Walking away from the unfulfilling, seeking higher truth", "reversed": "Inability to let go, aimless wandering, returning back"},
    "9 of Cups": {"suit": "Cups", "number": 9, "decan": "Pisces 2", "astrology": "Jupiter in Pisces", "title": "Lord of Material Happiness",
                  "upright": "Wish fulfillment, contentment, sensual satisfaction", "reversed": "Smug arrogance, overindulgence, hollow triumph"},
    "10 of Cups": {"suit": "Cups", "number": 10, "decan": "Pisces 3", "astrology": "Mars in Pisces", "title": "Lord of Perfected Success",
                   "upright": "Domestic bliss, enduring emotional harmony, family peace", "reversed": "Shattered household, family drama, superficial joy"},

    "2 of Swords": {"suit": "Swords", "number": 2, "decan": "Libra 1", "astrology": "Moon in Libra", "title": "Lord of Peace Restored",
                    "upright": "Stalemate, truce, blocked emotions, difficult balance", "reversed": "Stalemate broken, mask dropped, difficult choice made"},
    "3 of Swords": {"suit": "Swords", "number": 3, "decan": "Libra 2", "astrology": "Saturn in Libra", "title": "Lord of Sorrow",
                    "upright": "Heartbreak, piercing grief, painful truth, separation", "reversed": "Emotional healing, releasing old agony, reconciliation"},
    "4 of Swords": {"suit": "Swords", "number": 4, "decan": "Libra 3", "astrology": "Jupiter in Libra", "title": "Lord of Rest from Strife",
                    "upright": "Convalescence, retreat, mental sanctuary, quiet respite", "reversed": "Forced recovery, return to stress, restless mind"},
    "5 of Swords": {"suit": "Swords", "number": 5, "decan": "Aquarius 1", "astrology": "Venus in Aquarius", "title": "Lord of Defeat",
                    "upright": "Hollow victory, malicious conquest, gloating, betrayal", "reversed": "Reconciliation, ending toxic disputes, lingering spite"},
    "6 of Swords": {"suit": "Swords", "number": 6, "decan": "Aquarius 2", "astrology": "Mercury in Aquarius", "title": "Lord of Earned Success",
                    "upright": "Transition, passage to calm waters, guided recovery", "reversed": "Rough crossing, unresolved baggage, stalled retreat"},
    "7 of Swords": {"suit": "Swords", "number": 7, "decan": "Aquarius 3", "astrology": "Moon in Aquarius", "title": "Lord of Unstable Effort",
                    "upright": "Stealth, tactical cunning, strategic withdrawal, theft", "reversed": "Caught red-handed, confessions, cowardly surrender"},
    "8 of Swords": {"suit": "Swords", "number": 8, "decan": "Gemini 1", "astrology": "Jupiter in Gemini", "title": "Lord of Shortened Force",
                    "upright": "Self-imposed limits, mental paralysis, trapped feeling", "reversed": "Release, stepping out of mental cage, clarity"},
    "9 of Swords": {"suit": "Swords", "number": 9, "decan": "Gemini 2", "astrology": "Mars in Gemini", "title": "Lord of Despair and Cruelty",
                    "upright": "Nightmares, insomnia, acute psychological anguish, guilt", "reversed": "Healing from trauma, dawn of hope, recovery"},
    "10 of Swords": {"suit": "Swords", "number": 10, "decan": "Gemini 3", "astrology": "Sun in Gemini", "title": "Lord of Ruin",
                     "upright": "Absolute rock-bottom, defeat, inevitable ending, betrayal", "reversed": "Surviving the worst, inevitable recovery, regeneration"},

    "2 of Pentacles": {"suit": "Pentacles", "number": 2, "decan": "Capricorn 1", "astrology": "Jupiter in Capricorn", "title": "Lord of Harmonious Change",
                       "upright": "Juggling priorities, financial adaptability, agile flow", "reversed": "Overextended, chaotic finances, dropping the ball"},
    "3 of Pentacles": {"suit": "Pentacles", "number": 3, "decan": "Capricorn 2", "astrology": "Mars in Capricorn", "title": "Lord of Material Works",
                       "upright": "Collaborative mastery, architectural craft, teamwork", "reversed": "Ego clashes in team, poor craftsmanship, disruption"},
    "4 of Pentacles": {"suit": "Pentacles", "number": 4, "decan": "Capricorn 3", "astrology": "Sun in Capricorn", "title": "Lord of Earthly Power",
                       "upright": "Hoarding security, possessiveness, rigid boundary", "reversed": "Greed released, reckless expenditure, financial loss"},
    "5 of Pentacles": {"suit": "Pentacles", "number": 5, "decan": "Taurus 1", "astrology": "Mercury in Taurus", "title": "Lord of Material Trouble",
                       "upright": "Poverty, exclusion, financial hardship, spiritual chill", "reversed": "Recovery, shelter found, end of poverty trap"},
    "6 of Pentacles": {"suit": "Pentacles", "number": 6, "decan": "Taurus 2", "astrology": "Moon in Taurus", "title": "Lord of Material Success",
                       "upright": "Balanced charity, patronage, fair distribution of resources", "reversed": "Stinginess, debts, strings-attached philanthropy"},
    "7 of Pentacles": {"suit": "Pentacles", "number": 7, "decan": "Taurus 3", "astrology": "Saturn in Taurus", "title": "Lord of Success Unfulfilled",
                       "upright": "Assessment, patient investment, evaluating progress", "reversed": "Impatience, wasted effort, abandoning the crop"},
    "8 of Pentacles": {"suit": "Pentacles", "number": 8, "decan": "Virgo 1", "astrology": "Sun in Virgo", "title": "Lord of Prudence",
                       "upright": "Apprenticeship, craftsmanship, meticulous skill building", "reversed": "Shoddy work, lack of effort, tedious perfectionism"},
    "9 of Pentacles": {"suit": "Pentacles", "number": 9, "decan": "Virgo 2", "astrology": "Venus in Virgo", "title": "Lord of Material Gain",
                       "upright": "Solitary luxury, self-reliance, refinement, abundance", "reversed": "Financial dependency, isolation, superficial security"},
    "10 of Pentacles": {"suit": "Pentacles", "number": 10, "decan": "Virgo 3", "astrology": "Mercury in Virgo", "title": "Lord of Wealth",
                        "upright": "Generational legacy, ancestral wealth, established dynasty", "reversed": "Family disputes, loss of inheritance, broken estate"},
}

COURT_CARDS_RWS = {
    # Wands
    "King of Wands": {"suit": "Wands", "rank": "King", "element": "Fire of Fire", "astrology": "Cardinal Fire",
                      "upright": "Charismatic visionary, bold leader, inspiring trailblazer, decisive authority",
                      "reversed": "Impatient tyrant, ruthless egomaniac, hot-tempered dictator"},
    "Queen of Wands": {"suit": "Wands", "rank": "Queen", "element": "Water of Fire", "astrology": "Fixed Fire",
                       "upright": "Radiant self-assurance, warm hospitality, creative vitality, passionate independence",
                       "reversed": "Jealous drama-seeker, demanding, insecure, vindictive"},
    "Knight of Wands": {"suit": "Wands", "rank": "Knight", "element": "Air of Fire", "astrology": "Mutable Fire",
                        "upright": "Fearless pursuit of ambition, dashing explorer, rushing into action",
                        "reversed": "Reckless impulsiveness, aggressive show-off, abandoning projects halfway"},
    "Page of Wands": {"suit": "Wands", "rank": "Page", "element": "Earth of Fire", "astrology": "Earth of Fire",
                      "upright": "Curious explorer of ideas, passionate messenger, enthusiastic student",
                      "reversed": "Unfocused rebel, loud-mouthed braggart, easily discouraged"},

    # Cups
    "King of Cups": {"suit": "Cups", "rank": "King", "element": "Fire of Water", "astrology": "Cardinal Water",
                     "upright": "Emotional mastery, calm under pressure, compassionate diplomat, wise counselor",
                     "reversed": "Passive-aggressive manipulator, moody addict, repressed volatility"},
    "Queen of Cups": {"suit": "Cups", "rank": "Queen", "element": "Water of Water", "astrology": "Fixed Water",
                      "upright": "Clairvoyant empath, deep dreamer, loving healer, profound emotional wisdom",
                      "reversed": "Emotionally needy, codependent, drowning in irrational moodiness"},
    "Knight of Cups": {"suit": "Cups", "rank": "Knight", "element": "Air of Water", "astrology": "Mutable Water",
                       "upright": "Poet, romantic quester, bearer of peace and heartfelt invitations",
                       "reversed": "Manipulative seducer, delusional dreamer, unrealistic escapist"},
    "Page of Cups": {"suit": "Cups", "rank": "Page", "element": "Earth of Water", "astrology": "Earth of Water",
                     "upright": "Creative inspiration, unexpected intuitive messages, youthful open-heartedness",
                     "reversed": "Emotional immaturity, easily hurt, shallow daydreams"},

    # Swords
    "King of Swords": {"suit": "Swords", "rank": "King", "element": "Fire of Air", "astrology": "Cardinal Air",
                      "upright": "Uncompromising truth, intellectual clarity, objective law, ethical authority",
                      "reversed": "Cold-blooded tyrant, cynical bully, sadistic authoritarian"},
    "Queen of Swords": {"suit": "Swords", "rank": "Queen", "element": "Water of Air", "astrology": "Fixed Air",
                        "upright": "Sharp discernment, sorrow transformed into fierce wisdom, cutting through deceit",
                        "reversed": "Bitter cynic, spiteful critic, weaponized coldness"},
    "Knight of Swords": {"suit": "Swords", "rank": "Knight", "element": "Air of Air", "astrology": "Mutable Air",
                         "upright": "Lightning-fast intellect, charging directly into the storm for truth, fearless champion",
                         "reversed": "Reckless tactlessness, argumentative bully, destructive fanatic"},
    "Page of Swords": {"suit": "Swords", "rank": "Page", "element": "Earth of Air", "astrology": "Earth of Air",
                       "upright": "Mental curiosity, scouting for facts, alert researcher, vigilant guardian",
                       "reversed": "Deceitful spy, paranoid snoop, sharp-tongued gossip"},

    # Pentacles
    "King of Pentacles": {"suit": "Pentacles", "rank": "King", "element": "Fire of Earth", "astrology": "Cardinal Earth",
                          "upright": "Seasoned provider, financial tycoon, grounded stability, master of systems",
                          "reversed": "Corrupt materialist, greedy miser, obstinate hoarder"},
    "Queen of Pentacles": {"suit": "Pentacles", "rank": "Queen", "element": "Water of Earth", "astrology": "Fixed Earth",
                           "upright": "Nurturing abundance, practical healer, sensible hospitality, earthly prosperity",
                           "reversed": "Smothering anxiousness, financial neglect, materialistic pettiness"},
    "Knight of Pentacles": {"suit": "Pentacles", "rank": "Knight", "element": "Air of Earth", "astrology": "Mutable Earth",
                            "upright": "Unshakable work ethic, methodical progress, reliable guardian, enduring patience",
                            "reversed": "Stagnant workaholic, obstinate resistor of change, bone-idle sloth"},
    "Page of Pentacles": {"suit": "Pentacles", "rank": "Page", "element": "Earth of Earth", "astrology": "Earth of Earth",
                          "upright": "Studious apprentice, pragmatic beginner, planting seeds of wealth, focus on skill",
                          "reversed": "Lack of discipline, short-sighted carelessness, wasted talent"}
}

ALL_78_CARDS = {}
for num, data in MAJOR_ARCANA_RWS.items():
    ALL_78_CARDS[data["name"]] = {**data, "type": "Major Arcana"}
for name, data in MINOR_PIPS_RWS.items():
    ALL_78_CARDS[name] = {**data, "type": "Minor Arcana (Pip)"}
for name, data in COURT_CARDS_RWS.items():
    ALL_78_CARDS[name] = {**data, "type": "Minor Arcana (Court)"}

# =====================================================================
# 3. SPREAD & DIGNITY ENGINES
# =====================================================================

ELEMENT_RELATIONS = {
    ("Fire", "Air"): "Friendly / Mutually Supportive (Air feeds Fire)",
    ("Air", "Fire"): "Friendly / Mutually Supportive (Fire elevates Air)",
    ("Water", "Earth"): "Friendly / Mutually Supportive (Water nourishes Earth)",
    ("Earth", "Water"): "Friendly / Mutually Supportive (Earth shapes Water)",
    ("Fire", "Water"): "Hostile / Opposing (Water douses Fire)",
    ("Water", "Fire"): "Hostile / Opposing (Fire boils Water)",
    ("Air", "Earth"): "Hostile / Opposing (Air erodes Earth)",
    ("Earth", "Air"): "Hostile / Opposing (Earth resists Air)",
    ("Fire", "Earth"): "Neutral (Heat warms Earth)",
    ("Earth", "Fire"): "Neutral (Earth contains Fire)",
    ("Air", "Water"): "Neutral (Wind creates Waves)",
    ("Water", "Air"): "Neutral (Moisture humidifies Air)",
}

def evaluate_elemental_dignity(elem1: str, elem2: str) -> str:
    """Evaluate Golden Dawn Book T Elemental Dignity between two adjacent cards."""
    if elem1 == elem2:
        return "Strong Harmony (Same Element)"
    return ELEMENT_RELATIONS.get((elem1, elem2), "Neutral")

def calculate_greer_lifepath_suite(year: int, month: int, day: int, target_year: Optional[int] = None) -> Dict[str, Any]:
    """Calculate Mary K. Greer's Complete Karmic Lifepath Tarot Suite:
    1. Personality Card (Outer persona, life lesson)
    2. Soul Card (Core spiritual mission)
    3. Year Card (Theme of the target year)
    4. Shadow / Teacher Card (Hidden psychological blindspot & mentor archetype)
    """
    raw_sum = year + month + day
    p_base = sum(int(d) for d in str(raw_sum))
    if p_base > 22:
        p_card_num = sum(int(d) for d in str(p_base))
    else:
        p_card_num = p_base

    # Soul card derivation (Greer Rules)
    if p_card_num in range(1, 10):
        s_card_num = p_card_num # Unified Soul & Personality
    elif p_card_num == 19:
        s_card_num = 1 # 19 Sun -> 10 Wheel of Fortune -> 1 Magician triad
    elif p_card_num == 22:
        s_card_num = 4 # 22/0 Fool -> 4 Emperor
    else:
        s_card_num = sum(int(d) for d in str(p_card_num))

    # Shadow / Teacher Card: 22 - Personality Number (if p_card_num == 22/0, shadow is 22 Fool)
    shadow_num = (22 - p_card_num) if p_card_num not in (0, 22) else 22
    if shadow_num == 22:
        shadow_num = 0

    # Year Card
    curr_y = target_year if target_year else 2026
    y_sum = day + month + curr_y
    y_base = sum(int(d) for d in str(y_sum))
    if y_base > 22:
        year_card_num = sum(int(d) for d in str(y_base))
    else:
        year_card_num = y_base
    if year_card_num == 22:
        year_card_num = 0

    p_info = MAJOR_ARCANA_RWS.get(p_card_num, MAJOR_ARCANA_RWS[0])
    s_info = MAJOR_ARCANA_RWS.get(s_card_num, MAJOR_ARCANA_RWS[0])
    sh_info = MAJOR_ARCANA_RWS.get(shadow_num, MAJOR_ARCANA_RWS[0])
    yr_info = MAJOR_ARCANA_RWS.get(year_card_num, MAJOR_ARCANA_RWS[0])

    return {
        "birth_date": f"{year:04d}-{month:02d}-{day:02d}",
        "raw_birth_sum": raw_sum,
        "target_year": curr_y,
        "personality_card": {
            "number": p_card_num,
            "name": p_info["name"],
            "hebrew": p_info["hebrew"],
            "astrology": p_info["astrology"],
            "life_lesson": p_info["upright"]
        },
        "soul_card": {
            "number": s_card_num,
            "name": s_info["name"],
            "hebrew": s_info["hebrew"],
            "astrology": s_info["astrology"],
            "deep_calling": s_info["upright"]
        },
        "shadow_card": {
            "number": shadow_num,
            "name": sh_info["name"],
            "hebrew": sh_info["hebrew"],
            "astrology": sh_info["astrology"],
            "shadow_work_theme": sh_info["reversed"]
        },
        "year_card": {
            "year": curr_y,
            "number": year_card_num,
            "name": yr_info["name"],
            "hebrew": yr_info["hebrew"],
            "astrology": yr_info["astrology"],
            "annual_theme": yr_info["upright"]
        },
        "source": "Mary K. Greer, Tarot for Your Self (1984/2002)"
    }

def calculate_soul_and_personality_cards(year: int, month: int, day: int) -> Dict[str, Any]:
    """Backward-compatible wrapper for calculate_greer_lifepath_suite."""
    res = calculate_greer_lifepath_suite(year, month, day)
    return {
        "birth_date": res["birth_date"],
        "raw_birth_sum": res["raw_birth_sum"],
        "personality_card": res["personality_card"],
        "soul_card": res["soul_card"],
        "note": "Per Mary K. Greer (Tarot for Your Self): Personality card shows how you operate in the outer world; Soul card reveals your core spiritual purpose."
    }

CELTIC_CROSS_POSITIONS = {
    1: ("The Heart / Present", "Core essence of the situation, present state of consciousness"),
    2: ("The Cross / Obstacle", "The crossing energy, friction point, catalyst, or direct challenge"),
    3: ("The Root / Subconscious", "Underlying foundation, subconscious cause, deep historical origin"),
    4: ("The Past / Departing", "Recent events, fading influences, what is passing away"),
    5: ("The Crown / Aspiration", "Conscious goal, highest potential outcome, optimal focus"),
    6: ("The Near Future", "Next immediate development in the upcoming 1-3 months"),
    7: ("The Self / Internal Stance", "Querent's psychological posture, self-concept, personal agency"),
    8: ("The Environment / External", "External mirrors, family/work context, how others view you"),
    9: ("Hopes & Fears", "Secret aspirations, psychological projections, anxieties"),
    10: ("The Outcome / Culmination", "Final resolution if the current trajectory continues uninterrupted")
}

def generate_deterministic_draw(seed_str: str, count: int = 10) -> List[Tuple[str, bool]]:
    """Draw cards deterministically based on seed string (e.g. user question + birth data).
    Returns list of (card_name, is_reversed)."""
    h = hashlib.sha256(seed_str.encode("utf-8")).digest()
    card_names = list(ALL_78_CARDS.keys())
    # Deterministic shuffle via hash stream
    drawn = []
    available = list(card_names)
    for i in range(count):
        idx = (h[i * 2] * 256 + h[i * 2 + 1]) % len(available)
        card_name = available.pop(idx)
        # Reverse bit
        is_rev = bool(h[(i * 2 + 1) % len(h)] % 4 == 0) # 25% reversal probability
        drawn.append((card_name, is_rev))
    return drawn

def celtic_cross_reading(question: str, birth_data_seed: str, significator: Optional[str] = None) -> Dict[str, Any]:
    """Generate a canonical 10-card Celtic Cross Tarot Reading per Arthur Edward Waite (1910, Part III § 7).
    Includes Significator handling, 10 sequential stations, and central cross elemental tension.
    """
    seed = f"celtic_cross:{question}:{birth_data_seed}"
    cards_drawn = generate_deterministic_draw(seed, count=10)

    spread_cards = []
    for pos_num, (card_name, is_rev) in enumerate(cards_drawn, 1):
        pos_title, pos_meaning = CELTIC_CROSS_POSITIONS[pos_num]
        card_info = ALL_78_CARDS[card_name]
        orientation = "Reversed" if is_rev else "Upright"
        reading = card_info["reversed"] if is_rev else card_info["upright"]
        spread_cards.append({
            "position_number": pos_num,
            "position_name": pos_title,
            "position_context": pos_meaning,
            "card_name": card_name,
            "orientation": orientation,
            "card_type": card_info["type"],
            "astrology": card_info.get("astrology", card_info.get("element", "")),
            "reading": reading
        })

    # Central Cross Elemental Dignity (Card 1 & Card 2)
    e1 = ALL_78_CARDS[cards_drawn[0][0]].get("element", "Fire")
    e2 = ALL_78_CARDS[cards_drawn[1][0]].get("element", "Water")
    cross_dignity = evaluate_elemental_dignity(e1, e2)

    res = {
        "spread": "Canonical 10-Card Celtic Cross (RWS / Waite 1910)",
        "question": question,
        "central_cross_elemental_tension": cross_dignity,
        "cards": spread_cards,
        "synthesis": (
            f"Present state centers on {spread_cards[0]['card_name']} ({spread_cards[0]['orientation']}) "
            f"crossed by {spread_cards[1]['card_name']}. The subconscious foundation is rooted in "
            f"{spread_cards[2]['card_name']}, leading toward the ultimate culmination of {spread_cards[9]['card_name']}."
        )
    }
    if significator:
        res["significator"] = significator
    return res

def evaluate_triad_elemental_dignity(left_elem: str, center_elem: str, right_elem: str) -> Dict[str, Any]:
    """Evaluate Golden Dawn Book T Triad Elemental Dignities for 3-card spreads.
    Center card is the subject; Left & Right cards are modifying influences.
    """
    left_rel = evaluate_elemental_dignity(left_elem, center_elem)
    right_rel = evaluate_elemental_dignity(right_elem, center_elem)
    flank_rel = evaluate_elemental_dignity(left_elem, right_elem)

    # Calculate overall dignity score of center card
    # Friendly = +1, Harmony = +2, Neutral = 0, Hostile = -1
    def score_rel(rel_str: str) -> int:
        if "Harmony" in rel_str: return 2
        if "Friendly" in rel_str: return 1
        if "Hostile" in rel_str: return -1
        return 0

    total_score = score_rel(left_rel) + score_rel(right_rel)
    if total_score >= 2:
        status = "Strongly Dignified (Enhanced by supportive surroundings)"
    elif total_score == 1:
        status = "Well Dignified (Supported by surroundings)"
    elif total_score == 0:
        status = "Moderately Dignified / Balanced"
    elif total_score == -1:
        status = "Ill-Dignified (Weakened or challenged by surroundings)"
    else:
        status = "Severely Ill-Dignified (Hostile elemental clash on both sides)"

    return {
        "triad_elements": [left_elem, center_elem, right_elem],
        "left_to_center": left_rel,
        "right_to_center": right_rel,
        "flanking_interaction": flank_rel,
        "dignity_score": total_score,
        "center_status": status,
        "rule_source": "Golden Dawn Book T (Elemental Dignities)"
    }

def select_significator_card(age: int = 30, gender: str = "male", temperament: str = "air") -> Dict[str, Any]:
    """Select authentic Tarot Significator based on Arthur Edward Waite (1910, Part III § 7).
    - Male >= 40: King
    - Male < 40: Knight (in Waite 1910, Knight for mature / younger adult)
    - Female >= 40: Queen
    - Female < 40 / Youth: Page
    Suit by temperament/physical:
    - Fire (Wands): Fair, blond/auburn, energetic
    - Water (Cups): Light brown/fair, calm, artistic
    - Air (Swords): Dark hair, active, analytical/determined
    - Earth (Pentacles): Dark/black hair, swarthy, grounded, practical
    """
    gender_norm = gender.lower().strip()
    temp_norm = temperament.lower().strip()

    suit_map = {
        "fire": "Wands",
        "wands": "Wands",
        "water": "Cups",
        "cups": "Cups",
        "air": "Swords",
        "swords": "Swords",
        "earth": "Pentacles",
        "pentacles": "Pentacles"
    }
    suit = suit_map.get(temp_norm, "Wands")

    if gender_norm in ("male", "m", "man"):
        rank = "King" if age >= 40 else "Knight"
    elif gender_norm in ("female", "f", "woman"):
        rank = "Queen" if age >= 40 else "Page"
    else:
        rank = "Queen" if age >= 40 else "Knight"

    card_name = f"{rank} of {suit}"
    card_info = COURT_CARDS_RWS.get(card_name, COURT_CARDS_RWS["King of Wands"])

    return {
        "significator_card": card_name,
        "rank": rank,
        "suit": suit,
        "element": card_info["element"],
        "astrology": card_info["astrology"],
        "upright_meaning": card_info["upright"],
        "rule": "Arthur Edward Waite, Pictorial Key to the Tarot (1910, Part III § 7)"
    }

def decanic_natal_resonance(planets_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map Natal Planets/Ascendant in degrees to corresponding Tarot Decan Minor & Major Archetypes.
    Accepts planets_data like {"Sun": {"sign": "Leo", "degree": 14.5}, "Ascendant": {"sign": "Cancer", "degree": 5.2}}.
    """
    sign_decan_cards = {
        "Aries": ["2 of Wands", "3 of Wands", "4 of Wands"],
        "Taurus": ["5 of Pentacles", "6 of Pentacles", "7 of Pentacles"],
        "Gemini": ["8 of Swords", "9 of Swords", "10 of Swords"],
        "Cancer": ["2 of Cups", "3 of Cups", "4 of Cups"],
        "Leo": ["5 of Wands", "6 of Wands", "7 of Wands"],
        "Virgo": ["8 of Pentacles", "9 of Pentacles", "10 of Pentacles"],
        "Libra": ["2 of Swords", "3 of Swords", "4 of Swords"],
        "Scorpio": ["5 of Cups", "6 of Cups", "7 of Cups"],
        "Sagittarius": ["8 of Wands", "9 of Wands", "10 of Wands"],
        "Capricorn": ["2 of Pentacles", "3 of Pentacles", "4 of Pentacles"],
        "Aquarius": ["5 of Swords", "6 of Swords", "7 of Swords"],
        "Pisces": ["8 of Cups", "9 of Cups", "10 of Cups"]
    }

    sign_major_parent = {
        "Aries": "The Emperor", "Taurus": "The Hierophant", "Gemini": "The Lovers",
        "Cancer": "The Chariot", "Leo": "Strength", "Virgo": "The Hermit",
        "Libra": "Justice", "Scorpio": "Death", "Sagittarius": "Temperance",
        "Capricorn": "The Devil", "Aquarius": "The Star", "Pisces": "The Moon"
    }

    results = []
    for body_name, pos in planets_data.items():
        if not isinstance(pos, dict) or "sign" not in pos:
            continue
        sign = pos["sign"]
        deg = float(pos.get("degree", 0.0)) % 30.0
        decan_idx = min(2, int(deg // 10))

        decan_card_name = sign_decan_cards.get(sign, ["2 of Wands"])[decan_idx]
        card_info = MINOR_PIPS_RWS.get(decan_card_name, {})
        major_parent = sign_major_parent.get(sign, "The Fool")

        results.append({
            "celestial_body": body_name,
            "sign": sign,
            "degree": round(deg, 2),
            "decan": f"{sign} {decan_idx + 1}",
            "tarot_minor_card": decan_card_name,
            "title": card_info.get("title", ""),
            "chaldean_ruler": card_info.get("astrology", ""),
            "archetypal_major_parent": major_parent,
            "lived_archetype": card_info.get("upright", "")
        })

    return results

def three_card_reading(question: str, spread_type: str = "past_present_future", seed: str = "") -> Dict[str, Any]:
    """Generate a 3-Card Tarot Reading with Golden Dawn Triad Elemental Dignities."""
    type_map = {
        "past_present_future": ["Past Influences", "Present Moment", "Future Trajectory"],
        "situation_obstacle_advice": ["Current Situation", "Core Obstacle", "Actionable Guidance"],
        "mind_body_spirit": ["Mental Focus", "Physical / Action Reality", "Spiritual Calling"]
    }
    positions = type_map.get(spread_type, type_map["past_present_future"])
    draw = generate_deterministic_draw(f"3card:{spread_type}:{question}:{seed}", count=3)

    cards = []
    card_elements = []
    for pos_title, (c_name, is_rev) in zip(positions, draw):
        info = ALL_78_CARDS[c_name]
        orientation = "Reversed" if is_rev else "Upright"
        reading = info["reversed"] if is_rev else info["upright"]
        elem = info.get("element", "Fire")
        card_elements.append(elem)
        cards.append({
            "position": pos_title,
            "card_name": c_name,
            "orientation": orientation,
            "element": elem,
            "astrology": info.get("astrology", elem),
            "reading": reading
        })

    # Triad Elemental Dignity
    triad_dignity = evaluate_triad_elemental_dignity(card_elements[0], card_elements[1], card_elements[2])

    return {
        "spread": f"3-Card Spread ({spread_type.replace('_',' ').title()})",
        "question": question,
        "elemental_dignity_triad": triad_dignity,
        "cards": cards,
        "synthesis": f"{cards[0]['position']}: {cards[0]['card_name']} -> {cards[1]['position']}: {cards[1]['card_name']} -> {cards[2]['position']}: {cards[2]['card_name']}."
    }

def astrological_12_house_spread(seed_str: str) -> Dict[str, Any]:
    """Generate a 12-Card Astrological House Wheel Tarot Spread (Annual / General Life Overview)."""
    draw = generate_deterministic_draw(f"12house:{seed_str}", count=12)
    houses = []
    for hnum in range(1, 13):
        c_name, is_rev = draw[hnum - 1]
        info = ALL_78_CARDS[c_name]
        orientation = "Reversed" if is_rev else "Upright"
        reading = info["reversed"] if is_rev else info["upright"]
        houses.append({
            "house_number": hnum,
            "house_theme": f"House {hnum}",
            "card_name": c_name,
            "orientation": orientation,
            "astrology": info.get("astrology", info.get("element", "")),
            "reading": reading
        })

    return {
        "spread": "12-House Astrological Wheel Spread",
        "houses": houses,
        "note": "Each card governs one sector of life (1=Self, 2=Money, 7=Partnership, 10=Career...)."
    }
