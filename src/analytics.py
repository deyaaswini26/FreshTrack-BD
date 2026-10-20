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

import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

# Physical Constants for Arrhenius MKT Formulation
UNIVERSAL_GAS_CONSTANT_R = 8.314472  # J / (mol * K)
DEFAULT_ACTIVATION_ENERGY = 83144.0  # J / mol (standard USP <1079> recommendation for food/pharma)
KELVIN_OFFSET = 273.15

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


def enrich_summary_dataframe(
    summary_df: pd.DataFrame,
    raw_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Enriches the MapReduce output summary DataFrame with risk scores,
    duration estimates, risk classifications, and optional MKT if raw data is provided.
    """
    df = summary_df.copy()

    # Pre-calculate MKT per delivery if raw telemetry is passed
    mkt_map = {}
    if raw_df is not None and not raw_df.empty:
        for delivery_id, group in raw_df.groupby("delivery_id"):
            mkt_val = calculate_mkt(group["container_temp"].values)
            mkt_map[delivery_id] = mkt_val

    risk_scores = []
    risk_categories = []
    risk_colors = []
    mkt_list = []

    for _, row in df.iterrows():
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

        risk_scores.append(risk_info["risk_score"])
        risk_categories.append(risk_info["risk_category"])
        risk_colors.append(risk_info["color"])
        mkt_list.append(mkt_map.get(row["delivery_id"], None))

    df["risk_score"] = risk_scores
    df["risk_category"] = risk_categories
    df["risk_color"] = risk_colors
    if mkt_map:
        df["mean_kinetic_temp"] = mkt_list

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
