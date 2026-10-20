# FreshTrack BD — Architecture Specification
## Big Data Cold-Chain Storage & Delivery Risk Analytics

---

## 1. Executive Summary & Problem Scope

**FreshTrack BD** is an end-to-end Big Data analytics system designed to analyze temperature records from simulated food deliveries to identify cold-chain compliance and transit risks across products, delivery routes, warehouses, and time periods.

### Scope & Scientific Boundary
- **Objective**: Identify temperature excursions (breaches of target climate ranges), calculate duration of exposure, and highlight vulnerable logistics corridors and facilities.
- **Operational Compliance vs. Spoilage Disclaimer**: FreshTrack BD calculates *thermal exposure metrics* (such as degree-hours and time out of refrigeration) and illustrative compliance indices. It does **not** claim to predict actual microbiological growth, bacterial contamination, or food spoilage, as real spoilage depends on unmeasured biological variables (e.g., initial bacterial load, packaging atmosphere, pH, and water activity).

---

## 2. System Architecture & Dual-Mode Execution

FreshTrack BD enforces a strict separation between real Hadoop distributed execution and local pipeline simulation.

```
                      +---------------------------------------+
                      |   Simulated IoT Telemetry Generator   |
                      |        (src/data_generator.py)        |
                      +-------------------+-------------------+
                                          |
                                    [ Raw CSV ]
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        DYNAMIC RUNTIME MODE DETECTION                             |
|                           (src/hadoop_manager.py)                                 |
|                                                                                   |
|  Checks: $HADOOP_HOME, $JAVA_HOME, `which hadoop`, `which java`, NameNode status  |
+-----------------------------------------------------------------------------------+
       |                                                             |
       | [Mode A: Cluster Available]                                 | [Mode B: Fallback]
       v                                                             v
+---------------------------------------+   +---------------------------------------+
|          REAL_HADOOP MODE             |   |        LOCAL_STREAMING MODE           |
|      (Apache Hadoop Distributed)      |   |       (Local Pipe Emulation)          |
+---------------------------------------+   +---------------------------------------+
| 1. Stage CSV into HDFS:               |   | 1. Read local CSV file:               |
|    hdfs dfs -put data/raw/input.csv   |   |    cat data/raw/input.csv |           |
|    /user/freshtrack/raw/              |   |    python3 hadoop/mapper.py |         |
| 2. Run Hadoop Streaming Jar:          |   |    sort -k1,1 |                       |
|    hadoop jar hadoop-streaming.jar    |   |    python3 hadoop/reducer.py          |
|    -files mapper.py,reducer.py        |   |    > data/processed/summary.csv       |
|    -input /user/freshtrack/raw/       |   |                                       |
|    -output /user/freshtrack/out/      |   | * Strictly labeled as Local Pipe      |
|    -mapper "python3 mapper.py"        |   |   Emulation. Never claimed to be      |
|    -reducer "python3 reducer.py"      |   |   actual Hadoop execution.            |
| 3. Copy results back to local:        |   |                                       |
|    hdfs dfs -get /user/freshtrack/out |   | * Executes the exact same Python      |
| 4. Telemetry: Actual Hadoop Job ID    |   |   mapper & reducer scripts.           |
+---------------------------------------+   +---------------------------------------+
                                          |
                                  [ Processed Data ]
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                           ANALYTICS & RISK ENGINE                                 |
|                              (src/analytics.py)                                   |
|                                                                                   |
|   - Timestamp-aware breach duration & degree-hours accumulation                   |
|   - Telemetry integrity check (gap & duplicate tracking)                          |
|   - Optional: Mean Kinetic Temperature (MKT) with documented assumptions          |
|   - Optional: Illustrative Cold-Chain Risk Score (0 - 100)                        |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                       PRESENTATION & DASHBOARD LAYER                              |
|                              (Streamlit + Plotly)                                 |
|                                                                                   |
|   - Distinct Execution Mode Badge (`REAL_HADOOP` vs `LOCAL_STREAMING`)            |
|   - Fleet Overview & Route Compliance Heatmaps                                    |
|   - Time-series Excursion Deep-Dive (Container vs Target Temp Bounds)             |
|   - Offline-ready with pre-generated seed dataset                                 |
+-----------------------------------------------------------------------------------+
```

### Strict Mode Differentiation
1. **`REAL_HADOOP`**: Active **only** when a live Hadoop installation and HDFS NameNode are verified via real diagnostic commands (`hadoop version` and `hdfs dfs -ls /`). Outputs real Hadoop Job IDs and HDFS paths.
2. **`LOCAL_STREAMING`**: Emulates the MapReduce pipeline locally using standard Unix standard streams (`stdin` / `stdout`) and POSIX `sort`. Logs, UI, and documentation explicitly state that this is **Local Pipe Emulation**, not actual Hadoop execution.
3. **Algorithm Equivalence**: The same Python code in [`hadoop/mapper.py`](file:///Users/deyaaswinid/Desktop/FreshTrack%20BD/hadoop/mapper.py) and [`hadoop/reducer.py`](file:///Users/deyaaswinid/Desktop/FreshTrack%20BD/hadoop/reducer.py) executes in both modes without modification.

---

## 3. Data Schema Specifications

### 3.1 Input Telemetry Schema (`telemetry_raw.csv`)

A standard 14-column CSV format with header row:

| Column | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `record_id` | String | Unique telemetry UUID | `REC-10293-A` |
| `timestamp` | String (ISO 8601) | Timestamp of reading (UTC) | `2026-10-20T08:15:00Z` |
| `delivery_id` | String | Shipment consignment ID | `DEL-8401` |
| `vehicle_id` | String | Refrigerated transport vehicle | `VAN-104` |
| `route_id` | String | Route identifier | `RT-MUM-PUN-01` |
| `warehouse_id` | String | Origin / Transit warehouse hub | `WH-WEST-02` |
| `product_category` | String | Commodity type | `Dairy` |
| `target_temp_min` | Float (°C) | Safe lower temperature limit | `2.0` |
| `target_temp_max` | Float (°C) | Safe upper temperature limit | `4.0` |
| `container_temp` | Float (°C) | Internal cargo temperature reading | `6.8` |
| `ambient_temp` | Float (°C) | External environmental temperature | `32.5` |
| `door_open_flag` | Integer (0/1) | Door state (1 = open, 0 = closed) | `0` |
| `battery_level` | Integer (%) | IoT sensor battery percentage | `92` |
| `transit_status` | String | Consignment state | `IN_TRANSIT` |

### 3.2 Hadoop Streaming Intermediate Interface (Mapper to Reducer)

Hadoop Streaming passes lines of tab-separated text:
- **Key**: `<delivery_id>`
- **Value**: `<timestamp>\t<container_temp>\t<target_temp_min>\t<target_temp_max>\t<ambient_temp>\t<door_open_flag>\t<product_category>\t<route_id>\t<warehouse_id>`

Format:
```
<delivery_id>\t<timestamp>\t<container_temp>\t<target_temp_min>\t<target_temp_max>\t<ambient_temp>\t<door_open_flag>\t<product_category>\t<route_id>\t<warehouse_id>
```

### 3.3 Reducer Output Schema (`summary_metrics.csv`)

The reducer emits one aggregated record per consignment key:

| Column | Type | Description |
| :--- | :--- | :--- |
| `delivery_id` | String | Shipment consignment identifier |
| `route_id` | String | Associated transport route |
| `warehouse_id` | String | Associated transit warehouse |
| `product_category` | String | Product category |
| `total_readings` | Integer | Total raw records received |
| `valid_readings` | Integer | Valid non-corrupt readings evaluated |
| `duplicate_count` | Integer | Number of dropped duplicate timestamps |
| `gap_count` | Integer | Number of gaps exceeding `MAX_GAP_MINUTES` |
| `breach_reading_count` | Integer | Count of readings outside target bounds |
| `observed_breach_duration_min` | Float | Verified continuous breach duration (minutes) |
| `degree_hours_excursion` | Float | Cumulative degree-hours outside threshold |
| `max_temp` | Float (°C) | Maximum container temperature recorded |
| `min_temp` | Float (°C) | Minimum container temperature recorded |
| `avg_temp` | Float (°C) | Arithmetic mean container temperature |
| `door_open_count` | Integer | Readings where reefer doors were open |
| `sampling_integrity_pct` | Float (%) | Metric of telemetry continuity $(1 - \frac{\text{gaps}}{\text{expected intervals}}) \times 100$ |

---

## 4. Timestamp-Aware Excursion Calculation Algorithm

A common flaw in naive cold-chain analytics is assuming that a missing sensor reading implies the temperature remained constant. In real delivery logistics, sensors disconnect, reboot, or lose cellular connection.

### Formal Rules:
1. **Deduplication**: If multiple readings have identical timestamps for the same consignment, the earliest is retained or the duplicates are dropped with an increment to `duplicate_count`.
2. **Chronological Sorting**: The reducer buffers records for the current `<delivery_id>` and sorts them strictly by `timestamp`.
3. **Sampling Interval ($\Delta t$)**: For successive readings $R_{i-1}$ at $t_{i-1}$ and $R_i$ at $t_i$:
   $$\Delta t = t_i - t_{i-1} \quad (\text{in minutes})$$
4. **Gap Handling Threshold (`MAX_GAP_MINUTES = 15.0`)**:
   - If $\Delta t \le \text{MAX\_GAP\_MINUTES}$:
     - If $T_i > T_{\text{max}}$ (Warm Breach):
       $$\text{Duration} \mathrel{+}= \Delta t$$
       $$\text{Degree-Hours} \mathrel{+}= (T_i - T_{\text{max}}) \times \frac{\Delta t}{60}$$
     - If $T_i < T_{\text{min}}$ (Chill Breach):
       $$\text{Duration} \mathrel{+}= \Delta t$$
       $$\text{Degree-Hours} \mathrel{+}= (T_{\text{min}} - T_i) \times \frac{\Delta t}{60}$$
   - If $\Delta t > \text{MAX\_GAP\_MINUTES}$:
     - An **unobserved telemetry gap** occurred.
     - `gap_count` is incremented.
     - **Continuous excursion duration is NOT accumulated** across this interval, because the data cannot substantiate whether the temperature returned to normal or worsened during the outage.
     - The event is flagged as unverified for that period.

---

## 5. Illustrative Temperature Thresholds & Optional Science Models

### 5.1 Illustrative Threshold Guidelines

| Product Category | Target Min (°C) | Target Max (°C) | Operational Warning (°C) |
| :--- | :--- | :--- | :--- |
| **Fresh Dairy / Milk** | 2.0 | 4.0 | > 6.0 |
| **Chilled Poultry / Meat** | -1.0 | 2.0 | > 4.0 |
| **Deep Frozen Seafood** | -22.0 | -18.0 | > -15.0 |
| **Frozen Ice Cream** | -25.0 | -20.0 | > -16.0 |
| **Fresh Produce (Berries)** | 1.0 | 5.0 | > 8.0 |
| **Vaccines / Biopharma** | 2.0 | 8.0 | > 8.5 or < 1.5 |

### 5.2 Optional Metric 1: Mean Kinetic Temperature (MKT)
MKT is an established regulatory metric (USP <1079>) that represents the single isothermal temperature that reflects the same kinetic thermal degradation as a fluctuating temperature profile over time:
$$T_K = \frac{\frac{\Delta H}{R}}{-\ln\left( \frac{1}{n} \sum_{i=1}^{n} e^{-\frac{\Delta H}{R \cdot T_i}} \right)}$$
- $\Delta H$: Standard activation energy (assumed $83.144 \text{ kJ/mol}$)
- $R$: Universal gas constant ($8.314 \text{ J/mol}\cdot\text{K}$)
- $T_i$: Absolute temperature in Kelvin ($T_{^\circ\text{C}} + 273.15$)
- **Assumption & Limitation**: Assumes single first-order chemical degradation kinetics. Treated as an *indicative quality metric*, not a direct measure of food safety.

### 5.3 Optional Metric 2: Composite Cold-Chain Risk Index (0–100)
An operational heuristic to rank routes and warehouses:
$$\text{Risk Index} = \min\left(100, \; 0.35 \times (\text{Breach Rate} \times 100) + 0.35 \times (\text{Degree-Hours} \times 8) + 0.15 \times (\text{Door Open Ratio} \times 100) + 0.15 \times (\text{Gap Penalty})\right)$$
Clearly presented in the UI as a comparative ranking index for logistics management.

---

## 6. Scope & 2-Day Timeline Guardrails

To ensure completion within the 2-day expo deadline:
1. **Core Priority**:
   - Synthetic data generation with anomaly scenarios.
   - Exact Python mapper & reducer scripts.
   - Local Unix pipe streaming runner.
   - Comprehensive test suite comparing streaming results to a Pandas reference implementation.
   - Functional Streamlit dashboard with core KPI and deep-dive views.
2. **Deferred / Stretch Features**:
   - Complex GeoJSON map layers (fallback to clean Plotly route scatter/bar charts).
   - Video recording / heavy browser automation.
   - Native Hadoop Darwin ARM64 cluster setup (fallback remains primary on local Mac).
