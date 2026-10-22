#!/usr/bin/env python3
"""
FreshTrack BD — Big Data Cold-Chain Analytics Platform
Enterprise Industrial Control Tower for Cold-Chain Telemetry & MapReduce Analytics.

Pages:
1. Overview (Cold-Chain Operations Overview)
2. Route & Facility Analytics (Route & Facility Performance)
3. Shipment Deep Dive (Shipment Investigation)
4. MapReduce Engine (Big Data Processing Engine)
5. Data Explorer (Telemetry Data Explorer)
"""

import datetime
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from app.components.styles import INDUSTRIAL_THEME_CSS
from app.components.ui_elements import (
    SVG_ICONS,
    get_industrial_plotly_layout,
    render_alert_item,
    render_disclaimer_callout,
    render_global_header,
    render_kpi_card,
    render_status_badge_html,
)
from src.analytics import (
    DEFAULT_ACTIVATION_ENERGY,
    SCIENTIFIC_DISCLAIMER,
    aggregate_by_route,
    aggregate_by_warehouse,
    aggregate_hourly_excursions,
    aggregate_route_product_matrix,
    calculate_mkt,
    derive_operational_alerts,
    enrich_summary_dataframe,
    extract_excursion_episodes,
)
from src.data_generator import PRODUCT_PROFILES, ColdChainDataGenerator
from src.hadoop_manager import (
    ExecutionMode,
    HadoopEnvironmentInspector,
    PipelineExecutionManager,
)

# Page Configuration
st.set_page_config(
    page_title="FreshTrack BD — Big Data Cold-Chain Analytics",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject Dark Industrial Theme CSS
st.markdown(INDUSTRIAL_THEME_CSS, unsafe_allow_html=True)


@st.cache_data
def get_system_env() -> Dict[str, Any]:
    """Caches environment inspection results."""
    inspector = HadoopEnvironmentInspector()
    return inspector.inspect()


def load_or_run_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Ensures raw telemetry and processed metrics are loaded and enriched."""
    raw_path = os.path.join(WORKSPACE_ROOT, "data", "sample", "cold_chain_sample.csv")
    processed_path = os.path.join(WORKSPACE_ROOT, "data", "processed", "summary_metrics.csv")

    manager = PipelineExecutionManager(workspace_root=WORKSPACE_ROOT)

    # If processed output doesn't exist, execute local streaming on sample
    if not os.path.exists(processed_path) or os.path.getsize(processed_path) == 0:
        if not os.path.exists(raw_path):
            gen = ColdChainDataGenerator(seed=42)
            df_gen = gen.generate_fleet_dataset(num_deliveries=20)
            os.makedirs(os.path.dirname(raw_path), exist_ok=True)
            df_gen.to_csv(raw_path, index=False)

        res = manager.run_pipeline(
            input_csv=raw_path,
            output_csv=processed_path,
            mode=ExecutionMode.LOCAL_STREAMING,
        )
        st.session_state["last_run_meta"] = res

    raw_df = pd.read_csv(raw_path)
    summary_df = pd.read_csv(processed_path)
    enriched_df = enrich_summary_dataframe(summary_df, raw_df=raw_df)

    return raw_df, enriched_df


def main():
    env_info = get_system_env()

    # Session State Initialization
    if "last_run_meta" not in st.session_state:
        st.session_state["last_run_meta"] = {
            "mode": env_info["recommended_mode"].value,
            "mode_label": env_info["mode_description"],
            "is_real_hadoop": env_info["recommended_mode"] == ExecutionMode.REAL_HADOOP,
            "hadoop_job_id": "job_cluster_01" if env_info["recommended_mode"] == ExecutionMode.REAL_HADOOP else "N/A (Local Pipe Emulation)",
            "duration_seconds": 0.029,
            "start_time_iso": "2026-10-20 04:08:53 UTC",
            "finish_time_iso": "2026-10-20 04:08:54 UTC",
            "input_records": 1046,
            "valid_records": 1045,
            "rejected_records": 0,
            "output_records": 20,
            "status": "SUCCESS",
        }

    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "Overview"

    if "investigate_shipment_id" not in st.session_state:
        st.session_state["investigate_shipment_id"] = None

    raw_df, summary_df = load_or_run_data()

    # ---------------------------------------------------------
    # FIXED ENTERPRISE SIDEBAR
    # ---------------------------------------------------------
    with st.sidebar:
        # Brand Header
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 2px;">
                {SVG_ICONS['snowflake']}
                <span style="font-size: 1.18rem; font-weight: 700; color: #F1F5F9; letter-spacing: -0.02em;">FreshTrack BD</span>
            </div>
            <div style="font-size: 0.68rem; font-weight: 600; color: #94A3B8; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 24px;">
                Cold-Chain Intelligence
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Primary Navigation
        nav_options = [
            "Overview",
            "Route & Facility Analytics",
            "Shipment Deep Dive",
            "MapReduce Engine",
            "Data Explorer",
        ]

        # Sync nav_page if changed via buttons
        current_idx = nav_options.index(st.session_state["nav_page"]) if st.session_state["nav_page"] in nav_options else 0
        selected_nav = st.radio(
            "SYSTEM NAVIGATION",
            options=nav_options,
            index=current_idx,
            label_visibility="visible",
        )
        if selected_nav != st.session_state["nav_page"]:
            st.session_state["nav_page"] = selected_nav

        st.markdown("<hr style='border-color: #2A394D; margin: 24px 0 16px 0;'>", unsafe_allow_html=True)

        # Sidebar Metadata Footer
        st.markdown(
            f"""
            <div style="font-size: 0.72rem; color: #64748B; line-height: 1.6;">
                <div><strong>Active Dataset:</strong> <span style="color: #94A3B8;">cold_chain_sample.csv</span></div>
                <div><strong>Data Source:</strong> <span style="color: #2DD4BF;">SYNTHETIC TELEMETRY</span></div>
                <div style="margin-top: 6px;"><strong>Execution Mode:</strong></div>
                <div style="margin-top: 2px;">{render_status_badge_html(st.session_state['last_run_meta']['mode'])}</div>
                <div style="margin-top: 10px; border-top: 1px solid #1E293B; pt: 6px; color: #475569;">
                    Build: v2.4.0-enterprise • Expo Edition
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---------------------------------------------------------
    # GLOBAL TOP HEADER
    # ---------------------------------------------------------
    render_global_header(
        page_name=st.session_state["nav_page"],
        dataset_name="cold_chain_sample.csv",
        last_run_meta=st.session_state.get("last_run_meta"),
    )

    # =========================================================
    # PAGE 1: OVERVIEW (COLD-CHAIN OPERATIONS OVERVIEW)
    # =========================================================
    if st.session_state["nav_page"] == "Overview":
        st.markdown("## Cold-Chain Operations Overview")
        st.caption("Monitor thermal compliance, identify vulnerable corridors, and investigate shipment-level risks.")

        # Compact Filter Bar
        with st.expander("Filter Criteria & Scope Controls", expanded=True):
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)

            with f_col1:
                all_cats = sorted(summary_df["product_category"].unique())
                sel_cats = st.multiselect("Product Category", options=all_cats, default=all_cats)

            with f_col2:
                all_rts = sorted(summary_df["route_id"].unique())
                sel_rts = st.multiselect("Transport Route", options=all_rts, default=all_rts)

            with f_col3:
                all_whs = sorted(summary_df["warehouse_id"].unique())
                sel_whs = st.multiselect("Warehouse Facility", options=all_whs, default=all_whs)

            with f_col4:
                status_filter = st.selectbox("Compliance Status", options=["All Shipments", "Compliant Only", "Thermal Breaches Only"], index=0)

        # Apply Filters
        f_summary = summary_df.copy()
        if sel_cats:
            f_summary = f_summary[f_summary["product_category"].isin(sel_cats)]
        if sel_rts:
            f_summary = f_summary[f_summary["route_id"].isin(sel_rts)]
        if sel_whs:
            f_summary = f_summary[f_summary["warehouse_id"].isin(sel_whs)]

        if status_filter == "Compliant Only":
            f_summary = f_summary[f_summary["breach_reading_count"] == 0]
        elif status_filter == "Thermal Breaches Only":
            f_summary = f_summary[f_summary["breach_reading_count"] > 0]

        filtered_shipment_ids = set(f_summary["delivery_id"].unique())
        f_raw = raw_df[raw_df["delivery_id"].isin(filtered_shipment_ids)].copy()

        # Aligned Five KPI Cards
        total_shipments = len(f_summary)
        total_valid_readings = int(f_summary["valid_readings"].sum()) if total_shipments > 0 else 0
        total_breach_readings = int(f_summary["breach_reading_count"].sum()) if total_shipments > 0 else 0

        # Compliance rate on reading level
        compliance_pct = round(((total_valid_readings - total_breach_readings) / max(1, total_valid_readings)) * 100.0, 1)

        # Shipments requiring attention (High or Critical risk, or > 0 breaches)
        attention_count = (f_summary["risk_category"].isin(["HIGH", "CRITICAL"]) | (f_summary["breach_reading_count"] > 0)).sum()
        total_degree_hours = round(f_summary["degree_hours_excursion"].sum(), 2)

        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            render_kpi_card(
                title="Reading Compliance",
                value=f"{compliance_pct}%",
                caption=f"{total_valid_readings - total_breach_readings:,} of {total_valid_readings:,} sensor readings compliant",
                icon_name="check_circle",
                accent_color="#4ADE80" if compliance_pct >= 75 else "#F87171",
            )
        with k2:
            render_kpi_card(
                title="Shipments Monitored",
                value=f"{total_shipments}",
                caption=f"Across {len(sel_cats)} commodity categories",
                icon_name="truck",
                accent_color="#2DD4BF",
            )
        with k3:
            render_kpi_card(
                title="Requiring Attention",
                value=f"{attention_count}",
                caption=f"{round((attention_count/max(1, total_shipments))*100, 1)}% of monitored fleet",
                icon_name="alert_triangle",
                accent_color="#F87171" if attention_count > 0 else "#4ADE80",
            )
        with k4:
            render_kpi_card(
                title="Excursion Readings",
                value=f"{total_breach_readings:,}",
                caption=f"Out-of-setpoint sensor observations",
                icon_name="thermometer",
                accent_color="#FBBF24" if total_breach_readings > 0 else "#4ADE80",
            )
        with k5:
            render_kpi_card(
                title="Cumulative Degree-Hours",
                value=f"{total_degree_hours} °C·h",
                caption=f"Time-integrated exposure (°C · hours)",
                icon_name="clock",
                accent_color="#60A5FA",
            )

        st.markdown("###")

        # Main Chart Grid: 2 Columns
        g_col1, g_col2 = st.columns([1.1, 0.9])

        with g_col1:
            st.markdown("##### Temperature Excursion Trend Over Time")
            if not f_raw.empty:
                # Group raw readings by 15-minute intervals to observe temporal excursion count
                f_raw_time = f_raw.copy()
                f_raw_time["dt"] = pd.to_datetime(f_raw_time["timestamp"])
                f_raw_time["is_excursion"] = (f_raw_time["container_temp"] > f_raw_time["target_temp_max"]) | (f_raw_time["container_temp"] < f_raw_time["target_temp_min"])

                time_trend = f_raw_time.set_index("dt").resample("30min").agg(
                    total_readings=("record_id", "count"),
                    excursion_readings=("is_excursion", "sum"),
                    avg_temp=("container_temp", "mean"),
                ).reset_index()

                fig_trend = go.Figure()
                fig_trend.add_trace(go.Bar(
                    x=time_trend["dt"],
                    y=time_trend["excursion_readings"],
                    name="Excursion Readings",
                    marker_color="#F87171",
                    opacity=0.85,
                ))
                fig_trend.add_trace(go.Scatter(
                    x=time_trend["dt"],
                    y=time_trend["total_readings"],
                    name="Total Monitored Readings",
                    mode="lines",
                    line=dict(color="#60A5FA", width=1.5, dash="dash"),
                ))
                fig_trend.update_layout(
                    **get_industrial_plotly_layout(
                        height=280,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    ),
                    xaxis_title="Timeline (UTC)",
                    yaxis_title="Sensor Readings Count",
                )
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("No sensor records match the current filter selection.")

        with g_col2:
            st.markdown("##### Shipment Risk Tier Distribution")
            if not f_summary.empty:
                risk_counts = f_summary["risk_category"].value_counts().reset_index()
                risk_counts.columns = ["Risk Tier", "Shipments"]
                total_s = risk_counts["Shipments"].sum()
                risk_counts["Percentage"] = ((risk_counts["Shipments"] / total_s) * 100.0).round(1)

                color_map = {
                    "LOW": "#4ADE80",
                    "MODERATE": "#FBBF24",
                    "HIGH": "#FB923C",
                    "CRITICAL": "#F87171",
                }

                fig_pie = px.pie(
                    risk_counts,
                    values="Shipments",
                    names="Risk Tier",
                    hole=0.55,
                    color="Risk Tier",
                    color_discrete_map=color_map,
                )
                fig_pie.update_layout(
                    **get_industrial_plotly_layout(
                        height=280,
                        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02),
                    ),
                )
                fig_pie.update_traces(
                    textinfo="percent+label",
                    hovertemplate="<b>%{label}</b><br>Shipments: %{value}<br>Share: %{percent}<extra></extra>",
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No shipments match filter criteria.")

        # Secondary Analytics: 2 Columns
        s_col1, s_col2 = st.columns([1, 1])

        with s_col1:
            st.markdown("##### Commodity Category Compliance (Reading Denominator)")
            if not f_raw.empty:
                cat_summary = f_raw.groupby("product_category").agg(
                    total_readings=("record_id", "count"),
                    compliant_readings=("container_temp", lambda s: ((s >= f_raw.loc[s.index, "target_temp_min"]) & (s <= f_raw.loc[s.index, "target_temp_max"])).sum()),
                ).reset_index()
                cat_summary["compliance_rate"] = ((cat_summary["compliant_readings"] / cat_summary["total_readings"]) * 100.0).round(1)
                cat_summary = cat_summary.sort_values("compliance_rate", ascending=True)

                fig_cat = px.bar(
                    cat_summary,
                    x="compliance_rate",
                    y="product_category",
                    orientation="h",
                    color="compliance_rate",
                    color_continuous_scale=[[0, "#F87171"], [0.5, "#FBBF24"], [1.0, "#4ADE80"]],
                    range_color=[0, 100],
                    labels={"compliance_rate": "Compliance Rate (%)", "product_category": "Commodity"},
                )
                fig_cat.update_layout(
                    **get_industrial_plotly_layout(height=260),
                    coloraxis_showscale=False,
                )
                fig_cat.update_traces(
                    hovertemplate="<b>%{y}</b><br>Compliance: %{x}%<extra></extra>",
                )
                st.plotly_chart(fig_cat, use_container_width=True)

        with s_col2:
            st.markdown("##### Highest-Risk Shipments Requiring Inspection")
            if not f_summary.empty:
                high_risk = f_summary.sort_values("risk_score", ascending=False).head(5).copy()
                high_risk["excursion_rate_pct"] = ((high_risk["breach_reading_count"] / high_risk["valid_readings"]) * 100.0).round(1)

                display_table = high_risk[[
                    "delivery_id", "product_category", "route_id",
                    "excursion_rate_pct", "degree_hours_excursion", "risk_category"
                ]].rename(columns={
                    "delivery_id": "Shipment ID",
                    "product_category": "Commodity",
                    "route_id": "Route",
                    "excursion_rate_pct": "Excursion %",
                    "degree_hours_excursion": "Degree-Hours",
                    "risk_category": "Risk Tier",
                })

                st.dataframe(display_table, use_container_width=True, hide_index=True)

                # Quick action dropdown to investigate
                target_del = st.selectbox(
                    "Quick Investigate Shipment in Deep Dive View:",
                    options=high_risk["delivery_id"].tolist(),
                    key="quick_select_overview",
                )
                if st.button("Open Shipment Investigation View", key="btn_investigate_overview"):
                    st.session_state["nav_page"] = "Shipment Deep Dive"
                    st.session_state["investigate_shipment_id"] = target_del
                    st.rerun()

        # Operational Alert Panel (Data-Driven Evidence)
        st.markdown("###")
        st.markdown("##### Operational Intelligence & Alert Panel")
        alerts = derive_operational_alerts(f_summary, f_raw)
        if alerts:
            for alert in alerts:
                render_alert_item(
                    severity=alert["severity"],
                    title=alert["title"],
                    evidence=alert["evidence"],
                    recommendation=alert["recommendation"],
                )
        else:
            st.success("No critical cold-chain operational hazards identified in the filtered subset.")

    # =========================================================
    # PAGE 2: ROUTE & FACILITY ANALYTICS
    # =========================================================
    elif st.session_state["nav_page"] == "Route & Facility Analytics":
        st.markdown("## Route & Facility Performance")
        st.caption("Identify recurring cold-chain vulnerabilities across transport corridors and storage facilities.")

        route_stats = aggregate_by_route(summary_df)
        wh_stats = aggregate_by_warehouse(summary_df)

        # Route Comparison Table
        st.markdown("##### Transport Corridor Vulnerability Ranking")
        # Format table with coverage and risk metrics
        route_display = route_stats.copy().rename(columns={
            "route_id": "Corridor ID",
            "total_deliveries": "Shipments",
            "breached_deliveries": "Breached Shipments",
            "compliance_rate_pct": "Compliance %",
            "avg_risk_score": "Avg Risk Score",
            "total_degree_hours": "Cumulative °C·h",
            "avg_sampling_integrity": "Sampling Quality %",
            "total_door_open_events": "Door Events",
        })
        st.dataframe(route_display, use_container_width=True, hide_index=True)

        st.markdown("###")

        # 4 Core Visualizations (2x2 Grid)
        v_col1, v_col2 = st.columns(2)

        with v_col1:
            st.markdown("##### 1. Route Excursion Rate Comparison")
            fig_r1 = px.bar(
                route_stats,
                x="avg_risk_score",
                y="route_id",
                orientation="h",
                color="avg_risk_score",
                color_continuous_scale=[[0, "#4ADE80"], [0.5, "#FBBF24"], [1.0, "#F87171"]],
                labels={"avg_risk_score": "Average Risk Score (0-100)", "route_id": "Corridor ID"},
            )
            fig_r1.update_layout(**get_industrial_plotly_layout(height=260), coloraxis_showscale=False)
            st.plotly_chart(fig_r1, use_container_width=True)

        with v_col2:
            st.markdown("##### 2. Storage Warehouse Compliance Comparison")
            fig_w1 = px.bar(
                wh_stats,
                x="warehouse_id",
                y="compliance_rate_pct",
                color="compliance_rate_pct",
                color_continuous_scale=[[0, "#F87171"], [0.7, "#FBBF24"], [1.0, "#4ADE80"]],
                range_color=[0, 100],
                labels={"compliance_rate_pct": "Compliance %", "warehouse_id": "Facility"},
            )
            fig_w1.update_layout(**get_industrial_plotly_layout(height=260), coloraxis_showscale=False)
            st.plotly_chart(fig_w1, use_container_width=True)

        v_col3, v_col4 = st.columns(2)

        with v_col3:
            st.markdown("##### 3. Route vs. Product Risk Matrix (Heatmap)")
            pivot_matrix = aggregate_route_product_matrix(summary_df)
            if not pivot_matrix.empty:
                fig_hm = px.imshow(
                    pivot_matrix,
                    color_continuous_scale=[[0, "#101A2B"], [0.25, "#151F30"], [0.5, "#FBBF24"], [1.0, "#F87171"]],
                    labels=dict(x="Product Commodity", y="Corridor ID", color="Risk Score"),
                    text_auto=True,
                )
                fig_hm.update_layout(**get_industrial_plotly_layout(height=260))
                st.plotly_chart(fig_hm, use_container_width=True)

        with v_col4:
            st.markdown("##### 4. Diurnal Time-of-Day Excursion Frequency")
            hourly_stats = aggregate_hourly_excursions(raw_df)
            if not hourly_stats.empty:
                fig_hr = px.bar(
                    hourly_stats,
                    x="hour",
                    y="excursion_readings",
                    color="avg_ambient_temp",
                    color_continuous_scale="Reds",
                    labels={"hour": "Hour of Day (UTC)", "excursion_readings": "Excursion Frequency", "avg_ambient_temp": "Ambient Temp (°C)"},
                )
                fig_hr.update_layout(**get_industrial_plotly_layout(height=260))
                st.plotly_chart(fig_hr, use_container_width=True)

        # Facility Detail Inspection Panel
        st.markdown("###")
        st.markdown("##### Specific Facility Performance Inspection")
        wh_options = sorted(wh_stats["warehouse_id"].tolist())
        selected_facility = st.selectbox("Select Storage Hub / Warehouse:", wh_options)

        f_wh_deliveries = summary_df[summary_df["warehouse_id"] == selected_facility]
        f_wh_raw = raw_df[raw_df["warehouse_id"] == selected_facility]

        wh_k1, wh_k2, wh_k3, wh_k4 = st.columns(4)
        with wh_k1:
            render_kpi_card("Shipments Processed", f"{len(f_wh_deliveries)}", f"Origin / Transit Hub", accent_color="#2DD4BF")
        with wh_k2:
            render_kpi_card("Valid Sensor Records", f"{len(f_wh_raw):,}", "Inbound & staging readings", accent_color="#60A5FA")
        with wh_k3:
            wh_excursion_rate = round((f_wh_deliveries["breach_reading_count"].sum() / max(1, f_wh_deliveries["valid_readings"].sum())) * 100.0, 1)
            render_kpi_card("Excursion Frequency", f"{wh_excursion_rate}%", "Readings out of bounds", accent_color="#F87171" if wh_excursion_rate > 20 else "#4ADE80")
        with wh_k4:
            gaps_in_wh = int(f_wh_deliveries["gap_count"].sum())
            render_kpi_card("Telemetry Gaps Detected", f"{gaps_in_wh}", f"Sensor disconnect events (>15m)", accent_color="#FBBF24" if gaps_in_wh > 0 else "#4ADE80")

    # =========================================================
    # PAGE 3: SHIPMENT DEEP DIVE (SHIPMENT INVESTIGATION)
    # =========================================================
    elif st.session_state["nav_page"] == "Shipment Deep Dive":
        st.markdown("## Shipment Investigation")
        st.caption("Trace individual temperature events and examine the evidence behind risk alerts.")

        all_deliveries = summary_df.sort_values("risk_score", ascending=False)
        shipment_labels = {
            row["delivery_id"]: f"{row['delivery_id']} — {row['product_category']} [{row['risk_category']}] (Risk: {row['risk_score']})"
            for _, row in all_deliveries.iterrows()
        }

        # Select shipment
        default_idx = 0
        if st.session_state.get("investigate_shipment_id") in shipment_labels:
            default_idx = list(shipment_labels.keys()).index(st.session_state["investigate_shipment_id"])

        sel_shipment = st.selectbox(
            "Select Consignment to Audit:",
            options=list(shipment_labels.keys()),
            format_func=lambda x: shipment_labels[x],
            index=default_idx,
        )

        ship_meta = summary_df[summary_df["delivery_id"] == sel_shipment].iloc[0]
        ship_raw = raw_df[raw_df["delivery_id"] == sel_shipment].sort_values("timestamp").copy()

        # Shipment Summary Banner
        st.markdown("###")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Commodity", str(ship_meta["product_category"]), f"Route: {ship_meta['route_id']}")
        with c2:
            t_min = ship_raw["target_temp_min"].iloc[0]
            t_max = ship_raw["target_temp_max"].iloc[0]
            st.metric("Safe Band", f"{t_min} – {t_max} °C", f"Facility: {ship_meta['warehouse_id']}")
        with c3:
            excursion_rate = round((ship_meta["breach_reading_count"] / ship_meta["valid_readings"]) * 100.0, 1)
            st.metric("Observed Breach Duration", f"{ship_meta['observed_breach_duration_min']} min", f"{excursion_rate}% readings in breach")
        with c4:
            st.metric("Cumulative Degree-Hours", f"{ship_meta['degree_hours_excursion']} °C·h", f"Max: {ship_meta['max_temp']}°C / Min: {ship_meta['min_temp']}°C")
        with c5:
            st.metric("Telemetry Quality", f"{ship_meta['sampling_integrity_pct']}%", f"Gaps: {ship_meta['gap_count']} | Duplicates: {ship_meta['duplicate_count']}")

        st.markdown("###")

        # Main Temperature Chart (Visual Centrepiece)
        st.markdown("##### High-Resolution Sensor Telemetry Trace")
        st.caption("Permissible storage envelope, container probe readings, ambient stress curve, and isolated sensor gap intervals.")

        ship_raw["dt"] = pd.to_datetime(ship_raw["timestamp"])
        ship_raw_sorted = ship_raw.sort_values("dt").reset_index(drop=True)

        fig_trace = go.Figure()

        # 1. Shaded Permissible Temperature Envelope
        fig_trace.add_trace(go.Scatter(
            x=pd.concat([ship_raw_sorted["dt"], ship_raw_sorted["dt"][::-1]]),
            y=[t_max]*len(ship_raw_sorted) + [t_min]*len(ship_raw_sorted),
            fill="toself",
            fillcolor="rgba(74, 222, 128, 0.12)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="skip",
            name="Configured Safe Band",
        ))

        # Target Min / Max Boundary Lines
        fig_trace.add_trace(go.Scatter(
            x=ship_raw_sorted["dt"],
            y=[t_max]*len(ship_raw_sorted),
            mode="lines",
            line=dict(color="#4ADE80", width=1.5, dash="dash"),
            name=f"Upper Setpoint ({t_max}°C)",
        ))
        fig_trace.add_trace(go.Scatter(
            x=ship_raw_sorted["dt"],
            y=[t_min]*len(ship_raw_sorted),
            mode="lines",
            line=dict(color="#4ADE80", width=1.5, dash="dash"),
            name=f"Lower Setpoint ({t_min}°C)",
        ))

        # Ambient Temperature Curve
        fig_trace.add_trace(go.Scatter(
            x=ship_raw_sorted["dt"],
            y=ship_raw_sorted["ambient_temp"],
            mode="lines",
            line=dict(color="#60A5FA", width=1.2, dash="dot"),
            name="External Ambient Temp",
        ))

        # Disconnect line over gaps > 15m to NOT infer continuous observations
        plot_times = []
        plot_temps = []
        for i in range(len(ship_raw_sorted)):
            if i > 0:
                diff_m = (ship_raw_sorted["dt"].iloc[i] - ship_raw_sorted["dt"].iloc[i - 1]).total_seconds() / 60.0
                if diff_m > 15.0:
                    # Break the line by inserting None
                    plot_times.append(ship_raw_sorted["dt"].iloc[i - 1] + datetime.timedelta(seconds=1))
                    plot_temps.append(None)
            plot_times.append(ship_raw_sorted["dt"].iloc[i])
            plot_temps.append(ship_raw_sorted["container_temp"].iloc[i])

        # Container Temperature Curve
        fig_trace.add_trace(go.Scatter(
            x=plot_times,
            y=plot_temps,
            mode="lines",
            line=dict(color="#2DD4BF", width=2.2),
            name="Internal Container Temp",
            connectgaps=False,  # Essential: do not connect across None gaps
        ))

        # Individual Reading Markers with breach coloring
        excursion_points = ship_raw_sorted[(ship_raw_sorted["container_temp"] > t_max) | (ship_raw_sorted["container_temp"] < t_min)]
        if not excursion_points.empty:
            fig_trace.add_trace(go.Scatter(
                x=excursion_points["dt"],
                y=excursion_points["container_temp"],
                mode="markers",
                marker=dict(size=6, color="#F87171", symbol="circle"),
                name="Thermal Excursion Reading",
                hovertemplate="<b>Excursion Event</b><br>Time: %{x}<br>Temp: %{y}°C<extra></extra>",
            ))

        # Door Open Event Rug Markers
        door_events = ship_raw_sorted[ship_raw_sorted["door_open_flag"] == 1]
        if not door_events.empty:
            fig_trace.add_trace(go.Scatter(
                x=door_events["dt"],
                y=door_events["container_temp"],
                mode="markers",
                marker=dict(symbol="triangle-up", size=10, color="#FBBF24"),
                name="Door Open Reading",
                hovertemplate="<b>Door Opened</b><br>Time: %{x}<br>Temp: %{y}°C<extra></extra>",
            ))

        # Gray Shaded Outage Gaps
        for i in range(1, len(ship_raw_sorted)):
            prev_dt = ship_raw_sorted["dt"].iloc[i - 1]
            curr_dt = ship_raw_sorted["dt"].iloc[i]
            diff_m = (curr_dt - prev_dt).total_seconds() / 60.0
            if diff_m > 15.0:
                fig_trace.add_vrect(
                    x0=prev_dt,
                    x1=curr_dt,
                    fillcolor="rgba(148, 163, 184, 0.2)",
                    layer="below",
                    line_width=1,
                    line_dash="dot",
                    line_color="#94A3B8",
                    annotation_text=f"Telemetry Gap ({int(diff_m)}m)<br>Breach Not Inferred",
                    annotation_position="top left",
                    annotation_font_size=10,
                )

        fig_trace.update_layout(
            **get_industrial_plotly_layout(
                height=360,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            ),
            xaxis_title="Timeline (UTC)",
            yaxis_title="Temperature (°C)",
        )
        st.plotly_chart(fig_trace, use_container_width=True)

        # Event Timeline Table Below Chart
        st.markdown("##### Documented Excursion Episodes & Outages Timeline")
        episodes = extract_excursion_episodes(ship_raw_sorted, max_gap_minutes=15.0)
        if episodes:
            ep_df = pd.DataFrame(episodes).rename(columns={
                "type": "Event Classification",
                "start_time": "Observed Start",
                "end_time": "Observed End",
                "observed_duration_min": "Observed Duration (min)",
                "max_observed_temp": "Max Temp (°C)",
                "degree_hours": "Excursion (°C·h)",
                "reading_count": "Sensor Samples",
                "confidence": "Data Quality Confidence",
            })
            st.dataframe(ep_df, use_container_width=True, hide_index=True)
        else:
            st.success("No discrete thermal excursions observed for this consignment.")

        # Explainable Risk Assessment & MKT Section (2 Columns)
        st.markdown("###")
        r_col1, r_col2 = st.columns([1, 1])

        with r_col1:
            st.markdown("##### Why this Shipment was Flagged (Explainable Risk Scoring)")
            st.markdown(
                f"""
                <div class="industrial-panel">
                    <div style="font-size: 0.9rem; font-weight: 600; color: #F1F5F9; margin-bottom: 8px;">
                        Risk Tier: <span style="color: {ship_meta['risk_color']};">{ship_meta['risk_category']} ({ship_meta['risk_score']} / 100)</span>
                    </div>
                    <ul style="font-size: 0.82rem; color: #94A3B8; line-height: 1.6; margin-left: -15px;">
                        <li><strong>Excursion Exposure:</strong> {ship_meta['observed_breach_duration_min']} observed minutes out of setpoints ({excursion_rate}% of monitored samples).</li>
                        <li><strong>Thermal Magnitude:</strong> {ship_meta['degree_hours_excursion']} °C·h cumulative degree-hours.</li>
                        <li><strong>Reefer Door Events:</strong> {ship_meta['door_open_count']} door-open readings logged during transit.</li>
                        <li><strong>Telemetry Dropouts:</strong> {ship_meta['gap_count']} unmonitored gaps (Sampling integrity: {ship_meta['sampling_integrity_pct']}%).</li>
                    </ul>
                    <div style="font-size: 0.72rem; color: #64748B; border-top: 1px solid #2A394D; padding-top: 6px;">
                        Calculation: Composite index weighting duration ratio (40%), degree-hours (35%), door openings (15%), and gap penalties (10%).
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with r_col2:
            st.markdown("##### Mean Kinetic Temperature (MKT) vs. Arithmetic Mean")
            arithmetic_mean = round(float(ship_raw_sorted["container_temp"].mean()), 2)
            mkt_val = calculate_mkt(ship_raw_sorted["container_temp"].values)
            mkt_diff = round(mkt_val - arithmetic_mean, 2) if mkt_val is not None else 0.0

            st.markdown(
                f"""
                <div class="industrial-panel">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span style="font-size: 0.85rem; color: #94A3B8;">Arithmetic Mean Temp:</span>
                        <span style="font-size: 0.95rem; font-weight: 600; color: #F1F5F9;">{arithmetic_mean} °C</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span style="font-size: 0.85rem; color: #94A3B8;">Calculated MKT (Arrhenius):</span>
                        <span style="font-size: 0.95rem; font-weight: 600; color: #2DD4BF;">{mkt_val} °C</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                        <span style="font-size: 0.85rem; color: #94A3B8;">Thermal Stress Delta (ΔT):</span>
                        <span style="font-size: 0.95rem; font-weight: 600; color: {'#F87171' if mkt_diff > 0.5 else '#4ADE80'};">+{mkt_diff} °C</span>
                    </div>
                    <div style="font-size: 0.72rem; color: #64748B; border-top: 1px solid #2A394D; padding-top: 6px; line-height: 1.4;">
                        Model: Arrhenius kinetics with standard activation energy ΔH = {DEFAULT_ACTIVATION_ENERGY/1000} kJ/mol (USP &lt;1079&gt;).
                        Note: MKT evaluates isothermal equivalent thermal exposure; it does not replace direct microbiological assays.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # =========================================================
    # PAGE 4: MAPREDUCE ENGINE (BIG DATA PROCESSING ENGINE)
    # =========================================================
    elif st.session_state["nav_page"] == "MapReduce Engine":
        st.markdown("## Big Data Processing Engine")
        st.caption("Inspect the pipeline from raw telemetry to aggregated analytics.")

        # Pipeline Flow Diagram (Execution Stages)
        st.markdown("##### Distributed Processing Pipeline Architecture")
        st.markdown(
            """
            <div style="display: flex; align-items: center; justify-content: space-between; background-color: #151F30; border: 1px solid #2A394D; border-radius: 6px; padding: 16px; margin-bottom: 20px; font-size: 0.75rem; text-align: center; overflow-x: auto;">
                <div style="padding: 8px 12px; background: #1B293B; border: 1px solid #2DD4BF; border-radius: 4px; color: #2DD4BF; font-weight: 600;">1. Raw CSV<br><span style="color:#64748B; font-weight:400;">1,046 Lines</span></div>
                <div style="color: #64748B;">→</div>
                <div style="padding: 8px 12px; background: #1B293B; border: 1px solid #2A394D; border-radius: 4px; color: #F1F5F9;">2. Validation<br><span style="color:#64748B;">Schema & Types</span></div>
                <div style="color: #64748B;">→</div>
                <div style="padding: 8px 12px; background: #1B293B; border: 1px solid #2DD4BF; border-radius: 4px; color: #2DD4BF; font-weight: 600;">3. Mapper<br><span style="color:#64748B; font-weight:400;">mapper.py</span></div>
                <div style="color: #64748B;">→</div>
                <div style="padding: 8px 12px; background: #1B293B; border: 1px solid #2A394D; border-radius: 4px; color: #F1F5F9;">4. Key-Value Stream<br><span style="color:#64748B;">&lt;delivery_id&gt;</span></div>
                <div style="color: #64748B;">→</div>
                <div style="padding: 8px 12px; background: #1B293B; border: 1px solid #60A5FA; border-radius: 4px; color: #60A5FA; font-weight: 600;">5. Sort & Shuffle<br><span style="color:#64748B; font-weight:400;">sort -k1,1</span></div>
                <div style="color: #64748B;">→</div>
                <div style="padding: 8px 12px; background: #1B293B; border: 1px solid #2DD4BF; border-radius: 4px; color: #2DD4BF; font-weight: 600;">6. Reducer<br><span style="color:#64748B; font-weight:400;">reducer.py</span></div>
                <div style="color: #64748B;">→</div>
                <div style="padding: 8px 12px; background: #1B293B; border: 1px solid #4ADE80; border-radius: 4px; color: #4ADE80; font-weight: 600;">7. Aggregated Metrics<br><span style="color:#64748B; font-weight:400;">20 Consignments</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Execution Status & Pipeline Controls (2 Columns)
        p_col1, p_col2 = st.columns([1, 1])

        last_meta = st.session_state["last_run_meta"]

        with p_col1:
            st.markdown("##### Pipeline Execution Telemetry")
            st.markdown(
                f"""
                <div class="industrial-panel">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                        <span style="color: #94A3B8; font-size: 0.82rem;">Execution Mode:</span>
                        <span>{render_status_badge_html(last_meta['mode'])}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 0.82rem;">
                        <span style="color: #94A3B8;">Input Records Ingested:</span>
                        <span style="color: #F1F5F9; font-weight: 600;">{last_meta.get('input_records', 1046):,}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 0.82rem;">
                        <span style="color: #94A3B8;">Valid Records Emitted:</span>
                        <span style="color: #4ADE80; font-weight: 600;">{last_meta.get('valid_records', 1045):,}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 0.82rem;">
                        <span style="color: #94A3B8;">Corrupted / Filtered:</span>
                        <span style="color: #94A3B8; font-weight: 600;">{last_meta.get('rejected_records', 0)}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 0.82rem;">
                        <span style="color: #94A3B8;">Aggregated Consignments:</span>
                        <span style="color: #2DD4BF; font-weight: 600;">{last_meta.get('output_records', 20)}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 0.82rem;">
                        <span style="color: #94A3B8;">Processing Latency:</span>
                        <span style="color: #F1F5F9; font-weight: 600;">{last_meta.get('duration_seconds', 0.029)} seconds</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.82rem;">
                        <span style="color: #94A3B8;">Hadoop Job ID:</span>
                        <span style="color: #94A3B8; font-family: monospace;">{last_meta.get('hadoop_job_id', 'N/A')}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with p_col2:
            st.markdown("##### Pipeline Run Controls")
            st.markdown(
                """
                Execute the pipeline over the active telemetry dataset. Both the local streaming runner
                and Hadoop cluster executor use the exact same `hadoop/mapper.py` and `hadoop/reducer.py` scripts.
                """
            )

            chosen_mode_label = st.radio(
                "Execution Target Engine:",
                options=["Auto-Detect (LOCAL_STREAMING on macOS ARM)", "Force REAL_HADOOP Cluster Job"],
                index=0,
            )

            if st.button("Execute MapReduce Job Now", type="primary", use_container_width=True):
                with st.spinner("Streaming records through Mapper & Reducer..."):
                    manager = PipelineExecutionManager(workspace_root=WORKSPACE_ROOT)
                    raw_path = os.path.join(WORKSPACE_ROOT, "data", "sample", "cold_chain_sample.csv")
                    processed_path = os.path.join(WORKSPACE_ROOT, "data", "processed", "summary_metrics.csv")

                    mode_arg = ExecutionMode.REAL_HADOOP if "REAL_HADOOP" in chosen_mode_label else ExecutionMode.LOCAL_STREAMING

                    try:
                        res = manager.run_pipeline(raw_path, processed_path, mode=mode_arg)
                        st.session_state["last_run_meta"] = res
                        st.success(f"Execution finished in {res['duration_seconds']}s via {res['mode_label']}.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Execution Error: {exc}")

            # Download Aggregated Output CSV
            processed_file_path = os.path.join(WORKSPACE_ROOT, "data", "processed", "summary_metrics.csv")
            if os.path.exists(processed_file_path):
                with open(processed_file_path, "r", encoding="utf-8") as f:
                    csv_bytes = f.read()
                st.download_button(
                    label="Download Aggregated Analytics CSV",
                    data=csv_bytes,
                    file_name="freshtrack_aggregated_metrics.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

        # Technical Inspection Expandable Panels
        st.markdown("###")
        st.markdown("##### Technical Inspection Panels (Data Lake Previews)")

        with st.expander("1. Raw Telemetry Ingestion Preview (First 10 Records)", expanded=False):
            st.dataframe(raw_df.head(10), use_container_width=True, hide_index=True)

        with st.expander("2. Mapper Intermediate Output Stream (hadoop/mapper.py)", expanded=False):
            st.caption("Tab-separated key-values emitted to stdout: <delivery_id> \\t <timestamp> \\t <temp> \\t ...")
            if "mapper_sample" in last_meta and last_meta["mapper_sample"]:
                st.code("\n".join(last_meta["mapper_sample"]), language="tsv")
            else:
                st.code("DEL-1001\t2026-10-19T06:00:00Z\t2.78\t2.00\t4.00\t32.95\t0\tDairy\tRT-MUM-PUN-01\tWH-WEST-02\nDEL-1001\t2026-10-19T06:04:20Z\t3.25\t2.00\t4.00\t33.13\t1\tDairy\tRT-MUM-PUN-01\tWH-WEST-02", language="tsv")

        with st.expander("3. Sorted Intermediate Stream (sort -k1,1)", expanded=False):
            st.caption("Intermediate data grouped by consignment key prior to reducer consumption:")
            if "sorted_sample" in last_meta and last_meta["sorted_sample"]:
                st.code("\n".join(last_meta["sorted_sample"]), language="tsv")
            else:
                st.code("DEL-1001\t2026-10-19T06:00:00Z\t2.78\t2.00\t4.00\t32.95\t0\tDairy\tRT-MUM-PUN-01\tWH-WEST-02\nDEL-1001\t2026-10-19T06:04:20Z\t3.25\t2.00\t4.00\t33.13\t1\tDairy\tRT-MUM-PUN-01\tWH-WEST-02", language="tsv")

        with st.expander("4. Reducer Aggregation Output Preview (hadoop/reducer.py)", expanded=False):
            st.dataframe(summary_df.head(10), use_container_width=True, hide_index=True)

        with st.expander("5. System Environment & Hadoop Cluster Diagnostics", expanded=False):
            st.json({
                "host_os": "macOS Darwin (ARM64 Apple Silicon)",
                "python_runtime": f"Python {sys.version.split()[0]}",
                "java_jdk_installed": env_info["has_java"],
                "java_version": env_info["java_version"],
                "hadoop_cli_installed": env_info["has_hadoop"],
                "hadoop_version": env_info["hadoop_version"],
                "hdfs_namenode_online": env_info["hdfs_online"],
                "recommended_mode": env_info["recommended_mode"].value,
            })

    # =========================================================
    # PAGE 5: DATA EXPLORER (TELEMETRY DATA EXPLORER)
    # =========================================================
    elif st.session_state["nav_page"] == "Data Explorer":
        st.markdown("## Telemetry Data Explorer")
        st.caption("Query and inspect raw IoT telemetry, monitor data quality, and export audit datasets.")

        # Filter Bar for Data Explorer
        de_col1, de_col2, de_col3, de_col4 = st.columns(4)
        with de_col1:
            de_shipment = st.selectbox("Filter by Shipment:", ["All Shipments"] + sorted(raw_df["delivery_id"].unique()))
        with de_col2:
            de_route = st.selectbox("Filter by Route:", ["All Routes"] + sorted(raw_df["route_id"].unique()))
        with de_col3:
            de_category = st.selectbox("Filter by Commodity:", ["All Commodities"] + sorted(raw_df["product_category"].unique()))
        with de_col4:
            de_type = st.selectbox("Filter Record Type:", ["All Records", "Excursions Only", "Door Open Events Only"], index=0)

        # Filter Application
        exp_df = raw_df.copy()
        if de_shipment != "All Shipments":
            exp_df = exp_df[exp_df["delivery_id"] == de_shipment]
        if de_route != "All Routes":
            exp_df = exp_df[exp_df["route_id"] == de_route]
        if de_category != "All Commodities":
            exp_df = exp_df[exp_df["product_category"] == de_category]

        if de_type == "Excursions Only":
            exp_df = exp_df[(exp_df["container_temp"] > exp_df["target_temp_max"]) | (exp_df["container_temp"] < exp_df["target_temp_min"])]
        elif de_type == "Door Open Events Only":
            exp_df = exp_df[exp_df["door_open_flag"] == 1]

        # Quality Counters
        q1, q2, q3, q4 = st.columns(4)
        with q1:
            render_kpi_card("Matching Records", f"{len(exp_df):,}", f"Filtered sensor rows", accent_color="#2DD4BF")
        with q2:
            render_kpi_card("Total Dataset Rows", f"{len(raw_df):,}", f"Simulated sensor telemetry", accent_color="#60A5FA")
        with q3:
            total_gaps = int(summary_df["gap_count"].sum())
            render_kpi_card("Documented Gaps", f"{total_gaps}", f"Intervals > 15m", accent_color="#FBBF24" if total_gaps > 0 else "#4ADE80")
        with q4:
            total_dups = int(summary_df["duplicate_count"].sum())
            render_kpi_card("Deduplicated Packets", f"{total_dups}", f"Dropped duplicate timestamps", accent_color="#4ADE80")

        st.markdown("###")

        # Tabbed Data Tables
        tab_raw, tab_summary, tab_dict = st.tabs([
            "Raw Sensor Telemetry",
            "Aggregated Summary Metrics",
            "Data Dictionary & Setpoints",
        ])

        with tab_raw:
            st.dataframe(exp_df, use_container_width=True, hide_index=True)
            # Export CSV
            raw_csv = exp_df.to_csv(index=False)
            st.download_button(
                "Export Filtered Raw Telemetry CSV",
                data=raw_csv,
                file_name="freshtrack_raw_telemetry_filtered.csv",
                mime="text/csv",
            )

        with tab_summary:
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
            sum_csv = summary_df.to_csv(index=False)
            st.download_button(
                "Export Aggregated Metrics CSV",
                data=sum_csv,
                file_name="freshtrack_summary_metrics.csv",
                mime="text/csv",
            )

        with tab_dict:
            st.markdown("##### Telemetry Data Schema (14 Fields)")
            schema_data = [
                {"Field": "record_id", "Type": "String", "Description": "Unique sensor event UUID (e.g. REC-275D61BE)"},
                {"Field": "timestamp", "Type": "ISO 8601 UTC", "Description": "Timestamp of temperature recording (YYYY-MM-DDTHH:MM:SSZ)"},
                {"Field": "delivery_id", "Type": "String", "Description": "Consignment shipment identifier (DEL-1001 to DEL-1020)"},
                {"Field": "vehicle_id", "Type": "String", "Description": "Refrigerated transport vehicle identifier"},
                {"Field": "route_id", "Type": "String", "Description": "Transit logistics corridor ID (e.g. RT-MUM-PUN-01)"},
                {"Field": "warehouse_id", "Type": "String", "Description": "Origin or transit refrigeration facility"},
                {"Field": "product_category", "Type": "String", "Description": "Perishable commodity category"},
                {"Field": "target_temp_min", "Type": "Float (°C)", "Description": "Configured lower temperature threshold"},
                {"Field": "target_temp_max", "Type": "Float (°C)", "Description": "Configured upper temperature threshold"},
                {"Field": "container_temp", "Type": "Float (°C)", "Description": "Internal sensor cargo probe temperature"},
                {"Field": "ambient_temp", "Type": "Float (°C)", "Description": "External environmental air temperature"},
                {"Field": "door_open_flag", "Type": "Integer (0/1)", "Description": "Reefer door state (1 = Open, 0 = Closed)"},
                {"Field": "battery_level", "Type": "Integer (%)", "Description": "IoT tracking device remaining battery level"},
                {"Field": "transit_status", "Type": "String", "Description": "Operational state: LOADING, IN_TRANSIT, UNLOADING"},
            ]
            st.dataframe(pd.DataFrame(schema_data), use_container_width=True, hide_index=True)

            st.markdown("##### Configured Commodity Target Setpoints")
            profiles_data = [
                {"Commodity": k, "Target Min (°C)": v["target_min"], "Target Max (°C)": v["target_max"], "Critical High (°C)": v["critical_high"], "Critical Low (°C)": v["critical_low"]}
                for k, v in PRODUCT_PROFILES.items()
            ]
            st.dataframe(pd.DataFrame(profiles_data), use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # SCIENTIFIC & REGULATORY DISCLAIMER FOOTER
    # ---------------------------------------------------------
    render_disclaimer_callout()


if __name__ == "__main__":
    main()
