#!/usr/bin/env bash
# ==============================================================================
# FreshTrack BD — Real Apache Hadoop Distributed Streaming Job Runner
# MODE: REAL_HADOOP
# Submits mapper.py and reducer.py to a real Apache Hadoop YARN/HDFS cluster.
# Fails immediately if Hadoop / HDFS is not installed or unreachable.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

LOCAL_INPUT="${1:-"$WORKSPACE_ROOT/data/raw/telemetry_raw.csv"}"
LOCAL_OUTPUT="${2:-"$WORKSPACE_ROOT/data/processed/summary_metrics.csv"}"

HDFS_BASE_DIR="/user/freshtrack"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
HDFS_INPUT_DIR="$HDFS_BASE_DIR/input_$TIMESTAMP"
HDFS_OUTPUT_DIR="$HDFS_BASE_DIR/output_$TIMESTAMP"

echo "======================================================================"
echo " FreshTrack BD — Real Hadoop Distributed Job Runner"
echo " MODE: REAL_HADOOP"
echo "======================================================================"

# 1. Verify Hadoop Binary
if ! command -v hadoop &>/dev/null; then
    echo "❌ FATAL: 'hadoop' command not found in PATH." >&2
    echo "To run in simulation mode without Hadoop, execute: hadoop/run_local_streaming.sh" >&2
    exit 1
fi

# 2. Verify HDFS Reachability
if ! hdfs dfs -ls / &>/dev/null; then
    echo "❌ FATAL: HDFS NameNode is unreachable. Hadoop daemons are offline." >&2
    echo "To run in simulation mode without Hadoop, execute: hadoop/run_local_streaming.sh" >&2
    exit 1
fi

# 3. Locate Hadoop Streaming Jar
STREAMING_JAR=""
if [ -n "${HADOOP_HOME:-}" ] && [ -d "$HADOOP_HOME" ]; then
    STREAMING_JAR=$(find "$HADOOP_HOME" -name "hadoop-streaming*.jar" 2>/dev/null | head -n 1)
fi

if [ -z "$STREAMING_JAR" ]; then
    # Search common system directories
    STREAMING_JAR=$(find /usr/lib/hadoop /usr/local/hadoop /opt/hadoop -name "hadoop-streaming*.jar" 2>/dev/null | head -n 1 || true)
fi

if [ -z "$STREAMING_JAR" ]; then
    echo "❌ FATAL: Could not locate hadoop-streaming*.jar in HADOOP_HOME or system paths." >&2
    exit 1
fi

echo "✅ Hadoop Cluster Verified: $(hadoop version | head -n 1)"
echo "✅ Hadoop Streaming Jar: $STREAMING_JAR"

# 4. Stage Input to HDFS
echo "Uploading $LOCAL_INPUT to HDFS at $HDFS_INPUT_DIR..."
hdfs dfs -mkdir -p "$HDFS_INPUT_DIR"
hdfs dfs -put -f "$LOCAL_INPUT" "$HDFS_INPUT_DIR/telemetry.csv"

# 5. Launch MapReduce Job
echo "Submitting MapReduce Job to YARN..."
hadoop jar "$STREAMING_JAR" \
    -files "$SCRIPT_DIR/mapper.py,$SCRIPT_DIR/reducer.py" \
    -mapper "python3 mapper.py" \
    -reducer "python3 reducer.py" \
    -input "$HDFS_INPUT_DIR/telemetry.csv" \
    -output "$HDFS_OUTPUT_DIR"

# 6. Retrieve Results from HDFS
echo "Retrieving aggregated results from $HDFS_OUTPUT_DIR to $LOCAL_OUTPUT..."
mkdir -p "$(dirname "$LOCAL_OUTPUT")"
hdfs dfs -getmerge "$HDFS_OUTPUT_DIR" "$LOCAL_OUTPUT"

echo "✅ REAL_HADOOP Job finished successfully. Output saved to $LOCAL_OUTPUT."
echo "======================================================================"
