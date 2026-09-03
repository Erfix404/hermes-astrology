#!/usr/bin/env python3
"""Astraea Financial Astrology & Astro-Trading Engine (v4.1.0).
Comprehensive Quantitative Cosmic Market Intelligence System.
Based on:
- W.D. Gann: Square of 9, Planetary Price Lines, Geometric Angles, Law of Vibration
- Donald Bradley: Siderograph Potential Models (Aspect weights + Declinations)
- Raymond Merriman (MMA): Geocosmic Signatures & Critical Reversal Dates (CRD)
- Louise McWhirter: North Node 18.6-Year Macro Business Cycle
- Bill Meridian: Planetary Stock Trading & First-Trade / Genesis Horoscopes

Zero heavy external dependencies — pure Python with math and ephemeris integration.
"""

from typing import Dict, List, Optional, Tuple, Any
import math
from datetime import datetime, timedelta, timezone

# ═════════════════════════════════════════════════════════════════════════════
#  1. ASSET GENESIS REGISTRY (First-Trade & Inception Epochs)
# ═════════════════════════════════════════════════════════════════════════════

FINANCIAL_GENESIS_REGISTRY: Dict[str, Dict[str, Any]] = {
    "BTC": {
        "name": "Bitcoin",
        "category": "Crypto",
        "date": "2009-01-03 18:15:05",
        "lat": 51.5074, "lng": -0.1278, # London (Genesis Block Time)
        "sun_sign": "Capricorn",
        "gann_multiplier": 100.0,
        "description": "Bitcoin Genesis Block (Block 0 mined by Satoshi Nakamoto)"
    },
    "ETH": {
        "name": "Ethereum",
        "category": "Crypto",
        "date": "2015-07-30 15:26:13",
        "lat": 47.1662, "lng": 8.5155, # Zug, Switzerland
        "sun_sign": "Leo",
        "gann_multiplier": 10.0,
        "description": "Ethereum Frontier Genesis Block execution"
    },
    "SOL": {
        "name": "Solana",
        "category": "Crypto",
        "date": "2020-03-16 12:00:00",
        "lat": 37.7749, "lng": -122.4194, # San Francisco
        "sun_sign": "Pisces",
        "gann_multiplier": 1.0,
        "description": "Solana Genesis Block / Mainnet Beta Launch"
    },
    "SPX": {
        "name": "S&P 500 / NYSE",
        "category": "Indices",
        "date": "1792-05-17 14:56:02",
        "lat": 40.7128, "lng": -74.0060, # Wall Street, New York
        "sun_sign": "Taurus",
        "gann_multiplier": 10.0,
        "description": "NYSE Buttonwood Agreement"
    },
    "NASDAQ": {
        "name": "Nasdaq Composite",
        "category": "Indices",
        "date": "1971-02-08 09:30:00",
        "lat": 40.7128, "lng": -74.0060, # New York
        "sun_sign": "Aquarius",
        "gann_multiplier": 10.0,
        "description": "First Day of Nasdaq Trading"
    },
    "GOLD": {
        "name": "Gold (Fiat Era)",
        "category": "Commodities",
        "date": "1971-08-15 21:00:00",
        "lat": 38.8951, "lng": -77.0364, # Washington D.C.
        "sun_sign": "Leo",
        "gann_multiplier": 10.0,
        "description": "Nixon Shock — End of Gold Standard"
    },
    "OIL": {
        "name": "Crude Oil (WTI Futures)",
        "category": "Commodities",
        "date": "1983-03-30 09:30:00",
        "lat": 40.7128, "lng": -74.0060, # NYMEX, New York
        "sun_sign": "Aries",
        "gann_multiplier": 1.0,
        "description": "NYMEX Light Sweet Crude Oil Futures Contract Launch"
    },
    "EURUSD": {
        "name": "Euro / US Dollar",
        "category": "Forex",
        "date": "1999-01-01 00:00:00",
        "lat": 50.1109, "lng": 8.6821, # Frankfurt (ECB)
        "sun_sign": "Capricorn",
        "gann_multiplier": 0.001,
        "description": "Official Inception of the Euro Currency"
    },
    "AAPL": {
        "name": "Apple Inc.",
        "category": "Equities",
        "date": "1980-12-12 09:30:00",
        "lat": 40.7128, "lng": -74.0060, # NASDAQ IPO
        "sun_sign": "Sagittarius",
        "gann_multiplier": 1.0,
        "description": "Apple Initial Public Offering (IPO)"
    },
    "NVDA": {
        "name": "NVIDIA Corporation",
        "category": "Equities",
        "date": "1999-01-22 09:30:00",
        "lat": 40.7128, "lng": -74.0060, # NASDAQ IPO
        "sun_sign": "Aquarius",
        "gann_multiplier": 1.0,
        "description": "NVIDIA Initial Public Offering (IPO)"
    }
}

# ═════════════════════════════════════════════════════════════════════════════
#  2. W.D. GANN MATHEMATICAL ENGINE (Square of 9 & Planetary Price Lines)
# ═════════════════════════════════════════════════════════════════════════════

class GannSquare9Engine:
    """W.D. Gann Square of 9 Spiral Calculator:
    Converts between Price and Degrees, computes cardinal & ordinal cross harmonics,
    and calculates dynamic Price-Time resonance levels."""

    @staticmethod
    def price_to_degree(price: float) -> float:
        """Calculate exact angle (0° to 360°) of a price on the Square of 9 spiral."""
        if price <= 0:
            return 0.0
        root = math.sqrt(price)
        # Gann root cycle: each integer addition to sqrt(price) is a 360° rotation (2.0 on root = 360°)
        # Angle theta = (root - int(root)) * 360
        base_cycle = (root % 2.0) / 2.0
        return round((base_cycle * 360.0) % 360.0, 2)

    @staticmethod
    def degree_to_price(base_price: float, degree_offset: float) -> float:
        """Project target price given an angular shift (e.g. +90°, +180°, +360°) on Square of 9."""
        if base_price <= 0:
            return 0.0
        root = math.sqrt(base_price)
        # In Gann Square of 9: 180° = +1.0 to root, 360° = +2.0 to root
        root_delta = degree_offset / 180.0
        target_root = root + root_delta
        if target_root < 0:
            return 0.0
        return round(target_root ** 2, 2)

    @staticmethod
    def compute_harmonics(price: float) -> Dict[str, Any]:
        """Compute key geometric harmonic support and resistance levels from a price pivot."""
        angles = [45, 90, 120, 135, 180, 225, 240, 270, 315, 360]
        resistances = {}
        supports = {}
        for ang in angles:
            resistances[f"+{ang}°"] = GannSquare9Engine.degree_to_price(price, ang)
            supports[f"-{ang}°"] = GannSquare9Engine.degree_to_price(price, -ang)

        return {
            "pivot_price": price,
            "current_angle_deg": GannSquare9Engine.price_to_degree(price),
            "cardinal_cross": {
                "0°_base": price,
                "90°_square": resistances["+90°"],
                "180°_opposition": resistances["+180°"],
                "270°_square": resistances["+270°"],
                "360°_octave": resistances["+360°"]
            },
            "trine_harmonics": {
                "120°_trine": resistances["+120°"],
                "240°_trine": resistances["+240°"]
            },
            "support_levels": supports,
            "resistance_levels": resistances
        }

    @staticmethod
    def planetary_price_lines(planetary_longitudes: Dict[str, float],
                              current_price: float,
                              asset_key: str = "BTC") -> List[Dict[str, Any]]:
        """Calculate dynamic Planetary Price Lines per W.D. Gann & Bill Meridian.
        Formula: Price = (Planet_Longitude + 360 * k) * Scale
        Finds the nearest active support/resistance lines surrounding the current price."""
        mult = FINANCIAL_GENESIS_REGISTRY.get(asset_key, {}).get("gann_multiplier", 10.0)
        lines = []

        for planet, lon in planetary_longitudes.items():
            if planet in ("North Node", "South Node", "Chiron"):
                continue
            base_p = lon * mult
            # Find cycle index k that brackets current_price
            cycle_span = 360.0 * mult
            if cycle_span <= 0:
                continue
            k = int(current_price // cycle_span)

            candidate_prices = [
                (lon + 360.0 * (k - 1)) * mult,
                (lon + 360.0 * k) * mult,
                (lon + 360.0 * (k + 1)) * mult,
                (lon + 360.0 * (k + 2)) * mult
            ]

            for cp in candidate_prices:
                if cp <= 0: continue
                diff_pct = round(((cp - current_price) / current_price) * 100.0, 2)
                if abs(diff_pct) <= 25.0: # Filter lines within +/- 25% of current price
                    lines.append({
                        "planet": planet,
                        "longitude_deg": round(lon, 2),
                        "price_level": round(cp, 2),
                        "distance_pct": diff_pct,
                        "role": "Resistance" if cp > current_price else "Support"
                    })

        lines.sort(key=lambda x: abs(x["distance_pct"]))
        return lines


class GannAnglesEngine:
    """W.D. Gann Geometric Price-Time Squaring & Angles Calculator.
    Calculates the 9 canonical Gann Rays (1x8, 1x4, 1x3, 1x2, 1x1, 2x1, 3x1, 4x1, 8x1)
    from a swing pivot point over time steps (bars/days)."""

    GANN_RAY_RATIOS = {
        "1x8": 8.0,    # 1 Unit Time = 8 Units Price (Ultra Fast)
        "1x4": 4.0,    # 1 Unit Time = 4 Units Price
        "1x3": 3.0,    # 1 Unit Time = 3 Units Price
        "1x2": 2.0,    # 1 Unit Time = 2 Units Price
        "1x1": 1.0,    # 1 Unit Time = 1 Unit Price (True Equilibrium / 45°)
        "2x1": 0.5,    # 2 Units Time = 1 Unit Price (1/2)
        "3x1": 0.3333, # 3 Units Time = 1 Unit Price (1/3)
        "4x1": 0.25,   # 4 Units Time = 1 Unit Price (1/4)
        "8x1": 0.125   # 8 Units Time = 1 Unit Price (1/8)
    }

    @staticmethod
    def project_angles(pivot_price: float,
                       bars_elapsed: int,
                       price_unit: float = 1.0,
                       direction: str = "up") -> Dict[str, float]:
        """Project dynamic Gann Angle levels for a given number of bars elapsed from a pivot."""
        levels = {}
        sign = 1.0 if direction.lower() == "up" else -1.0
        for name, ratio in GannAnglesEngine.GANN_RAY_RATIOS.items():
            proj_p = pivot_price + (sign * ratio * price_unit * bars_elapsed)
            levels[name] = round(max(0.0, proj_p), 2)
        return {
            "pivot_price": pivot_price,
            "bars_elapsed": bars_elapsed,
            "direction": direction,
            "angles": levels,
            "equilibrium_1x1": levels["1x1"],
            "rule": "W.D. Gann Price and Time Balance: Market remains bullish above 1x1 and bearish below 1x1."
        }


class GeorgeBayerEngine:
    """George Bayer Planetary Speed & 5-Fold Quintile Harmonic Engine (1937/1942).
    Evaluates Mercury/Mars speeds, 5-fold Quintile harmonics (72°, 144°, 216°, 288°),
    and Egg of Columbus acceleration inflection points."""

    QUINTILE_ANGLES = [72.0, 144.0, 216.0, 288.0]

    @staticmethod
    def evaluate_mercury_speed(mercury_speed_lon: float) -> Dict[str, Any]:
        """Classify Mercury speed relative to mean motion (~1.38°/day)."""
        abs_spd = abs(mercury_speed_lon)
        if abs_spd <= 0.05:
            cond = "Stationary (Imminent Major Trend Reversal)"
            action = "PREPARE_PIVOT"
        elif mercury_speed_lon < 0:
            cond = "Retrograde Motion (Choppy, Whipsaws, Counter-trend Rallies)"
            action = "MEAN_REVERSION"
        elif abs_spd >= 1.80:
            cond = "Maximum Velocity (Blowout Climax Phase / Extreme Momentum)"
            action = "TREND_ACCELERATION"
        else:
            cond = "Normal Direct Motion"
            action = "TREND_FOLLOWING"

        return {
            "mercury_speed_deg_day": round(mercury_speed_lon, 3),
            "condition": cond,
            "recommended_strategy": action,
            "source": "George Bayer, Time Factors in the Stock Market (1937)"
        }

    @staticmethod
    def compute_quintile_levels(base_degree: float) -> List[float]:
        """Compute the 5-fold Pentagram harmonics from a base degree."""
        return [round((base_degree + ang) % 360.0, 2) for ang in GeorgeBayerEngine.QUINTILE_ANGLES]

# ═════════════════════════════════════════════════════════════════════════════
#  3. DONALD BRADLEY SIDEROGRAPH ENGINE (Quantitative Planetary Potential)
# ═════════════════════════════════════════════════════════════════════════════

class BradleySiderographEngine:
    """Donald Bradley Siderograph Potential Calculator (1947).
    Calculates net planetary potential curve by summing:
    1. Long-Term aspects (Jupiter, Saturn, Uranus, Neptune, Pluto)
    2. Middle-Term aspects (Sun, Mars, Venus, Mercury with outer planets)
    3. Declinations of Venus and Mars.
    Peaks and troughs identify critical macroeconomic turning points."""

    ASPECT_WEIGHTS = {
        "conjunction": (0.0, 10.0, 1.0),   # angle, orb, weight
        "sextile":     (60.0, 6.0, 0.5),
        "square":      (90.0, 8.0, -1.0),
        "trine":       (120.0, 8.0, 1.0),
        "opposition":  (180.0, 10.0, -1.0),
        "parallel":    (0.0, 1.5, 0.75),
        "contraparallel": (0.0, 1.5, -0.75)
    }

    OUTER_PLANETS = {"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
    INNER_PLANETS = {"Sun", "Mercury", "Venus", "Mars"}

    @staticmethod
    def calculate_potential(lons: Dict[str, float],
                            decls: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Compute single-day Bradley Potential components."""
        long_term = 0.0
        middle_term = 0.0

        planets = list(lons.keys())
        n = len(planets)

        for i in range(n):
            for j in range(i + 1, n):
                p1, p2 = planets[i], planets[j]
                if p1 in ("North Node", "South Node") or p2 in ("North Node", "South Node"):
                    continue

                diff = abs((lons[p1] - lons[p2] + 180.0) % 360.0 - 180.0)

                # Check major aspects
                for asp_name, (ang, orb, w) in BradleySiderographEngine.ASPECT_WEIGHTS.items():
                    if asp_name in ("parallel", "contraparallel"):
                        continue
                    dev = abs(diff - ang)
                    if dev <= orb:
                        val = w * (1.0 - (dev / orb))
                        if p1 in BradleySiderographEngine.OUTER_PLANETS and p2 in BradleySiderographEngine.OUTER_PLANETS:
                            long_term += val * 2.0 # Outer-outer pairs have double weight
                        else:
                            middle_term += val

        # Declination component (if provided)
        decl_term = 0.0
        if decls:
            if "Venus" in decls:
                decl_term += decls["Venus"] * 0.2
            if "Mars" in decls:
                decl_term += decls["Mars"] * 0.2

        net_potential = long_term + middle_term + decl_term

        return {
            "long_term_potential": round(long_term, 3),
            "middle_term_potential": round(middle_term, 3),
            "declination_potential": round(decl_term, 3),
            "net_siderograph_potential": round(net_potential, 3)
        }

# ═════════════════════════════════════════════════════════════════════════════
#  4. RAYMOND MERRIMAN GEOCOSMIC & CRD ENGINE (Critical Reversal Dates)
# ═════════════════════════════════════════════════════════════════════════════

class MerrimanCRDEngine:
    """Raymond Merriman (MMA) Geocosmic Market Timing Engine.
    Identifies Critical Reversal Dates (CRD) by clustering high-potency geocosmic signatures:
    - Level 1 (Weight 10): Planetary Stations (Direct/Retrograde), Cardinal Ingresses of Sun/Mars, Solar/Lunar Eclipses.
    - Level 2 (Weight 6): Hard aspects (0°, 90°, 180°) between outer planets and Sun/Mars.
    - Level 3 (Weight 3): Soft aspects (60°, 120°) and lunar phases.
    When composite window score >= 15 within a 3-day orb, a high-probability reversal is flagged."""

    @staticmethod
    def evaluate_crd_cluster(signatures: List[Dict[str, Any]]) -> Dict[str, Any]:
        score = 0
        sig_count = len(signatures)
        key_events = []

        for sig in signatures:
            lvl = sig.get("level", 3)
            desc = sig.get("description", "")
            if lvl == 1:
                score += 10
                key_events.append(f"Level 1: {desc}")
            elif lvl == 2:
                score += 6
                key_events.append(f"Level 2: {desc}")
            else:
                score += 3
                key_events.append(f"Level 3: {desc}")

        is_crd = score >= 15
        confidence = min(98, 40 + (score * 3))

        return {
            "is_critical_reversal_date": is_crd,
            "crd_score": score,
            "confidence_percentage": confidence,
            "market_status": "HIGH-PROBABILITY PIVOT WINDOW" if is_crd else "Normal Cosmic Flow",
            "active_signatures": key_events,
            "trading_action": (
                "Prepare for major trend exhaustion and reversal; tighten trailing stop-loss and look for exhaustion candles."
                if is_crd else "Trade with prevailing trend; no extreme cosmic inflection detected."
            )
        }

# ═════════════════════════════════════════════════════════════════════════════
#  5. LOUISE MCWHIRTER 18.6-YEAR MACRO BUSINESS CYCLE ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class McWhirterCycleEngine:
    """Louise McWhirter Theory of Stock Market Forecasting (1938).
    Tracks the North Node (18.6-year cycle) through the zodiac to identify macroeconomic tides:
    - Cancer / Leo: Peak prosperity, speculative frenzy, macro bull top.
    - Gemini / Virgo: Transition from expansion to moderation.
    - Taurus / Libra: Balanced economy.
    - Aries / Scorpio: Decline into recession / tightening credit.
    - Pisces / Sagittarius: Deepening contraction.
    - Aquarius / Capricorn: Macro bottom, maximum financial pessimism, generational accumulation window."""

    NODE_ECONOMIC_PHASES = {
        "Cancer": ("Macro Economic Peak", "Extreme euphoria, speculative bubble top, peak corporate profits", "BULLISH_EXHAUSTION"),
        "Leo": ("Late Expansion / Peak", "High market valuations, aggressive capital expenditure", "BULLISH_TOP"),
        "Gemini": ("Upper Transition", "Decelerating growth, distribution phase", "NEUTRAL_TRANSITION"),
        "Virgo": ("Moderation", "Supply chain adjustments, economic cooling", "NEUTRAL_CONSOLIDATION"),
        "Taurus": ("Normal Prosperity", "Steady economic growth, solid dividend yields", "STEADY_ACCUMULATION"),
        "Libra": ("Balanced Equilibrium", "Equilibrium in financial markets", "NEUTRAL_BALANCE"),
        "Aries": ("Contraction Inception", "Monetary tightening, inflation peaks, rising debt strain", "BEARISH_COMMENCEMENT"),
        "Scorpio": ("Intense Liquidity Stress", "Credit contractions, corporate insolvencies, debt workouts", "BEARISH_CONTRACTION"),
        "Pisces": ("Deep Economic Slump", "Stagnation, pessimism, monetary stimulus beginnings", "BEARISH_BOTTOMING"),
        "Sagittarius": ("Recessionary Lows", "Low interest rates, early recovery seeds", "EARLY_RECOVERY"),
        "Aquarius": ("Generational Market Bottom", "Maximum despair, historical buying opportunity", "GENERATIONAL_BUY"),
        "Capricorn": ("Structural Reset", "Austerity, restructuring, bedrock bottom formation", "GENERATIONAL_BUY")
    }

    @staticmethod
    def evaluate_node_cycle(north_node_lon: float) -> Dict[str, Any]:
        signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                 "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        sign_idx = int(north_node_lon // 30) % 12
        sign = signs[sign_idx]
        deg_in_sign = round(north_node_lon % 30.0, 2)

        phase_title, desc, posture = McWhirterCycleEngine.NODE_ECONOMIC_PHASES.get(
            sign, ("Normal Phase", "Standard market condition", "NEUTRAL")
        )

        return {
            "cycle_name": "Louise McWhirter 18.6-Year North Node Business Cycle",
            "north_node_sign": sign,
            "degree_in_sign": deg_in_sign,
            "macro_phase": phase_title,
            "economic_description": desc,
            "strategic_market_posture": posture,
            "reference": "Louise McWhirter, McWhirter Theory of Stock Market Forecasting (1938)"
        }

# ═════════════════════════════════════════════════════════════════════════════
#  6. QUANTITATIVE ASTRO-TRADING STRATEGY & CONFLUENCE ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class AstroTradingStrategyEngine:
    """Master Quantitative Astro-Trading Strategy Synthesizer.
    Evaluates real-time / target market data against all 6 cosmic trading setups:
    1. Planetary Station Pivots
    2. Cardinal Ingress Breakouts
    3. Bradley Siderograph Extrema
    4. Gann Square of 9 Price-Time Lines
    5. Moon Void-of-Course Volatility Filter
    6. Carter Eclipse Resonance Triggers

    Emits actionable signals: Action (BUY / SELL / HOLD), Confluence Score (0-100),
    Stop-Loss, Take-Profit targets, and Risk/Reward analysis."""

    @staticmethod
    def generate_trade_setup(asset_key: str,
                             current_price: float,
                             longitudes: Dict[str, float],
                             speeds: Dict[str, float],
                             eclipses_active: Optional[List[float]] = None,
                             is_moon_voc: bool = False) -> Dict[str, Any]:
        asset_info = FINANCIAL_GENESIS_REGISTRY.get(asset_key.upper(), FINANCIAL_GENESIS_REGISTRY["BTC"])
        confluence_score = 50.0
        bullish_factors = []
        bearish_factors = []
        warnings = []

        # 1. Planetary Station Check (Mars, Mercury, Venus)
        for p in ("Mars", "Mercury", "Venus"):
            spd = speeds.get(p, 1.0)
            if abs(spd) <= 0.05: # Stationary turning point
                if spd < 0: # Stationary Retrograde (usually bearish/turbulent)
                    confluence_score += 15.0
                    bearish_factors.append(f"Stationary Retrograde on {p} (v={spd:.3f}°/day) — high probability trend exhaustion/top")
                else: # Stationary Direct (bullish recovery)
                    confluence_score += 15.0
                    bullish_factors.append(f"Stationary Direct on {p} (v={spd:.3f}°/day) — bullish momentum release/bottoming")

        # 2. Cardinal Ingress Check
        for p in ("Sun", "Mars"):
            lon = longitudes.get(p, 0.0)
            deg_norm = lon % 90.0 # Cardinal points are 0°, 90°, 180°, 270°
            if deg_norm <= 1.0 or deg_norm >= 89.0:
                confluence_score += 12.0
                bullish_factors.append(f"Cardinal World Axis Ingress on {p} (lon={lon:.1f}°) — impending macro volatility breakout")

        # 3. Moon Void-of-Course Rule
        if is_moon_voc:
            warnings.append("MOON VOID-OF-COURSE ACTIVE: Breakouts are high-risk / prone to failure. Prefer Mean-Reversion range trading.")
            confluence_score -= 10.0

        # 4. Gann Square of 9 Resonance
        sq9_info = GannSquare9Engine.compute_harmonics(current_price)
        sq9_angle = sq9_info["current_angle_deg"]
        # Check if price is sitting on a Cardinal Cross level (0°, 90°, 180°, 270°) within 5°
        is_cardinal_cross = any(abs(sq9_angle - target_ang) <= 5.0 for target_ang in (0, 90, 180, 270, 360))
        if is_cardinal_cross:
            confluence_score += 10.0
            bullish_factors.append(f"Gann Square of 9 Harmonic: Price is sitting directly on a Cardinal Cross Angle ({sq9_angle}°)")

        # 5. Planetary Price Lines
        price_lines = GannSquare9Engine.planetary_price_lines(longitudes, current_price, asset_key)
        nearest_support = None
        nearest_resistance = None
        for pl in price_lines:
            if pl["role"] == "Support" and (nearest_support is None or pl["price_level"] > nearest_support["price_level"]):
                nearest_support = pl
            elif pl["role"] == "Resistance" and (nearest_resistance is None or pl["price_level"] < nearest_resistance["price_level"]):
                nearest_resistance = pl

        # Determine Trade Direction
        net_bull = len(bullish_factors)
        net_bear = len(bearish_factors)

        if net_bull > net_bear:
            action = "STRONG BUY" if confluence_score >= 75 else "BUY / ACCUMULATE"
            sl_price = round(nearest_support["price_level"] * 0.98, 2) if nearest_support else round(current_price * 0.95, 2)
            tp1 = round(nearest_resistance["price_level"], 2) if nearest_resistance else round(current_price * 1.08, 2)
            tp2 = round(tp1 * 1.05, 2)
        elif net_bear > net_bull:
            action = "STRONG SELL / SHORT" if confluence_score >= 75 else "SELL / HEDGE"
            sl_price = round(nearest_resistance["price_level"] * 1.02, 2) if nearest_resistance else round(current_price * 1.05, 2)
            tp1 = round(nearest_support["price_level"], 2) if nearest_support else round(current_price * 0.92, 2)
            tp2 = round(tp1 * 0.95, 2)
        else:
            action = "HOLD / CONSOLIDATION"
            sl_price = round(current_price * 0.96, 2)
            tp1 = round(current_price * 1.04, 2)
            tp2 = round(current_price * 1.08, 2)

        return {
            "asset": asset_info["name"],
            "asset_category": asset_info["category"],
            "current_price": current_price,
            "recommended_action": action,
            "confluence_score": min(98, max(25, int(confluence_score))),
            "trade_parameters": {
                "entry_price": current_price,
                "stop_loss": sl_price,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "risk_reward_ratio": f"1:{round(abs(tp1 - current_price) / max(0.01, abs(current_price - sl_price)), 2)}"
            },
            "gann_square_of_9": {
                "current_spiral_angle": f"{sq9_angle}°",
                "nearest_planetary_support": nearest_support,
                "nearest_planetary_resistance": nearest_resistance
            },
            "bullish_cosmic_drivers": bullish_factors,
            "bearish_cosmic_drivers": bearish_factors,
            "operational_warnings": warnings
        }

# ═════════════════════════════════════════════════════════════════════════════
#  7. HARMONIC PLANETARY COMPOSITE WAVE ENGINE (Fourier Synodic Superposition)
# ═════════════════════════════════════════════════════════════════════════════

class HarmonicCompositeWaveEngine:
    """Fourier Planetary Synodic Cycle Composite Wave Engine.
    Superimposes dominant astronomical synodic periods to construct continuous
    predictive momentum and trend waves for financial markets (Timing Solution model)."""

    SYNODIC_CYCLES = {
        "Lunar_Synodic":    {"period_days": 29.5306,   "amplitude": 0.35, "phase": 0.0},
        "Mercury_Synodic":  {"period_days": 115.8775,  "amplitude": 0.50, "phase": 0.5},
        "Venus_Synodic":    {"period_days": 583.9214,  "amplitude": 0.75, "phase": 1.2},
        "Mars_Synodic":     {"period_days": 779.9361,  "amplitude": 1.00, "phase": 2.1},
        "Jupiter_Saturn":   {"period_days": 7253.45,   "amplitude": 2.20, "phase": 0.8},
        "Jupiter_Uranus":   {"period_days": 5046.00,   "amplitude": 1.80, "phase": 3.0},
        "Saturn_Pluto":     {"period_days": 12175.0,   "amplitude": 2.50, "phase": 1.5},
        "Uranus_Pluto":     {"period_days": 47900.0,   "amplitude": 2.00, "phase": 0.0}
    }

    @staticmethod
    def compute_wave_at_day(t_day_offset: float) -> float:
        """Calculate superposition value W(t) = sum(A_k * cos(2*pi*t / T_k + phi_k))."""
        val = 0.0
        for info in HarmonicCompositeWaveEngine.SYNODIC_CYCLES.values():
            t_k = info["period_days"]
            a_k = info["amplitude"]
            phi_k = info["phase"]
            val += a_k * math.cos((2.0 * math.pi * t_day_offset / t_k) + phi_k)
        return round(val, 3)

    @staticmethod
    def forecast_composite_series(start_date: datetime, days: int = 30) -> List[Dict[str, Any]]:
        """Generate day-by-day harmonic wave values for the upcoming forecast window."""
        series = []
        for i in range(days):
            cur_dt = start_date + timedelta(days=i)
            w_val = HarmonicCompositeWaveEngine.compute_wave_at_day(float(i))
            series.append({
                "day_index": i,
                "date": cur_dt.strftime("%Y-%m-%d"),
                "composite_wave_value": w_val
            })
        return series

    @staticmethod
    def render_sparkline(values: List[float]) -> str:
        """Render a clean Unicode sparkline from wave series."""
        if not values:
            return ""
        bars = " ▂▃▄▅▆▇█"
        mn = min(values)
        mx = max(values)
        rng = (mx - mn) if (mx - mn) > 0 else 1.0
        return "".join(bars[min(7, int(((v - mn) / rng) * 7.0))] for v in values)


# ═════════════════════════════════════════════════════════════════════════════
#  8. GANN CIRCLE OF 24 & DIURNAL INTRADAY PLANETARY CLOCK
# ═════════════════════════════════════════════════════════════════════════════

class GannCircle24ClockEngine:
    """W.D. Gann Circle of 24 Diurnal Intraday Planetary Clock.
    Maps the 24-hour diurnal rotation of the Earth (360° / 24 hrs = 15° per hour = 1° per 4 min)
    to calculate intraday price/time turning points across global trading sessions."""

    MAJOR_SESSIONS = {
        "Tokyo_Open":    {"hour_utc": 0,  "name": "Tokyo / Asian Session Open"},
        "London_Open":   {"hour_utc": 7,  "name": "London / European Session Open"},
        "NY_Open":       {"hour_utc": 13, "name": "New York / US Equities Open"},
        "London_Close":  {"hour_utc": 16, "name": "London Fixing / European Close"},
        "NY_Close":      {"hour_utc": 21, "name": "US Market Settlement / Close"}
    }

    @staticmethod
    def compute_intraday_pivots(current_price: float, session_hour_utc: int = 13) -> Dict[str, Any]:
        """Calculate 24-hour diurnal angle and intraday price harmonics."""
        diurnal_angle = (session_hour_utc * 15.0) % 360.0
        # Convert diurnal angle to price ladder via Square of 9
        ladder = {}
        for offset_hr in (0, 3, 6, 9, 12, 18):
            deg = (offset_hr * 15.0)
            ladder[f"+{offset_hr}h ({deg:.0f}°)"] = GannSquare9Engine.degree_to_price(current_price, deg)
            if offset_hr > 0:
                ladder[f"-{offset_hr}h (-{deg:.0f}°)"] = GannSquare9Engine.degree_to_price(current_price, -deg)

        return {
            "session_hour_utc": session_hour_utc,
            "diurnal_rotation_deg": diurnal_angle,
            "hourly_velocity_deg": "15.0°/hour (0.25°/min)",
            "cardinal_hour_angles": {
                "00:00_UTC": 0.0,
                "06:00_UTC": 90.0,
                "12:00_UTC": 180.0,
                "18:00_UTC": 270.0
            },
            "intraday_price_ladder": ladder,
            "rule": "W.D. Gann Circle of 24: High-frequency turning points align with 90° (6-hour) and 45° (3-hour) diurnal harmonics."
        }


# ═════════════════════════════════════════════════════════════════════════════
#  9. BILL MERIDIAN ASSET GENESIS HOROSCOPY & ECLIPSE ALIGNMENT ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class AssetGenesisHoroscopyEngine:
    """Bill Meridian Planetary Stock Trading & Asset Genesis Horoscopy Engine.
    Evaluates Transits to Natal Genesis Horoscopes and identifies Carter Eclipse Activations."""

    ASPECT_ORBS = {
        "conjunction": (0.0, 2.0, "Potent Initiation / Volatility Flash"),
        "sextile":     (60.0, 1.5, "Opportunity / Smooth Liquidity"),
        "square":      (90.0, 2.0, "Crisis / Severe Resistance / Sharp Correction"),
        "trine":       (120.0, 2.0, "Effortless Expansion / Bullish Continuation"),
        "opposition":  (180.0, 2.0, "Climax / Polarization / Major Trend Top or Bottom")
    }

    @staticmethod
    def evaluate_genesis_transits(asset_key: str,
                                 transit_longitudes: Dict[str, float],
                                 active_eclipses: Optional[List[float]] = None) -> Dict[str, Any]:
        """Evaluate real-time celestial transits to the asset's Genesis natal positions."""
        asset_info = FINANCIAL_GENESIS_REGISTRY.get(asset_key.upper(), FINANCIAL_GENESIS_REGISTRY["BTC"])
        # Approximate natal positions for Genesis assets (or derived from genesis epoch)
        # Built-in high-precision Genesis anchor positions:
        genesis_natal = {
            "BTC": {"Sun": 283.5, "Moon": 12.0, "Mercury": 278.4, "Venus": 331.2, "Mars": 272.1, "Jupiter": 299.8, "Saturn": 171.4, "Pluto": 271.3},
            "ETH": {"Sun": 127.2, "Moon": 296.5, "Mercury": 134.1, "Venus": 149.8, "Mars": 105.0, "Jupiter": 148.1, "Saturn": 238.2, "Pluto": 283.8},
            "SPX": {"Sun": 57.0, "Moon": 358.2, "Mercury": 64.5, "Venus": 48.0, "Mars": 334.1, "Jupiter": 110.2, "Saturn": 344.0, "Pluto": 352.0},
            "GOLD": {"Sun": 142.5, "Moon": 74.0, "Mercury": 151.2, "Venus": 115.4, "Mars": 322.0, "Jupiter": 240.1, "Saturn": 64.8, "Pluto": 178.5}
        }.get(asset_key.upper(), {"Sun": 283.5, "Jupiter": 299.8, "Saturn": 171.4})

        hits = []
        for t_body, t_lon in transit_longitudes.items():
            if t_body in ("North Node", "South Node"): continue
            for n_body, n_lon in genesis_natal.items():
                sep = abs((t_lon - n_lon + 180.0) % 360.0 - 180.0)
                for asp_name, (target_ang, max_orb, desc) in AssetGenesisHoroscopyEngine.ASPECT_ORBS.items():
                    dev = abs(sep - target_ang)
                    if dev <= max_orb:
                        hits.append({
                            "transiting_planet": t_body,
                            "genesis_natal_point": n_body,
                            "aspect": asp_name,
                            "exactness_orb": round(dev, 2),
                            "interpretation": desc
                        })

        hits.sort(key=lambda x: x["exactness_orb"])

        # Eclipse activations
        eclipse_triggers = []
        if active_eclipses:
            for ecl_deg in active_eclipses:
                for n_body, n_lon in genesis_natal.items():
                    diff = abs((ecl_deg - n_lon + 180.0) % 360.0 - 180.0)
                    if diff <= 2.0:
                        eclipse_triggers.append({
                            "eclipse_degree": round(ecl_deg, 2),
                            "activated_genesis_point": n_body,
                            "orb": round(diff, 2),
                            "significance": f"CRITICAL ECLIPSE RESONANCE: Eclipse directly activates Genesis {n_body} — major multi-month inflection."
                        })

        return {
            "asset_name": asset_info["name"],
            "genesis_epoch": asset_info["date"],
            "active_transits_count": len(hits),
            "top_genesis_transits": hits[:5],
            "eclipse_triggers": eclipse_triggers,
            "method_source": "Bill Meridian, Planetary Stock Trading IV (2008)"
        }


# ═════════════════════════════════════════════════════════════════════════════
#  10. INTERACTIVE ASCII ASTRO-TRADING TERMINAL & DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════

class AstroTerminalDashboard:
    """Rich ASCII Astro-Trading Terminal & Quantitative Visualizer."""

    @staticmethod
    def render_dashboard(trade_setup: Dict[str, Any],
                         siderograph_pot: float,
                         wave_forecast: List[Dict[str, Any]]) -> str:
        """Render a high-impact, box-drawn ASCII trading terminal view."""
        asset = trade_setup["asset"]
        price = trade_setup["current_price"]
        action = trade_setup["recommended_action"]
        conf = trade_setup["confluence_score"]
        tp = trade_setup["trade_parameters"]
        gann = trade_setup["gann_square_of_9"]

        # Gauge bar (width 12)
        filled = int((conf / 100.0) * 12)
        gauge = "[" + "█" * filled + "░" * (12 - filled) + f"] {conf}%"

        # Sparkline
        wave_vals = [d["composite_wave_value"] for d in wave_forecast[:24]]
        spark = HarmonicCompositeWaveEngine.render_sparkline(wave_vals)

        s1 = gann["nearest_planetary_support"]
        r1 = gann["nearest_planetary_resistance"]
        s1_str = f"${s1['price_level']} ({s1['planet']})" if s1 else "N/A"
        r1_str = f"${r1['price_level']} ({r1['planet']})" if r1 else "N/A"

        out = [
            "╔══════════════════════════════════════════════════════════════════════════════════╗",
            f"║          ASTRAEA CELESTIAL TRADING TERMINAL — {asset.upper():<25} ║",
            "╠══════════════════════════════════════════════════════════════════════════════════╣",
            f"║  Market Price:     ${price:<15.2f}    Recommendation: {action:<22} ║",
            f"║  Cosmic Confluence: {gauge:<18}   Bradley Sidero: {siderograph_pot:+.2f} Potential           ║",
            "╟──────────────────────────────────────────────────────────────────────────────────╢",
            f"║  30-Day Cycle Wave: {spark:<20}    Gann Angle:     {gann['current_spiral_angle']:<15}     ║",
            f"║  Key Planetary S/R: [Sup] {s1_str:<18} [Res] {r1_str:<18}   ║",
            "╟──────────────────────────────────────────────────────────────────────────────────╢",
            f"║  EXECUTION PARAMETERS:                                                           ║",
            f"║    • Entry: ${tp['entry_price']:<10.2f}   • Stop-Loss: ${tp['stop_loss']:<10.2f}                           ║",
            f"║    • Target 1: ${tp['take_profit_1']:<10.2f} • Target 2:   ${tp['take_profit_2']:<10.2f}  • R/R: {tp['risk_reward_ratio']:<10} ║",
            "╚══════════════════════════════════════════════════════════════════════════════════╝"
        ]
        return "\n".join(out)


# ═════════════════════════════════════════════════════════════════════════════
#  11. CHRISTOPHER CAROLAN SPIRAL CALENDAR ENGINE (Lunar-Fibonacci Harmonics)
# ═════════════════════════════════════════════════════════════════════════════

class CarolanSpiralCalendarEngine:
    """Christopher Carolan Spiral Calendar Engine (1992).
    Calculates lunar-Fibonacci projected dates: T_n = L_s * sqrt(F_n).
    Pinpoints future market inflection windows and multi-pivot resonance clusters."""

    LUNAR_SYNODIC_MONTH = 29.530588853
    FIBONACCI_NUMBERS = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765]

    @staticmethod
    def compute_spiral_projections(pivot_date: datetime, max_index: int = 15) -> List[Dict[str, Any]]:
        """Calculate forward spiral dates from a key historical market pivot."""
        projections = []
        for idx in range(1, min(len(CarolanSpiralCalendarEngine.FIBONACCI_NUMBERS), max_index + 1)):
            fn = CarolanSpiralCalendarEngine.FIBONACCI_NUMBERS[idx]
            sqrt_fn = math.sqrt(fn)
            days_delta = CarolanSpiralCalendarEngine.LUNAR_SYNODIC_MONTH * sqrt_fn
            target_dt = pivot_date + timedelta(days=days_delta)
            projections.append({
                "fibonacci_index": idx,
                "fibonacci_number": fn,
                "sqrt_fibonacci": round(sqrt_fn, 4),
                "days_offset": round(days_delta, 2),
                "projected_date": target_dt.strftime("%Y-%m-%d"),
                "synodic_cycles": round(sqrt_fn, 2)
            })
        return projections

    @staticmethod
    def find_spiral_clusters(pivot_dates: List[datetime], max_index: int = 12, cluster_window_days: int = 3) -> List[Dict[str, Any]]:
        """Find convergence dates where multiple historical pivots project into the same narrow window."""
        all_hits: List[Tuple[datetime, datetime, int]] = []
        for p_dt in pivot_dates:
            for pr in CarolanSpiralCalendarEngine.compute_spiral_projections(p_dt, max_index):
                dt_obj = datetime.strptime(pr["projected_date"], "%Y-%m-%d")
                all_hits.append((dt_obj, p_dt, pr["fibonacci_number"]))

        all_hits.sort(key=lambda x: x[0])
        clusters = []
        used = set()

        for i in range(len(all_hits)):
            if i in used: continue
            base_t, orig_p, fn = all_hits[i]
            matched_group = [all_hits[i]]
            for j in range(i + 1, len(all_hits)):
                if abs((all_hits[j][0] - base_t).days) <= cluster_window_days:
                    matched_group.append(all_hits[j])
                    used.add(j)

            if len(matched_group) >= 2: # Cluster of 2 or more hits
                avg_timestamp = sum(m[0].timestamp() for m in matched_group) / len(matched_group)
                avg_dt = datetime.fromtimestamp(avg_timestamp, tz=timezone.utc)
                clusters.append({
                    "cluster_date": avg_dt.strftime("%Y-%m-%d"),
                    "hits_count": len(matched_group),
                    "cluster_power_score": len(matched_group) * 10,
                    "contributing_pivots": [m[1].strftime("%Y-%m-%d") for m in matched_group],
                    "fibonacci_harmonics": [m[2] for m in matched_group]
                })

        clusters.sort(key=lambda x: -x["hits_count"])
        return clusters


# ═════════════════════════════════════════════════════════════════════════════
#  12. HELIOCENTRIC PLANETARY DYNAMICS & HARMONIC INGRESS ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class HeliocentricTradingEngine:
    """Heliocentric Planetary Coordinates & Aspect Harmonic Engine.
    Evaluates True Sun-centered celestial coordinates without Earth retrograde distortion.
    Solves Kepler's equation for heliocentric longitude and calculates helio price lines."""

    # Mean orbital elements (a: AU, e: eccentricity, i: incl deg, N: node deg, w: perihelion deg, M0: mean anom deg, n: daily motion deg)
    HELIO_ELEMENTS = {
        "Mercury": {"a": 0.387098, "e": 0.205630, "w": 77.456, "M0": 174.794, "n": 4.092334},
        "Venus":   {"a": 0.723332, "e": 0.006773, "w": 131.572, "M0": 50.115,  "n": 1.602130},
        "Earth":   {"a": 1.000000, "e": 0.016708, "w": 102.947, "M0": 357.517, "n": 0.985600},
        "Mars":    {"a": 1.523679, "e": 0.093405, "w": 336.040, "M0": 19.373,  "n": 0.524033},
        "Jupiter": {"a": 5.2044,   "e": 0.048498, "w": 14.728,  "M0": 20.020,  "n": 0.083085},
        "Saturn":  {"a": 9.5826,   "e": 0.055546, "w": 92.598,  "M0": 317.020, "n": 0.033444},
        "Uranus":  {"a": 19.2184,  "e": 0.046381, "w": 170.954, "M0": 142.238, "n": 0.011728},
        "Neptune": {"a": 30.1104,  "e": 0.009456, "w": 44.971,  "M0": 256.228, "n": 0.005981},
        "Pluto":   {"a": 39.4820,  "e": 0.248807, "w": 224.066, "M0": 14.882,  "n": 0.003960}
    }

    @staticmethod
    def _solve_kepler(m_deg: float, e: float) -> float:
        """Newton-Raphson solver for Kepler's Equation: M = E - e*sin(E)."""
        m_rad = math.radians(m_deg % 360.0)
        e_rad = m_rad
        for _ in range(15):
            delta = e_rad - e * math.sin(e_rad) - m_rad
            if abs(delta) < 1e-7:
                break
            e_rad -= delta / (1.0 - e * math.cos(e_rad))
        return e_rad

    @staticmethod
    def compute_helio_longitudes(jd: float) -> Dict[str, float]:
        """Compute accurate Heliocentric Longitudes (0° to 360°) for all planets."""
        d = jd - 2451545.0 # Days since J2000.0
        helio_lons = {}
        for p, elem in HeliocentricTradingEngine.HELIO_ELEMENTS.items():
            m_curr = (elem["M0"] + elem["n"] * d) % 360.0
            e_rad = HeliocentricTradingEngine._solve_kepler(m_curr, elem["e"])
            # True anomaly v
            sin_v = (math.sqrt(1.0 - elem["e"]**2) * math.sin(e_rad)) / (1.0 - elem["e"] * math.cos(e_rad))
            cos_v = (math.cos(e_rad) - elem["e"]) / (1.0 - elem["e"] * math.cos(e_rad))
            v_deg = math.degrees(math.atan2(sin_v, cos_v))
            helio_lon = (v_deg + elem["w"]) % 360.0
            helio_lons[p] = round(helio_lon, 2)
        return helio_lons

    @staticmethod
    def detect_helio_aspects(jd: float, orb: float = 2.0) -> List[Dict[str, Any]]:
        """Detect exact heliocentric aspects (Conjunction, Trine, Square, Opposition)."""
        lons = HeliocentricTradingEngine.compute_helio_longitudes(jd)
        aspects = []
        bodies = list(lons.keys())
        for i in range(len(bodies)):
            for j in range(i + 1, len(bodies)):
                p1, p2 = bodies[i], bodies[j]
                sep = abs((lons[p1] - lons[p2] + 180.0) % 360.0 - 180.0)
                for ang, name, bias in [(0.0, "Conjunction", "Initiation"), (60.0, "Sextile", "Smooth"),
                                        (90.0, "Square", "Stress/Reversal"), (120.0, "Trine", "Expansion"),
                                        (180.0, "Opposition", "Polarity/Climax")]:
                    if abs(sep - ang) <= orb:
                        aspects.append({
                            "pair": f"{p1}-{p2}",
                            "aspect": name,
                            "exactness_orb": round(abs(sep - ang), 2),
                            "helio_lons": f"{p1}:{lons[p1]}°, {p2}:{lons[p2]}°",
                            "market_bias": bias
                        })
        return aspects


# ═════════════════════════════════════════════════════════════════════════════
#  13. SOLAR SUNSPOT ACTIVITY & GEOMAGNETIC CYCLE ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class SolarGeomagneticCycleEngine:
    """Solar Sunspot & Hale Magnetic Cycle Macroeconomic Engine.
    Models the 11.07-year Schwabe sunspot wave and 22.14-year Hale magnetic wave.
    Correlates solar maxima with speculative liquidity peaks and minima with accumulation."""

    SCHWABE_CYCLE_YEARS = 11.07
    HALE_CYCLE_YEARS = 22.14
    SOLAR_CYCLE_25_MIN = datetime(2019, 12, 1) # Solar Cycle 25 minimum epoch

    @staticmethod
    def evaluate_solar_regime(target_date: datetime) -> Dict[str, Any]:
        """Compute solar cycle phase, Hale magnetic polarity, and macroeconomic liquidity regime."""
        dt_diff_years = (target_date - SolarGeomagneticCycleEngine.SOLAR_CYCLE_25_MIN).total_seconds() / (365.2422 * 86400)
        phase_in_cycle = (dt_diff_years % SolarGeomagneticCycleEngine.SCHWABE_CYCLE_YEARS) / SolarGeomagneticCycleEngine.SCHWABE_CYCLE_YEARS

        # Sine model of sunspot activity (0.0 to 1.0)
        sunspot_activity_pct = round((math.sin(2.0 * math.pi * phase_in_cycle - math.pi / 2.0) + 1.0) * 50.0, 1)

        # Hale magnetic polarity
        hale_phase = (dt_diff_years % SolarGeomagneticCycleEngine.HALE_CYCLE_YEARS) / SolarGeomagneticCycleEngine.HALE_CYCLE_YEARS
        polarity = "Positive (+ / North Polarity Leading)" if hale_phase < 0.5 else "Negative (- / South Polarity Leading)"

        if sunspot_activity_pct >= 80.0:
            regime = "Solar Maximum / Peak Speculative Expansion (High Volatility, Inflationary Liquidity)"
            posture = "BULLISH_PEAK_DISTRIBUTION"
        elif sunspot_activity_pct <= 25.0:
            regime = "Solar Minimum / Deep Economic Accumulation (Low Volatility, Bedrock Value Formations)"
            posture = "MACRO_ACCUMULATION"
        else:
            regime = "Mid-Cycle Transition Phase"
            posture = "TREND_CONTINUATION"

        return {
            "target_date": target_date.strftime("%Y-%m-%d"),
            "schwabe_cycle_progress": f"{round(phase_in_cycle * 100.0, 1)}%",
            "sunspot_activity_intensity": f"{sunspot_activity_pct}%",
            "hale_magnetic_polarity": polarity,
            "macro_liquidity_regime": regime,
            "strategic_posture": posture,
            "reference": "Edward R. Dewey / Fed Reserve Geomagnetic & Solar Cycle Market Studies"
        }


# ═════════════════════════════════════════════════════════════════════════════
#  14. W.D. GANN ADVANCED GEOMETRIC MATRICES (Square of 144, 52 & Hexagon)
# ═════════════════════════════════════════════════════════════════════════════

class GannAdvancedMatricesEngine:
    """W.D. Gann Master Calculators: Square of 144, Square of 52 & Hexagon Chart."""

    @staticmethod
    def compute_square_of_144(base_price: float) -> Dict[str, Any]:
        """Compute the Master Fibonacci 144 grid (12x12 price-time divisions)."""
        root = math.sqrt(base_price)
        # Fractional eighths of the 144 master circle
        levels = {}
        for n in range(1, 9):
            deg_shift = (n / 8.0) * 360.0
            levels[f"{n}/8_Octave ({deg_shift:.0f}°)"] = round((root + (deg_shift / 180.0)) ** 2, 2)
        return {
            "base_pivot_price": base_price,
            "matrix_type": "W.D. Gann Square of 144 (Master Fibonacci Matrix)",
            "octave_levels": levels,
            "halfway_gravity_point": levels["4/8_Octave (180°)"]
        }

    @staticmethod
    def compute_square_of_52(pivot_date: datetime, weeks_elapsed: int = 52) -> Dict[str, Any]:
        """Compute Square of 52 (52 weeks = 1 solar time year squaring)."""
        projections = {}
        for quarter in (13, 26, 39, 52):
            dt = pivot_date + timedelta(weeks=quarter)
            projections[f"Quarter_{quarter//13}_({quarter}w)"] = dt.strftime("%Y-%m-%d")
        return {
            "pivot_origin": pivot_date.strftime("%Y-%m-%d"),
            "weeks_elapsed": weeks_elapsed,
            "annual_time_squaring_dates": projections,
            "rule": "Square of 52: 13-week quarter cycles mark natural seasonal trend pivots."
        }

    @staticmethod
    def compute_hexagon_chart(current_price: float) -> Dict[str, Any]:
        """Compute Gann Hexagon Chart levels (60° sextile harmonics)."""
        root = math.sqrt(current_price)
        levels = {}
        for k in range(1, 7):
            deg = k * 60.0
            levels[f"Hex_{k}_({deg:.0f}°)"] = round((root + (deg / 180.0)) ** 2, 2)
        return {
            "current_price": current_price,
            "matrix_type": "W.D. Gann Hexagon Chart (60° Radial Ring)",
            "hexagon_harmonic_resistances": levels
        }


# ═════════════════════════════════════════════════════════════════════════════
#  15. SECTOR & ASSET-SPECIFIC COSMIC RESONANCE ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class SectorAstroResonanceEngine:
    """Specialized Sector & Asset Astro-Resonance Synthesizer."""

    SECTOR_RULES = {
        "CRYPTO": {
            "primary_rulers": ["Uranus", "Pluto"],
            "catalysts": "Mars-Uranus hard aspects (sudden massive liquidations/breakouts), Pluto transits (institutional liquidity).",
            "volatility_driver": "Moon Out-of-Bounds & Mercury Retrograde."
        },
        "CRUDE_OIL": {
            "primary_rulers": ["Mars", "Neptune"],
            "catalysts": "Jupiter-Neptune aspects (supply gluts/liquidity surges), Mars-Pluto (geopolitical supply crunches).",
            "volatility_driver": "Aries Cardinal Ingress."
        },
        "GOLD_SILVER": {
            "primary_rulers": ["Sun", "Moon", "Venus"],
            "catalysts": "Sun-Pluto aspects (currency devaluations/safe haven rushes), Venus Retrograde (cyclical price resets).",
            "volatility_driver": "Eclipses on Taurus-Scorpio / Leo-Aquarius axis."
        },
        "TECH_SEMIS": {
            "primary_rulers": ["Mercury", "Uranus"],
            "catalysts": "Mercury speed blowout phases (AI/tech euphoric expansions), Uranus stations (paradigm shifts).",
            "volatility_driver": "Gemini-Aquarius air trines."
        }
    }

    @staticmethod
    def evaluate_sector(sector_name: str) -> Dict[str, Any]:
        s_key = sector_name.upper().replace(" ", "_")
        info = SectorAstroResonanceEngine.SECTOR_RULES.get(s_key, SectorAstroResonanceEngine.SECTOR_RULES["CRYPTO"])
        return {
            "sector": s_key,
            "cosmic_rulers": info["primary_rulers"],
            "primary_catalysts": info["catalysts"],
            "volatility_drivers": info["volatility_driver"]
        }


# ═════════════════════════════════════════════════════════════════════════════
#  16. ASTRO-STATISTICAL SIGNIFICANCE & EVENT-STUDY ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class AstroStatisticalSignificanceEngine:
    """Astro-Statistical Permutation & Event-Study Anomaly Analyzer."""

    @staticmethod
    def calculate_z_score(sample_returns: List[float], baseline_mean: float = 0.0005, baseline_std: float = 0.015) -> Dict[str, Any]:
        """Compute Welch's Z-Score to verify if astro-event returns deviate significantly from random noise."""
        if not sample_returns:
            return {"z_score": 0.0, "is_statistically_significant": False}
        n = len(sample_returns)
        sample_mean = sum(sample_returns) / n
        std_err = baseline_std / math.sqrt(n)
        z = (sample_mean - baseline_mean) / std_err if std_err > 0 else 0.0
        is_sig = abs(z) >= 1.96 # 95% Confidence Level (p < 0.05)

        return {
            "sample_size": n,
            "sample_mean_return": round(sample_mean, 5),
            "z_score": round(z, 3),
            "confidence_level": "99% (p < 0.01)" if abs(z) >= 2.58 else "95% (p < 0.05)" if is_sig else "Not Statistically Significant (Noise)",
            "is_statistically_significant": is_sig,
            "statistical_edge": f"Edge observed: {round((sample_mean - baseline_mean)*100, 3)}% abnormal return" if is_sig else "Within random distribution"
        }


# ═════════════════════════════════════════════════════════════════════════════
#  17. ANDRE BARBAULT PLANETARY CYCLICAL INDEX (BCI) ENGINE (1967)
# ═════════════════════════════════════════════════════════════════════════════

class BarbaultCyclicalIndexEngine:
    """Andre Barbault Planetary Cyclical Index (Indice Cyclique Planétaire - BCI).
    Measures the sum of all 10 mutual angular distances among the 5 outer planets:
    Jupiter, Saturn, Uranus, Neptune, Pluto.
    Formula: BCI(t) = sum_{i < j} min(|lon_i - lon_j|, 360 - |lon_i - lon_j|).
    Velocity dBCI/dt identifies macro secular economic expansions vs systemic crises."""

    OUTER_BODIES = ["Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]

    @staticmethod
    def compute_bci(longitudes: Dict[str, float]) -> Dict[str, Any]:
        """Calculate Barbault BCI index value in degrees [0, 1800]."""
        pairs = []
        total_arc = 0.0
        n = len(BarbaultCyclicalIndexEngine.OUTER_BODIES)

        for i in range(n):
            for j in range(i + 1, n):
                p1 = BarbaultCyclicalIndexEngine.OUTER_BODIES[i]
                p2 = BarbaultCyclicalIndexEngine.OUTER_BODIES[j]
                l1 = longitudes.get(p1, 0.0)
                l2 = longitudes.get(p2, 0.0)
                diff = abs(l1 - l2) % 360.0
                arc = min(diff, 360.0 - diff)
                total_arc += arc
                pairs.append({"pair": f"{p1}-{p2}", "shortest_arc_deg": round(arc, 2)})

        # Classify regime based on BCI amplitude
        if total_arc >= 1100.0:
            regime = "Macro Planetary Dispersion (Secular Economic Prosperity & Global Growth)"
            posture = "SECULAR_BULLISH"
        elif total_arc <= 550.0:
            regime = "Macro Planetary Compression / Crisis Cluster (Major Geopolitical Stress / Stagflation / Reset)"
            posture = "SECULAR_DEFENSIVE_ACCUMULATION"
        else:
            regime = "Neutral / Transitional Global Equilibrium"
            posture = "BALANCED_TREND_FOLLOWING"

        return {
            "bci_total_arc_degrees": round(total_arc, 2),
            "theoretical_range": "0° (All 5 in Conjunction) to 1800° (All in Opposition)",
            "empirical_historical_mean": 900.0,
            "macro_economic_regime": regime,
            "strategic_posture": posture,
            "ten_planetary_arcs": pairs,
            "reference": "Andre Barbault, Les Astres et l'Histoire (1967) / L'Avenir du Monde (2020)"
        }


# ═════════════════════════════════════════════════════════════════════════════
#  18. W.D. GANN MASS PRESSURE COMPOSITE FORECASTING CURVE ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class GannMassPressureEngine:
    """W.D. Gann Mass Pressure Forecasting Curve.
    Superimposes the 4 master cyclical waves:
    1. 60-Year Great Master Cycle (w=0.40)
    2. 20-Year Jupiter-Saturn Synodic Cycle (w=0.25)
    3. 10-Year Decennial Polarity Cycle (w=0.20)
    4. 1-Year Annual Seasonal Cycle (w=0.15)
    Formula: MP(t) = sum(w_k * cos(2*pi*t / T_k + phi_k))."""

    CYCLES = {
        "60Y_Great_Master": {"period_years": 59.578, "weight": 0.40, "phase": 0.5},
        "20Y_Jupiter_Saturn": {"period_years": 19.859, "weight": 0.25, "phase": 1.2},
        "10Y_Decennial":      {"period_years": 10.000, "weight": 0.20, "phase": 2.4},
        "1Y_Seasonal":        {"period_years": 1.0000, "weight": 0.15, "phase": 0.0}
    }

    @staticmethod
    def compute_mass_pressure_point(t_years: float) -> float:
        """Compute single continuous Mass Pressure value normalized in [-100, +100]."""
        raw_val = 0.0
        for info in GannMassPressureEngine.CYCLES.values():
            t_k = info["period_years"]
            w_k = info["weight"]
            phi_k = info["phase"]
            raw_val += w_k * math.cos((2.0 * math.pi * t_years / t_k) + phi_k)
        return round(raw_val * 100.0, 2)

    @staticmethod
    def generate_mass_pressure_forecast(start_date: datetime, months_forward: int = 24) -> List[Dict[str, Any]]:
        """Generate monthly forecast curve of Gann Mass Pressure."""
        series = []
        for m in range(months_forward):
            dt = start_date + timedelta(days=m * 30.4375)
            t_years = m / 12.0
            mp_val = GannMassPressureEngine.compute_mass_pressure_point(t_years)
            series.append({
                "month_offset": m,
                "date": dt.strftime("%Y-%m-%d"),
                "mass_pressure_score": mp_val,
                "projected_bias": "Bullish Expansion" if mp_val > 20 else "Bearish Contraction" if mp_val < -20 else "Consolidation"
            })
        return series


# ═════════════════════════════════════════════════════════════════════════════
#  19. SEPHARIAL TIDAL & INTRA-DAY TIMING ENGINE (The Silver Key)
# ═════════════════════════════════════════════════════════════════════════════

class SepharialTidalEngine:
    """Sepharial (Dr. Walter Gorn Old, 1913) Market Timing & Lunar Velocity Tide Engine.
    Evaluates:
    1. Lunar Anomalistic Speed & Tidal Pressure (Apogee vs Perigee)
    2. Arc of Direction (1° Ecliptic Arc = 1 Solar Year)
    3. Planetary Hours & 24-minute Sub-tide vibrations."""

    @staticmethod
    def evaluate_lunar_tide(moon_daily_speed_deg: float) -> Dict[str, Any]:
        """Classify speculative market gravitational tide from Lunar daily motion."""
        # Mean lunar speed: ~13.176°/day (Ranges from 11.8° Apogee to 15.2° Perigee)
        v_min, v_max = 11.8, 15.2
        norm_tide = min(1.0, max(0.0, (moon_daily_speed_deg - v_min) / (v_max - v_min)))
        tide_pct = round(norm_tide * 100.0, 1)

        if tide_pct >= 75.0:
            cond = "Lunar Perigee Climax (Maximum Tidal Gravitational Torque — Sharp Volatility Spikes)"
            posture = "HIGH_VOLATILITY_BREAKOUT"
        elif tide_pct <= 25.0:
            cond = "Lunar Apogee Minimum (Minimum Gravitational Pull — Market Drifts, Low Momentum, False Breaks)"
            posture = "RANGE_BOUND_MEAN_REVERSION"
        else:
            cond = "Normal Lunar Gravitational Motion"
            posture = "TREND_FOLLOWING"

        return {
            "lunar_daily_speed": round(moon_daily_speed_deg, 3),
            "gravitational_tide_strength": f"{tide_pct}%",
            "market_condition": cond,
            "tactical_posture": posture,
            "source": "Sepharial, The Silver Key (1913)"
        }

    @staticmethod
    def compute_arc_of_direction(genesis_year: int, current_year: int, natal_points: Dict[str, float]) -> Dict[str, float]:
        """Compute Sepharial Primary Arc of Direction: 1.0° per year from Genesis Radix."""
        elapsed_years = current_year - genesis_year
        arc_dir = elapsed_years * 1.0
        directed_points = {}
        for body, lon in natal_points.items():
            directed_points[body] = round((lon + arc_dir) % 360.0, 2)
        return directed_points


# ═════════════════════════════════════════════════════════════════════════════
#  20. MULTI-TIMEFRAME ASTRO-TRADING ORCHESTRATOR & INSTITUTIONAL TRADE CARD
# ═════════════════════════════════════════════════════════════════════════════

class AstroTradeOrchestrator:
    """Master Institutional Multi-Timeframe Astro-Trading Orchestrator.
    Synthesizes:
    - Tier 1 (Macro, 35%): Barbault BCI + McWhirter Node Cycle + Solar Flux
    - Tier 2 (Swing, 45%): Bradley Siderograph + Merriman CRD + Carolan Spiral + Helio Aspects
    - Tier 3 (Intraday, 20%): Gann Circle of 24 + Square of 9 + Sepharial Lunar Tide
    Produces the comprehensive Institutional Trade Card."""

    @staticmethod
    def generate_institutional_trade_card(
        asset_key: str,
        current_price: float,
        macro_bias_score: float,       # [-100, +100] from Barbault/McWhirter
        swing_crd_score: float,        # [0, 100]% from Bradley/Merriman
        swing_direction: int,          # +1 (Long), -1 (Short), 0 (Neutral)
        intraday_score: float          # [-100, +100] from Gann 24/Sepharial
    ) -> Dict[str, Any]:
        w_macro = 0.35
        w_swing = 0.45
        w_intra = 0.20

        composite_score = (
            (w_macro * macro_bias_score) +
            (w_swing * swing_crd_score * swing_direction) +
            (w_intra * intraday_score)
        )
        composite_score = max(-100.0, min(100.0, composite_score))

        if composite_score >= 55.0:
            action = "INSTITUTIONAL STRONG BUY (HIGH CONFLUENCE LONG)"
            sl_pct = 0.96; tp1_pct = 1.06; tp2_pct = 1.12
        elif composite_score <= -55.0:
            action = "INSTITUTIONAL STRONG SELL (HIGH CONFLUENCE SHORT)"
            sl_pct = 1.04; tp1_pct = 0.94; tp2_pct = 0.88
        elif composite_score >= 20.0:
            action = "MOMENTUM BUY / DIP ACCUMULATION"
            sl_pct = 0.97; tp1_pct = 1.04; tp2_pct = 1.08
        elif composite_score <= -20.0:
            action = "DEFENSIVE HEDGE / SELL RALLIES"
            sl_pct = 1.03; tp1_pct = 0.96; tp2_pct = 0.92
        else:
            action = "NEUTRAL CONSOLIDATION / CASH PRESERVATION"
            sl_pct = 0.98; tp1_pct = 1.02; tp2_pct = 1.04

        return {
            "asset": asset_key.upper(),
            "current_price": current_price,
            "institutional_action": action,
            "composite_confluence_score": round(composite_score, 1),
            "tier_breakdown": {
                "macro_tier_35pct": round(macro_bias_score, 1),
                "swing_tier_45pct": round(swing_crd_score * swing_direction, 1),
                "intraday_tier_20pct": round(intraday_score, 1)
            },
            "order_matrix": {
                "entry_price": current_price,
                "stop_loss": round(current_price * sl_pct, 2),
                "take_profit_1": round(current_price * tp1_pct, 2),
                "take_profit_2": round(current_price * tp2_pct, 2),
                "risk_reward": f"1:{round(abs(current_price * tp1_pct - current_price) / max(0.01, abs(current_price - current_price * sl_pct)), 2)}"
            }
        }


# ═════════════════════════════════════════════════════════════════════════════
#  21. ARCH CRAWFORD CRASH TRIGGER & BRADLEY DIVERGENCE ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class CrawfordCrashTriggerEngine:
    """Arch Crawford (Crawford Perspectives - Wall Street Timer #1) Market Crash Engine.
    Identifies high-probability market crashes and panic selloffs when:
    1. Mars-Uranus hard aspects (0°, 90°, 180°, 135°) occur within ±1.5°
    2. Combined with a Full Moon/New Moon at Lunar Perigee or Solar/Lunar Eclipse within ±72h
    3. Confirmed by Bradley Siderograph negative divergence."""

    @staticmethod
    def evaluate_crash_hazard(mars_lon: float,
                              uranus_lon: float,
                              is_lunar_perigee: bool = False,
                              is_eclipse_window: bool = False,
                              siderograph_divergence: bool = False) -> Dict[str, Any]:
        sep = abs((mars_lon - uranus_lon + 180.0) % 360.0 - 180.0)
        hard_aspect = None
        exact_orb = 999.0
        for ang, aname in [(0.0, "Conjunction"), (90.0, "Square"), (180.0, "Opposition"), (135.0, "Sesquisquare")]:
            dev = abs(sep - ang)
            if dev <= 1.5:
                hard_aspect = aname
                exact_orb = dev
                break

        hazard_score = 0
        reasons = []
        if hard_aspect:
            hazard_score += 45
            reasons.append(f"Mars-Uranus Hard Aspect Active: {hard_aspect} (Orb {exact_orb:.2f}°)")
        if is_lunar_perigee:
            hazard_score += 25
            reasons.append("Lunar Perigee / Extreme Gravitational Tide Confluence (±48h)")
        if is_eclipse_window:
            hazard_score += 20
            reasons.append("Solar/Lunar Eclipse Trigger Window Active (±72h)")
        if siderograph_divergence:
            hazard_score += 10
            reasons.append("Bradley Siderograph Bearish Oscillator Divergence Confirmed")

        is_crash_hazard = hazard_score >= 65
        return {
            "is_crash_warning_active": is_crash_hazard,
            "crash_hazard_score": hazard_score,
            "status": "CRITICAL CRASH & PANIC WARNING" if is_crash_hazard else "ELEVATED VOLATILITY" if hazard_score >= 40 else "NORMAL_MARKET_CONDITIONS",
            "active_catalysts": reasons,
            "protective_action": "Execute capital preservation: Move to cash, buy out-of-the-money put options, or deploy tight stop-losses." if is_crash_hazard else "Maintain standard risk parameters.",
            "source": "Arch Crawford, Crawford Perspectives (Hulbert Financial Digest Ranked #1)"
        }


# ═════════════════════════════════════════════════════════════════════════════
#  22. MICHAEL S. JENKINS PRICE-TIME SQUARING & PLANETARY VECTOR ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class JenkinsGeometryEngine:
    """Michael S. Jenkins (Secret Science of the Stock Market, 1992).
    Calculates Price-Time Squaring targets and True Daily Planetary Motion slope trajectories."""

    @staticmethod
    def calculate_price_time_square(pivot_price: float, harmonic_deg: float = 90.0, direction: int = 1) -> Dict[str, Any]:
        """Formula: P_target = (sqrt(P_pivot) +/- (harmonic_deg / 180.0))^2."""
        if pivot_price <= 0: return {"target_price": 0.0}
        root_p = math.sqrt(pivot_price)
        shift = (harmonic_deg / 180.0) * (1.0 if direction >= 0 else -1.0)
        target_root = root_p + shift
        target_p = (target_root ** 2) if target_root > 0 else 0.0

        # Time squaring: bars elapsed equal to root of pivot price
        time_squaring_bars = round(root_p)

        return {
            "pivot_price": pivot_price,
            "harmonic_degree": harmonic_deg,
            "direction": "Upward Resistance" if direction >= 0 else "Downward Support",
            "target_price": round(target_p, 2),
            "natural_time_squaring_bars": time_squaring_bars,
            "rule": f"Michael Jenkins Rule: Market squares price at {round(target_p,2)} after {time_squaring_bars} time units from pivot."
        }


# ═════════════════════════════════════════════════════════════════════════════
#  23. DAN FERRERA MASTER CYCLE & 84-MONTH PANIC CYCLE ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class FerreraMasterCycleEngine:
    """Dan Ferrera (Mysteries of Gann Explained, 2003 / Wheels in the Sky).
    Decomposes the 20-Year Jupiter-Saturn Synodic Master Cycle and 84-Month (7-Year) Uranus Panic Cycle."""

    @staticmethod
    def evaluate_panic_cycle_node(months_from_major_low: int) -> Dict[str, Any]:
        """Calculates 84-month Uranus sub-harmonic panic and exhaustion turning points."""
        m_mod = months_from_major_low % 84
        if m_mod in range(0, 3) or m_mod in range(82, 85):
            stage = "Month 84 Master Return: Secular Cycle Reset / Ultimate Accumulation Floor"
            action = "STRONG_SECULAR_BUY"
        elif m_mod in range(19, 23):
            stage = "Month 21 (90° Square): First Major Distribution Top / Post-Euphoria Correction"
            action = "TAKE_PROFIT_DEFENSIVE"
        elif m_mod in range(40, 44):
            stage = "Month 42 (180° Opposition): Half-Cycle Panic Zone / Liquidity Contraction Bottom"
            action = "HIGH_VOLATILITY_REVERSAL_BUY"
        elif m_mod in range(61, 65):
            stage = "Month 63 (270° Square): Pre-Cycle Climax / Late Expansion Bull Run"
            action = "TREND_FOLLOWING_LONG"
        else:
            stage = "Inter-Harmonic Normal Cycle Progression"
            action = "NEUTRAL"

        return {
            "cycle_months_elapsed": months_from_major_low,
            "position_in_84m_cycle": f"Month {m_mod} of 84",
            "cycle_stage": stage,
            "tactical_action": action,
            "source": "Dan Ferrera, Gann's Master Panic Cycle (7 Years / 84 Months)"
        }


# ═════════════════════════════════════════════════════════════════════════════
#  24. OLGA MORALES HELIO PRICE LINES & INTRADAY 4-MIN CLOCK ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class OlgaMoralesIntradayEngine:
    """Olga Morales (Astrology for Traders, Planetary Price Lines & Wheel of 24).
    Calculates exact 4-minute per degree time-turning triggers and Helio Mars-Jupiter-Saturn channel lines."""

    @staticmethod
    def calculate_4min_turning_trigger(minutes_since_session_open: float, target_turning_angles: List[float] = [0.0, 90.0, 180.0, 270.0]) -> Dict[str, Any]:
        """Every 4 minutes = 1.0° of Ascendant/MC angular advance."""
        current_deg = (minutes_since_session_open / 4.0) % 360.0
        nearest_trigger = None
        min_dist = 999.0
        for ang in target_turning_angles:
            dist = abs((current_deg - ang + 180.0) % 360.0 - 180.0)
            if dist < min_dist:
                min_dist = dist
                nearest_trigger = ang

        is_turning_moment = min_dist <= 0.25 # Within 1 minute of exact turning
        return {
            "minutes_from_open": minutes_since_session_open,
            "current_diurnal_degree": round(current_deg, 2),
            "nearest_harmonic_angle": nearest_trigger,
            "angular_distance_to_pivot": round(min_dist, 2),
            "is_intraday_turning_trigger": is_turning_moment,
            "action": "EXECUTE INTRADAY REVERSAL ORDER (1m/5m Pinbar confirmation)" if is_turning_moment else "Wait for next 4-minute angular alignment."
        }


# ═════════════════════════════════════════════════════════════════════════════
#  25. ALPHEE LAVOIE & KAYE SHINKER ASTEROID HARMONICS & PROBABILITY ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class LavoieAsteroidHarmonicsEngine:
    """Alphee Lavoie & Kaye Shinker Financial Astrology Asteroids & Probability Tables.
    Integrates Ceres (Agriculture), Vesta (Housing/Real Estate), Pallas (Semiconductors/Tech), Juno (Mergers)."""

    ASTEROID_SECTORS = {
        "CERES": {"sector": "Agriculture & Grains (Corn, Wheat, Soybeans)", "bullish_aspect": "Trine/Sextile Jupiter", "win_rate": 73.1, "z_score": 2.48},
        "VESTA": {"sector": "Real Estate & Homebuilders (ITB, XHB)", "bullish_aspect": "Trine/Conjunction Venus", "win_rate": 69.8, "z_score": 2.18},
        "PALLAS": {"sector": "Semiconductors, Microchips & High-Tech (SMH, NVDA, QQQ)", "bullish_aspect": "Conjunction/Trine Uranus", "win_rate": 72.3, "z_score": 2.34},
        "JUNO": {"sector": "Mergers & Corporate Acquisitions (M&A, Antitrust)", "bullish_aspect": "Trine/Conjunction Saturn", "win_rate": 67.5, "z_score": 2.05}
    }

    @staticmethod
    def get_asteroid_probability_metric(asteroid_name: str) -> Dict[str, Any]:
        ast_key = asteroid_name.upper().strip()
        info = LavoieAsteroidHarmonicsEngine.ASTEROID_SECTORS.get(ast_key, LavoieAsteroidHarmonicsEngine.ASTEROID_SECTORS["PALLAS"])
        return {
            "asteroid": ast_key,
            "target_market_sector": info["sector"],
            "optimal_bullish_signature": info["bullish_aspect"],
            "historical_win_rate": f"{info['win_rate']}%",
            "statistical_z_score": info["z_score"],
            "is_statistically_actionable": info["win_rate"] >= 65.0 and info["z_score"] >= 2.0,
            "source": "Alphee Lavoie & Kaye Shinker, Financial Astrology Research"
        }




