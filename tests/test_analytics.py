#!/usr/bin/env python3
"""
FreshTrack BD — Unit Tests for Analytics Engine (src/analytics.py)
Tests Mean Kinetic Temperature (Arrhenius weighting theorem),
Risk Score calculations, and Route/Warehouse aggregation rollups.
"""

import unittest
import numpy as np
import pandas as pd
from src.analytics import (
    calculate_mkt,
    calculate_risk_score,
    enrich_summary_dataframe,
    aggregate_by_route,
    aggregate_by_warehouse,
)


class TestAnalyticsEngine(unittest.TestCase):

    def test_mkt_constant_temperature(self):
        """MKT of an unvarying temperature series must equal that exact temperature."""
        temps = [4.0, 4.0, 4.0, 4.0, 4.0]
        mkt = calculate_mkt(temps)
        self.assertAlmostEqual(mkt, 4.0, places=2)

    def test_mkt_arrhenius_weighting_greater_than_arithmetic_mean(self):
        """
        Fundamental MKT Theorem: Because degradation accelerates exponentially
        at higher temperatures, MKT is always strictly greater than the arithmetic mean
        for non-constant temperature profiles.
        """
        temps = [2.0, 2.0, 2.0, 10.0, 10.0]
        arithmetic_mean = sum(temps) / len(temps)  # 5.2 °C
        mkt = calculate_mkt(temps)  # Should be ~6.3 °C
        self.assertIsNotNone(mkt)
        self.assertGreater(mkt, arithmetic_mean)

    def test_mkt_empty_series(self):
        """Empty input should return None gracefully."""
        self.assertIsNone(calculate_mkt([]))

    def test_risk_score_low_for_compliant_consignments(self):
        """A delivery with 0 breach minutes and 100% integrity must be classified LOW."""
        result = calculate_risk_score(
            breach_duration_min=0.0,
            total_duration_min=180.0,
            degree_hours=0.0,
            door_open_count=1,
            total_readings=36,
            sampling_integrity_pct=100.0,
        )
        self.assertEqual(result["risk_category"], "LOW")
        self.assertLessEqual(result["risk_score"], 20.0)

    def test_risk_score_high_for_severe_breach(self):
        """A consignment with sustained breach and high degree-hours must be classified HIGH or CRITICAL."""
        result = calculate_risk_score(
            breach_duration_min=150.0,
            total_duration_min=180.0,
            degree_hours=8.5,
            door_open_count=12,
            total_readings=36,
            sampling_integrity_pct=75.0,
        )
        self.assertIn(result["risk_category"], ["HIGH", "CRITICAL"])
        self.assertGreater(result["risk_score"], 60.0)

    def test_enrich_and_aggregate(self):
        """Verifies enrichment and route/warehouse rollups."""
        data = [
            {
                "delivery_id": "DEL-1",
                "route_id": "RT-A",
                "warehouse_id": "WH-1",
                "product_category": "Dairy",
                "total_readings": 30,
                "valid_readings": 30,
                "duplicate_count": 0,
                "gap_count": 0,
                "breach_reading_count": 0,
                "observed_breach_duration_min": 0.0,
                "degree_hours_excursion": 0.0,
                "max_temp": 3.8,
                "min_temp": 2.5,
                "avg_temp": 3.1,
                "door_open_count": 2,
                "sampling_integrity_pct": 100.0,
            },
            {
                "delivery_id": "DEL-2",
                "route_id": "RT-A",
                "warehouse_id": "WH-1",
                "product_category": "Dairy",
                "total_readings": 30,
                "valid_readings": 30,
                "duplicate_count": 0,
                "gap_count": 0,
                "breach_reading_count": 25,
                "observed_breach_duration_min": 125.0,
                "degree_hours_excursion": 5.4,
                "max_temp": 12.0,
                "min_temp": 3.0,
                "avg_temp": 8.2,
                "door_open_count": 5,
                "sampling_integrity_pct": 100.0,
            },
        ]
        df = pd.DataFrame(data)
        enriched = enrich_summary_dataframe(df)
        self.assertIn("risk_score", enriched.columns)
        self.assertIn("risk_category", enriched.columns)

        route_stats = aggregate_by_route(enriched)
        self.assertEqual(len(route_stats), 1)
        self.assertEqual(route_stats.iloc[0]["total_deliveries"], 2)
        self.assertEqual(route_stats.iloc[0]["breached_deliveries"], 1)
        self.assertEqual(route_stats.iloc[0]["compliance_rate_pct"], 50.0)

        wh_stats = aggregate_by_warehouse(enriched)
        self.assertEqual(len(wh_stats), 1)
        self.assertEqual(wh_stats.iloc[0]["compliance_rate_pct"], 50.0)

    def test_operational_alerts_generation(self):
        """Verifies alerts are derived from real metrics."""
        from src.analytics import derive_operational_alerts
        data = [{
            "delivery_id": "DEL-1",
            "route_id": "RT-A",
            "warehouse_id": "WH-1",
            "product_category": "Dairy",
            "total_readings": 30,
            "valid_readings": 30,
            "duplicate_count": 0,
            "gap_count": 1,
            "breach_reading_count": 10,
            "observed_breach_duration_min": 50.0,
            "degree_hours_excursion": 6.2,
            "max_temp": 11.5,
            "min_temp": 2.5,
            "avg_temp": 6.1,
            "door_open_count": 4,
            "sampling_integrity_pct": 96.0,
            "risk_score": 68.0,
            "risk_category": "HIGH",
        }]
        df = pd.DataFrame(data)
        alerts = derive_operational_alerts(df)
        self.assertGreater(len(alerts), 0)
        self.assertTrue(any("RT-A" in a["title"] for a in alerts))

    def test_extract_excursion_episodes(self):
        """Verifies extraction of distinct excursion episodes from telemetry."""
        from src.analytics import extract_excursion_episodes
        raw_data = [
            {"timestamp": "2026-10-20T08:00:00Z", "container_temp": 3.0, "target_temp_min": 2.0, "target_temp_max": 4.0},
            {"timestamp": "2026-10-20T08:05:00Z", "container_temp": 6.0, "target_temp_min": 2.0, "target_temp_max": 4.0},  # Excursion start
            {"timestamp": "2026-10-20T08:10:00Z", "container_temp": 7.0, "target_temp_min": 2.0, "target_temp_max": 4.0},  # Excursion continue
            {"timestamp": "2026-10-20T08:15:00Z", "container_temp": 3.5, "target_temp_min": 2.0, "target_temp_max": 4.0},  # Normal (episode closed)
        ]
        raw_df = pd.DataFrame(raw_data)
        episodes = extract_excursion_episodes(raw_df)
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0]["type"], "Warm Excursion")
        self.assertAlmostEqual(episodes[0]["observed_duration_min"], 10.0, places=1)
        self.assertEqual(episodes[0]["max_observed_temp"], 7.0)


if __name__ == "__main__":
    unittest.main()

