# FreshTrack BD — Big Data Cold-Chain Analytics Platform

> *"Turning cold-chain telemetry into actionable intelligence."*

[![Platform: macOS ARM64](https://img.shields.io/badge/Platform-macOS%20ARM64-blue.svg)](https://apple.com)
[![Python: 3.12](https://img.shields.io/badge/Python-3.12-green.svg)](https://python.org)
[![Hadoop: MapReduce Streaming](https://img.shields.io/badge/Hadoop-MapReduce%20Streaming-orange.svg)](https://hadoop.apache.org)
[![Dashboard: Streamlit Enterprise](https://img.shields.io/badge/Dashboard-Streamlit%20Enterprise-red.svg)](https://streamlit.io)
[![Visualization: Plotly Industrial](https://img.shields.io/badge/Visualization-Plotly%20Dark-teal.svg)](https://plotly.com)

**FreshTrack BD** is an enterprise-grade industrial analytics platform designed to analyze high-frequency temperature telemetry from simulated refrigerated food deliveries. It detects cold-chain compliance breaches, ranks vulnerable transport corridors and storage hubs, and demonstrates an end-to-end distributed MapReduce pipeline compatible with Apache Hadoop Streaming.

---

## 1. System Architecture & Dual-Mode Execution

FreshTrack BD enforces a strict, transparent separation between distributed Hadoop processing and local emulation:

```
[Raw IoT Telemetry CSV]
         │
         ├──► [Mode A: REAL_HADOOP] (Apache Hadoop YARN + HDFS Cluster)
         │    hadoop jar hadoop-streaming.jar -mapper mapper.py -reducer reducer.py
         │    Status: Verified dynamically via `hadoop version` & `hdfs dfs -ls /`
         │
         └──► [Mode B: LOCAL_STREAMING] (Deterministic Unix Pipe Emulation)
              cat telemetry_raw.csv | python3 mapper.py | sort -k1,1 | python3 reducer.py
              Status: Runs identical streaming scripts with pure POSIX standard streams
```

### Engineering & Scientific Integrity Guarantees
- **No Fabricated Clusters**: If native Hadoop daemons are absent (as on macOS Apple Silicon without containerized Linux), the platform explicitly displays `LOCAL_STREAMING (Unix Pipe Emulation)` and leaves `Hadoop Job ID: N/A`. It **never** describes local Unix pipes as actual Hadoop execution.
- **Identical Python Code**: Both modes execute the exact same [hadoop/mapper.py](file:///Users/deyaaswinid/Desktop/FreshTrack%20BD/hadoop/mapper.py) and [hadoop/reducer.py](file:///Users/deyaaswinid/Desktop/FreshTrack%20BD/hadoop/reducer.py) scripts without modification.
- **Timestamp-Aware Quality Rules**:
  - Drops duplicate sensor packets to prevent artificial duration inflation.
  - Enforces `MAX_GAP_MINUTES = 15.0`: Continuous breach duration is **not** inferred across unmonitored dropouts.
- **Scientific Boundaries (USP <1079> / FDA)**:
  - Mean Kinetic Temperature (MKT) calculates thermal exposure via the Arrhenius equation ($\Delta H = 83.144 \text{ kJ/mol}$).
  - Documented as an *operational compliance indicator*, **not** a predictive assay of biological bacterial growth.

---

## 2. Five Enterprise Navigation Views

The application provides an industrial control tower organized into five distinct operational views:

| View | Purpose | Key Technical Capabilities |
| :--- | :--- | :--- |
| **1. Overview** | Executive Operations Control | Fleet compliance rate (reading-level denominator), monitored shipment counts, high-risk flags, degree-hours total, temporal excursion trend bar chart, risk tier donut chart, commodity compliance comparison, sortable high-risk shipment table, and data-driven operational intelligence alerts. |
| **2. Route & Facility Analytics** | Vulnerability Ranking | Corridor risk table, route excursion comparison bar chart, warehouse compliance bar chart, Route vs. Product risk heatmap, diurnal time-of-day excursion frequency, and facility loading inspection. |
| **3. Shipment Deep Dive** | Audit & Root Cause Analysis | Consignment selector, safe temperature envelope, high-resolution sensor telemetry trace (line broken across outages, door-open markers, unobserved gap annotations), documented excursion episodes timeline table, explainable risk breakdown, and Arrhenius MKT vs. arithmetic mean analysis. |
| **4. MapReduce Engine** | Big Data Pipeline Transparency | Interactive 7-stage processing diagram, execution telemetry panel, MapReduce execution controls, downloadable aggregated CSV, and live data lake previews (Raw CSV, Mapper stdout, Sorted stream, Reducer stdout). |
| **5. Data Explorer** | Audit & Data Quality | Filterable raw sensor telemetry grid, aggregated summary metrics grid, schema data dictionary (14 columns), commodity target thresholds, and CSV export. |

---

## 3. Directory Layout

```
FreshTrack BD/
├── README.md                      # Project documentation and presentation guide
├── architecture.md               # Full technical architecture & math models
├── requirements.txt              # Python project dependencies
├── .gitignore                    # Git exclusions
├── app/                          # Presentation Layer
│   ├── main.py                   # 5-view enterprise Streamlit dashboard
│   └── components/               # Custom UI modules
│       ├── styles.py             # Dark industrial CSS design system (#0B1220 / #101A2B)
│       └── ui_elements.py        # Clean SVG line icons, headers, KPI cards, Plotly layout
├── data/
│   ├── raw/                      # Ingested simulated sensor CSVs
│   ├── processed/                # MapReduce output CSVs and summary metrics
│   └── sample/                   # Pre-packaged 1,045 records across 20 deliveries
├── docs/
│   ├── architecture.md           # Architecture mirror
│   ├── project_plan.md           # Refined 2-day implementation roadmap
│   └── expo_presentation_guide.md# Speaker cheat-sheet & judge walkthrough
├── hadoop/
│   ├── mapper.py                 # Hadoop Streaming mapper (stdin -> stdout)
│   ├── reducer.py                # Timestamp-aware Hadoop Streaming reducer
│   ├── run_local_streaming.sh    # Unix pipe streaming execution script
│   └── run_hadoop_job.sh         # Real cluster launch script
├── scripts/
│   └── check_env.sh              # Diagnostic tool to verify system & Hadoop
├── src/
│   ├── analytics.py              # Arrhenius MKT, Risk Scoring, corridor rollups
│   ├── data_generator.py         # Realistic IoT cold-chain telemetry generator
│   └── hadoop_manager.py         # Dynamic environment probe & pipeline controller
└── tests/
    ├── test_pipeline_parity.py   # Parity tests vs ground-truth Pandas reference
    └── test_analytics.py         # Unit tests for MKT physics and risk scoring
```

---

## 4. Quick Start & Setup

### Step 1: Run Environment Diagnostic
```bash
./scripts/check_env.sh
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run Unit Test Suite
```bash
python3 -m unittest discover tests/ -v
```

### Step 4: Launch the Enterprise Dashboard
```bash
streamlit run app/main.py
```
Open **http://localhost:8501** in your browser.

---

## 5. Expo Demonstration Sequence (For Judges & Industrial Experts)

1. **The Problem Statement**: Open **Overview** and highlight the global compliance rate and thermal excursion metrics. Explain how cold chains generate massive sensor streams that require distributed MapReduce aggregation.
2. **Corridor Vulnerabilities**: Switch to **Route & Facility Analytics**. Show the corridor fragility ranking and route-product risk heatmap to demonstrate how specific routes experience chronic failure.
3. **Sensor Science & Gap Handling**: Switch to **Shipment Deep Dive**. Select a breached delivery (e.g. `DEL-1004` [Frozen Desserts]):
   - Show the green permissible temperature envelope.
   - Point out how the line breaks across outage gaps (> 15 min) with gray shaded annotations (*"Telemetry Gap (>15m) — Breach Not Inferred"*).
   - Point out Arrhenius Mean Kinetic Temperature (MKT) and explain how exponential thermal weighting differs from arithmetic averages.
4. **Hadoop Streaming Engine**: Switch to **MapReduce Engine**. Point to the transparent execution badge (`LOCAL_STREAMING (Unix Pipe Emulation)`). Click **"Execute MapReduce Job Now"** to run the pipeline live. Expand the technical panels to show actual tab-separated intermediate key-values emitted by `mapper.py`.
5. **Data Explorer**: Switch to **Data Explorer** to demonstrate raw data querying, data dictionary schemas, and CSV export.
