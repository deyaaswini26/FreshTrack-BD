#!/usr/bin/env python3
"""
FreshTrack BD — Pipeline Parity & Edge Case Test Suite
Compares the output of the Hadoop Streaming MapReduce pipeline (mapper.py + reducer.py)
against an independent, ground-truth Pandas reference implementation across:
1. Normal compliant journeys
2. Continuous refrigeration failures
3. Dropped duplicate timestamps
4. Irregular sampling intervals
5. Unobserved telemetry gaps (> 15 minutes) - ensuring continuous breach is NOT inferred
6. Full 1,000+ record realistic dataset
"""

import datetime
import os
import subprocess
import sys
import tempfile
import unittest
import pandas as pd
import numpy as np

# Ground-truth reference implementation in pure Python / Pandas
MAX_GAP_MINUTES = 15.0


def calculate_pandas_reference(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Independent ground-truth reference implementation using Pandas.
    Follows the exact same timestamp-aware rules specified in architecture.md.
    """
    results = []
    grouped = raw_df.groupby("delivery_id", sort=True)

    for delivery_id, group in grouped:
        total_readings = len(group)
        # Sort chronologically by timestamp
        group_sorted = group.copy()
        group_sorted["dt"] = pd.to_datetime(group_sorted["timestamp"])
        group_sorted = group_sorted.sort_values("dt")

        metadata = group_sorted.iloc[0]
        route_id = str(metadata["route_id"])
        warehouse_id = str(metadata["warehouse_id"])
        product_category = str(metadata["product_category"])

        # Deduplicate identical timestamps
        seen_timestamps = set()
        deduped_rows = []
        duplicate_count = 0

        for _, row in group_sorted.iterrows():
            ts = row["timestamp"]
            if ts in seen_timestamps:
                duplicate_count += 1
                continue
            seen_timestamps.add(ts)
            deduped_rows.append(row)

        valid_readings = len(deduped_rows)
        gap_count = 0
        breach_reading_count = 0
        observed_breach_duration_min = 0.0
        degree_hours_excursion = 0.0
        door_open_count = 0
        temps = []

        prev_time = None

        for row in deduped_rows:
            curr_time = row["dt"]
            temp = float(row["container_temp"])
            t_min = float(row["target_temp_min"])
            t_max = float(row["target_temp_max"])
            door = int(row["door_open_flag"])

            temps.append(temp)
            if door == 1:
                door_open_count += 1

            is_breach = (temp > t_max) or (temp < t_min)
            if is_breach:
                breach_reading_count += 1

            if prev_time is not None:
                delta_min = (curr_time - prev_time).total_seconds() / 60.0

                if delta_min <= MAX_GAP_MINUTES:
                    # Valid observation interval
                    if is_breach:
                        observed_breach_duration_min += delta_min
                        if temp > t_max:
                            degree_hours_excursion += (temp - t_max) * (delta_min / 60.0)
                        elif temp < t_min:
                            degree_hours_excursion += (t_min - temp) * (delta_min / 60.0)
                else:
                    # Unobserved gap - do NOT infer breach duration across this outage
                    gap_count += 1

            prev_time = curr_time

        max_temp = max(temps) if temps else 0.0
        min_temp = min(temps) if temps else 0.0
        avg_temp = sum(temps) / len(temps) if temps else 0.0

        intervals = max(1, valid_readings - 1)
        integrity_pct = max(0.0, min(100.0, ((intervals - gap_count) / intervals) * 100.0))

        results.append({
            "delivery_id": delivery_id,
            "route_id": route_id,
            "warehouse_id": warehouse_id,
            "product_category": product_category,
            "total_readings": total_readings,
            "valid_readings": valid_readings,
            "duplicate_count": duplicate_count,
            "gap_count": gap_count,
            "breach_reading_count": breach_reading_count,
            "observed_breach_duration_min": round(observed_breach_duration_min, 2),
            "degree_hours_excursion": round(degree_hours_excursion, 4),
            "max_temp": round(max_temp, 2),
            "min_temp": round(min_temp, 2),
            "avg_temp": round(avg_temp, 2),
            "door_open_count": door_open_count,
            "sampling_integrity_pct": round(integrity_pct, 2),
        })

    return pd.DataFrame(results)


def run_streaming_pipeline(input_csv_path: str) -> pd.DataFrame:
    """Executes mapper.py and reducer.py through a Python-native equivalent of a local pipe."""
    workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    mapper = os.path.join(workspace, "hadoop", "mapper.py")
    reducer = os.path.join(workspace, "hadoop", "reducer.py")

    with open(input_csv_path, "r", encoding="utf-8") as csv_file:
        input_text = csv_file.read()

    p_map = subprocess.Popen(
        [sys.executable, mapper],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    map_stdout, map_stderr = p_map.communicate(input=input_text.encode("utf-8"))
    if p_map.returncode != 0:
        raise RuntimeError(f"Mapper failed ({p_map.returncode}): {map_stderr.decode('utf-8')}")

    mapper_lines = map_stdout.decode("utf-8").splitlines()
    sorted_lines = sorted(mapper_lines, key=lambda line: line.split("\t", 1)[0])
    sorted_text = "\n".join(sorted_lines)
    if sorted_lines:
        sorted_text += "\n"

    with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as tmp:
        tmp_name = tmp.name

    p_red = subprocess.Popen(
        [sys.executable, reducer],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    reducer_stdout, reducer_stderr = p_red.communicate(input=sorted_text.encode("utf-8"))
    if p_red.returncode != 0:
        raise RuntimeError(f"Reducer failed ({p_red.returncode}): {reducer_stderr.decode('utf-8')}")

    with open(tmp_name, "w", encoding="utf-8") as tmp_file:
        tmp_file.write(reducer_stdout.decode("utf-8"))

    df = pd.read_csv(tmp_name)
    os.remove(tmp_name)
    return df


class TestPipelineParity(unittest.TestCase):
    """Parity tests asserting streaming pipeline output matches reference implementation."""

    def test_normal_compliant_delivery(self):
        """Tests that a fully compliant delivery records zero breaches and 100% integrity."""
        data = [
            ["REC-1", "2026-10-20T08:00:00Z", "DEL-TEST-01", "VAN-1", "RT-1", "WH-1", "Dairy", 2.0, 4.0, 3.0, 30.0, 0, 90, "IN_TRANSIT"],
            ["REC-2", "2026-10-20T08:05:00Z", "DEL-TEST-01", "VAN-1", "RT-1", "WH-1", "Dairy", 2.0, 4.0, 3.2, 30.5, 0, 90, "IN_TRANSIT"],
            ["REC-3", "2026-10-20T08:10:00Z", "DEL-TEST-01", "VAN-1", "RT-1", "WH-1", "Dairy", 2.0, 4.0, 3.1, 31.0, 0, 89, "IN_TRANSIT"],
        ]
        columns = [
            "record_id", "timestamp", "delivery_id", "vehicle_id", "route_id", "warehouse_id",
            "product_category", "target_temp_min", "target_temp_max", "container_temp",
            "ambient_temp", "door_open_flag", "battery_level", "transit_status"
        ]
        df = pd.DataFrame(data, columns=columns)

        with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as tmp:
            df.to_csv(tmp.name, index=False)
            tmp_path = tmp.name

        try:
            ref_df = calculate_pandas_reference(df)
            pipe_df = run_streaming_pipeline(tmp_path)

            self.assertEqual(len(ref_df), 1)
            self.assertEqual(len(pipe_df), 1)
            self.assertEqual(pipe_df.iloc[0]["breach_reading_count"], 0)
            self.assertEqual(pipe_df.iloc[0]["observed_breach_duration_min"], 0.0)
            self.assertEqual(pipe_df.iloc[0]["degree_hours_excursion"], 0.0)
            self.assertEqual(pipe_df.iloc[0]["gap_count"], 0)
            self.assertEqual(pipe_df.iloc[0]["duplicate_count"], 0)
            self.assertEqual(pipe_df.iloc[0]["sampling_integrity_pct"], 100.0)
        finally:
            os.remove(tmp_path)

    def test_duplicate_timestamps_handling(self):
        """Verifies duplicate timestamps are dropped without inflating time or reading counts."""
        data = [
            ["REC-1", "2026-10-20T08:00:00Z", "DEL-DUP-01", "VAN-1", "RT-1", "WH-1", "Dairy", 2.0, 4.0, 3.0, 30.0, 0, 90, "IN_TRANSIT"],
            ["REC-1-DUP", "2026-10-20T08:00:00Z", "DEL-DUP-01", "VAN-1", "RT-1", "WH-1", "Dairy", 2.0, 4.0, 3.0, 30.0, 0, 90, "IN_TRANSIT"], # Duplicate
            ["REC-2", "2026-10-20T08:05:00Z", "DEL-DUP-01", "VAN-1", "RT-1", "WH-1", "Dairy", 2.0, 4.0, 3.2, 30.5, 0, 90, "IN_TRANSIT"],
        ]
        columns = [
            "record_id", "timestamp", "delivery_id", "vehicle_id", "route_id", "warehouse_id",
            "product_category", "target_temp_min", "target_temp_max", "container_temp",
            "ambient_temp", "door_open_flag", "battery_level", "transit_status"
        ]
        df = pd.DataFrame(data, columns=columns)

        with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as tmp:
            df.to_csv(tmp.name, index=False)
            tmp_path = tmp.name

        try:
            ref_df = calculate_pandas_reference(df)
            pipe_df = run_streaming_pipeline(tmp_path)

            self.assertEqual(pipe_df.iloc[0]["total_readings"], 3)
            self.assertEqual(pipe_df.iloc[0]["valid_readings"], 2)
            self.assertEqual(pipe_df.iloc[0]["duplicate_count"], 1)
            self.assertEqual(ref_df.iloc[0]["duplicate_count"], pipe_df.iloc[0]["duplicate_count"])
        finally:
            os.remove(tmp_path)

    def test_unobserved_long_gap_does_not_infer_breach(self):
        """
        CRITICAL REQUIREMENT: A 50-minute outage must increment gap_count,
        and continuous breach duration MUST NOT be inferred across the gap.
        """
        data = [
            ["REC-1", "2026-10-20T08:00:00Z", "DEL-GAP-01", "VAN-1", "RT-1", "WH-1", "Dairy", 2.0, 4.0, 3.0, 30.0, 0, 90, "IN_TRANSIT"],
            ["REC-2", "2026-10-20T08:05:00Z", "DEL-GAP-01", "VAN-1", "RT-1", "WH-1", "Dairy", 2.0, 4.0, 6.0, 30.0, 0, 90, "IN_TRANSIT"], # Breach (warm: 6 > 4) -> delta = 5 min
            # 50-minute outage (sensor lost)
            ["REC-3", "2026-10-20T08:55:00Z", "DEL-GAP-01", "VAN-1", "RT-1", "WH-1", "Dairy", 2.0, 4.0, 7.0, 30.0, 0, 85, "IN_TRANSIT"], # Still breach, but delta = 50 min > MAX_GAP
            ["REC-4", "2026-10-20T09:00:00Z", "DEL-GAP-01", "VAN-1", "RT-1", "WH-1", "Dairy", 2.0, 4.0, 6.5, 30.0, 0, 85, "IN_TRANSIT"], # Breach -> delta = 5 min
        ]
        columns = [
            "record_id", "timestamp", "delivery_id", "vehicle_id", "route_id", "warehouse_id",
            "product_category", "target_temp_min", "target_temp_max", "container_temp",
            "ambient_temp", "door_open_flag", "battery_level", "transit_status"
        ]
        df = pd.DataFrame(data, columns=columns)

        with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as tmp:
            df.to_csv(tmp.name, index=False)
            tmp_path = tmp.name

        try:
            ref_df = calculate_pandas_reference(df)
            pipe_df = run_streaming_pipeline(tmp_path)

            row = pipe_df.iloc[0]
            # Valid continuous breach should ONLY be 5 min (REC-2) + 5 min (REC-4) = 10 min.
            # It must NOT include the 50 minutes of outage!
            self.assertEqual(row["gap_count"], 1)
            self.assertAlmostEqual(row["observed_breach_duration_min"], 10.0, places=2)
            # Degree hours: REC-2: (6.0 - 4.0)*(5/60) = 0.1667; REC-4: (6.5 - 4.0)*(5/60) = 0.2083; Sum = 0.3750
            self.assertAlmostEqual(row["degree_hours_excursion"], 0.375, places=3)
            # Assert exact match with pandas reference
            self.assertEqual(row["gap_count"], ref_df.iloc[0]["gap_count"])
            self.assertAlmostEqual(row["observed_breach_duration_min"], ref_df.iloc[0]["observed_breach_duration_min"], places=2)
            self.assertAlmostEqual(row["degree_hours_excursion"], ref_df.iloc[0]["degree_hours_excursion"], places=3)
        finally:
            os.remove(tmp_path)

    def test_full_sample_dataset_parity(self):
        """Verifies 100% parity against Pandas across all consignments in the 1,000+ sample dataset."""
        sample_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data", "sample", "cold_chain_sample.csv")
        )
        self.assertTrue(os.path.exists(sample_path), "Sample CSV must exist")

        raw_df = pd.read_csv(sample_path)
        ref_df = calculate_pandas_reference(raw_df).sort_values("delivery_id").reset_index(drop=True)
        pipe_df = run_streaming_pipeline(sample_path).sort_values("delivery_id").reset_index(drop=True)

        self.assertEqual(len(ref_df), len(pipe_df))

        # Check column-by-column equality
        for col in ["delivery_id", "route_id", "warehouse_id", "product_category",
                    "total_readings", "valid_readings", "duplicate_count", "gap_count",
                    "breach_reading_count", "door_open_count"]:
            np.testing.assert_array_equal(ref_df[col].values, pipe_df[col].values, err_msg=f"Mismatch in column {col}")

        # Check numeric floating point columns with tolerance
        for num_col in ["observed_breach_duration_min", "degree_hours_excursion",
                        "max_temp", "min_temp", "avg_temp", "sampling_integrity_pct"]:
            np.testing.assert_allclose(
                ref_df[num_col].values,
                pipe_df[num_col].values,
                rtol=1e-3,
                atol=1e-2,
                err_msg=f"Floating point mismatch in column {num_col}"
            )


if __name__ == "__main__":
    unittest.main()
