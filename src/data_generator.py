#!/usr/bin/env python3
"""
FreshTrack BD — Synthetic Cold-Chain Telemetry Generator
Generates realistic multi-commodity food delivery sensor logs with intentional
thermal anomalies, door events, ambient heatwaves, and data-integrity edge cases
(irregular sampling, missing readings, telemetry gaps, and duplicate timestamps).
"""

import argparse
import datetime
import math
import os
import random
import uuid
from typing import Dict, List, Optional, Tuple
import pandas as pd

# Product Category Threshold Guidelines (Illustrative regulatory guidelines)
PRODUCT_PROFILES = {
    "Dairy": {
        "target_min": 2.0,
        "target_max": 4.0,
        "default_temp": 3.0,
        "critical_high": 7.0,
        "critical_low": 0.5,
    },
    "Meat": {
        "target_min": -1.0,
        "target_max": 2.0,
        "default_temp": 0.5,
        "critical_high": 5.0,
        "critical_low": -3.0,
    },
    "Seafood": {
        "target_min": -22.0,
        "target_max": -18.0,
        "default_temp": -20.0,
        "critical_high": -14.0,
        "critical_low": -26.0,
    },
    "Frozen": {
        "target_min": -25.0,
        "target_max": -20.0,
        "default_temp": -22.5,
        "critical_high": -16.0,
        "critical_low": -29.0,
    },
    "Produce": {
        "target_min": 1.0,
        "target_max": 5.0,
        "default_temp": 3.5,
        "critical_high": 9.0,
        "critical_low": -0.5,
    },
    "Vaccines": {
        "target_min": 2.0,
        "target_max": 8.0,
        "default_temp": 4.5,
        "critical_high": 9.5,
        "critical_low": 1.0,
    },
}

ROUTES = [
    {"route_id": "RT-MUM-PUN-01", "name": "Mumbai to Pune Express", "base_ambient": 33.0},
    {"route_id": "RT-DEL-JAI-02", "name": "Delhi to Jaipur Corridor", "base_ambient": 36.0},
    {"route_id": "RT-BLR-CHE-03", "name": "Bangalore to Chennai Highway", "base_ambient": 31.0},
    {"route_id": "RT-KOL-PAT-04", "name": "Kolkata to Patna Transit", "base_ambient": 32.0},
    {"route_id": "RT-HYD-VIZ-05", "name": "Hyderabad to Vizag Route", "base_ambient": 34.0},
]

WAREHOUSES = ["WH-NORTH-01", "WH-WEST-02", "WH-SOUTH-01", "WH-EAST-01"]
VEHICLE_PREFIXES = ["VAN", "REEFER", "TRK"]

CSV_COLUMNS = [
    "record_id",
    "timestamp",
    "delivery_id",
    "vehicle_id",
    "route_id",
    "warehouse_id",
    "product_category",
    "target_temp_min",
    "target_temp_max",
    "container_temp",
    "ambient_temp",
    "door_open_flag",
    "battery_level",
    "transit_status",
]


class ColdChainDataGenerator:
    """Simulates realistic IoT temperature logs with configurable anomaly profiles."""

    def __init__(self, seed: Optional[int] = 42):
        if seed is not None:
            random.seed(seed)
        self.seed = seed

    def generate_delivery(
        self,
        delivery_idx: int,
        start_time: datetime.datetime,
        category: str,
        route_info: Dict,
        anomaly_type: str = "COMPLIANT",
        duration_hours: float = 4.0,
        nominal_interval_min: float = 5.0,
    ) -> List[Dict]:
        """Generates time-series sensor telemetry for a single delivery."""
        profile = PRODUCT_PROFILES[category]
        delivery_id = f"DEL-{1000 + delivery_idx:04d}"
        vehicle_id = f"{random.choice(VEHICLE_PREFIXES)}-{random.randint(101, 399)}"
        warehouse_id = random.choice(WAREHOUSES)
        route_id = route_info["route_id"]
        base_ambient = route_info["base_ambient"]

        records = []
        current_time = start_time
        end_time = start_time + datetime.timedelta(hours=duration_hours)

        container_temp = profile["default_temp"]
        battery = random.randint(85, 100)

        # Decide anomaly characteristics
        compressor_failure_time = None
        if anomaly_type == "COOLING_FAILURE":
            # Compressor fails between 25% and 50% into the trip
            compressor_failure_time = start_time + datetime.timedelta(
                hours=duration_hours * random.uniform(0.25, 0.50)
            )

        gap_injected = False
        duplicate_injected = False

        while current_time <= end_time:
            # Ambient temperature variations (diurnal sine wave + noise)
            elapsed_hours = (current_time - start_time).total_seconds() / 3600.0
            ambient_temp = base_ambient + 3.0 * math.sin(elapsed_hours) + random.gauss(0, 0.4)
            ambient_temp = round(ambient_temp, 2)

            door_open = 0
            # Transit status transitions
            if elapsed_hours < 0.2:
                transit_status = "LOADING"
                door_open = 1 if random.random() < 0.6 else 0
            elif current_time >= end_time - datetime.timedelta(minutes=20):
                transit_status = "UNLOADING"
                door_open = 1 if random.random() < 0.7 else 0
            else:
                transit_status = "IN_TRANSIT"
                # Occasional brief inspection stop
                if random.random() < 0.04:
                    door_open = 1

            # Container temperature physics simulation
            if anomaly_type == "COMPLIANT":
                # Healthy reefer unit maintaining target band with slight sensor jitter
                target_center = (profile["target_min"] + profile["target_max"]) / 2.0
                container_temp += 0.25 * (target_center - container_temp) + random.gauss(0, 0.15)
                if door_open:
                    container_temp += random.uniform(0.2, 0.6)

            elif anomaly_type == "COOLING_FAILURE":
                if current_time >= compressor_failure_time:
                    # Insulation warming towards ambient
                    warming_rate = 0.08 * (ambient_temp - container_temp)
                    container_temp += warming_rate * (nominal_interval_min / 5.0) + random.gauss(0, 0.1)
                else:
                    container_temp += random.gauss(0, 0.12)

            elif anomaly_type == "DOOR_AJAR":
                # Reefer door poorly sealed during transit
                if random.random() < 0.35:
                    door_open = 1
                    container_temp += random.uniform(0.5, 1.2)
                else:
                    target_center = (profile["target_min"] + profile["target_max"]) / 2.0
                    container_temp += 0.15 * (target_center - container_temp) + random.gauss(0, 0.2)

            elif anomaly_type == "OVER_CHILLING":
                # Thermostat sensor stuck low, over-freezing
                container_temp = profile["target_min"] - random.uniform(1.0, 3.5)

            # Record creation
            record = {
                "record_id": f"REC-{uuid.uuid4().hex[:8].upper()}",
                "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "delivery_id": delivery_id,
                "vehicle_id": vehicle_id,
                "route_id": route_id,
                "warehouse_id": warehouse_id,
                "product_category": category,
                "target_temp_min": profile["target_min"],
                "target_temp_max": profile["target_max"],
                "container_temp": round(container_temp, 2),
                "ambient_temp": ambient_temp,
                "door_open_flag": door_open,
                "battery_level": max(5, int(battery - elapsed_hours * 1.5)),
                "transit_status": transit_status,
            }
            records.append(record)

            # Edge Case 1: Injected Duplicate Timestamp
            if not duplicate_injected and elapsed_hours > 1.0 and random.random() < 0.15:
                # Same timestamp with slightly noisy re-transmitted reading
                dup_record = record.copy()
                dup_record["record_id"] = f"REC-{uuid.uuid4().hex[:8].upper()}"
                records.append(dup_record)
                duplicate_injected = True

            # Determine next interval step
            # Edge Case 2: Injected Long Telemetry Gap (e.g. 35 - 55 min sensor disconnect)
            if not gap_injected and elapsed_hours > 1.5 and random.random() < 0.25:
                step_minutes = random.uniform(35.0, 50.0)  # Exceeds MAX_GAP_MINUTES (15 min)
                gap_injected = True
            else:
                # Normal or slightly jittered sampling (4 to 6 minutes)
                step_minutes = nominal_interval_min + random.uniform(-0.8, 0.8)

            current_time += datetime.timedelta(minutes=step_minutes)

        return records

    def generate_fleet_dataset(
        self,
        num_deliveries: int = 12,
        start_date: Optional[datetime.datetime] = None,
    ) -> pd.DataFrame:
        """Generates a complete dataset containing multiple deliveries and varied anomaly profiles."""
        if start_date is None:
            start_date = datetime.datetime(2026, 10, 19, 6, 0, 0)

        categories = list(PRODUCT_PROFILES.keys())
        all_records = []

        anomaly_distribution = [
            "COMPLIANT",
            "COMPLIANT",
            "COMPLIANT",
            "COOLING_FAILURE",
            "DOOR_AJAR",
            "OVER_CHILLING",
        ]

        for i in range(num_deliveries):
            category = categories[i % len(categories)]
            route_info = ROUTES[i % len(ROUTES)]
            anomaly = anomaly_distribution[i % len(anomaly_distribution)]
            # Stagger start times
            delivery_start = start_date + datetime.timedelta(
                hours=random.uniform(0.5, 8.0) * (i // 3)
            )
            duration = random.uniform(3.0, 6.5)

            delivery_records = self.generate_delivery(
                delivery_idx=i + 1,
                start_time=delivery_start,
                category=category,
                route_info=route_info,
                anomaly_type=anomaly,
                duration_hours=duration,
                nominal_interval_min=5.0,
            )
            all_records.extend(delivery_records)

        df = pd.DataFrame(all_records)
        return df


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic cold-chain sensor data.")
    parser.add_argument("--deliveries", type=int, default=16, help="Number of deliveries to simulate")
    parser.add_argument(
        "--output",
        type=str,
        default="data/sample/cold_chain_sample.csv",
        help="Path for generated output CSV",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    generator = ColdChainDataGenerator(seed=args.seed)
    df = generator.generate_fleet_dataset(num_deliveries=args.deliveries)
    df.to_csv(args.output, index=False)

    print(f"✅ Generated {len(df)} records across {args.deliveries} deliveries.")
    print(f"📁 Saved to: {args.output}")
    print(f"📊 Summary of categories simulated:\n{df['product_category'].value_counts().to_string()}")


if __name__ == "__main__":
    main()
