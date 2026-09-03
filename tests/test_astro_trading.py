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


class TestAstroTradingInstitutionalMasterTier(unittest.TestCase):
    """Test Barbault BCI, Gann Mass Pressure, Sepharial Silver Key & Trade Card."""

    def test_barbault_cyclical_index(self):
        lons = {"Jupiter": 120.0, "Saturn": 10.0, "Uranus": 60.0, "Neptune": 0.0, "Pluto": 300.0}
        bci = ate.BarbaultCyclicalIndexEngine.compute_bci(lons)
        self.assertIn("bci_total_arc_degrees", bci)
        self.assertEqual(len(bci["ten_planetary_arcs"]), 10)
        self.assertGreater(bci["bci_total_arc_degrees"], 0)

    def test_gann_mass_pressure(self):
        mp_pt = ate.GannMassPressureEngine.compute_mass_pressure_point(0.0)
        self.assertIsInstance(mp_pt, float)
        forecast = ate.GannMassPressureEngine.generate_mass_pressure_forecast(datetime(2026, 9, 2), months_forward=12)
        self.assertEqual(len(forecast), 12)
        self.assertIn("mass_pressure_score", forecast[0])

    def test_sepharial_silver_key(self):
        tide = ate.SepharialTidalEngine.evaluate_lunar_tide(14.8) # High speed near perigee
        self.assertIn("Lunar Perigee Climax", tide["market_condition"])
        self.assertEqual(tide["tactical_posture"], "HIGH_VOLATILITY_BREAKOUT")

    def test_institutional_trade_card(self):
        card = ate.AstroTradeOrchestrator.generate_institutional_trade_card(
            asset_key="BTC",
            current_price=65000.0,
            macro_bias_score=60.0,
            swing_crd_score=80.0,
            swing_direction=1,
            intraday_score=50.0
        )
        self.assertEqual(card["asset"], "BTC")
        self.assertIn("INSTITUTIONAL STRONG BUY", card["institutional_action"])
        self.assertGreater(card["composite_confluence_score"], 50.0)
        self.assertIn("stop_loss", card["order_matrix"])


class TestContemporaryMastersSetups(unittest.TestCase):
    """Test Arch Crawford, Michael Jenkins, Dan Ferrera, Olga Morales, Alphee Lavoie."""

    def test_crawford_crash_trigger(self):
        res_crash = ate.CrawfordCrashTriggerEngine.evaluate_crash_hazard(
            mars_lon=60.0, uranus_lon=60.5, is_lunar_perigee=True, is_eclipse_window=True
        )
        self.assertTrue(res_crash["is_crash_warning_active"])
        self.assertIn("CRITICAL CRASH", res_crash["status"])

    def test_jenkins_price_time_squaring(self):
        res_j = ate.JenkinsGeometryEngine.calculate_price_time_square(pivot_price=6400.0, harmonic_deg=90.0, direction=1)
        self.assertEqual(res_j["target_price"], 6480.25) # (80 + 0.5)^2 = 80.5^2
        self.assertEqual(res_j["natural_time_squaring_bars"], 80)

    def test_ferrera_panic_cycle(self):
        res_f = ate.FerreraMasterCycleEngine.evaluate_panic_cycle_node(months_from_major_low=42)
        self.assertIn("Month 42 (180° Opposition)", res_f["cycle_stage"])
        self.assertEqual(res_f["tactical_action"], "HIGH_VOLATILITY_REVERSAL_BUY")

    def test_olga_morales_4min_clock(self):
        res_o = ate.OlgaMoralesIntradayEngine.calculate_4min_turning_trigger(minutes_since_session_open=360.0) # 360 min = 90 deg
        self.assertEqual(res_o["current_diurnal_degree"], 90.0)
        self.assertTrue(res_o["is_intraday_turning_trigger"])

    def test_lavoie_asteroid_metrics(self):
        res_ast = ate.LavoieAsteroidHarmonicsEngine.get_asteroid_probability_metric("PALLAS")
        self.assertEqual(res_ast["asteroid"], "PALLAS")
        self.assertTrue(res_ast["is_statistically_actionable"])

    def test_eight_masters_exhaustive_setups(self):
        all_8 = ate.EightMastersExhaustiveSetupsEngine.evaluate_all_eight_setups("BTC", 65000.0, atr14=1200.0)
        self.assertEqual(len(all_8), 8)
        self.assertEqual(all_8[0]["setup_id"], "GANN_SWING_SQ9")
        self.assertIn("stop_loss", all_8[0])
        self.assertIn("take_profit_1", all_8[0])
        self.assertIn("take_profit_2", all_8[0])
        # Check CLI integration
        res_cli = ae.calculate_full_profile({"mode": "eight_masters", "asset": "BTC", "price": 65000.0})
        self.assertIn("eight_masters_exhaustive_setups", res_cli)
        self.assertEqual(len(res_cli["eight_masters_exhaustive_setups"]), 8)


class TestUndergroundAndAdvancedMasters(unittest.TestCase):
    """Test Murrey Math, Jeanne Long Universal Clock, Larry Williams, Bayer Polarity & Crypto Accelerator."""

    def test_murrey_math_octaves(self):
        frame = ate.MurreyMathGannOctavesEngine.calculate_murrey_frame(65000.0)
        self.assertEqual(frame["master_frame"], "[0.0 to 100000.0]")
        self.assertEqual(frame["octave_step"], 12500.0)
        self.assertIn("4/8_Major_Equilibrium_Mid", frame["murrey_levels"])
        self.assertEqual(frame["murrey_levels"]["4/8_Major_Equilibrium_Mid"], 50000.0)

    def test_jeanne_long_universal_clock(self):
        lons = {"Mars": 90.0, "Jupiter": 180.0}
        clock = ate.JeanneLongUniversalClockEngine.calculate_universal_clock_moment(hour_utc=6, minute_utc=0, current_price=65000.0, planetary_lons=lons)
        self.assertEqual(clock["universal_clock_time_angle"], 90.0)
        self.assertTrue(clock["has_intraday_reversal_trigger"])

    def test_larry_williams_lunar_edge(self):
        edge_nm = ate.LarryWilliamsLunarEdgeEngine.evaluate_lunar_phase_edge(days_since_new_moon=1.5)
        self.assertEqual(edge_nm["tactical_bias"], "BULLISH_ACCUMULATION")
        edge_fm = ate.LarryWilliamsLunarEdgeEngine.evaluate_lunar_phase_edge(days_since_new_moon=14.8)
        self.assertEqual(edge_fm["tactical_bias"], "BEARISH_PULLBACK_CAUTION")

    def test_bayer_declination_polarity(self):
        flip = ate.BayerDeclinationPolarityEngine.check_declination_polarity_flip(current_decl=0.15, previous_decl=-0.20, planet="Moon")
        self.assertTrue(flip["is_polarity_flip_active"])
        self.assertIn("BULLISH_MOMENTUM_SURGE", flip["polarity_signal"])

    def test_crypto_genesis_accelerator(self):
        t_lons = {"Mars": 283.57} # Exact hit on BTC genesis Mars
        acc = ate.CryptoGenesisAcceleratorEngine.evaluate_crypto_inception_trigger(t_lons)
        self.assertTrue(acc["has_crypto_acceleration_trigger"])
        self.assertGreater(acc["active_triggers_count"], 0)

    def test_institutional_master_signal_7step(self):
        t_lons = {"Sun": 160.0, "Moon": 162.0, "Mars": 283.57, "Jupiter": 120.0, "Saturn": 10.0, "Uranus": 60.0, "Neptune": 0.0, "Pluto": 300.0, "North Node": 92.0}
        speeds = {"Mars": 0.02, "Mercury": 1.2, "Venus": 1.0}
        decls = {"Moon": 0.10, "Mars": 15.0}
        sig = ate.InstitutionalMasterSignalEngine.generate_master_signal(
            asset_key="BTC",
            current_price=65000.0,
            target_date=datetime(2026, 9, 3, 12, 0),
            planetary_lons=t_lons,
            planetary_speeds=speeds,
            planetary_decls=decls,
            atr14=1200.0,
            is_moon_voc=False
        )
        self.assertEqual(sig["asset"], "BTC")
        self.assertIn(sig["directional_signal"], ("INSTITUTIONAL STRONG BUY", "BUY / ACCUMULATE", "HOLD / CASH PRESERVATION", "SELL / SHORT"))
        self.assertGreaterEqual(sig["confluence_score"], 25.0)
        self.assertIn("entry_price", sig["order_parameters"])
        self.assertIn("stop_loss", sig["order_parameters"])
        self.assertIn("take_profit_1", sig["order_parameters"])
        self.assertIn("take_profit_2", sig["order_parameters"])
        self.assertIn("take_profit_3", sig["order_parameters"])
        self.assertIn("narrative_fa", sig)
        # Check CLI mode
        res_cli = ae.calculate_full_profile({"mode": "master_signal", "asset": "BTC", "price": 65000.0})
        self.assertIn("institutional_master_signal", res_cli)


class TestApexMasterSuiteEngines(unittest.TestCase):
    """Test Solar System Barycenter, Digital Spectral FFT, Williams COT Confluence & Walker Polar Targets."""

    def test_solar_system_barycenter(self):
        helio_lons = {"Jupiter": 120.0, "Saturn": 10.0, "Uranus": 60.0, "Neptune": 0.0}
        ssb = ate.SolarSystemBarycenterEngine.compute_barycenter_displacement(helio_lons)
        self.assertIn("barycenter_distance_au", ssb)
        self.assertIn("barycenter_displacement_solar_radii", ssb)
        self.assertGreater(ssb["barycenter_displacement_solar_radii"], 0.0)

    def test_digital_spectral_fft(self):
        # Synthetic cyclical wave series with known length
        prices = [100.0 + 10.0 * math.sin(2.0 * math.pi * i / 12.0) for i in range(48)]
        cycles = ate.DigitalSpectralFFTEngine.extract_dominant_cycles(prices, top_k=3)
        self.assertGreater(len(cycles), 0)
        self.assertIn("period_bars", cycles[0])
        self.assertAlmostEqual(cycles[0]["period_bars"], 12.0, delta=1.0)

    def test_williams_cot_confluence(self):
        cot_buy = ate.WilliamsCOTConfluenceEngine.evaluate_cot_lunar_signal(
            net_commercial=48000.0, min_commercial_156=10000.0, max_commercial_156=50000.0,
            days_since_new_moon=1.0, williams_r14=-85.0
        )
        self.assertIn("LARRY_WILLIAMS_ULTRA_BUY", cot_buy["institutional_confluence_signal"])
        self.assertEqual(cot_buy["macro_bias"], "MAXIMUM_BULLISH_CONFLUENCE")

    def test_walker_polar_targets(self):
        p_targets = ate.WalkerPolarTargetEngine.compute_polar_harmonics(100.0) # root 10.0
        self.assertEqual(p_targets["target_180deg_opposition"], 121.0) # (10 + 1)^2
        self.assertEqual(p_targets["target_360deg_full_octave"], 144.0) # (10 + 2)^2
        self.assertIn("sub_harmonic_stop_loss_22_5deg", p_targets)

    def test_master_audit_cli(self):
        res_audit = ae.calculate_full_profile({"mode": "master_audit", "asset": "BTC", "price": 65000.0})
        self.assertIn("master_audit_suite", res_audit)
        suite = res_audit["master_audit_suite"]
        self.assertIn("master_signal", suite)
        self.assertIn("barycenter", suite)
        self.assertIn("walker_polar", suite)
        self.assertIn("eight_masters", suite)


class TestCowanSBCMusicalAndSimulationSuite(unittest.TestCase):
    """Test Bradley Cowan 4D, Sarvatobhadra Chakra 81-grid, Musical Harmonics, Kinematics & Backtester."""

    def test_cowan_4d_platonic(self):
        phi_exp = ate.BradleyCowan4DGeometryEngine.compute_pentagonal_phi_expansions(100.0, 30.0)
        self.assertIn("T_1 (1.618x)", phi_exp["pentagonal_time_nodes_days"])
        self.assertEqual(phi_exp["pentagonal_time_nodes_days"]["T_1 (1.618x)"], 48.5)
        self.assertEqual(phi_exp["pentagonal_price_expansions"]["P_1 (1.618x)"], 161.8)

    def test_sarvatobhadra_chakra(self):
        nak_map = {"Jupiter": 15, "Venus": 15, "Saturn": 28} # 15 casts front vedha on Janma 1
        sbc = ate.SarvatobhadraChakra81Engine.evaluate_sbc_vedha_score(nak_map, janma_nakshatra_idx=1)
        self.assertIn("sbc_composite_vedha_score", sbc)
        self.assertIn("tactical_bias", sbc)

    def test_pythagorean_musical_harmonics(self):
        music = ate.PythagoreanMusicalHarmonicsEngine.compute_musical_price_ladder(100.0)
        self.assertEqual(music["musical_overtone_levels"]["Octave (2:1)"], 200.0)
        self.assertEqual(music["musical_overtone_levels"]["Perfect Fifth (3:2)"], 150.0)

    def test_planetary_kinematics(self):
        kin = ate.PlanetaryKinematicsAccelerationEngine.compute_kinematics(118.0, 119.0, 120.0, 121.0, 122.0)
        self.assertEqual(kin["angular_velocity_deg_day"], 1.0)
        self.assertEqual(kin["angular_acceleration_deg_day2"], 0.0)
        self.assertTrue(kin["is_acceleration_inflection"])

    def test_saros_eclipse_family(self):
        saros = ate.SarosEclipseFamiliesEngine.evaluate_saros_recurrence(datetime(2026, 9, 3))
        self.assertIn("saros_cycles_from_1929", saros)
        self.assertGreater(saros["saros_cycles_from_1929"], 5.0)

    def test_backtest_simulator(self):
        prices = [100.0, 102.0, 105.0, 108.0, 112.0, 115.0, 120.0, 125.0]
        signals = [1, 1, 1, 1, 1, 1, 1, 1]
        sim = ate.QuantitativeAstroBacktestSimulator.simulate_strategy_performance(prices, signals)
        self.assertGreater(sim["final_equity"], 100000.0)
        self.assertEqual(sim["win_rate_percentage"], "100.0%")
        self.assertIn("annualized_sharpe_ratio", sim)

    def test_astraea_quant_trading_api_backtest(self):
        bt_res = ate.AstraeaQuantTradingAPI.run_historical_backtest("BTC")
        self.assertEqual(bt_res["asset"], "BTC")
        self.assertEqual(bt_res["verification_status"], "AUDITED_AND_REPRODUCIBLE")
        self.assertIn("performance_metrics", bt_res)
        self.assertGreater(bt_res["total_bars_evaluated"], 100)
        self.assertGreaterEqual(bt_res["performance_metrics"]["profit_factor"], 2.0)

    def test_astraea_quant_trading_api_decisive_signal(self):
        t_lons = {"Sun": 160.0, "Moon": 162.0, "Mars": 283.57, "Jupiter": 120.0, "Saturn": 10.0, "Uranus": 60.0, "Neptune": 0.0, "Pluto": 300.0, "North Node": 92.0}
        speeds = {"Mars": 0.02, "Mercury": 1.2, "Venus": 1.0}
        decls = {"Moon": 0.10, "Mars": 15.0}
        sig = ate.AstraeaQuantTradingAPI.analyze_market_decisive(
            asset_key="BTC", current_price=65000.0, target_date=datetime(2026, 9, 3),
            planetary_lons=t_lons, planetary_speeds=speeds, planetary_decls=decls
        )
        self.assertIn("decisive_action", sig)
        self.assertIn("is_actionable_trade_active", sig)
        # Check CLI integration
        res_cli = ae.calculate_full_profile({"mode": "run_backtest", "asset": "BTC"})
        self.assertIn("historical_astro_backtest", res_cli)


if __name__ == "__main__":
    unittest.main(verbosity=2)
