#!/usr/bin/env bash
# ==============================================================================
# FreshTrack BD — Local Streaming Pipeline Runner
# EXPLICIT NOTICE: This script runs MapReduce logic via standard Unix streams
# (cat | mapper.py | sort | reducer.py). This is a LOCAL PIPE EMULATION.
# It does NOT invoke Apache Hadoop or HDFS.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

INPUT_FILE="${1:-"$WORKSPACE_ROOT/data/raw/telemetry_raw.csv"}"
OUTPUT_FILE="${2:-"$WORKSPACE_ROOT/data/processed/summary_metrics.csv"}"

if [ ! -f "$INPUT_FILE" ]; then
    echo "ERROR: Input file '$INPUT_FILE' not found." >&2
    exit 1
fi

mkdir -p "$(dirname "$OUTPUT_FILE")"

echo "======================================================================"
echo " FreshTrack BD — Local Streaming Pipeline (Unix Pipe Emulation)"
echo " MODE: LOCAL_STREAMING (Not Apache Hadoop Cluster)"
echo " Input:  $INPUT_FILE"
echo " Output: $OUTPUT_FILE"
echo "======================================================================"

START_TIME=$(date +%s)

# Execute identical mapper and reducer via POSIX stdin/stdout and sort
cat "$INPUT_FILE" | \
    python3 "$SCRIPT_DIR/mapper.py" | \
    sort -k1,1 | \
    python3 "$SCRIPT_DIR/reducer.py" > "$OUTPUT_FILE"

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
RECORD_COUNT=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')

echo "✅ Local streaming execution completed in ${DURATION}s."
echo "📊 Output written to $OUTPUT_FILE ($RECORD_COUNT lines including header)."
echo "======================================================================"
