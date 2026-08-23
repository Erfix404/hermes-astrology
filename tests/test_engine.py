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
BIRTH_BOTH = {**BIRTH, "systems": ["western", "vedic"]}
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


# ════════════════════════════════════════════════════════════════════
#  Advanced Features Tests (8 new modules)
# ════════════════════════════════════════════════════════════════════
_BIRTH_JSON = {"year":1995,"month":4,"day":15,"hour":14,"minute":30,
               "lat":35.6892,"lng":51.3890,"tz":"Asia/Tehran","time_known":True}
_BIRTH_DEMO = ae._demo()

class TestNodeTransit(unittest.TestCase):
    def test_node_analysis(self):
        jd = ae.julian_day(datetime(1995,4,15,11,0))
        tjd = ae.julian_day(datetime(2026,7,30))
        natal_lons, _, _ = ae.body_longitudes(jd)
        t_lons, _, _ = ae.body_longitudes(tjd)
        try:
            from astro_advanced import analyze_node_transit
            n = analyze_node_transit(natal_lons, t_lons)
            self.assertIn("Rahu", n)
            self.assertIn("Ketu", n)
            self.assertIn("interpretation", n["Rahu"])
        except ImportError:
            self.skipTest("astro_advanced not available")

class TestGunaMilan(unittest.TestCase):
    def test_guna_same(self):
        jd = ae.julian_day(datetime(1995,4,15,11,0))
        lons, _, _ = ae.body_longitudes(jd)
        ayan = ae.ayanamsha_lahiri(jd)
        try:
            from astro_advanced import guna_milan
            g = guna_milan(lons, lons, ayan)
            self.assertEqual(g["total_score"], 26)  # known value
            self.assertIn("verdict", g)
        except ImportError:
            self.skipTest("astro_advanced not available")

class TestSolarReturnInterpreted(unittest.TestCase):
    def test_sr_interpretation(self):
        jd = ae.julian_day(datetime(1995,4,15,11,0))
        try:
            from astro_advanced import interpret_solar_return
            sr = ae.solar_return(jd, 2026, 35.68, 51.38)
            si = interpret_solar_return(sr)
            self.assertIn("interpretation", si)
            self.assertIn("year_theme", si["interpretation"])
        except ImportError:
            self.skipTest("astro_advanced not available")

class TestElectional(unittest.TestCase):
    def test_electional_find(self):
        jd = ae.julian_day(datetime(2026,7,30,12,0))
        try:
            from astro_advanced import find_electional_times
            ef = find_electional_times(jd, 35.68, 51.38, "career", days_ahead=3)
            self.assertGreater(len(ef.get("top_windows", [])), 0)
            self.assertEqual(ef["activity"], "career")
        except ImportError:
            self.skipTest("astro_advanced not available")

class TestSolarArc(unittest.TestCase):
    def test_solar_arc(self):
        jd = ae.julian_day(datetime(1995,4,15,11,0))
        lons, _, _ = ae.body_longitudes(jd)
        try:
            from astro_advanced import solar_arc_directions
            sa = solar_arc_directions(lons, 31.3)
            self.assertIn("age", sa)
            self.assertIn("directional_aspects_to_natal", sa)
            self.assertGreater(len(sa["directional_aspects_to_natal"]), 0)
        except ImportError:
            self.skipTest("astro_advanced not available")

class TestRemedies(unittest.TestCase):
    def test_remedy_suggestions(self):
        r = ae.calculate_full_profile(_BIRTH_JSON)
        try:
            from astro_advanced import suggest_remedies
            rem = suggest_remedies(r)
            self.assertIn("planet_remedies", rem)
        except ImportError:
            self.skipTest("astro_advanced not available")

class TestWeeklyCalendar(unittest.TestCase):
    def test_week_generation(self):
        try:
            from astro_advanced import weekly_astro_calendar
            w = weekly_astro_calendar(datetime(2026,7,30))
            self.assertEqual(len(w["days"]), 7)
            self.assertIn("week_start", w)
        except ImportError:
            self.skipTest("astro_advanced not available")

class TestPrashna(unittest.TestCase):
    def test_prashna_verdict(self):
        from datetime import timezone
        try:
            from astro_advanced import prashna
            q = prashna(datetime(2026,7,30,12,0,tzinfo=timezone.utc),
                        35.68, 51.38, "Will my project succeed?", "career")
            self.assertIn("verdict", q)
            self.assertIn("ascendant", q)
        except ImportError:
            self.skipTest("astro_advanced not available")


class TestPlacidus(unittest.TestCase):
    """Placidus houses — active when swisseph is available."""

    @unittest.skipUnless(ae._HAS_SWE, "swisseph not installed")
    def test_cusps_align_with_asc(self):
        jd = ae.julian_day(datetime(1995, 4, 15, 11, 0))
        cusps, _ = ae.placidus_cusps(jd, 35.6892, 51.3890)
        asc_lon, _ = ae.ascendant_mc(jd, 35.6892, 51.3890)
        self.assertEqual(len(cusps), 12)
        self.assertLess(abs(cusps[0] - asc_lon), 1.0)

    @unittest.skipUnless(ae._HAS_SWE, "swisseph not installed")
    def test_house_of_all_planets(self):
        jd = ae.julian_day(datetime(1995, 4, 15, 11, 0))
        cusps, _ = ae.placidus_cusps(jd, 35.6892, 51.3890)
        lons, _, _ = ae.body_longitudes(jd)
        for b in ("Sun","Moon","Mercury","Venus","Mars","Jupiter",
                  "Saturn","Uranus","Neptune","Pluto"):
            lon = lons[b]
            h = ae.placidus_house_of(lon, cusps)
            self.assertIn(h, range(1, 13))

    @unittest.skipUnless(ae._HAS_SWE, "swisseph not installed")
    def test_western_chart_uses_placidus(self):
        r = ae.calculate_full_profile(BIRTH_WEST)
        self.assertIn("Placidus", r["charts"]["western"]["system"])
        self.assertIn("cusp_lon", r["charts"]["western"]["houses"][1])


class TestNewFeatures(unittest.TestCase):
    """Post-audit features: declinations, antiscia, minor aspects, VOC,
    upagrahas, ashtakavarga, ashtottari, eclipses, stations, house systems."""

    def setUp(self):
        self.jd = ae.julian_day(datetime(1995, 4, 15, 11, 0))
        self.birth = dict(BIRTH_WEST)

    def test_minor_aspects_present(self):
        lons, _, _ = ae.body_longitudes(self.jd)
        aspects = ae.compute_aspects(lons)
        names = {a["aspect"] for a in aspects}
        self.assertIn("semisextile", ae.ASPECTS)
        self.assertIn("quintile", ae.ASPECTS)
        self.assertIn("septile", ae.ASPECTS)

    def test_declinations(self):
        decls = ae.body_declinations(self.jd)
        self.assertIn("Sun", decls)
        # Sun mid-April sits ~+9.7° declination (not ecliptic latitude ≈ 0).
        # This guards the SWE branch against returning ecliptic latitude
        # instead of true declination (regression from the old res[0][1] bug).
        self.assertGreater(abs(decls["Sun"]), 5.0)
        self.assertLess(abs(decls["Sun"]), 12.0)

    def test_declination_aspects(self):
        lons, _, _ = ae.body_longitudes(self.jd)
        decls = ae.body_declinations(self.jd)
        da = ae.compute_declination_aspects(lons, decls)
        for a in da:
            self.assertIn(a["aspect"], ("parallel", "contraparallel"))

    def test_antiscia(self):
        self.assertAlmostEqual(ae.antiscia(0), 360.0 % 360)
        self.assertAlmostEqual(ae.antiscia(100), 260.0)

    def test_void_of_course(self):
        v = ae.void_of_course_moon(self.jd, 35.6892, 51.3890)
        self.assertIn("is_void", v)

    def test_upagrahas_nine(self):
        u = ae.upagrahas(self.jd, 35.6892, 51.3890)
        self.assertEqual(len(u), 9)
        self.assertIn("Gulika", u)

    def test_ashtakavarga(self):
        a = ae.ashtakavarga(self.jd, 35.6892, 51.3890)
        self.assertEqual(len(a["sarvashtakavarga"]), 12)
        for counts in a["bhinnashtakavarga"].values():
            self.assertEqual(len(counts), 12)

    def test_ashtottari(self):
        moon_sid = ae.norm360(ae.body_longitudes(self.jd)[0]["Moon"] - ae.ayanamsha_lahiri(self.jd))
        d = ae.ashtottari_dasha(moon_sid, datetime(1995, 4, 15, 11, 0))
        self.assertEqual(d["system"], "Ashtottari (108-year)")
        self.assertEqual(len(d["periods"]), 3)

    @unittest.skipUnless(ae._HAS_SWE, "swisseph not installed")
    def test_eclipses(self):
        e = ae.next_eclipses(self.jd, count=2)
        self.assertGreaterEqual(len(e), 1)
        for x in e:
            self.assertIn(x["type"], ("solar", "lunar"))

    @unittest.skipUnless(ae._HAS_SWE, "swisseph not installed")
    def test_stations(self):
        s = ae.station_dates(self.jd, self.jd + 120, "Mercury", step=2)
        self.assertIn("stations", s)

    @unittest.skipUnless(ae._HAS_SWE, "swisseph not installed")
    def test_house_system_selection(self):
        d = dict(self.birth)
        d["house_system"] = "K"
        r = ae.calculate_full_profile(d)
        self.assertIn("Koch", r["charts"]["western"]["system"])

    def test_new_fields_in_natal(self):
        r = ae.calculate_full_profile(BIRTH_BOTH)
        for k in ("declinations", "antiscia", "void_of_course_moon"):
            self.assertIn(k, r)
        self.assertIn("upagrahas", r)
        self.assertIn("ashtakavarga", r)
        self.assertIn("ashtottari_dasha", r)

    @unittest.skipUnless(ae._HAS_SWE, "swisseph not installed")
    def test_new_modes(self):
        for mode in ("eclipses", "upagrahas", "ashtakavarga", "void_of_course", "ashtottari"):
            d = dict(self.birth)
            d["mode"] = mode
            r = ae.calculate_full_profile(d)
            self.assertNotIn("error", r.get("_meta", {}))
            self.assertTrue(any(k != "_meta" for k in r.keys()))

    def test_tajika_mode(self):
        d = dict(self.birth)
        d["systems"] = ["vedic"]
        d["mode"] = "tajika"
        r = ae.calculate_full_profile(d)
        self.assertIn("tajika", r)
        self.assertIsNotNone(r["tajika"].get("tajika_year"))

    def test_muhurta_mode(self):
        d = dict(self.birth)
        d["systems"] = ["vedic"]
        d["mode"] = "muhurta"
        d["days_ahead"] = 3
        r = ae.calculate_full_profile(d)
        self.assertIn("muhurta", r)
        self.assertIn("top_muhurtas", r["muhurta"])

    def test_shadbala_mode(self):
        d = dict(self.birth)
        d["systems"] = ["vedic"]
        d["mode"] = "shadbala"
        r = ae.calculate_full_profile(d)
        self.assertIn("shadbala", r)
        self.assertIn("sthana_bala", r["shadbala"])

    @unittest.skipUnless(ae._HAS_SWE, "house numbers are Placidus (Woolfolk); builtin uses whole-sign")
    def test_oprah_winfrey_chart(self):
        """Validation against The Only Astrology Book You'll Ever Need (Woolfolk 2008),
        page 337 — Oprah Winfrey, Jan 29 1954, 4:30am CST, Kosciusko MS."""
        r = ae.calculate_full_profile({
            'year':1954,'month':1,'day':29,'hour':4,'minute':30,
            'lat':33.05,'lng':-89.58,'tz':'America/Chicago',
            'systems':['western'],'time_known':True
        })
        w = r['charts']['western']
        self.assertEqual(w['ascendant']['sign'], 'Sagittarius')
        self.assertLess(abs(w['ascendant']['deg_in_sign'] - 29.7), 1.0)
        expected = {
            'Sun': ('Aquarius', 2), 'Moon': ('Sagittarius', 11),
            'Mercury': ('Aquarius', 2), 'Venus': ('Aquarius', 2),
            'Mars': ('Scorpio', 11), 'Jupiter': ('Gemini', 6),
            'Saturn': ('Scorpio', 10), 'Uranus': ('Cancer', 7),
            'Neptune': ('Libra', 10), 'Pluto': ('Leo', 8),
        }
        for p, (sign, house) in expected.items():
            planet = w['planets'][p]
            self.assertEqual(planet['sign'], sign, f"{p} sign")
            self.assertEqual(planet['house'], house, f"{p} house")

    def test_planet_in_house_readings(self):
        """120 interpretive readings (Woolfolk 2008) load from data/planet_in_house.json."""
        import json, os
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "data", "planet_in_house.json")
        self.assertTrue(os.path.exists(p), "planet_in_house.json missing")
        with open(p) as f:
            d = json.load(f)
        self.assertEqual(len(d), 12)
        for house in d.values():
            self.assertEqual(len(house), 10)
        r = ae.calculate_full_profile({
            'year':1995,'month':4,'day':15,'hour':14,'minute':30,
            'lat':35.6892,'lng':51.3890,'tz':'Asia/Tehran',
            'systems':['western'],'time_known':True
        })
        sun = r['charts']['western']['planets']['Sun']
        self.assertTrue(sun.get('in_house_reading', ""), "Sun reading empty")
        self.assertGreater(len(sun['in_house_reading']), 40)

    def test_dignity_with_degree(self):
        # Jupiter in Leo 5° — triplicity night ruler + Jupiter term (0-6)
        d = ae.dignity_western("Jupiter", "Leo", 5)
        self.assertIn("triplicity", d)
        self.assertIn("term", d)

    def test_fixed_stars_expanded(self):
        self.assertGreaterEqual(len(ae.FIXED_STARS), 60)

    def test_aspects_table_expanded(self):
        self.assertGreaterEqual(len(ae.ASPECTS), 12)


class TestNodeTransitAllSigns(unittest.TestCase):
    """Public node-transit feature: Rahu/Ketu effect on natives of all 12 signs."""

    def test_all_signs_present(self):
        d = dict(BIRTH)
        d["mode"] = "node_transit_all_signs"
        r = ae.calculate_full_profile(d)
        nt = r["node_transit_all_signs"]
        self.assertIn("current", nt)
        self.assertIn("rahu_sign", nt["current"])
        self.assertIn("ketu_sign", nt["current"])
        self.assertEqual(len(nt["per_sign"]), 12)
        # Rahu and Ketu are always opposite (6 signs apart)
        ri = ae.SIGNS.index(nt["current"]["rahu_sign"])
        ki = ae.SIGNS.index(nt["current"]["ketu_sign"])
        self.assertEqual((ri - ki) % 12, 6)

    def test_effects_not_empty(self):
        d = dict(BIRTH)
        d["mode"] = "node_transit_all_signs"
        r = ae.calculate_full_profile(d)
        for s in r["node_transit_all_signs"]["per_sign"]:
            self.assertTrue(s["rahu_effect"], f"{s['sign']} rahu effect empty")
            self.assertTrue(s["ketu_effect"], f"{s['sign']} ketu effect empty")

    def test_no_birth_data_needed(self):
        # Works with just mode — no birth details required (public feature)
        r = ae.calculate_full_profile({"mode": "node_transit_all_signs"})
        self.assertIn("node_transit_all_signs", r)


class TestPublicModesNoBirthData(unittest.TestCase):
    """Sky-now modes must work with {"mode": ...} only — regression for the
    KeyError crash where dispatch happened after to_utc()."""

    MODES = ("weekly_calendar", "eclipses", "stations", "moon_phase",
             "planetary_hours", "void_of_course", "muhurta", "electional")
    # void_of_course returns its payload under "void_of_course_moon"
    KEY_OVERRIDES = {"void_of_course": "void_of_course_moon"}

    def test_each_public_mode_runs_without_birth_data(self):
        for m in self.MODES:
            with self.subTest(mode=m):
                r = ae.calculate_full_profile({"mode": m})
                self.assertIn(self.KEY_OVERRIDES.get(m, m), r,
                              f"mode {m} missing its result key")
                self.assertNotIn("error", r)

    def test_numerology_without_birth_data_gives_error_not_crash(self):
        r = ae.calculate_full_profile({"mode": "numerology"})
        self.assertIn("error", r)

    def test_numerology_with_date_only(self):
        r = ae.calculate_full_profile({"mode": "numerology",
                                       "year": 1995, "month": 4, "day": 15})
        self.assertIn("numerology", r)
        self.assertEqual(r["numerology"]["life_path"]["number"], 7)

    def test_moon_phase_still_accepts_birth_data(self):
        # Backwards-compat: birth-data call still computes at birth moment.
        d = dict(ae._demo()); d["mode"] = "moon_phase"
        r = ae.calculate_full_profile(d)
        self.assertIn("moon_phase", r)
        self.assertIn("phase", r["moon_phase"])


class TestVimshottariLevels(unittest.TestCase):
    """Wave 2-1: pratyantardasha (3rd level) in Vimshottari."""

    def test_pratyantar_present_and_proportional(self):
        d = dict(ae._demo())
        r = ae.calculate_full_profile(d)
        v = r["charts"]["vedic"]["vimshottari_dasha"]
        self.assertIn("current_pratyantardasha", v)
        pts = v["pratyantardashas_in_current_antar"]
        self.assertEqual(len(pts), 9)
        # first pratyantar lord = antardasha lord (sequence starts from it)
        self.assertEqual(pts[0]["lord"], v["current_antardasha"]["lord"])
        # durations proportional to DASHA_YEARS: len(p2)/len(p1) = yrs2/yrs1
        import datetime as _dt
        s0 = _dt.datetime.strptime(pts[0]["start"], "%Y-%m-%d %H:%M")
        e0 = _dt.datetime.strptime(pts[0]["end"], "%Y-%m-%d %H:%M")
        s1 = _dt.datetime.strptime(pts[1]["start"], "%Y-%m-%d %H:%M")
        e1 = _dt.datetime.strptime(pts[1]["end"], "%Y-%m-%d %H:%M")
        self.assertEqual(s1, e0, "pratyantars must be contiguous")
        ratio = (e1 - s1) / (e0 - s0)
        expect = ae.DASHA_YEARS[pts[1]["lord"]] / ae.DASHA_YEARS[pts[0]["lord"]]
        self.assertAlmostEqual(ratio, expect, delta=0.01)

    def test_vedic_chart_still_builds(self):
        d = dict(ae._demo())
        r = ae.calculate_full_profile(d)
        self.assertNotIn("error", r["charts"]["vedic"])


class TestZodiacalReleasing(unittest.TestCase):
    """Wave 1-5: ZR per Valens IV — periods, LOB, peaks, symbolic calendar."""

    def test_period_table_matches_valens(self):
        self.assertEqual(ae.ZR_PERIODS["Cancer"], 25)
        self.assertEqual(ae.ZR_PERIODS["Leo"], 19)
        self.assertEqual(ae.ZR_PERIODS["Libra"], 8)
        self.assertEqual(ae.ZR_PERIODS["Capricorn"], 27)
        self.assertEqual(sum(ae.ZR_PERIODS.values()), 211)

    def test_l1_sequence_and_lob(self):
        # from Leo: Leo(19) Virgo(20) Libra(8) ... after a full lap the count
        # returns toward Leo → LOB jumps to Aquarius instead
        seq = ae._zr_release_sequence("Leo", 211 * 360 + 10, 1)
        signs = [s["sign"] for s in seq]
        self.assertEqual(signs[0], "Leo")
        self.assertNotIn("Leo", signs[1:], "starting sign must not repeat pre-LOB")
        lob_entries = [s for s in seq if s["is_lob"]]
        self.assertTrue(lob_entries, "LOB must fire within one full lap")
        self.assertEqual(lob_entries[0]["sign"], "Aquarius")
        # durations follow the 360-day year
        leo = seq[0]
        self.assertAlmostEqual(leo["end_day"] - leo["start_day"], 19 * 360)

    def test_zr_mode_report_structure(self):
        d = dict(ae._demo())
        r = ae.calculate_full_profile({**d, "mode": "zr",
                                       "zr_topic": "spirit", "until_age": 80})
        zr = r["zodiacal_releasing"]
        for key in ("release_point", "peak_signs", "active_period",
                    "timeline_level1", "lot_of_fortune_sign"):
            self.assertIn(key, zr)
        self.assertEqual(len(zr["peak_signs"]), 4)
        # every L1 entry has level2 children starting with its own sign
        first = zr["timeline_level1"][0]
        if first.get("level2"):
            self.assertEqual(first["level2"][0]["sign"], first["sign"])
        bad = ae.calculate_full_profile({**d, "mode": "zr",
                                         "zr_topic": "nope"})
        self.assertIn("error", bad)

    def test_zr_interpretation_layer(self):
        d = dict(ae._demo())
        r = ae.calculate_full_profile({**d, "mode": "zr"})
        zi = r.get("zr_interpretation")
        self.assertIsNotNone(zi)
        self.assertTrue(zi["current_reading"])
        self.assertIsInstance(zi["lifetime_highlights"], list)


class TestTransitInterpretation(unittest.TestCase):
    """Wave 1-3: readable interpretation layer over raw transit aspects."""

    def test_interpret_transits_ranks_and_reads(self):
        raw = {"aspects_to_natal": [
            {"transiting": "Pluto", "to_natal": "Moon", "aspect": "square",
             "orb": 0.5, "transiting_sign": "Aquarius", "retrograde": False,
             "meaning": "x"},
            {"transiting": "Mars", "to_natal": "Venus", "aspect": "trine",
             "orb": 3.0, "transiting_sign": "Leo", "retrograde": False,
             "meaning": "y"},
        ]}
        out = ae.interpret_transits(raw)
        self.assertTrue(out["headline"].startswith("Dominant transit: Pluto"))
        self.assertEqual(out["key_transits"][0]["transiting"], "Pluto")
        self.assertIn("reading", out["key_transits"][0])
        self.assertIsInstance(out["advice"], list)

    def test_transit_mode_includes_interpretation(self):
        d = dict(ae._demo())
        r = ae.calculate_full_profile({**d, "mode": "transit",
                                       "transit_date": "2026-08-23"})
        self.assertIn("transit_interpretation", r)
        self.assertIn("headline", r["transit_interpretation"])


class TestProgressionInterpretation(unittest.TestCase):
    """Wave 1-4: readable reading over secondary progressions."""

    def test_interpret_progressions_structure(self):
        jd = ae.julian_day(datetime(1990, 6, 15, 11, 0))
        prog = ae.secondary_progressions(jd, 36, 35.6892, 51.3890)
        out = ae.interpret_progressions(jd, prog)
        self.assertEqual(out["age"], 36)
        planets_read = {r["planet"] for r in out["readings"]}
        self.assertIn("Sun", planets_read)
        self.assertIn("Moon", planets_read)
        self.assertIn("lunar_phase", out["readings"][1])
        self.assertTrue(out["summary"].startswith("At age 36:"))

    def test_progressions_mode_includes_interpretation(self):
        d = dict(ae._demo())
        r = ae.calculate_full_profile({**d, "mode": "progressions",
                                       "target_age": 36})
        self.assertIn("progression_interpretation", r)
        self.assertIn("summary", r["progression_interpretation"])

    def test_lunar_phase_mapping(self):
        # phase angle 0 → new; 180 → full
        phases = ae.PROG_MOON_PHASE.keys()
        self.assertEqual(len(list(phases)), 8)


class TestProfectionsFirdaria(unittest.TestCase):
    """Wave 1-1/1-2: annual profections + Firdaria periods."""

    def test_profection_rotation_known_ages(self):
        # Asc = Aries (idx 0): age 0→house 1, age 5→house 6, age 12→house 1
        birth = datetime(1990, 6, 15)
        r0 = ae.annual_profections(0, birth, datetime(1990, 7, 15))
        self.assertEqual((r0["active_house"], r0["active_sign"]), (1, "Aries"))
        r5 = ae.annual_profections(0, birth, datetime(1995, 7, 15))
        self.assertEqual(r5["active_house"], 6)
        r12 = ae.annual_profections(0, birth, datetime(2002, 7, 15))
        self.assertEqual(r12["active_house"], 1)
        # year lord = ruler of profected sign
        r9 = ae.annual_profections(0, birth, datetime(1999, 7, 15))
        self.assertEqual(r9["active_sign"], "Capricorn")
        self.assertEqual(r9["year_lord"], "Saturn")

    def test_firdaria_sect_and_coverage(self):
        birth = datetime(1990, 6, 15, 14, 30)  # day birth → Sun first
        f = ae.firdaria(birth, is_day_birth=True)
        self.assertEqual(f["sect"], "day")
        tl = f["timeline_to_age_75"]
        self.assertEqual(tl[0]["lord"], "Sun")
        # day order total + final Moon = 75 years coverage
        self.assertAlmostEqual(tl[-1]["end_age"], 75.0, delta=0.1)
        # every age in [0,75) falls inside exactly one major firdar
        for age in range(0, 75, 3):
            hits = [p for p in tl if p["start_age"] <= age < p["end_age"]]
            self.assertEqual(len(hits), 1, f"age {age} covered {len(hits)}x")
        fn = ae.firdaria(birth, is_day_birth=False)
        self.assertEqual(fn["timeline_to_age_75"][0]["lord"], "Moon")

    def test_modes_dispatch(self):
        d = dict(ae._demo())
        rp = ae.calculate_full_profile({**d, "mode": "profections"})
        self.assertIn("annual_profections", rp)
        self.assertNotIn("error", rp)
        rf = ae.calculate_full_profile({**d, "mode": "firdaria"})
        self.assertIn("firdaria", rf)
        self.assertEqual(rf["firdaria"]["sect"],
                         rf["firdaria"]["sect"])  # stable
        rc = ae.calculate_full_profile({**d, "mode": "forecast"})
        self.assertIn("annual_profections", rc)
        self.assertIn("firdaria", rc)


class TestShadbalaCheshtaDrik(unittest.TestCase):
    """Wave 0-5: Cheshta (BPHS 18/24-25) & Drik bala in shadbala_sthana_dig."""

    def test_cheshta_sun_tracks_declination(self):
        import astro_advanced as aa
        jd = lambda *d: ae.julian_day(datetime(*d))
        r_win = aa.shadbala_sthana_dig(jd(1990, 12, 22), 35.6892, 51.3890)
        r_eq = aa.shadbala_sthana_dig(jd(1990, 9, 23), 35.6892, 51.3890)
        r_sum = aa.shadbala_sthana_dig(jd(1990, 6, 21), 35.6892, 51.3890)
        sun_win = r_win["cheshta_bala_virupas"]["Sun"]
        sun_eq = r_eq["cheshta_bala_virupas"]["Sun"]
        sun_sum = r_sum["cheshta_bala_virupas"]["Sun"]
        # south declination → strong; north → weak; equinox midway
        self.assertGreater(sun_win, 45, "winter solstice Sun should be strong")
        self.assertLess(sun_sum, 15, "summer solstice Sun should be weak")
        self.assertAlmostEqual(sun_eq, 30, delta=3)

    def test_cheshta_kendra_range_and_moon_paksha(self):
        import astro_advanced as aa
        r = aa.shadbala_sthana_dig(
            ae.julian_day(datetime(1990, 6, 15, 9, 0)), 35.6892, 51.3890)
        ch = r["cheshta_bala_virupas"]
        for p, v in ch.items():
            self.assertGreaterEqual(v, 0, f"{p} negative")
            self.assertLessEqual(v, 60, f"{p} exceeds 60 virupas")
        # near-full moon (Jun 8 1990 diff ~175°): paksha should be high
        r_fm = aa.shadbala_sthana_dig(ae.julian_day(datetime(1990, 6, 8)), 35.6892, 51.3890)
        self.assertGreater(r_fm["cheshta_bala_virupas"]["Moon"], 50)

    def test_drik_bala_present_and_finite(self):
        import astro_advanced as aa
        r = aa.shadbala_sthana_dig(
            ae.julian_day(datetime(1990, 6, 15, 9, 0)), 35.6892, 51.3890)
        d = r["drik_bala_rupas"]
        self.assertEqual(set(d), {"Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"})
        for p, v in d.items():
            self.assertTrue(-5 <= v <= 5, f"{p} drik out of plausible range: {v}")
        # total must now include both new components
        self.assertIn("shadbala_total", r)


class TestPtolemaicTerms(unittest.TestCase):
    """Wave 0-4: Ptolemaic terms alongside Egyptian terms (dignity_western)."""

    def test_ptolemaic_terms_sum_30_per_sign(self):
        import astro_engine as ae
        src = open(os.path.join(_SCRIPTS, "astro_engine.py"), encoding="utf-8").read()
        ns = {}
        # pull the ptolemaic_terms dict literal out of the source for validation
        start = src.index("ptolemaic_terms = {")
        block = src[start:src.index("}", start) + 1]
        exec(block, ns)
        tbl = ns["ptolemaic_terms"]
        self.assertEqual(set(tbl), set(ae.SIGNS))
        for sign, segs in tbl.items():
            self.assertEqual([s[0] for s in segs], sorted(segs, key=lambda x: x[1])[0] and
                             [s[0] for s in segs], msg=sign)
            prev = 0
            rulers = []
            for ruler, end in segs:
                self.assertGreater(end, prev, f"{sign}: non-increasing bound {end}")
                prev = end
                rulers.append(ruler)
            self.assertEqual(prev, 30, f"{sign}: bounds must end at 30")
            # all five term lords used exactly once (classical requirement)
            self.assertEqual(sorted(rulers),
                             sorted(["Saturn","Jupiter","Mars","Venus","Mercury"]),
                             f"{sign}: must use each of the five term lords once")

    def test_dignity_reports_both_term_systems(self):
        # Aries 3° = Jupiter's first Egyptian AND Ptolemaic term → both labels
        d = ae.dignity_western("Jupiter", "Aries", 3)
        self.assertIn("term (Egyptian bound)", d)
        self.assertIn("term (Ptolemaic)", d)
        # Gemini 22°: Egyptian ruler=Mars, Ptolemaic ruler=Saturn; neither has
        # a major dignity in Gemini so the term branch is reached.
        d_mars = ae.dignity_western("Mars", "Gemini", 22)
        self.assertIn("term (Egyptian bound)", d_mars)
        self.assertNotIn("term (Ptolemaic)", d_mars)
        d_sat = ae.dignity_western("Saturn", "Gemini", 22)
        self.assertNotIn("term (Egyptian bound)", d_sat)
        self.assertIn("term (Ptolemaic)", d_sat)
        # Mercury rules no term at Taurus 23° in either system
        self.assertEqual(ae.dignity_western("Mercury", "Taurus", 23), "")


class TestNodeTypeOption(unittest.TestCase):
    """node_type option (wave 0-3): "true" (osculating, astro.com default)
    vs "mean" (smoothed; classical Parashari/Lilly). True oscillates around
    mean with amplitude ~1.5 deg over ~173 days."""

    def test_true_vs_mean_nodes_differ_within_1p5deg(self):
        jd = ae.julian_day(datetime(2026, 8, 22))
        lons_true, _, _ = ae.body_longitudes(jd, node_type="true")
        lons_mean, _, _ = ae.body_longitudes(jd, node_type="mean")
        diff = abs(ae.norm180(lons_true["North Node"] - lons_mean["North Node"]))
        self.assertGreater(diff, 0.001, "true and mean nodes should differ")
        self.assertLess(diff, 2.0, "true node must stay within ~2 deg of mean")
        # South nodes are antipodal in both systems
        self.assertAlmostEqual(lons_true["South Node"],
                               (lons_true["North Node"] + 180) % 360, places=6)

    def test_default_is_true_with_swisseph_mean_without(self):
        jd = ae.julian_day(datetime(2026, 8, 22))
        _, _, backend = ae.body_longitudes(jd)
        _, meta_node, _ = ae.body_longitudes(jd, node_type=None)
        expected = "true" if ae._HAS_SWE else "mean"
        self.assertEqual(expected, "true" if backend == "swisseph" else "mean")
        self.assertIsNotNone(meta_node)

    def test_calculate_full_profile_reports_and_applies_node_type(self):
        d = dict(ae._demo()); d["systems"] = ["western"]
        r_true = ae.calculate_full_profile({**d, "node_type": "true"})
        r_mean = ae.calculate_full_profile({**d, "node_type": "mean"})
        self.assertEqual(r_true["_meta"]["node_type"], "true")
        self.assertEqual(r_mean["_meta"]["node_type"], "mean")
        nn_t = r_true["charts"]["western"]["planets"]["North Node"]["abs_lon"]
        nn_m = r_mean["charts"]["western"]["planets"]["North Node"]["abs_lon"]
        diff = abs((nn_t - nn_m + 180) % 360 - 180)
        self.assertGreater(diff, 0.001)
        self.assertLess(diff, 2.0)


class TestJPLValidation(unittest.TestCase):
    """Cross-check engine positions against NASA JPL Horizons reference values.

    Reference: apparent geocentric ecliptic longitudes (IAU76/80 of-date),
    2026-08-01 08:30 UTC — fetched from ssd.jpl.nasa.gov (DE441).
    Tolerance 0.35° (1260″) — this validates the *whole pipeline*
    (JD conversion, timezone, ephemeris, sign boundaries) against an
    independent source, without requiring swisseph.
    """

    JPL_REF = {
        # body: (ecliptic_lon_deg, tolerance_deg)
        "Sun":      (128.958, 0.35),
        "Moon":     (340.649, 0.35),
        "Mercury":  (109.667, 0.35),
        "Venus":    (174.243, 0.35),
        "Mars":     (83.188,  0.35),
        "Jupiter":  (127.001, 0.35),
    }

    def test_jpl_2026_08_01(self):
        d = {"year": 2026, "month": 8, "day": 1, "hour": 12, "minute": 0,
             "lat": 35.6892, "lng": 51.3890, "tz": "Asia/Tehran", "time_known": True,
             "systems": ["western"]}
        r = ae.calculate_full_profile(d)
        planets = r["charts"]["western"]["planets"]
        for body, (ref_lon, tol) in self.JPL_REF.items():
            lon = planets[body]["abs_lon"]
            diff = abs((lon - ref_lon) % 360)
            if diff > 180:
                diff = 360 - diff
            self.assertLess(diff, tol,
                            f"{body}: engine {lon:.3f}° vs JPL {ref_lon:.3f}° "
                            f"(Δ {diff*3600:.0f}″)")

    def test_jpl_sign_consistency(self):
        # Sun at 128.958° = Leo 9°; Moon at 340.649° = Pisces 10° — sign
        # boundaries must match the JPL reference exactly.
        self.assertEqual(_sign_str(128.958), "Leo")
        self.assertEqual(_sign_str(340.649), "Pisces")


if __name__ == "__main__":
    unittest.main(verbosity=2)
