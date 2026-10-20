# FreshTrack BD — Refined 2-Day College Project Expo Implementation Plan

**Target Event**: College Project Expo  
**Timeline**: 48 Hours (2 Days)  
**Host Environment**: macOS Apple Silicon (ARM64), Python 3.12, Antigravity IDE  
**Updated**: Reflecting Refinements for Execution Mode Honesty, Timestamp-Awareness, and Scope Control.

---

## 1. Core Principles & Refinements

1. **Explicit Mode Distinction**:
   - `REAL_HADOOP`: Active only when verified against a live cluster.
   - `LOCAL_STREAMING`: Explicitly labeled as Unix pipe emulation (`cat | mapper | sort | reducer`). Never claimed to be Hadoop execution.
2. **Timestamp-Aware Calculations**:
   - Reducer buffers by consignment key and sorts by timestamp.
   - Deduplicates timestamps and tracks gaps exceeding `MAX_GAP_MINUTES = 15`.
   - Never infers continuous breach duration across unmonitored gaps.
3. **Transparent Scientific Models**:
   - Mean Kinetic Temperature (MKT) and Risk Index are documented as operational thermal compliance indicators, with explicit disclaimers that they do not predict microbial food spoilage.
4. **Scope Discipline for 2 Days**:
   - Prioritize synthetic dataset generator, sample CSV, mapper/reducer, local streaming runner, and Pandas parity tests.
   - Defer advanced map layers and heavy recording until the core pipeline and Streamlit dashboard are solid.
5. **Offline Ready**:
   - Pre-generate a rich sample dataset in `data/sample/` so the system runs smoothly without network dependencies.

---

## 2. 48-Hour Sprint Breakdown

```
+--------------------------------------------------------------------------------+
| SPRINT 1 (Hours 0 - 6): FOUNDATIONS & SCHEMAS (COMPLETED)                      |
|  [x] Environment diagnostic script with live system probing (scripts/check_env.sh)|
|  [x] Architecture specification with stable schemas (architecture.md)         |
|  [x] Scaffolding (.gitignore, requirements.txt, folder layout)                 |
+--------------------------------------------------------------------------------+
| SPRINT 2 (Hours 6 - 12): SYNTHETIC DATA & STREAMING MAPREDUCE CORE (IN PROGRESS)|
|  [ ] IoT Cold-Chain Data Generator (src/data_generator.py)                    |
|      - Supports multi-product profiles, routes, ambient heatwaves, door events|
|      - Injects edge cases: gaps, duplicate timestamps, irregular frequencies  |
|  [ ] Pre-generated sample CSV (data/sample/cold_chain_sample.csv)              |
|  [ ] Hadoop Streaming Mapper (hadoop/mapper.py)                               |
|  [ ] Timestamp-Aware Hadoop Streaming Reducer (hadoop/reducer.py)              |
|  [ ] Local Streaming Unix Runner (hadoop/run_local_streaming.sh)                |
|  [ ] Hadoop Manager with dynamic environment probing (src/hadoop_manager.py)   |
|  [ ] Comprehensive parity test suite vs Pandas reference (tests/)              |
+--------------------------------------------------------------------------------+
| SPRINT 3 (Hours 12 - 18): ANALYTICS ENGINE & STREAMLIT DASHBOARD               |
|  [ ] Analytics library (src/analytics.py): MKT, CDHE, Risk Index              |
|  [ ] Streamlit multi-view layout (app/main.py):                               |
|      - Persistent execution mode badge (REAL_HADOOP vs LOCAL_STREAMING)       |
|      - Executive KPI Cards (compliance rate, total deliveries, breaches)       |
|      - Route & Warehouse Risk Summary                                         |
|      - Excursion Deep-Dive (Container vs Target thresholds)                   |
+--------------------------------------------------------------------------------+
| SPRINT 4 (Hours 18 - 24): DEMO PACKAGING & EXPO PREPARATION                   |
|  [ ] Verification of 100% offline startup from data/sample                     |
|  [ ] Expo presentation cheat-sheet & talking points                            |
|  [ ] Final test verification & documentation sign-off                          |
+--------------------------------------------------------------------------------+
```

---

## 3. Immediate Action Items (Step 1 & Step 2)

- [ ] **Step 1**: Implement `src/data_generator.py` and output `data/sample/cold_chain_sample.csv` (1,000+ realistic records across 10+ deliveries, containing normal conditions, cooling breaches, sensor disconnects/gaps, and duplicate timestamps).
- [ ] **Step 2**: Implement `hadoop/mapper.py`, `hadoop/reducer.py`, `hadoop/run_local_streaming.sh`, `src/hadoop_manager.py`, and `tests/test_pipeline_parity.py`. Run tests and report exact results.
