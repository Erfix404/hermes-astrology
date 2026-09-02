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

        data_wave = {"mode": "harmonic_wave", "days": 30}
        res_w = ae.calculate_full_profile(data_wave)
        self.assertIn("harmonic_planetary_wave", res_w)

        data_clock = {"mode": "gann_clock", "price": 65000.0, "hour_utc": 13}
        res_ck = ae.calculate_full_profile(data_clock)
        self.assertIn("gann_circle_24", res_ck)

        data_gt = {"mode": "genesis_transits", "asset": "BTC"}
        res_gt = ae.calculate_full_profile(data_gt)
        self.assertIn("genesis_transits", res_gt)

        data_dash = {"mode": "terminal_dashboard", "asset": "BTC", "price": 65000.0}
        res_dash = ae.calculate_full_profile(data_dash)
        self.assertIn("terminal_dashboard", res_dash)


class TestAstroTradingEliteModules(unittest.TestCase):
    """Test Harmonic Waves, Circle of 24 Clock, Genesis Horoscopy & Terminal Dashboard."""

    def test_harmonic_composite_wave(self):
        w0 = ate.HarmonicCompositeWaveEngine.compute_wave_at_day(0.0)
        self.assertIsInstance(w0, float)
        series = ate.HarmonicCompositeWaveEngine.forecast_composite_series(datetime(2026, 9, 2), days=30)
        self.assertEqual(len(series), 30)
        spark = ate.HarmonicCompositeWaveEngine.render_sparkline([d["composite_wave_value"] for d in series])
        self.assertEqual(len(spark), 30)

    def test_gann_circle_24_clock(self):
        pivots = ate.GannCircle24ClockEngine.compute_intraday_pivots(current_price=65000.0, session_hour_utc=13)
        self.assertEqual(pivots["session_hour_utc"], 13)
        self.assertEqual(pivots["diurnal_rotation_deg"], 195.0)
        self.assertIn("+0h (0°)", pivots["intraday_price_ladder"])

    def test_asset_genesis_horoscopy_btc(self):
        t_lons = {"Jupiter": 283.5, "Saturn": 171.4, "Pluto": 271.3} # Exact conjunctions to BTC genesis
        eclipses = [283.5]
        res = ate.AssetGenesisHoroscopyEngine.evaluate_genesis_transits("BTC", t_lons, eclipses)
        self.assertEqual(res["asset_name"], "Bitcoin")
        self.assertGreater(res["active_transits_count"], 0)
        self.assertEqual(len(res["eclipse_triggers"]), 1)

    def test_terminal_dashboard_render(self):
        lons = {"Sun": 160.0, "Mars": 90.5, "Jupiter": 120.0, "Saturn": 350.0}
        speeds = {"Mars": 0.02, "Mercury": 1.2, "Venus": 1.0}
        setup = ate.AstroTradingStrategyEngine.generate_trade_setup("BTC", 65000.0, lons, speeds)
        wave_series = ate.HarmonicCompositeWaveEngine.forecast_composite_series(datetime(2026, 9, 2), 30)
        view = ate.AstroTerminalDashboard.render_dashboard(setup, siderograph_pot=12.5, wave_forecast=wave_series)
        self.assertIn("ASTRAEA CELESTIAL TRADING TERMINAL", view)
        self.assertIn("Market Price", view)
        self.assertIn("EXECUTION PARAMETERS", view)


class TestSixResearchFrontiers(unittest.TestCase):
    """Test 6 Ultra-Deep Financial Astrology Research Frontiers."""

    def test_carolan_spiral_calendar(self):
        p_dt = datetime(2026, 9, 2)
        projs = ate.CarolanSpiralCalendarEngine.compute_spiral_projections(p_dt, max_index=5)
        self.assertEqual(len(projs), 5)
        # Fn = 1 -> days_offset = 29.53
        self.assertAlmostEqual(projs[0]["days_offset"], 29.53, places=1)
        # Clusters
        clusters = ate.CarolanSpiralCalendarEngine.find_spiral_clusters([p_dt, datetime(2026, 8, 1)])
        self.assertIsInstance(clusters, list)

    def test_heliocentric_dynamics(self):
        jd = ae.julian_day(datetime(2026, 9, 2))
        helio_lons = ate.HeliocentricTradingEngine.compute_helio_longitudes(jd)
        self.assertIn("Earth", helio_lons)
        self.assertIn("Mars", helio_lons)
        self.assertTrue(0 <= helio_lons["Mars"] <= 360.0)
        aspects_h = ate.HeliocentricTradingEngine.detect_helio_aspects(jd)
        self.assertIsInstance(aspects_h, list)

    def test_solar_geomagnetic_cycle(self):
        dt = datetime(2026, 9, 2)
        sol = ate.SolarGeomagneticCycleEngine.evaluate_solar_regime(dt)
        self.assertIn("sunspot_activity_intensity", sol)
        self.assertIn("macro_liquidity_regime", sol)
        self.assertIn("strategic_posture", sol)

    def test_gann_advanced_matrices(self):
        # Square of 144
        sq144 = ate.GannAdvancedMatricesEngine.compute_square_of_144(6400.0) # root 80
        self.assertIn("4/8_Octave (180°)", sq144["octave_levels"])
        self.assertEqual(sq144["halfway_gravity_point"], 6561.0) # 81^2

        # Square of 52
        sq52 = ate.GannAdvancedMatricesEngine.compute_square_of_52(datetime(2026, 1, 1))
        self.assertEqual(len(sq52["annual_time_squaring_dates"]), 4)

        # Hexagon Chart
        hex_c = ate.GannAdvancedMatricesEngine.compute_hexagon_chart(100.0) # root 10
        self.assertIn("Hex_1_(60°)", hex_c["hexagon_harmonic_resistances"])

    def test_sector_astro_resonance(self):
        sec_crypto = ate.SectorAstroResonanceEngine.evaluate_sector("CRYPTO")
        self.assertIn("Uranus", sec_crypto["cosmic_rulers"])
        sec_oil = ate.SectorAstroResonanceEngine.evaluate_sector("CRUDE_OIL")
        self.assertIn("Neptune", sec_oil["cosmic_rulers"])

    def test_astro_statistical_significance(self):
        # Highly positive abnormal returns
        pos_rets = [0.035, 0.042, 0.028, 0.039, 0.031, 0.045, 0.029]
        res_sig = ate.AstroStatisticalSignificanceEngine.calculate_z_score(pos_rets, baseline_mean=0.0005, baseline_std=0.015)
        self.assertTrue(res_sig["is_statistically_significant"])
        self.assertGreater(res_sig["z_score"], 2.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
