#!/usr/bin/env python3
"""
FreshTrack BD — Timestamp-Aware Hadoop Streaming Reducer
Aggregates telemetry records per consignment key (<delivery_id>), enforces
chronological timestamp sorting, handles missing readings, duplicate timestamps,
and unobserved gaps (> MAX_GAP_MINUTES), and calculates temperature excursions.

Input: Tab-separated key-values from mapper, sorted by key:
       <delivery_id>\t<timestamp>\t<container_temp>\t<target_temp_min>\t<target_temp_max>\t<ambient_temp>\t<door_open_flag>\t<product_category>\t<route_id>\t<warehouse_id>

Output: CSV summary metrics per delivery:
        delivery_id,route_id,warehouse_id,product_category,total_readings,valid_readings,duplicate_count,gap_count,breach_reading_count,observed_breach_duration_min,degree_hours_excursion,max_temp,min_temp,avg_temp,door_open_count,sampling_integrity_pct
"""

import datetime
import sys

# Maximum gap allowed between successive readings before marking as unobserved outage
MAX_GAP_MINUTES = 15.0

OUTPUT_HEADER = (
    "delivery_id,route_id,warehouse_id,product_category,total_readings,valid_readings,"
    "duplicate_count,gap_count,breach_reading_count,observed_breach_duration_min,"
    "degree_hours_excursion,max_temp,min_temp,avg_temp,door_open_count,sampling_integrity_pct\n"
)


def parse_iso_timestamp(ts_str: str) -> datetime.datetime:
    """Parses ISO 8601 UTC timestamp strings like 2026-10-20T08:15:00Z."""
    ts_clean = ts_str.strip().rstrip("Z")
    if "." in ts_clean:
        return datetime.datetime.fromisoformat(ts_clean)
    return datetime.datetime.strptime(ts_clean, "%Y-%m-%dT%H:%M:%S")


def process_consignment(delivery_id: str, records: list) -> str:
    """
    Computes timestamp-aware quality metrics for a single consignment.
    records: list of dicts with parsed telemetry fields
    """
    total_readings = len(records)
    if total_readings == 0:
        return ""

    # 1. Sort records chronologically by timestamp
    records.sort(key=lambda r: r["timestamp"])

    metadata = records[0]
    route_id = metadata["route_id"]
    warehouse_id = metadata["warehouse_id"]
    product_category = metadata["product_category"]

    valid_readings = 0
    duplicate_count = 0
    gap_count = 0
    breach_reading_count = 0
    observed_breach_duration_min = 0.0
    degree_hours_excursion = 0.0
    door_open_count = 0

    all_temps = []
    deduped_records = []
    seen_timestamps = set()

    # 2. De-duplicate identical timestamps
    for rec in records:
        ts = rec["timestamp"]
        if ts in seen_timestamps:
            duplicate_count += 1
            continue
        seen_timestamps.add(ts)
        deduped_records.append(rec)
        valid_readings += 1

    if not deduped_records:
        return ""

    # 3. Analyze time-series and calculate excursions
    prev_time = None

    for i, rec in enumerate(deduped_records):
        curr_time = rec["timestamp"]
        temp = rec["container_temp"]
        t_min = rec["target_temp_min"]
        t_max = rec["target_temp_max"]
        door_open = rec["door_open"]

        all_temps.append(temp)
        if door_open == 1:
            door_open_count += 1

        is_breach = (temp > t_max) or (temp < t_min)
        if is_breach:
            breach_reading_count += 1

        if prev_time is not None:
            delta_min = (curr_time - prev_time).total_seconds() / 60.0

            if delta_min <= MAX_GAP_MINUTES:
                # Valid continuous observation window
                if is_breach:
                    observed_breach_duration_min += delta_min
                    if temp > t_max:
                        degree_hours_excursion += (temp - t_max) * (delta_min / 60.0)
                    elif temp < t_min:
                        degree_hours_excursion += (t_min - temp) * (delta_min / 60.0)
            else:
                # Long gap: do NOT infer continuous breach across unmonitored window
                gap_count += 1

        prev_time = curr_time

    # 4. Compute temperature statistics
    max_temp = max(all_temps) if all_temps else 0.0
    min_temp = min(all_temps) if all_temps else 0.0
    avg_temp = sum(all_temps) / len(all_temps) if all_temps else 0.0

    # 5. Compute sampling integrity percentage
    intervals_evaluated = max(1, valid_readings - 1)
    integrity_pct = max(0.0, min(100.0, ((intervals_evaluated - gap_count) / intervals_evaluated) * 100.0))

    return (
        f"{delivery_id},{route_id},{warehouse_id},{product_category},"
        f"{total_readings},{valid_readings},{duplicate_count},{gap_count},"
        f"{breach_reading_count},{observed_breach_duration_min:.2f},"
        f"{degree_hours_excursion:.4f},{max_temp:.2f},{min_temp:.2f},"
        f"{avg_temp:.2f},{door_open_count},{integrity_pct:.2f}\n"
    )


def reduce_stream():
    current_key = None
    current_records = []
    header_emitted = False

    # Check if header should be printed (e.g. standalone or first task)
    if not header_emitted:
        sys.stdout.write(OUTPUT_HEADER)
        header_emitted = True

    for line_num, line in enumerate(sys.stdin, start=1):
        line = line.strip()
        if not line:
            continue

        parts = line.split("\t")
        if len(parts) < 10:
            continue

        key = parts[0]

        try:
            timestamp = parse_iso_timestamp(parts[1])
            container_temp = float(parts[2])
            target_min = float(parts[3])
            target_max = float(parts[4])
            ambient_temp = float(parts[5])
            door_open = int(parts[6])
            category = parts[7]
            route_id = parts[8]
            warehouse_id = parts[9]
        except (ValueError, IndexError) as err:
            sys.stderr.write(f"WARN [Reducer Line {line_num}]: Parse error ({err}). Skipped.\n")
            continue

        record = {
            "timestamp": timestamp,
            "container_temp": container_temp,
            "target_temp_min": target_min,
            "target_temp_max": target_max,
            "ambient_temp": ambient_temp,
            "door_open": door_open,
            "product_category": category,
            "route_id": route_id,
            "warehouse_id": warehouse_id,
        }

        if current_key is None:
            current_key = key

        if key != current_key:
            # Emit aggregated result for previous consignment
            output_line = process_consignment(current_key, current_records)
            if output_line:
                sys.stdout.write(output_line)
            current_key = key
            current_records = [record]
        else:
            current_records.append(record)

    # Emit final consignment
    if current_key is not None and current_records:
        output_line = process_consignment(current_key, current_records)
        if output_line:
            sys.stdout.write(output_line)


if __name__ == "__main__":
    reduce_stream()
