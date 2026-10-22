#!/usr/bin/env python3
"""
FreshTrack BD — Quality & Risk Analytics Engine
Provides scientific and operational cold-chain metrics:
1. Mean Kinetic Temperature (MKT) via Arrhenius formulation
2. Cumulative Degree-Hours Excursions (CDHE)
3. Composite Cold-Chain Risk Score (0 - 100)
4. Route & Warehouse Risk Aggregations

DISCLAIMER:
All metrics computed herein are operational thermal compliance indicators
derived from time-temperature exposure history. They do NOT predict microbiological
proliferation, bacterial colony counts, or actual food spoilage, which require
direct chemical, biological, and packaging assays.
"""

import datetime
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

# Physical Constants & Operating Rules
UNIVERSAL_GAS_CONSTANT_R = 8.314472  # J / (mol * K)
DEFAULT_ACTIVATION_ENERGY = 83144.0  # J / mol (standard USP <1079> recommendation for food/pharma)
KELVIN_OFFSET = 273.15
MAX_GAP_MINUTES = 15.0  # Threshold beyond which unobserved outages do NOT infer breach duration


class EvidenceQuality(str, Enum):
    """Categorical states for telemetry evidence quality and temporal coverage."""
    GOOD = "Good"
    LIMITED = "Limited"
    POOR = "Poor"
    UNKNOWN = "Unknown"


SCIENTIFIC_DISCLAIMER = (
    "Operational Thermal Compliance Indicator. FreshTrack BD evaluates physical temperature "
    "excursions against defined setpoint boundaries. These values reflect cold-chain compliance "
    "and thermal exposure; they do not represent biological food safety assays or spoilage predictions."
)


def calculate_mkt(
    temperatures_celsius: Union[List[float], np.ndarray, pd.Series],
    activation_energy: float = DEFAULT_ACTIVATION_ENERGY,
) -> Optional[float]:
    """
    Computes the Mean Kinetic Temperature (MKT) in degrees Celsius using the Arrhenius equation.
    
    Formula:
        Tk = (dH / R) / -ln( (1/n) * sum( exp(-dH / (R * Ti)) ) )
    
    Parameters:
        temperatures_celsius: List or Series of temperature readings in °C.
        activation_energy: Activation energy dH in J/mol (default 83.144 kJ/mol).
        
    Returns:
        Mean Kinetic Temperature in °C, or None if temperatures list is empty.
    """
    if len(temperatures_celsius) == 0:
        return None

    # Filter out NaNs
    temps = np.array(temperatures_celsius, dtype=float)
    temps = temps[~np.isnan(temps)]
    n = len(temps)
    if n == 0:
        return None

    # Convert to Kelvin
    temps_k = temps + KELVIN_OFFSET

    # Prevent negative or absolute zero Kelvin
    if np.any(temps_k <= 0):
        raise ValueError("Temperature readings below absolute zero (0 K) encountered.")

    dh_over_r = activation_energy / UNIVERSAL_GAS_CONSTANT_R
    # Vectorized exponentiation
    exp_terms = np.exp(-dh_over_r / temps_k)
    mean_exp = np.mean(exp_terms)

    if mean_exp <= 0:
        return None

    # Calculate MKT in Kelvin, then convert back to Celsius
    mkt_k = dh_over_r / (-np.log(mean_exp))
    return round(float(mkt_k - KELVIN_OFFSET), 2)


def calculate_risk_score(
    breach_duration_min: float,
    total_duration_min: float,
    degree_hours: float,
    door_open_count: int,
    total_readings: int,
    sampling_integrity_pct: float,
) -> Dict[str, Union[float, str]]:
    """
    Calculates an illustrative composite Cold-Chain Risk Score between 0 and 100.
    
    Weights:
        - 40% Breach Duration Ratio (time spent outside safe bounds)
        - 35% Thermal Excursion Magnitude (degree-hours)
        - 15% Loading / Door Exposure Frequency
        - 10% Telemetry Gap Penalty (lack of continuous visibility)
        
    Returns:
        Dict containing:
            - 'risk_score': Float between 0.0 and 100.0
            - 'risk_category': 'LOW', 'MODERATE', 'HIGH', or 'CRITICAL'
            - 'color': Hex color code for dashboard rendering
    """
    # 1. Breach Duration Ratio (0 - 40 pts)
    effective_total = max(1.0, total_duration_min)
    breach_ratio = min(1.0, breach_duration_min / effective_total)
    duration_pts = breach_ratio * 40.0

    # 2. Degree Hours Magnitude (0 - 35 pts)
    # Cap at ~4.0 degree-hours for full 35 pts
    degree_hours_pts = min(35.0, (degree_hours / 4.0) * 35.0)

    # 3. Door Exposure (0 - 15 pts)
    door_ratio = min(1.0, door_open_count / max(1, total_readings))
    door_pts = door_ratio * 15.0

    # 4. Telemetry Gap Penalty (0 - 10 pts)
    gap_penalty = max(0.0, (100.0 - sampling_integrity_pct) * 0.10)

    total_score = duration_pts + degree_hours_pts + door_pts + gap_penalty
    total_score = round(max(0.0, min(100.0, total_score)), 1)

    if total_score <= 20.0:
        category = "LOW"
        color = "#4ADE80"  # Industrial Green
    elif total_score <= 50.0:
        category = "MODERATE"
        color = "#FBBF24"  # Warning Amber
    elif total_score <= 75.0:
        category = "HIGH"
        color = "#FB923C"  # High Risk Orange
    else:
        category = "CRITICAL"
        color = "#F87171"  # Critical Red

    return {
        "risk_score": total_score,
        "risk_category": category,
        "color": color,
    }


def parse_telemetry_timestamp(val: Any) -> Optional[datetime.datetime]:
    """Parses ISO timestamp strings or datetime objects into a Python datetime object."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    if isinstance(val, pd.Timestamp):
        return val.to_pydatetime()
    if isinstance(val, datetime.datetime):
        return val
    if isinstance(val, str):
        val_clean = val.strip().rstrip("Z")
        if not val_clean:
            return None
        try:
            if "." in val_clean:
                return datetime.datetime.fromisoformat(val_clean)
            return datetime.datetime.strptime(val_clean, "%Y-%m-%dT%H:%M:%S")
        except Exception:
            try:
                dt = pd.to_datetime(val)
                if pd.isna(dt):
                    return None
                return dt.to_pydatetime()
            except Exception:
                return None
    return None


def assess_telemetry_quality(
    timestamps: Union[List[Any], pd.Series, np.ndarray],
    expected_interval_min: Optional[float] = None,
    observation_window_min: Optional[float] = None,
    max_gap_minutes: float = MAX_GAP_MINUTES,
) -> Dict[str, Any]:
    """
    Evaluates telemetry evidence quality and temporal coverage.
    
    IMPORTANT RULES:
    1. Coverage is calculated ONLY when expected_interval_min and observation_window_min
       are known (> 0). If either is unknown, coverage is None and evidence_quality is UNKNOWN.
    2. Duplicate timestamps are identified and not counted as unique observations.
    3. Invalid/unparseable timestamps are rejected and counted.
    4. Intervals > max_gap_minutes (default 15.0m) are treated as unobserved dropouts.
       Time is NOT accumulated as monitored duration across unobserved dropouts.
    """
    total_records = len(timestamps) if timestamps is not None else 0
    valid_timestamps: List[datetime.datetime] = []
    invalid_timestamp_count = 0
    duplicate_count = 0
    seen_timestamps = set()

    if timestamps is not None:
        for item in timestamps:
            dt = parse_telemetry_timestamp(item)
            if dt is None:
                invalid_timestamp_count += 1
                continue
            if dt in seen_timestamps:
                duplicate_count += 1
                continue
            seen_timestamps.add(dt)
            valid_timestamps.append(dt)

    valid_timestamps.sort()
    valid_readings = len(valid_timestamps)

    gap_count = 0
    unobserved_gap_duration_min = 0.0
    monitored_duration_min = 0.0

    if valid_readings >= 2:
        for i in range(1, valid_readings):
            delta_min = (valid_timestamps[i] - valid_timestamps[i - 1]).total_seconds() / 60.0
            if delta_min <= max_gap_minutes:
                monitored_duration_min += delta_min
            else:
                gap_count += 1
                unobserved_gap_duration_min += delta_min

    # Check whether expected interval and observation window are known
    has_known_baseline = (
        expected_interval_min is not None
        and expected_interval_min > 0
        and observation_window_min is not None
        and observation_window_min > 0
    )

    if not has_known_baseline:
        return {
            "evidence_quality": EvidenceQuality.UNKNOWN.value,
            "telemetry_coverage_pct": None,
            "monitored_duration_min": round(monitored_duration_min, 1),
            "unobserved_gap_duration_min": round(unobserved_gap_duration_min, 1),
            "gap_count": gap_count,
            "total_records": total_records,
            "valid_readings": valid_readings,
            "duplicate_count": duplicate_count,
            "invalid_timestamp_count": invalid_timestamp_count,
            "observation_window_min": observation_window_min,
            "expected_interval_min": expected_interval_min,
            "expected_readings": None,
            "quality_summary": "Expected sampling interval or observation window unknown; coverage cannot be mathematically established.",
        }

    # When expected interval and observation window are known:
    expected_readings = max(1, int(round(observation_window_min / expected_interval_min)) + 1)
    
    # Calculate temporal coverage: ratio of actively monitored duration to observation window
    coverage_pct = round(min(100.0, max(0.0, (monitored_duration_min / observation_window_min) * 100.0)), 1)

    # Classify Evidence Quality state:
    # Good: >= 90% coverage and no unobserved gaps (gap_count == 0 or unobserved_gap_duration_min == 0)
    # Limited: 60% <= coverage < 90% OR (coverage >= 90% but with isolated gaps)
    # Poor: coverage < 60% OR significant unobserved outage
    if coverage_pct >= 90.0 and gap_count == 0:
        quality_state = EvidenceQuality.GOOD.value
        quality_summary = f"Continuous high-density telemetry ({coverage_pct}% coverage, 0 gaps) verifies monitoring throughout the {observation_window_min:.0f} min window."
    elif coverage_pct >= 60.0 and unobserved_gap_duration_min <= (0.25 * observation_window_min):
        quality_state = EvidenceQuality.LIMITED.value
        quality_summary = f"Partial telemetry coverage ({coverage_pct}%). {gap_count} unobserved outage(s) totaling {unobserved_gap_duration_min:.1f} min detected."
    else:
        quality_state = EvidenceQuality.POOR.value
        quality_summary = f"Poor telemetry coverage ({coverage_pct}%). Prolonged unobserved gap(s) totaling {unobserved_gap_duration_min:.1f} min leave substantial transit unmonitored."

    return {
        "evidence_quality": quality_state,
        "telemetry_coverage_pct": coverage_pct,
        "monitored_duration_min": round(monitored_duration_min, 1),
        "unobserved_gap_duration_min": round(unobserved_gap_duration_min, 1),
        "gap_count": gap_count,
        "total_records": total_records,
        "valid_readings": valid_readings,
        "duplicate_count": duplicate_count,
        "invalid_timestamp_count": invalid_timestamp_count,
        "observation_window_min": round(observation_window_min, 1),
        "expected_interval_min": round(expected_interval_min, 1),
        "expected_readings": expected_readings,
        "quality_summary": quality_summary,
    }


def generate_gap_aware_assessment(
    observed_risk_info: Dict[str, Any],
    telemetry_quality_info: Dict[str, Any],
    observed_breach_duration_min: float = 0.0,
    degree_hours_excursion: float = 0.0,
) -> Dict[str, Any]:
    """
    Synthesizes observed temperature risk with telemetry evidence quality.
    
    CRITICAL SAFETY RULES:
    1. A consignment with low observed risk but poor/limited evidence must NOT be presented
       as low-risk without qualification.
    2. Never make claims that a consignment is "safe" or "spoiled".
    3. Clearly separate observed risk from evidence quality.
    """
    obs_cat = observed_risk_info.get("risk_category", "LOW").upper()
    obs_score = float(observed_risk_info.get("risk_score", 0.0))
    ev_quality = telemetry_quality_info.get("evidence_quality", EvidenceQuality.UNKNOWN.value)
    coverage = telemetry_quality_info.get("telemetry_coverage_pct")
    gap_count = int(telemetry_quality_info.get("gap_count", 0))
    unobserved_gap_min = float(telemetry_quality_info.get("unobserved_gap_duration_min", 0.0))
    window_min = telemetry_quality_info.get("observation_window_min")

    # Determine Qualified Risk Label
    if obs_cat == "LOW":
        if ev_quality == EvidenceQuality.GOOD.value:
            qualified_label = "Compliant (High Telemetry Confidence)"
        elif ev_quality == EvidenceQuality.LIMITED.value:
            qualified_label = "Low Observed Excursion (Qualified: Limited Telemetry)"
        elif ev_quality == EvidenceQuality.POOR.value:
            qualified_label = "Low Observed Excursion (Unverified — Poor Telemetry Coverage)"
        else:
            qualified_label = "Low Observed Excursion (Unverified — Unknown Sampling Rate)"
    elif obs_cat == "MODERATE":
        if ev_quality == EvidenceQuality.GOOD.value:
            qualified_label = "Moderate Observed Risk (Verified Telemetry)"
        elif ev_quality == EvidenceQuality.LIMITED.value:
            qualified_label = "Moderate Observed Risk (Limited Coverage)"
        elif ev_quality == EvidenceQuality.POOR.value:
            qualified_label = "Moderate Observed Risk (Compounded by Poor Coverage)"
        else:
            qualified_label = "Moderate Observed Risk (Unknown Sampling Rate)"
    else:  # HIGH or CRITICAL
        severity = obs_cat.title()
        if ev_quality == EvidenceQuality.GOOD.value:
            qualified_label = f"{severity} Thermal Exposure (Verified Telemetry)"
        elif ev_quality == EvidenceQuality.LIMITED.value:
            qualified_label = f"{severity} Thermal Exposure (Limited Telemetry)"
        elif ev_quality == EvidenceQuality.POOR.value:
            qualified_label = f"{severity} Thermal Exposure (Compounded by Poor Coverage)"
        else:
            qualified_label = f"{severity} Thermal Exposure (Unknown Sampling Rate)"

    # Construct Explanation based on actual data
    exp_parts = []
    if obs_cat == "LOW" and observed_breach_duration_min == 0.0:
        exp_parts.append(f"Zero temperature breaches ({degree_hours_excursion:.2f} °C·h) were recorded during actively monitored intervals.")
    else:
        exp_parts.append(
            f"Recorded {observed_breach_duration_min:.1f} minutes in active temperature excursion "
            f"with {degree_hours_excursion:.3f} °C·h degree-hours during monitored intervals."
        )

    if coverage is not None and window_min is not None:
        if gap_count > 0:
            exp_parts.append(
                f"Telemetry coverage is {coverage}% across the {window_min:.0f} minute window, "
                f"with {gap_count} unobserved outage(s) exceeding 15 minutes totaling {unobserved_gap_min:.1f} minutes of missing telemetry."
            )
            exp_parts.append(
                f"Conditions during the {unobserved_gap_min:.1f} minutes of missing data cannot be confirmed from sensor telemetry; "
                "continuous compliance or excursion must not be inferred across unobserved blackouts."
            )
        else:
            exp_parts.append(f"Continuous telemetry coverage was verified at {coverage}% with 0 unobserved sensor blackouts.")
    else:
        exp_parts.append("Telemetry sampling frequency or observation window was not specified; mathematical coverage percentage cannot be established.")

    if obs_cat == "LOW" and ev_quality in [EvidenceQuality.POOR.value, EvidenceQuality.LIMITED.value]:
        exp_parts.append(
            "CRITICAL AUDIT NOTE: Although received telemetry shows low breach duration, "
            f"the {ev_quality.lower()} telemetry coverage prevents confirming unbroken cold-chain compliance. "
            "This consignment must not be treated as compliant without physical verification."
        )

    if obs_cat in ["HIGH", "CRITICAL"] and ev_quality in [EvidenceQuality.POOR.value, EvidenceQuality.LIMITED.value]:
        exp_parts.append(
            f"CRITICAL AUDIT NOTE: Significant thermal excursion is confirmed in monitored intervals, "
            f"and an additional {unobserved_gap_min:.1f} minutes of missing data represents unassessed operational risk."
        )

    explanation = " ".join(exp_parts)

    # Construct Actionable Recommendation based on real data
    if ev_quality == EvidenceQuality.POOR.value:
        if obs_cat in ["HIGH", "CRITICAL"]:
            rec_action = (
                f"Quarantine consignment immediately. Sustained thermal breach ({observed_breach_duration_min:.1f} min) "
                f"is compounded by {unobserved_gap_min:.1f} min of missing telemetry. Extract physical data logger memory "
                "and conduct mandatory lot quality evaluation."
            )
        else:
            rec_action = (
                f"Quarantine consignment for physical audit. Do not release inventory based solely on low observed readings; "
                f"extract internal hardware data logger to verify conditions during the {unobserved_gap_min:.1f} min unobserved outage. "
                "Inspect telematics gateway."
            )
    elif ev_quality == EvidenceQuality.LIMITED.value:
        if obs_cat in ["HIGH", "CRITICAL"]:
            rec_action = (
                f"Quarantine consignment. Confirmed thermal excursion ({observed_breach_duration_min:.1f} min, {degree_hours_excursion:.2f} °C·h). "
                "Inspect product lot and cross-reference vehicle refrigeration event logs."
            )
        else:
            rec_action = (
                f"Secondary receiving inspection required. Inspect auxiliary temperature indicator strip or download internal logger "
                f"to verify thermal integrity across the {unobserved_gap_min:.1f} min unobserved gap prior to inventory disposition."
            )
    elif ev_quality == EvidenceQuality.GOOD.value:
        if obs_cat in ["HIGH", "CRITICAL"]:
            rec_action = (
                f"Quarantine consignment. Continuous high-confidence telemetry confirms severe thermal excursion "
                f"({observed_breach_duration_min:.1f} min, {degree_hours_excursion:.2f} °C·h). Notify logistics provider of cold-chain failure."
            )
        elif obs_cat == "MODERATE":
            rec_action = (
                f"Standard receiving inspection with thermal check. Minor transient excursions ({observed_breach_duration_min:.1f} min) "
                "logged; verify receiving core temperature."
            )
        else:
            rec_action = (
                "Clear for standard receiving protocol. High-density continuous telemetry confirms temperature setpoint adherence across transit."
            )
    else:  # UNKNOWN
        if obs_cat in ["HIGH", "CRITICAL"]:
            rec_action = (
                f"Quarantine consignment due to high observed thermal breach ({observed_breach_duration_min:.1f} min). "
                "Verify logger configuration and conduct physical QA assay."
            )
        else:
            rec_action = (
                "Cross-reference physical temperature datalogger and establish configured sampling interval in manifest before final disposition."
            )

    return {
        "observed_risk_score": obs_score,
        "observed_risk_category": obs_cat,
        "evidence_quality": ev_quality,
        "telemetry_coverage_pct": coverage,
        "gap_count": gap_count,
        "unobserved_gap_duration_min": unobserved_gap_min,
        "qualified_risk_label": qualified_label,
        "explanation": explanation,
        "recommended_action": rec_action,
    }


def calculate_gap_aware_risk(
    timestamps: Union[List[Any], pd.Series, np.ndarray],
    observed_breach_duration_min: float,
    degree_hours_excursion: float,
    door_open_count: int,
    total_readings: int,
    sampling_integrity_pct: float,
    expected_interval_min: Optional[float] = None,
    observation_window_min: Optional[float] = None,
    total_duration_min: Optional[float] = None,
    max_gap_minutes: float = MAX_GAP_MINUTES,
) -> Dict[str, Any]:
    """
    Convenience function that calculates both the observed risk score and the telemetry
    evidence quality, returning an integrated gap-aware risk assessment.
    """
    eff_window = observation_window_min if (observation_window_min and observation_window_min > 0) else total_duration_min
    if eff_window is None or eff_window <= 0:
        eff_window = max(30.0, float(total_readings) * 5.0)

    obs_risk = calculate_risk_score(
        breach_duration_min=observed_breach_duration_min,
        total_duration_min=eff_window,
        degree_hours=degree_hours_excursion,
        door_open_count=door_open_count,
        total_readings=total_readings,
        sampling_integrity_pct=sampling_integrity_pct,
    )

    quality_info = assess_telemetry_quality(
        timestamps=timestamps,
        expected_interval_min=expected_interval_min,
        observation_window_min=observation_window_min,
        max_gap_minutes=max_gap_minutes,
    )

    assessment = generate_gap_aware_assessment(
        observed_risk_info=obs_risk,
        telemetry_quality_info=quality_info,
        observed_breach_duration_min=observed_breach_duration_min,
        degree_hours_excursion=degree_hours_excursion,
    )

    result = {**obs_risk, **quality_info, **assessment}
    return result


def enrich_summary_dataframe(
    summary_df: pd.DataFrame,
    raw_df: Optional[pd.DataFrame] = None,
    expected_interval_min: Optional[float] = None,
) -> pd.DataFrame:
    """
    Enriches the MapReduce output summary DataFrame with risk scores,
    duration estimates, risk classifications, optional MKT, and Gap-Aware
    evidence quality metrics if raw data is provided.
    """
    df = summary_df.copy()

    # Pre-calculate MKT and timestamps per delivery if raw telemetry is passed
    mkt_map = {}
    timestamps_map = {}
    if raw_df is not None and not raw_df.empty:
        for delivery_id, group in raw_df.groupby("delivery_id"):
            mkt_val = calculate_mkt(group["container_temp"].values)
            mkt_map[delivery_id] = mkt_val
            timestamps_map[delivery_id] = group["timestamp"].tolist()

    risk_scores = []
    risk_categories = []
    risk_colors = []
    mkt_list = []
    evidence_qualities = []
    coverage_pcts = []
    qualified_labels = []
    gap_explanations = []
    recommended_actions = []

    for _, row in df.iterrows():
        deliv_id = row["delivery_id"]
        # Estimate total trip duration from valid readings (nominal 5m interval)
        total_trip_min = max(30.0, float(row["valid_readings"]) * 5.0)

        risk_info = calculate_risk_score(
            breach_duration_min=float(row["observed_breach_duration_min"]),
            total_duration_min=total_trip_min,
            degree_hours=float(row["degree_hours_excursion"]),
            door_open_count=int(row["door_open_count"]),
            total_readings=int(row["total_readings"]),
            sampling_integrity_pct=float(row["sampling_integrity_pct"]),
        )

        deliv_timestamps = timestamps_map.get(deliv_id, [])
        window_min = None
        if deliv_timestamps and expected_interval_min is not None and expected_interval_min > 0:
            first_dt = parse_telemetry_timestamp(deliv_timestamps[0])
            last_dt = parse_telemetry_timestamp(deliv_timestamps[-1])
            if first_dt and last_dt:
                window_min = max((last_dt - first_dt).total_seconds() / 60.0, total_trip_min)

        quality_info = assess_telemetry_quality(
            timestamps=deliv_timestamps,
            expected_interval_min=expected_interval_min,
            observation_window_min=window_min,
            max_gap_minutes=MAX_GAP_MINUTES,
        )

        assessment = generate_gap_aware_assessment(
            observed_risk_info=risk_info,
            telemetry_quality_info=quality_info,
            observed_breach_duration_min=float(row["observed_breach_duration_min"]),
            degree_hours_excursion=float(row["degree_hours_excursion"]),
        )

        risk_scores.append(risk_info["risk_score"])
        risk_categories.append(risk_info["risk_category"])
        risk_colors.append(risk_info["color"])
        mkt_list.append(mkt_map.get(deliv_id, None))
        evidence_qualities.append(assessment["evidence_quality"])
        coverage_pcts.append(assessment["telemetry_coverage_pct"])
        qualified_labels.append(assessment["qualified_risk_label"])
        gap_explanations.append(assessment["explanation"])
        recommended_actions.append(assessment["recommended_action"])

    df["risk_score"] = risk_scores
    df["risk_category"] = risk_categories
    df["risk_color"] = risk_colors
    if mkt_map:
        df["mean_kinetic_temp"] = mkt_list

    df["evidence_quality"] = evidence_qualities
    df["telemetry_coverage_pct"] = coverage_pcts
    df["qualified_risk_label"] = qualified_labels
    df["gap_explanation"] = gap_explanations
    df["recommended_action"] = recommended_actions

    return df


def aggregate_by_route(summary_df: pd.DataFrame) -> pd.DataFrame:
    """Rolls up delivery-level metrics to Route level to identify fragile transport corridors."""
    route_stats = summary_df.groupby("route_id").agg(
        total_deliveries=("delivery_id", "count"),
        breached_deliveries=("breach_reading_count", lambda x: (x > 0).sum()),
        avg_risk_score=("risk_score", "mean"),
        max_risk_score=("risk_score", "max"),
        total_degree_hours=("degree_hours_excursion", "sum"),
        avg_sampling_integrity=("sampling_integrity_pct", "mean"),
        total_door_open_events=("door_open_count", "sum"),
    ).reset_index()

    route_stats["compliance_rate_pct"] = round(
        ((route_stats["total_deliveries"] - route_stats["breached_deliveries"])
         / route_stats["total_deliveries"]) * 100.0, 1
    )
    route_stats["avg_risk_score"] = route_stats["avg_risk_score"].round(1)
    route_stats["total_degree_hours"] = route_stats["total_degree_hours"].round(2)
    route_stats["avg_sampling_integrity"] = route_stats["avg_sampling_integrity"].round(1)

    return route_stats.sort_values("avg_risk_score", ascending=False)


def aggregate_by_warehouse(summary_df: pd.DataFrame) -> pd.DataFrame:
    """Rolls up delivery-level metrics to Warehouse facility level."""
    wh_stats = summary_df.groupby("warehouse_id").agg(
        total_deliveries=("delivery_id", "count"),
        breached_deliveries=("breach_reading_count", lambda x: (x > 0).sum()),
        avg_risk_score=("risk_score", "mean"),
        total_degree_hours=("degree_hours_excursion", "sum"),
        avg_sampling_integrity=("sampling_integrity_pct", "mean"),
    ).reset_index()

    wh_stats["compliance_rate_pct"] = round(
        ((wh_stats["total_deliveries"] - wh_stats["breached_deliveries"])
         / wh_stats["total_deliveries"]) * 100.0, 1
    )
    wh_stats["avg_risk_score"] = wh_stats["avg_risk_score"].round(1)
    wh_stats["total_degree_hours"] = wh_stats["total_degree_hours"].round(2)

    return wh_stats.sort_values("avg_risk_score", ascending=False)


def derive_operational_alerts(summary_df: pd.DataFrame, raw_df: Optional[pd.DataFrame] = None) -> List[Dict[str, Any]]:
    """
    Computes data-driven operational findings derived from actual processed metrics.
    Explains the evidence and distinguishes confirmed observations from inferred risk.
    """
    alerts = []

    if summary_df.empty:
        return alerts

    # 1. High-risk route corridor alert
    route_stats = aggregate_by_route(summary_df)
    if not route_stats.empty and route_stats.iloc[0]["breached_deliveries"] > 0:
        top_route = route_stats.iloc[0]
        alerts.append({
            "severity": "CRITICAL" if top_route["avg_risk_score"] > 60 else "WARNING",
            "title": f"Corridor Vulnerability: {top_route['route_id']}",
            "evidence": (
                f"Observed {top_route['breached_deliveries']} out of {top_route['total_deliveries']} shipments "
                f"({top_route['compliance_rate_pct']}% compliance rate) with {top_route['total_degree_hours']} °C·h "
                f"cumulative degree-hours excursion. Average risk score: {top_route['avg_risk_score']}."
            ),
            "recommendation": "Inspect vehicle refrigeration units and loading dock thermal seals assigned to this corridor.",
        })

    # 2. Facility / Warehouse recurring breach alert
    wh_stats = aggregate_by_warehouse(summary_df)
    if not wh_stats.empty and wh_stats.iloc[0]["breached_deliveries"] > 0:
        top_wh = wh_stats.iloc[0]
        alerts.append({
            "severity": "WARNING",
            "title": f"Facility Loading Hazard: {top_wh['warehouse_id']}",
            "evidence": (
                f"Facility logged {top_wh['breached_deliveries']} thermal breach consignments "
                f"with {top_wh['total_degree_hours']} °C·h total excursion exposure."
            ),
            "recommendation": "Review staging duration and pre-cooling procedures prior to vehicle dispatch.",
        })

    # 3. Severe single-consignment excursion alert
    high_consignments = summary_df.sort_values("degree_hours_excursion", ascending=False)
    if not high_consignments.empty and high_consignments.iloc[0]["degree_hours_excursion"] > 5.0:
        worst = high_consignments.iloc[0]
        alerts.append({
            "severity": "CRITICAL",
            "title": f"Extended Excursion: Consignment {worst['delivery_id']} ({worst['product_category']})",
            "evidence": (
                f"Sustained {worst['observed_breach_duration_min']} minutes in active thermal excursion with "
                f"{worst['degree_hours_excursion']} °C·h degree-hours. Max container temp reached {worst['max_temp']} °C "
                f"on route {worst['route_id']}."
            ),
            "recommendation": "Isolate shipment for quality control inspection and verify cold-chain logger data.",
        })

    # 4. Telemetry Gap / Data Quality alert
    gap_consignments = summary_df[summary_df["gap_count"] > 0]
    if not gap_consignments.empty:
        total_gaps = int(gap_consignments["gap_count"].sum())
        lowest_integrity = gap_consignments["sampling_integrity_pct"].min()
        alerts.append({
            "severity": "INFO",
            "title": f"Telemetry Dropouts: {len(gap_consignments)} Shipments Impacted",
            "evidence": (
                f"{total_gaps} unobserved sensor gaps (> 15 minutes) detected across {len(gap_consignments)} consignments. "
                f"Lowest sampling integrity: {lowest_integrity}%. Note: Per rule MAX_GAP_MINUTES, breach durations "
                f"were NOT accumulated across unobserved intervals."
            ),
            "recommendation": "Inspect IoT gateway battery levels and cellular dead-zones along active routes.",
        })

    return alerts


def extract_excursion_episodes(delivery_raw_df: pd.DataFrame, max_gap_minutes: float = 15.0) -> List[Dict[str, Any]]:
    """
    Extracts discrete excursion episodes from raw time-series sensor data for a delivery.
    Returns episode start, end, observed duration, max temp, degree-hours, and confidence.
    """
    if delivery_raw_df.empty:
        return []

    df = delivery_raw_df.copy()
    df["dt"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("dt").reset_index(drop=True)

    t_min = float(df["target_temp_min"].iloc[0])
    t_max = float(df["target_temp_max"].iloc[0])

    episodes = []
    current_episode = None

    for i in range(len(df)):
        row = df.iloc[i]
        curr_time = row["dt"]
        temp = float(row["container_temp"])
        is_breach = (temp > t_max) or (temp < t_min)

        if i > 0:
            prev_row = df.iloc[i - 1]
            delta_min = (curr_time - prev_row["dt"]).total_seconds() / 60.0
            is_gap = delta_min > max_gap_minutes
        else:
            delta_min = 0.0
            is_gap = False

        if is_breach:
            breach_type = "Warm Excursion" if temp > t_max else "Chill Injury"
            delta_dh = (abs(temp - (t_max if temp > t_max else t_min)) * (delta_min / 60.0)) if delta_min <= max_gap_minutes else 0.0
            added_duration = delta_min if delta_min <= max_gap_minutes else 0.0

            if current_episode is None or is_gap or current_episode["type"] != breach_type:
                # Close previous if gap occurred
                if current_episode is not None:
                    episodes.append(current_episode)
                # Start new episode
                current_episode = {
                    "type": breach_type,
                    "start_time": curr_time.strftime("%H:%M:%S UTC"),
                    "end_time": curr_time.strftime("%H:%M:%S UTC"),
                    "observed_duration_min": added_duration,
                    "max_observed_temp": temp,
                    "min_observed_temp": temp,
                    "degree_hours": delta_dh,
                    "has_gaps": is_gap,
                    "reading_count": 1,
                    "confidence": "Moderate (Gap adjacent)" if is_gap else "High (Continuous)",
                }
            else:
                # Accumulate into existing episode
                current_episode["end_time"] = curr_time.strftime("%H:%M:%S UTC")
                current_episode["observed_duration_min"] += added_duration
                current_episode["max_observed_temp"] = max(current_episode["max_observed_temp"], temp)
                current_episode["min_observed_temp"] = min(current_episode["min_observed_temp"], temp)
                current_episode["degree_hours"] += delta_dh
                current_episode["reading_count"] += 1
        else:
            # Normal temp: close current episode if any
            if current_episode is not None:
                episodes.append(current_episode)
                current_episode = None

    if current_episode is not None:
        episodes.append(current_episode)

    # Round metrics for display
    for ep in episodes:
        ep["observed_duration_min"] = round(ep["observed_duration_min"], 1)
        ep["degree_hours"] = round(ep["degree_hours"], 3)
        ep["max_observed_temp"] = round(ep["max_observed_temp"], 1)
        ep["min_observed_temp"] = round(ep["min_observed_temp"], 1)

    return episodes


def aggregate_route_product_matrix(summary_df: pd.DataFrame) -> pd.DataFrame:
    """Computes cross-tabulation of average risk scores across Routes and Products."""
    if summary_df.empty:
        return pd.DataFrame()
    pivot = summary_df.pivot_table(
        index="route_id",
        columns="product_category",
        values="risk_score",
        aggfunc="mean",
        fill_value=0.0,
    ).round(1)
    return pivot


def aggregate_hourly_excursions(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Groups raw readings by hour of day (0-23) to compute diurnal excursion frequency."""
    if raw_df.empty:
        return pd.DataFrame()
    df = raw_df.copy()
    df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour
    df["is_breach"] = (df["container_temp"] > df["target_temp_max"]) | (df["container_temp"] < df["target_temp_min"])

    hourly = df.groupby("hour").agg(
        total_readings=("record_id", "count"),
        excursion_readings=("is_breach", "sum"),
        avg_container_temp=("container_temp", "mean"),
        avg_ambient_temp=("ambient_temp", "mean"),
    ).reset_index()

    hourly["excursion_rate_pct"] = round((hourly["excursion_readings"] / hourly["total_readings"]) * 100.0, 1)
    hourly["avg_container_temp"] = hourly["avg_container_temp"].round(1)
    hourly["avg_ambient_temp"] = hourly["avg_ambient_temp"].round(1)

    return hourly
