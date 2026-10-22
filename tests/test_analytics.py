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
    assess_telemetry_quality,
    generate_gap_aware_assessment,
    calculate_gap_aware_risk,
    EvidenceQuality,
    MAX_GAP_MINUTES,
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

    def test_mkt_nan_filtering_and_invalid_kelvin(self):
        """NaN values should be filtered out; sub-absolute zero values should raise ValueError."""
        temps_with_nan = [4.0, float("nan"), 4.0, float("nan"), 4.0]
        mkt = calculate_mkt(temps_with_nan)
        self.assertAlmostEqual(mkt, 4.0, places=2)

        # Temperatures <= -273.15 C violate laws of physics (0 Kelvin)
        with self.assertRaises(ValueError):
            calculate_mkt([-300.0, 4.0])

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

    def test_gap_aware_complete_data(self):
        """
        Complete telemetry test:
        100% continuous coverage with 0 gaps over 60 min window yields Good evidence quality.
        Qualified risk label conveys high telemetry confidence.
        System never claims shipment is 'safe' or 'spoiled'.
        """
        # 13 points every 5 minutes from 08:00 to 09:00 (60 minutes)
        timestamps = [
            f"2026-10-20T08:{m:02d}:00Z" for m in range(0, 60, 5)
        ] + ["2026-10-20T09:00:00Z"]
        quality = assess_telemetry_quality(
            timestamps,
            expected_interval_min=5.0,
            observation_window_min=60.0,
            max_gap_minutes=MAX_GAP_MINUTES,
        )
        self.assertEqual(quality["evidence_quality"], EvidenceQuality.GOOD.value)
        self.assertEqual(quality["telemetry_coverage_pct"], 100.0)
        self.assertEqual(quality["gap_count"], 0)
        self.assertEqual(quality["duplicate_count"], 0)
        self.assertEqual(quality["invalid_timestamp_count"], 0)

        # Compliant shipment (0 breach)
        assessment = generate_gap_aware_assessment(
            observed_risk_info={"risk_category": "LOW", "risk_score": 4.0},
            telemetry_quality_info=quality,
            observed_breach_duration_min=0.0,
            degree_hours_excursion=0.0,
        )
        self.assertEqual(assessment["evidence_quality"], EvidenceQuality.GOOD.value)
        self.assertEqual(assessment["observed_risk_category"], "LOW")
        self.assertIn("High Telemetry Confidence", assessment["qualified_risk_label"])
        # Must not claim "safe" or "spoiled"
        self.assertNotIn("safe", assessment["explanation"].lower())
        self.assertNotIn("spoiled", assessment["explanation"].lower())
        self.assertNotIn("safe", assessment["recommended_action"].lower())
        self.assertNotIn("spoiled", assessment["recommended_action"].lower())

    def test_gap_aware_missing_data(self):
        """
        Missing telemetry test:
        Observation window is 120 minutes, but telemetry stops after 30 minutes (25% coverage).
        Evidence quality must be Poor.
        Low observed risk must be qualified, and physical logger extraction recommended.
        """
        # Only 7 readings covering 30 minutes in a 120-minute window
        timestamps = [f"2026-10-20T08:{m:02d}:00Z" for m in range(0, 35, 5)]
        quality = assess_telemetry_quality(
            timestamps,
            expected_interval_min=5.0,
            observation_window_min=120.0,
            max_gap_minutes=15.0,
        )
        self.assertEqual(quality["evidence_quality"], EvidenceQuality.POOR.value)
        self.assertEqual(quality["telemetry_coverage_pct"], 25.0)
        self.assertEqual(quality["monitored_duration_min"], 30.0)

        assessment = generate_gap_aware_assessment(
            observed_risk_info={"risk_category": "LOW", "risk_score": 5.0},
            telemetry_quality_info=quality,
            observed_breach_duration_min=0.0,
            degree_hours_excursion=0.0,
        )
        self.assertEqual(assessment["evidence_quality"], EvidenceQuality.POOR.value)
        self.assertIn("Poor Telemetry Coverage", assessment["qualified_risk_label"])
        self.assertIn("Unverified", assessment["qualified_risk_label"])
        self.assertIn("Quarantine", assessment["recommended_action"])
        self.assertNotIn("safe", assessment["explanation"].lower())
        self.assertNotIn("spoiled", assessment["explanation"].lower())

    def test_gap_aware_long_gaps(self):
        """
        Long gap test (>15 minutes):
        Telemetry has a 60-minute sensor dropout during an 80-minute transit.
        Gap count must be 1, unobserved duration must be 60 min, coverage must reflect only 20 min (25%).
        Unobserved gap must NOT be inferred as continuous breach or continuous compliance.
        """
        # 08:00, 08:05, 08:10 -> 10m monitored
        # GAP: 08:10 to 09:10 (60 minutes > 15m)
        # 09:10, 09:15, 09:20 -> 10m monitored
        timestamps = [
            "2026-10-20T08:00:00Z",
            "2026-10-20T08:05:00Z",
            "2026-10-20T08:10:00Z",
            "2026-10-20T09:10:00Z",
            "2026-10-20T09:15:00Z",
            "2026-10-20T09:20:00Z",
        ]
        quality = assess_telemetry_quality(
            timestamps,
            expected_interval_min=5.0,
            observation_window_min=80.0,
            max_gap_minutes=15.0,
        )
        self.assertEqual(quality["gap_count"], 1)
        self.assertEqual(quality["unobserved_gap_duration_min"], 60.0)
        self.assertEqual(quality["monitored_duration_min"], 20.0)
        self.assertEqual(quality["telemetry_coverage_pct"], 25.0)
        self.assertEqual(quality["evidence_quality"], EvidenceQuality.POOR.value)

        assessment = generate_gap_aware_assessment(
            observed_risk_info={"risk_category": "LOW", "risk_score": 6.0},
            telemetry_quality_info=quality,
            observed_breach_duration_min=0.0,
            degree_hours_excursion=0.0,
        )
        # Must explicitly mention that continuous excursion/compliance cannot be inferred
        self.assertIn("must not be inferred across unobserved blackouts", assessment["explanation"])
        self.assertNotIn("safe", assessment["explanation"].lower())
        self.assertNotIn("spoiled", assessment["explanation"].lower())

    def test_gap_aware_duplicate_and_invalid_timestamps(self):
        """
        Duplicate and malformed timestamps test:
        Duplicate timestamps must be deduplicated and counted.
        Invalid/null timestamps must be filtered out and counted without crashing.
        """
        timestamps = [
            "2026-10-20T08:00:00Z",
            "2026-10-20T08:05:00Z",
            "2026-10-20T08:05:00Z",  # Duplicate
            "INVALID_TIMESTAMP",      # Invalid
            None,                     # None
            "2026-10-20T08:10:00Z",
            "2026-10-20T08:10:00Z",  # Duplicate
            "2026-10-20T08:15:00Z",
        ]
        quality = assess_telemetry_quality(
            timestamps,
            expected_interval_min=5.0,
            observation_window_min=15.0,
            max_gap_minutes=15.0,
        )
        self.assertEqual(quality["duplicate_count"], 2)
        self.assertEqual(quality["invalid_timestamp_count"], 2)
        self.assertEqual(quality["valid_readings"], 4)
        self.assertEqual(quality["monitored_duration_min"], 15.0)
        self.assertEqual(quality["evidence_quality"], EvidenceQuality.GOOD.value)

    def test_gap_aware_unknown_sampling_intervals(self):
        """
        Unknown sampling interval / observation window test:
        When expected interval or window is None, zero, or negative,
        coverage must be None and evidence_quality must be Unknown.
        """
        timestamps = ["2026-10-20T08:00:00Z", "2026-10-20T08:05:00Z"]
        # Case 1: None
        quality_none = assess_telemetry_quality(
            timestamps,
            expected_interval_min=None,
            observation_window_min=None,
        )
        self.assertEqual(quality_none["evidence_quality"], EvidenceQuality.UNKNOWN.value)
        self.assertIsNone(quality_none["telemetry_coverage_pct"])

        # Case 2: Zero or negative
        quality_zero = assess_telemetry_quality(
            timestamps,
            expected_interval_min=0,
            observation_window_min=50.0,
        )
        self.assertEqual(quality_zero["evidence_quality"], EvidenceQuality.UNKNOWN.value)
        self.assertIsNone(quality_zero["telemetry_coverage_pct"])

        assessment = generate_gap_aware_assessment(
            observed_risk_info={"risk_category": "LOW", "risk_score": 8.0},
            telemetry_quality_info=quality_none,
            observed_breach_duration_min=0.0,
            degree_hours_excursion=0.0,
        )
        self.assertEqual(assessment["evidence_quality"], EvidenceQuality.UNKNOWN.value)
        self.assertIn("Unknown Sampling Rate", assessment["qualified_risk_label"])
        self.assertIn("mathematical coverage percentage cannot be established", assessment["explanation"])

    def test_gap_aware_high_risk_shipment_with_poor_coverage(self):
        """
        High observed risk with poor telemetry coverage:
        Confirmed thermal excursion compounded by unobserved gaps.
        Both observed risk (HIGH/CRITICAL) and evidence quality (Poor) must be preserved separately.
        Recommendation mandates immediate quarantine without claiming product is 'spoiled'.
        """
        timestamps = [
            "2026-10-20T08:00:00Z",
            "2026-10-20T08:05:00Z",
            "2026-10-20T08:10:00Z",
            "2026-10-20T09:10:00Z",  # 60 min gap
            "2026-10-20T09:15:00Z",
        ]
        quality = assess_telemetry_quality(
            timestamps,
            expected_interval_min=5.0,
            observation_window_min=75.0,
            max_gap_minutes=15.0,
        )
        self.assertEqual(quality["evidence_quality"], EvidenceQuality.POOR.value)

        # High observed breach
        assessment = generate_gap_aware_assessment(
            observed_risk_info={"risk_category": "HIGH", "risk_score": 76.5},
            telemetry_quality_info=quality,
            observed_breach_duration_min=30.0,
            degree_hours_excursion=2.45,
        )
        self.assertEqual(assessment["observed_risk_category"], "HIGH")
        self.assertEqual(assessment["evidence_quality"], EvidenceQuality.POOR.value)
        self.assertIn("Compounded by Poor Coverage", assessment["qualified_risk_label"])
        self.assertIn("Quarantine consignment immediately", assessment["recommended_action"])
        self.assertNotIn("safe", assessment["explanation"].lower())
        self.assertNotIn("spoiled", assessment["explanation"].lower())
        self.assertNotIn("spoiled", assessment["recommended_action"].lower())

    def test_gap_aware_low_observed_risk_with_poor_coverage_not_presented_as_safe(self):
        """
        CRITICAL CORE SAFETY TEST:
        A shipment with a low observed risk score (e.g. 0 breach minutes) but long sensor-data gaps
        must NOT appear safe or low-risk without qualification.
        """
        timestamps = [
            "2026-10-20T08:00:00Z",
            "2026-10-20T08:05:00Z",
            "2026-10-20T09:05:00Z",  # 60m gap
            "2026-10-20T09:10:00Z",
        ]
        assessment = calculate_gap_aware_risk(
            timestamps=timestamps,
            observed_breach_duration_min=0.0,
            degree_hours_excursion=0.0,
            door_open_count=0,
            total_readings=4,
            sampling_integrity_pct=50.0,
            expected_interval_min=5.0,
            observation_window_min=70.0,
            max_gap_minutes=15.0,
        )
        # 1. Observed score is low
        self.assertLess(assessment["observed_risk_score"], 20.0)
        self.assertEqual(assessment["observed_risk_category"], "LOW")
        # 2. Evidence quality is Poor
        self.assertEqual(assessment["evidence_quality"], EvidenceQuality.POOR.value)
        # 3. Label must NOT say just "Low Risk" or "Safe"
        self.assertNotIn("safe", assessment["qualified_risk_label"].lower())
        self.assertIn("Unverified", assessment["qualified_risk_label"])
        self.assertIn("Poor Telemetry Coverage", assessment["qualified_risk_label"])
        # 4. Explanation and recommendation must explicitly address the unobserved gap
        self.assertIn("CRITICAL AUDIT NOTE", assessment["explanation"])
        self.assertIn("Quarantine consignment for physical audit", assessment["recommended_action"])
        self.assertNotIn("safe", assessment["explanation"].lower())
        self.assertNotIn("spoiled", assessment["explanation"].lower())


if __name__ == "__main__":
    unittest.main()


