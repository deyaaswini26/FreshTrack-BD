#!/usr/bin/env python3
"""
FreshTrack BD — Hadoop Streaming Mapper
Reads raw CSV telemetry stream from sys.stdin, validates schema types,
filters corrupt records, and emits tab-separated key-value pairs to sys.stdout.

Key:   <delivery_id>
Value: <timestamp>\t<container_temp>\t<target_temp_min>\t<target_temp_max>\t<ambient_temp>\t<door_open_flag>\t<product_category>\t<route_id>\t<warehouse_id>
"""

import csv
import sys


def parse_and_map():
    reader = csv.reader(sys.stdin)
    corrupted_count = 0

    for line_num, row in enumerate(reader, start=1):
        if not row:
            continue

        # Skip CSV Header if present
        if row[0].strip() == "record_id" or "timestamp" in row:
            continue

        # Expect 14 columns as defined in input schema
        if len(row) < 14:
            sys.stderr.write(f"WARN [Line {line_num}]: Incomplete columns ({len(row)}/14). Skipped.\n")
            corrupted_count += 1
            continue

        try:
            record_id = row[0].strip()
            timestamp_str = row[1].strip()
            delivery_id = row[2].strip()
            vehicle_id = row[3].strip()
            route_id = row[4].strip()
            warehouse_id = row[5].strip()
            product_category = row[6].strip()

            target_temp_min = float(row[7])
            target_temp_max = float(row[8])
            container_temp = float(row[9])
            ambient_temp = float(row[10])
            door_open_flag = int(row[11])

            # Validation check
            if not delivery_id or not timestamp_str:
                sys.stderr.write(f"WARN [Line {line_num}]: Missing delivery_id or timestamp. Skipped.\n")
                corrupted_count += 1
                continue

            # Emit Key \t Values
            # Key = delivery_id
            values = [
                timestamp_str,
                f"{container_temp:.2f}",
                f"{target_temp_min:.2f}",
                f"{target_temp_max:.2f}",
                f"{ambient_temp:.2f}",
                str(door_open_flag),
                product_category,
                route_id,
                warehouse_id,
            ]
            sys.stdout.write(f"{delivery_id}\t{chr(9).join(values)}\n")

        except (ValueError, IndexError) as err:
            sys.stderr.write(f"WARN [Line {line_num}]: Type conversion failed ({err}). Skipped.\n")
            corrupted_count += 1
            continue

    if corrupted_count > 0:
        sys.stderr.write(f"INFO: Mapper finished with {corrupted_count} dropped/corrupted records.\n")


if __name__ == "__main__":
    parse_and_map()
