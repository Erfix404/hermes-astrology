#!/usr/bin/env python3
"""Comprehensive Unit Tests for Astraea Financial Astrology & Astro-Trading Engine."""

import os
import sys
import unittest
import math
from datetime import datetime, timezone

_SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, _SCRIPTS)

import astro_trading_engine as ate
import astro_engine as ae


class TestGannSquare9Engine(unittest.TestCase):
    """Test Gann Square of 9 Mathematical Conversions and Planetary Price Lines."""

    def test_price_to_degree_and_back(self):
        # Base price 100 -> sqrt is 10.0 -> root % 2.0 = 0.0 -> 0 degrees
        deg_100 = ate.GannSquare9Engine.price_to_degree(100.0)
        self.assertEqual(deg_100, 0.0)

        # Degree to price: +180 deg from 100 -> (sqrt(100) + 180/180)^2 = (10+1)^2 = 121
        p_180 = ate.GannSquare9Engine.degree_to_price(100.0, 180.0)
        self.assertEqual(p_180, 121.0)

        # +360 deg from 100 -> (10 + 2)^2 = 144
        p_360 = ate.GannSquare9Engine.degree_to_price(100.0, 360.0)
        self.assertEqual(p_360, 144.0)

        # -90 deg from 100 -> (10 - 0.5)^2 = 9.5^2 = 90.25
        p_minus90 = ate.GannSquare9Engine.degree_to_price(100.0, -90.0)
        self.assertEqual(p_minus90, 90.25)

    def test_compute_harmonics_cardinal_cross(self):
        harmonics = ate.GannSquare9Engine.compute_harmonics(6400.0) # sqrt = 80
        cc = harmonics["cardinal_cross"]
        self.assertEqual(cc["0°_base"], 6400.0)
        self.assertEqual(cc["180°_opposition"], 6561.0) # (80+1)^2 = 81^2 = 6561
        self.assertEqual(cc["360°_octave"], 6724.0)     # (80+2)^2 = 82^2 = 6724

    def test_planetary_price_lines_btc(self):
        lons = {"Sun": 160.0, "Jupiter": 120.0, "Saturn": 350.0}
        lines = ate.GannSquare9Engine.planetary_price_lines(lons, current_price=65000.0, asset_key="BTC")
        self.assertGreater(len(lines), 0)
        for pl in lines:
            self.assertIn(pl["role"], ("Support", "Resistance"))
            self.assertIn("distance_pct", pl)


class TestBradleySiderographEngine(unittest.TestCase):
    """Test Donald Bradley Siderograph Potential Calculations."""

    def test_calculate_potential_symmetry(self):
        # Trine aspect between Jupiter and Uranus (120 deg apart) -> should yield positive potential
        lons = {"Jupiter": 0.0, "Uranus": 120.0, "Saturn": 200.0}
        decls = {"Venus": 10.0, "Mars": -5.0}
        pot = ate.BradleySiderographEngine.calculate_potential(lons, decls)
        self.assertIn("long_term_potential", pot)
        self.assertIn("net_siderograph_potential", pot)
        self.assertIsInstance(pot["net_siderograph_potential"], float)


class TestMerrimanCRDAndMcWhirter(unittest.TestCase):
    """Test Merriman CRD Clustering and Louise McWhirter 18.6-Year Node Cycle."""

    def test_merriman_crd_cluster(self):
        sigs_high = [
            {"level": 1, "description": "Mars Stationary Direct"},
            {"level": 1, "description": "Sun Cardinal Ingress 0° Aries"}
        ]
        res_high = ate.MerrimanCRDEngine.evaluate_crd_cluster(sigs_high)
        self.assertTrue(res_high["is_critical_reversal_date"])
        self.assertGreaterEqual(res_high["crd_score"], 20)

        sigs_low = [{"level": 3, "description": "Moon Trine Venus"}]
        res_low = ate.MerrimanCRDEngine.evaluate_crd_cluster(sigs_low)
        self.assertFalse(res_low["is_critical_reversal_date"])

    def test_mcwhirter_node_cycle(self):
        # Node in Leo (135°) -> Macro Economic Peak
        res_leo = ate.McWhirterCycleEngine.evaluate_node_cycle(135.0)
        self.assertEqual(res_leo["north_node_sign"], "Leo")
        self.assertIn("Peak", res_leo["macro_phase"])

        # Node in Aquarius (315°) -> Generational Market Bottom
        res_aq = ate.McWhirterCycleEngine.evaluate_node_cycle(315.0)
        self.assertEqual(res_aq["north_node_sign"], "Aquarius")
        self.assertEqual(res_aq["strategic_market_posture"], "GENERATIONAL_BUY")


class TestAstroTradingStrategyEngine(unittest.TestCase):
    """Test Master Quantitative Astro-Trading Strategy Synthesizer."""

    def test_generate_trade_setup_btc(self):
        lons = {"Sun": 160.0, "Mars": 90.5, "Jupiter": 120.0, "Saturn": 350.0}
        speeds = {"Mars": 0.02, "Mercury": 1.2, "Venus": 1.0} # Mars stationary direct
        setup = ate.AstroTradingStrategyEngine.generate_trade_setup(
            asset_key="BTC",
            current_price=65000.0,
            longitudes=lons,
            speeds=speeds,
            is_moon_voc=False
        )
        self.assertEqual(setup["asset"], "Bitcoin")
        self.assertIn(setup["recommended_action"], ("BUY / ACCUMULATE", "STRONG BUY", "HOLD / CONSOLIDATION"))
        self.assertGreater(setup["confluence_score"], 50)
        self.assertIn("stop_loss", setup["trade_parameters"])
        self.assertIn("take_profit_1", setup["trade_parameters"])

    def test_astro_engine_integration_modes(self):
        # Test full integration via astro_engine.calculate_full_profile
        data_trading = {"mode": "astro_trading", "asset": "BTC", "price": 64000.0, "year": 2026, "month": 9, "day": 2}
        res_t = ae.calculate_full_profile(data_trading)
        self.assertIn("astro_trade_setup", res_t)

        data_bradley = {"mode": "bradley", "year": 2026, "month": 9, "day": 2}
        res_b = ae.calculate_full_profile(data_bradley)
        self.assertIn("bradley_siderograph", res_b)

        data_gann = {"mode": "gann_sq9", "price": 65000.0, "asset": "BTC", "year": 2026, "month": 9, "day": 2}
        res_g = ae.calculate_full_profile(data_gann)
        self.assertIn("gann_square_of_9", res_g)

        data_crd = {"mode": "crd_calendar", "year": 2026, "month": 9, "day": 2}
        res_c = ae.calculate_full_profile(data_crd)
        self.assertIn("geocosmic_crd", res_c)

        data_mcw = {"mode": "mcwhirter", "year": 2026, "month": 9, "day": 2}
        res_m = ae.calculate_full_profile(data_mcw)
        self.assertIn("mcwhirter_cycle", res_m)

        data_angles = {"mode": "gann_angles", "pivot_price": 60000.0, "bars_elapsed": 10}
        res_a = ae.calculate_full_profile(data_angles)
        self.assertIn("gann_angles", res_a)

        data_bayer = {"mode": "bayer", "year": 2026, "month": 9, "day": 2}
        res_by = ae.calculate_full_profile(data_bayer)
        self.assertIn("bayer_mercury_analysis", res_by)


if __name__ == "__main__":
    unittest.main(verbosity=2)
