#!/usr/bin/env python3
"""Astro-Databank AA-Rated Validation Test Suite.
Validates hermes-astrology v3.0 against internationally verified historical charts
(Source: Astro-Databank Rodden Rating AA — from Birth Certificates / Hospital Records).

Test Subjects:
1. Carl Gustav Jung (Astrologer & Psychiatrist): 1875-07-26 19:32 LMT, Kesswil, Switzerland
2. Albert Einstein (Theoretical Physicist): 1879-03-14 11:30 LMT, Ulm, Germany
3. Steve Jobs (Apple Co-founder): 1955-02-24 19:15 PST, San Francisco, CA
"""

import os
import sys
import unittest
from datetime import datetime

_SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, _SCRIPTS)

import astro_engine as ae


class TestAstroDatabankAARatedCharts(unittest.TestCase):
    """Validation against Rodden Rating AA historical charts."""

    def test_carl_jung_chart(self):
        """Carl Jung: Sun in Leo, Moon in Taurus, Ascendant in Aquarius.
        Born 1875 in Kesswil, Switzerland (pre-standard timezone, LMT +0h37m)."""
        data = {
            "year": 1875, "month": 7, "day": 26, "hour": 19, "minute": 32,
            "lat": 47.5999, "lng": 9.3167, "utc_offset": 9.3167 / 15.0,
            "systems": ["western", "vedic"]
        }
        res = ae.calculate_full_profile(data)
        b3 = res["summary"]["big_three"]
        self.assertEqual(b3["sun"], "Leo")
        self.assertEqual(b3["moon"], "Taurus")
        self.assertEqual(b3["ascendant"], "Aquarius")

        # Vedic Moon Nakshatra: Bharani (23° Aries sidereal)
        vedic = res["charts"]["vedic"]
        self.assertEqual(vedic["janma_nakshatra"]["name"], "Bharani")

    def test_albert_einstein_chart(self):
        """Albert Einstein: Sun in Pisces, Moon in Sagittarius, Ascendant in Cancer."""
        data = {
            "year": 1879, "month": 3, "day": 14, "hour": 11, "minute": 30,
            "lat": 48.4011, "lng": 9.9876, "tz": "Europe/Berlin",
            "systems": ["western", "vedic"]
        }
        res = ae.calculate_full_profile(data)
        b3 = res["summary"]["big_three"]
        self.assertEqual(b3["sun"], "Pisces")
        self.assertEqual(b3["moon"], "Sagittarius")
        self.assertEqual(b3["ascendant"], "Cancer")

        # 10th House (Career) Stellium in Aries (Sun, Mercury, Venus, Saturn)
        w_planets = res["charts"]["western"]["planets"]
        self.assertEqual(w_planets["Mercury"]["sign"], "Aries")
        self.assertEqual(w_planets["Venus"]["sign"], "Aries")
        self.assertEqual(w_planets["Saturn"]["sign"], "Aries")

    def test_steve_jobs_chart(self):
        """Steve Jobs: Sun in Pisces, Moon in Aries, Ascendant in Virgo."""
        data = {
            "year": 1955, "month": 2, "day": 24, "hour": 19, "minute": 15,
            "lat": 37.7749, "lng": -122.4194, "tz": "America/Los_Angeles",
            "systems": ["western", "vedic"]
        }
        res = ae.calculate_full_profile(data)
        b3 = res["summary"]["big_three"]
        self.assertEqual(b3["sun"], "Pisces")
        self.assertEqual(b3["moon"], "Aries")
        self.assertEqual(b3["ascendant"], "Virgo")

        # Mars in Aries (House 8 - intense drive and pioneer)
        w_planets = res["charts"]["western"]["planets"]
        self.assertEqual(w_planets["Mars"]["sign"], "Aries")


if __name__ == "__main__":
    unittest.main()
