#!/usr/bin/env bash
# ==============================================================================
# FreshTrack BD - Environment Diagnostic Script
# Detects OS Architecture, Java, Hadoop, HDFS status, and Python packages.
# ==============================================================================

set -u

echo "======================================================================"
echo " FreshTrack BD — Environment & Dependency Diagnostic Check"
echo "======================================================================"

OS_ARCH=$(uname -m)
OS_NAME=$(uname -s)
echo " Operating System: $OS_NAME ($OS_ARCH)"

# 1. Check Python
echo -n "[1/5] Checking Python 3... "
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version)
    echo "FOUND: $PY_VER"
else
    echo "MISSING: python3 not found!"
fi

# 2. Check Java Runtime / JDK
echo -n "[2/5] Checking Java JDK... "
if command -v java &>/dev/null && java -version &>/dev/null; then
    JAVA_VER=$(java -version 2>&1 | head -n 1)
    echo "FOUND: $JAVA_VER"
    HAVE_JAVA=1
else
    echo "NOT INSTALLED: Java runtime / OpenJDK not located."
    HAVE_JAVA=0
fi

# 3. Check Hadoop CLI
echo -n "[3/5] Checking Hadoop Binary... "
if command -v hadoop &>/dev/null; then
    HADOOP_VER=$(hadoop version 2>&1 | head -n 1)
    echo "FOUND: $HADOOP_VER"
    HAVE_HADOOP=1
else
    echo "NOT INSTALLED: 'hadoop' command not found in PATH."
    HAVE_HADOOP=0
fi

# 4. Check HDFS Status
echo -n "[4/5] Checking HDFS Service... "
if [ "$HAVE_HADOOP" -eq 1 ]; then
    if hdfs dfs -ls / &>/dev/null; then
        echo "ACTIVE: HDFS NameNode is reachable."
        HDFS_STATUS="ONLINE"
    else
        echo "INACTIVE: HDFS daemon is not running."
        HDFS_STATUS="OFFLINE"
    fi
else
    echo "SKIPPED: Hadoop is not installed."
    HDFS_STATUS="NOT_INSTALLED"
fi

# 5. Check Key Python Libraries
echo "[5/5] Checking Required Python Libraries..."
for pkg in pandas streamlit plotly numpy pyarrow; do
    echo -n "   - $pkg: "
    if python3 -c "import $pkg" &>/dev/null; then
        VER=$(python3 -c "import $pkg; print(getattr($pkg, '__version__', 'installed'))")
        echo "INSTALLED ($VER)"
    else
        echo "MISSING (Run 'pip install -r requirements.txt')"
    fi
done

echo "======================================================================"
echo " DIAGNOSIS & RUNTIME MODE RECOMMENDATION"
echo "======================================================================"
if [ "$HAVE_JAVA" -eq 1 ] && [ "$HAVE_HADOOP" -eq 1 ] && [ "$HDFS_STATUS" = "ONLINE" ]; then
    echo " Status: FULL NATIVE HADOOP AVAILABLE"
    echo " FreshTrack BD will use real HDFS storage & Hadoop Streaming MapReduce."
elif [ "$OS_ARCH" = "arm64" ]; then
    echo " Status: MACOS APPLE SILICON (ARM64) DUAL-MODE ACTIVE"
    echo " -> Native Hadoop is NOT configured or daemons are down."
    echo " -> FreshTrack BD Fallback Engine: Unix Streaming MapReduce Pipe Emulation"
    echo "    (Executes identical Python mapper.py & reducer.py scripts with strict"
    echo "     isolation, real key-sorting, and zero simulated claims)."
fi
echo "======================================================================"
