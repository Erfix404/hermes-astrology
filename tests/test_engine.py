#!/usr/bin/env python3
"""Tests for hermes-astrology engine. Zero deps — stdlib unittest only."""
import json, os, sys, unittest
from datetime import datetime

_SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, _SCRIPTS)

import astro_engine as ae

# ── test data ─────────────────────────────────────────────────────────
BIRTH = {"year": 1995, "month": 4, "day": 15, "hour": 14, "minute": 30,
         "lat": 35.6892, "lng": 51.3890, "tz": "Asia/Tehran", "time_known": True}
BIRTH_WEST = {**BIRTH, "systems": ["western"]}
BIRTH_ALL = {**BIRTH, "systems": ["western", "vedic", "bazi"]}


def _sign_str(lon):
    s = ae.sign_of(lon)
    return s if isinstance(s, str) else s[0]


class TestJulianDay(unittest.TestCase):
    def test_jd_known_date(self):
        dt = datetime(2000, 1, 1, 12, 0)
        self.assertAlmostEqual(ae.julian_day(dt), 2451545.0, places=4)
    def test_jd_monotonic(self):
        self.assertLess(ae.julian_day(datetime(2000,1,1)),
                        ae.julian_day(datetime(2000,6,15)))


class TestSignOf(unittest.TestCase):
    def test_aries(self):   self.assertEqual(_sign_str(15), "Aries")
    def test_taurus(self):  self.assertEqual(_sign_str(45), "Taurus")
    def test_gemini(self):  self.assertEqual(_sign_str(75), "Gemini")
    def test_cancer(self):  self.assertEqual(_sign_str(100), "Cancer")
    def test_leo(self):     self.assertEqual(_sign_str(140), "Leo")
    def test_virgo(self):   self.assertEqual(_sign_str(170), "Virgo")
    def test_libra(self):   self.assertEqual(_sign_str(190), "Libra")
    def test_scorpio(self): self.assertEqual(_sign_str(220), "Scorpio")
    def test_sagitta(self): self.assertEqual(_sign_str(250), "Sagittarius")
    def test_capri(self):   self.assertEqual(_sign_str(280), "Capricorn")
    def test_aquarius(self):self.assertEqual(_sign_str(310), "Aquarius")
    def test_pisces(self):  self.assertEqual(_sign_str(345), "Pisces")
    def test_wrap(self):    self.assertEqual(_sign_str(360), "Aries")
    def test_zero(self):    self.assertEqual(_sign_str(0), "Aries")


class TestWesternChart(unittest.TestCase):
    data = ae.calculate_full_profile(BIRTH_WEST)
    def test_meta(self):        self.assertIn("_meta", self.data)
    def test_western_present(self): self.assertIn("western", self.data["charts"])
    def test_mode(self):        self.assertEqual(self.data["mode"], "natal")
    def test_planets_dict(self):
        pl = self.data["charts"]["western"]["planets"]
        self.assertIsInstance(pl, dict)
        self.assertGreaterEqual(len(pl), 10)
    def test_ascendant(self):
        self.assertIn("sign", self.data["charts"]["western"]["ascendant"])
    def test_midheaven(self):
        self.assertIn("sign", self.data["charts"]["western"]["midheaven"])
    def test_aspects(self):
        self.assertGreater(len(self.data["charts"]["western"]["aspects"]), 0)
    def test_elements(self):
        self.assertGreater(len(self.data["charts"]["western"]["element_balance"]), 0)
    def test_summary(self):     self.assertIn("summary", self.data)
    def test_engine_backend(self):
        self.assertIn(self.data["_meta"]["engine_backend"], {"builtin", "swisseph"})

    life_phase = ae.calculate_full_profile(BIRTH_WEST).get("life_phase", {})
    def test_life_phase(self):
        self.assertIn("current_age", self.life_phase)

    special = ae.calculate_full_profile(BIRTH_WEST)
    def test_special_points(self):
        self.assertIn("special_points", self.special)

    demo = ae._demo()
    def test_demo(self):
        self.assertIn("year", self.demo)


class TestVedicChart(unittest.TestCase):
    result = ae.calculate_full_profile({"systems": ["vedic"], **BIRTH})
    def test_vedic_present(self):
        self.assertIn("vedic", self.result["charts"])
    def test_lagna(self):
        self.assertIn("sign", self.result["charts"]["vedic"]["lagna"])
    def test_nakshatra(self):
        for p in self.result["charts"]["vedic"]["planets"].values():
            self.assertIn("nakshatra", p)
            break
    def test_planets_count(self):
        self.assertGreaterEqual(len(self.result["charts"]["vedic"]["planets"]), 9)


class TestBaZiChart(unittest.TestCase):
    result = ae.calculate_full_profile({"systems": ["bazi"], **BIRTH})
    def test_bazi_present(self):    self.assertIn("bazi", self.result["charts"])
    def test_day_master(self):      self.assertIn("day_master", self.result["charts"]["bazi"])
    def test_pillars(self):
        self.assertGreaterEqual(len(self.result["charts"]["bazi"]["four_pillars"]), 4)
    def test_luck_cycles(self):
        self.assertIn("luck_pillars", self.result["charts"]["bazi"])


class TestTransit(unittest.TestCase):
    result = ae.calculate_full_profile({**BIRTH, "systems": ["western"],
            "mode": "transit", "transit_date": "2026-07-30"})
    def test_mode(self):     self.assertEqual(self.result["mode"], "transit")
    def test_transits(self): self.assertIn("transits", self.result)


class TestMoonPhase(unittest.TestCase):
    def test_moon_phase(self):
        r = ae.calculate_full_profile({"mode": "moon_phase", "year":2026,"month":7,"day":30,
            "hour":0,"minute":0,"lat":0,"lng":0,"tz":"UTC","time_known":True,"systems":["western"]})
        mp = r["moon_phase"]
        self.assertIn("phase", mp)
        self.assertIn("illumination", mp)


class TestNumerology(unittest.TestCase):
    r = ae.calculate_full_profile({"mode":"numerology","year":1990,"month":6,"day":15,
        "hour":12,"minute":0,"lat":0,"lng":0,"tz":"UTC","time_known":False,"systems":["western"]})
    def test_life_path(self):   self.assertIn("life_path", self.r["numerology"])
    def test_personal_year(self): self.assertIn("personal_year", self.r["numerology"])


class TestPanchang(unittest.TestCase):
    def test_panchang(self):
        r = ae.calculate_full_profile({"mode":"panchang","year":2026,"month":7,"day":30,
            "hour":12,"minute":0,"lat":20,"lng":78,"tz":"UTC","time_known":True,"systems":["vedic"]})
        p = r["panchang"]
        for k in ("tithi","nakshatra","yoga","karana"):
            with self.subTest(key=k): self.assertIn(k, p)


class TestAspectPatterns(unittest.TestCase):
    def _mkdict(self, *lons):
        names = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"]
        return {names[i]: lons[i] if i < len(lons) else 0 for i in range(len(lons))}
    def test_grand_trine(self):
        names = [p["name"] for p in ae.detect_aspect_patterns(self._mkdict(10,130,250))]
        self.assertIn("Grand Trine", names)
    def test_t_square(self):
        names = [p["name"] for p in ae.detect_aspect_patterns(self._mkdict(0,180,90))]
        self.assertIn("T-Square", names)
    def test_empty(self):
        self.assertEqual(len(ae.detect_aspect_patterns(self._mkdict(10,47,93,200,312))), 0)
    def test_grand_cross(self):
        names = [p["name"] for p in ae.detect_aspect_patterns(self._mkdict(0,180,90,270))]
        self.assertIn("Grand Cross", names)


class TestSynastry(unittest.TestCase):
    def test_synastry(self):
        jd_a = ae.julian_day(datetime(1995,4,15,11,0))
        jd_b = ae.julian_day(datetime(1993,8,22,6,30))
        syn = ae.synastry(jd_a, jd_b)
        self.assertIn("inter_aspects", syn)
        self.assertGreater(len(syn["inter_aspects"]), 0)


class TestCompatibility(unittest.TestCase):
    def test_compatibility(self):
        jd_a = ae.julian_day(datetime(1995,4,15,11,0))
        jd_b = ae.julian_day(datetime(1993,8,22,6,30))
        s = ae.compatibility_score(jd_a, jd_b)
        self.assertIn("overall_score", s)
        self.assertGreaterEqual(s["overall_score"], 0)
        self.assertLessEqual(s["overall_score"], 100)
        for k in ("romantic","emotional","intellectual","physical","spiritual"):
            with self.subTest(key=k): self.assertIn(k, s["breakdown"])


class TestAyanamsha(unittest.TestCase):
    def test_lahiri_positive(self):
        a = ae.ayanamsha_lahiri(ae.julian_day(datetime(2000,1,1)))
        self.assertGreater(a, 20); self.assertLess(a, 26)
    def test_increasing(self):
        jd0 = ae.julian_day(datetime(1900,1,1))
        jd1 = ae.julian_day(datetime(2100,1,1))
        self.assertLess(ae.ayanamsha_lahiri(jd0), ae.ayanamsha_lahiri(jd1))


class TestDignity(unittest.TestCase):
    def test_rulership(self):
        self.assertIn("rulership", ae.dignity_western("Sun","Leo").lower())
    def test_fall(self):
        self.assertIn("fall", ae.dignity_western("Mars","Cancer").lower())
    def test_detriment(self):
        self.assertIn("detriment", ae.dignity_western("Venus","Aries").lower())
    def test_exaltation(self):
        d = ae.dignity_western("Jupiter","Cancer").lower()
        self.assertTrue("exalt" in d or "exalted" in d)


class TestPartOfFortune(unittest.TestCase):
    def test_day(self):  self.assertIsNotNone(ae.part_of_fortune(10,90,0,True))
    def test_night(self): self.assertIsNotNone(ae.part_of_fortune(10,90,0,False))


class TestSolarReturn(unittest.TestCase):
    def test_solar_return(self):
        sr = ae.solar_return(ae.julian_day(datetime(1995,4,15,11,0)), 2026, 35.68, 51.38)
        self.assertIn("chart", sr)
        self.assertIn("big_three", sr["chart"])


class TestVertex(unittest.TestCase):
    def test_vertex(self):
        v = ae.vertex(ae.julian_day(datetime(1995,4,15,11,0)), 35.68, 51.38)
        if isinstance(v, dict):
            self.assertIn("longitude", v)
        else:
            self.assertGreaterEqual(v, 0)


class TestEqualHouses(unittest.TestCase):
    def test_equal_houses(self):
        houses = ae.equal_houses(142.5)
        self.assertEqual(len(houses), 12)


class TestBlackMoonLilith(unittest.TestCase):
    def test_bml(self):
        bml = ae.black_moon_lilith(ae.julian_day(datetime(1995,4,15,11,0)))
        if isinstance(bml, dict):
            self.assertIn("longitude", bml)
        else:
            self.assertGreaterEqual(bml, 0)
            self.assertLessEqual(bml, 360)


class TestCompositeChart(unittest.TestCase):
    def test_composite(self):
        jd_a = ae.julian_day(datetime(1995,4,15,11,0))
        jd_b = ae.julian_day(datetime(1993,8,22,6,30))
        comp = ae.composite_chart(jd_a, jd_b, 35.68, 51.38, 28.61, 77.23)
        self.assertIn("planets", comp)


class TestSecondaryProgressions(unittest.TestCase):
    def test_progressions(self):
        jd = ae.julian_day(datetime(1995,4,15,11,0))
        prog = ae.secondary_progressions(jd, 30, 35.68, 51.38)
        self.assertIn("planets", prog)


class TestPlanetaryReturn(unittest.TestCase):
    def test_jupiter_return(self):
        pr = ae.planetary_return(ae.julian_day(datetime(1995,4,15,11,0)),
                                  "Jupiter", 2026, 35.68, 51.38)
        self.assertIn("planet", pr)


class TestAllSystems(unittest.TestCase):
    r = ae.calculate_full_profile(BIRTH_ALL)
    def test_three_systems(self):
        for s in ("western","vedic","bazi"):
            with self.subTest(system=s): self.assertIn(s, self.r["charts"])


class TestArabicParts(unittest.TestCase):
    def test_arabic_parts(self):
        r = ae.calculate_full_profile(BIRTH_WEST)
        self.assertIn("arabic_parts", r)
        self.assertGreater(len(r["arabic_parts"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
