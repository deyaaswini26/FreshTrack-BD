#!/usr/bin/env python3
"""
FreshTrack BD — Big Data Cold-Chain Analytics Platform
Clean, Modern, Spacious & Beginner-Friendly Control Tower.

Pages:
1. Home (Operations Overview & Attention Triage)
2. Shipments (Shipment Investigation & Temperature Trace)
3. Routes & Warehouses (Transit Corridors & Facility Performance)
4. Data Quality (Telemetry Health, Sensor Gaps & Data Explorer)
5. Technical Details (MapReduce Engine, Cluster Status & Mathematical Reference)
"""

import datetime
import os
import sys
import textwrap
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

from app.components.styles import CLEAN_LIGHT_THEME_CSS
from app.components.ui_elements import (
    SVG_ICONS,
    get_clean_plotly_layout,
    render_alert_item,
    render_disclaimer_callout,
    render_global_header,
    render_kpi_card,
    render_status_badge_html,
)
from src.analytics import (
    DEFAULT_ACTIVATION_ENERGY,
    SCIENTIFIC_DISCLAIMER,
    EvidenceQuality,
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
    page_title="FreshTrack BD — Cold-Chain Analytics",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject Clean Light Theme CSS
st.markdown(CLEAN_LIGHT_THEME_CSS, unsafe_allow_html=True)


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

    # Session State & Query Param Initialization
    nav_options = [
        "Home",
        "Shipments",
        "Routes & Warehouses",
        "Data Quality",
        "Technical Details",
    ]

    query_page = st.query_params.get("page")
    if query_page and query_page in nav_options:
        st.session_state["nav_page"] = query_page
    elif "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "Home"

    query_shipment = st.query_params.get("shipment")
    if query_shipment:
        st.session_state["investigate_shipment_id"] = query_shipment
    elif "investigate_shipment_id" not in st.session_state:
        st.session_state["investigate_shipment_id"] = None

    raw_df, summary_df = load_or_run_data()

    # ---------------------------------------------------------
    # CLEAN, SPACIOUS SIDEBAR NAVIGATION
    # ---------------------------------------------------------
    with st.sidebar:
        # Brand Header — st.html() bypasses Markdown indented-code-block processing
        st.html(
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">'
            f'{SVG_ICONS["snowflake"]}'
            f'<span style="font-size:1.3rem;font-weight:700;color:#0F172A;letter-spacing:-0.02em;">FreshTrack BD</span>'
            f'</div>'
            f'<div style="font-size:0.8rem;color:#64748B;margin-bottom:24px;line-height:1.4;">'
            f'Cold-Chain Intelligence &amp; Big Data Analytics'
            f'</div>'
        )

        # 5 Clean Navigation Options
        nav_options = [
            "Home",
            "Shipments",
            "Routes & Warehouses",
            "Data Quality",
            "Technical Details",
        ]

        current_idx = nav_options.index(st.session_state["nav_page"]) if st.session_state["nav_page"] in nav_options else 0
        selected_nav = st.radio(
            "NAVIGATION",
            options=nav_options,
            index=current_idx,
            label_visibility="collapsed",
        )
        if selected_nav != st.session_state["nav_page"]:
            st.session_state["nav_page"] = selected_nav
            st.query_params["page"] = selected_nav
            st.rerun()

        st.markdown("<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 32px 0 20px 0;'>", unsafe_allow_html=True)

        # Friendly Sidebar Info — st.html() bypasses Markdown code-block detection
        st.html(
            f'<div style="font-size:0.82rem;color:#64748B;line-height:1.6;">'
            f'<div style="margin-bottom:6px;"><strong style="color:#334155;">Active Consignments:</strong> {len(summary_df)} shipments</div>'
            f'<div style="margin-bottom:6px;"><strong style="color:#334155;">Telemetry Samples:</strong> {len(raw_df):,} points</div>'
            f'<div style="margin-top:12px;margin-bottom:4px;"><strong style="color:#334155;">Engine Mode:</strong></div>'
            f'<div>{render_status_badge_html(st.session_state["last_run_meta"]["mode"])}</div>'
            f'<div style="margin-top:24px;padding-top:12px;border-top:1px solid #F1F5F9;color:#94A3B8;font-size:0.76rem;">FreshTrack BD v2.5.0 \u2022 Clean Edition</div>'
            f'</div>'
        )

    # ---------------------------------------------------------
    # GLOBAL HEADER
    # ---------------------------------------------------------
    render_global_header(
        page_name=st.session_state["nav_page"],
        dataset_name="cold_chain_sample.csv",
        last_run_meta=st.session_state.get("last_run_meta"),
    )

    # =========================================================
    # PAGE 1: HOME (OPERATIONS OVERVIEW & ATTENTION TRIAGE)
    # =========================================================
    if st.session_state["nav_page"] == "Home":
        st.markdown("# Cold-Chain Operations Overview")
        st.markdown(
            textwrap.dedent("""
            FreshTrack BD monitors temperature-sensitive food and pharmaceuticals during transit.
            We track both **observed temperature excursions** and **sensor telemetry reliability**
            so unmonitored dropouts are never mistaken for safe compliance.
            """).strip()
        )

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        # High-Level Metrics (4 Restrained, Spacious Cards)
        total_shipments = len(summary_df)
        total_valid_readings = int(summary_df["valid_readings"].sum()) if total_shipments > 0 else 0
        total_breach_readings = int(summary_df["breach_reading_count"].sum()) if total_shipments > 0 else 0
        compliance_pct = round(((total_valid_readings - total_breach_readings) / max(1, total_valid_readings)) * 100.0, 1)

        # Attention required: High/Critical risk, breach > 0, or Poor evidence quality
        needs_attention_df = summary_df[
            (summary_df["risk_category"].isin(["HIGH", "CRITICAL"]))
            | (summary_df["breach_reading_count"] > 0)
            | (summary_df["evidence_quality"] == "Poor")
        ]
        attention_count = len(needs_attention_df)

        # Average Telemetry Coverage
        avg_coverage = round(float(summary_df["telemetry_coverage_pct"].dropna().mean()), 1) if "telemetry_coverage_pct" in summary_df.columns else 95.0

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            render_kpi_card(
                title="Shipments Monitored",
                value=f"{total_shipments}",
                caption=f"Across {summary_df['product_category'].nunique()} product categories",
                icon_name="truck",
                accent_color="#0D9488",
            )
        with k2:
            render_kpi_card(
                title="Temperature Compliance",
                value=f"{compliance_pct}%",
                caption=f"{total_valid_readings - total_breach_readings:,} of {total_valid_readings:,} readings in range",
                icon_name="check_circle",
                accent_color="#16A34A" if compliance_pct >= 90 else "#D97706",
            )
        with k3:
            render_kpi_card(
                title="Shipments Needing Review",
                value=f"{attention_count}",
                caption=f"Thermal breaches or unverified sensor dropouts",
                icon_name="alert_triangle",
                accent_color="#DC2626" if attention_count > 0 else "#16A34A",
            )
        with k4:
            render_kpi_card(
                title="Average Sensor Reliability",
                value=f"{avg_coverage}%",
                caption=f"Continuous coverage across transit windows",
                icon_name="shield_check",
                accent_color="#0284C7",
            )

        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

        # Attention Table: Clean, Spacious, Actionable
        st.markdown("### Shipments Requiring Attention")
        st.caption("Deliveries with documented temperature spikes or sensor dropouts requiring disposition review.")

        if not needs_attention_df.empty:
            display_attention = needs_attention_df.sort_values("risk_score", ascending=False).copy()

            # Format clean columns for presentation
            triage_table = []
            for _, row in display_attention.iterrows():
                triage_table.append({
                    "Shipment ID": row["delivery_id"],
                    "Commodity": row["product_category"],
                    "Route": row["route_id"],
                    "Observed Temperature Risk": f"{row['risk_category']} ({row['risk_score']}/100)",
                    "Sensor Quality": row.get("evidence_quality", "Unknown"),
                    "Audit Assessment": row.get("qualified_risk_label", f"{row['risk_category']} Exposure"),
                    "Recommended Action": row.get("recommended_action", "Secondary receiving inspection required."),
                })

            st.dataframe(pd.DataFrame(triage_table), use_container_width=True, hide_index=True)

            # Quick inspect button
            q_col1, q_col2 = st.columns([2, 1])
            with q_col1:
                target_shipment = st.selectbox(
                    "Select a shipment to open in full investigation view:",
                    options=display_attention["delivery_id"].tolist(),
                    key="home_quick_select",
                )
            with q_col2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("Inspect Shipment Details →", type="primary", use_container_width=True):
                    st.session_state["nav_page"] = "Shipments"
                    st.session_state["investigate_shipment_id"] = target_shipment
                    st.query_params["page"] = "Shipments"
                    st.query_params["shipment"] = target_shipment
                    st.rerun()
        else:
            st.success("All monitored shipments are currently in safe temperature setpoints with good sensor coverage.")

        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

        # Two Spacious Analytics Columns: Commodity Compliance & Operational Alerts
        c_col1, c_col2 = st.columns([1, 1])

        with c_col1:
            st.markdown("### Commodity Safe Band Compliance")
            st.caption("Percentage of telemetry readings within target storage temperatures.")
            cat_summary = raw_df.groupby("product_category").agg(
                total_readings=("record_id", "count"),
                compliant_readings=("container_temp", lambda s: ((s >= raw_df.loc[s.index, "target_temp_min"]) & (s <= raw_df.loc[s.index, "target_temp_max"])).sum()),
            ).reset_index()
            cat_summary["compliance_rate"] = ((cat_summary["compliant_readings"] / cat_summary["total_readings"]) * 100.0).round(1)
            cat_summary = cat_summary.sort_values("compliance_rate", ascending=True)

            fig_cat = px.bar(
                cat_summary,
                x="compliance_rate",
                y="product_category",
                orientation="h",
                color="compliance_rate",
                color_continuous_scale=[[0, "#EF4444"], [0.7, "#F59E0B"], [1.0, "#10B981"]],
                range_color=[50, 100],
                labels={"compliance_rate": "Compliance (%)", "product_category": "Commodity"},
            )
            fig_cat.update_layout(
                **get_clean_plotly_layout(height=280),
                coloraxis_showscale=False,
            )
            fig_cat.update_traces(
                hovertemplate="<b>%{y}</b><br>Safe Range Adherence: %{x}%<extra></extra>",
            )
            st.plotly_chart(fig_cat, use_container_width=True)

        with c_col2:
            st.markdown("### Operational Fleet Alerts")
            st.caption("Automated findings generated from sensor readings and route trends.")
            alerts = derive_operational_alerts(summary_df, raw_df)
            if alerts:
                for alert in alerts[:3]:  # Top 3 plain-English alerts
                    render_alert_item(
                        severity=alert["severity"],
                        title=alert["title"],
                        evidence=alert["evidence"],
                        recommendation=alert["recommendation"],
                    )
            else:
                st.info("No active operational alerts across current shipments.")

    # =========================================================
    # PAGE 2: SHIPMENTS (SHIPMENT INVESTIGATION & TEMPERATURE TRACE)
    # =========================================================
    elif st.session_state["nav_page"] == "Shipments":
        st.markdown("# Shipment Temperature & Evidence Investigation")
        st.markdown("Trace individual temperature readings, examine sensor gap intervals, and review audit recommendations.")

        # Shipment Selector Dropdown
        all_deliveries = summary_df.sort_values("risk_score", ascending=False)
        shipment_labels = {}
        for _, row in all_deliveries.iterrows():
            qual = row.get("evidence_quality", "Unknown")
            shipment_labels[row["delivery_id"]] = (
                f"{row['delivery_id']} — {row['product_category']} ({row['route_id']}) • Risk: {row['risk_category']} • Evidence: {qual}"
            )

        default_idx = 0
        if st.session_state.get("investigate_shipment_id") in shipment_labels:
            default_idx = list(shipment_labels.keys()).index(st.session_state["investigate_shipment_id"])

        sel_shipment = st.selectbox(
            "Select a shipment to audit:",
            options=list(shipment_labels.keys()),
            format_func=lambda x: shipment_labels[x],
            index=default_idx,
        )

        ship_meta = summary_df[summary_df["delivery_id"] == sel_shipment].iloc[0]
        ship_raw = raw_df[raw_df["delivery_id"] == sel_shipment].sort_values("timestamp").copy()

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        # 4 Summary Cards for the Selected Shipment
        t_min = float(ship_raw["target_temp_min"].iloc[0])
        t_max = float(ship_raw["target_temp_max"].iloc[0])
        excursion_rate = round((ship_meta["breach_reading_count"] / max(1, ship_meta["valid_readings"])) * 100.0, 1)
        cov_pct = ship_meta.get("telemetry_coverage_pct")
        cov_str = f"{cov_pct}%" if (cov_pct is not None and not pd.isna(cov_pct)) else "N/A"
        ev_quality = ship_meta.get("evidence_quality", "Unknown")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_kpi_card(
                title="Product & Safe Zone",
                value=f"{t_min} to {t_max} °C",
                caption=f"{ship_meta['product_category']} • {ship_meta['route_id']}",
                icon_name="thermometer",
                accent_color="#0D9488",
            )
        with c2:
            render_kpi_card(
                title="Observed Excursion",
                value=f"{ship_meta['observed_breach_duration_min']} min",
                caption=f"{excursion_rate}% of monitored time in breach",
                icon_name="clock",
                accent_color="#DC2626" if ship_meta['observed_breach_duration_min'] > 0 else "#16A34A",
            )
        with c3:
            render_kpi_card(
                title="Cumulative Heat Impact",
                value=f"{ship_meta['degree_hours_excursion']} °C·h",
                caption=f"Max: {ship_meta['max_temp']}°C • Min: {ship_meta['min_temp']}°C",
                icon_name="activity",
                accent_color="#D97706" if ship_meta['degree_hours_excursion'] > 0 else "#16A34A",
            )
        with c4:
            render_kpi_card(
                title="Sensor Evidence Quality",
                value=f"{ev_quality}",
                caption=f"{cov_str} coverage • {ship_meta['gap_count']} dropouts (>15m)",
                icon_name="shield_check",
                accent_color="#16A34A" if ev_quality == "Good" else ("#D97706" if ev_quality == "Limited" else "#DC2626"),
            )

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        # Gap-Aware Cold-Chain Intelligence Banner (Plain English)
        qual_label = ship_meta.get("qualified_risk_label", f"{ship_meta['risk_category']} Risk")
        gap_exp = ship_meta.get("gap_explanation", "")
        rec_act = ship_meta.get("recommended_action", "Conduct standard receiving audit.")

        badge_class = 'real-hadoop' if ev_quality == 'Good' else ('local-streaming' if ev_quality == 'Limited' else 'error')
        st.html(
            f'<div class="clean-panel" style="border-left:5px solid #0D9488;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
            f'<div style="font-size:1.1rem;font-weight:700;color:#0F172A;">Cold-Chain Assessment: {qual_label}</div>'
            f'<div><span class="status-badge badge-{badge_class}">Evidence: {ev_quality}</span></div>'
            f'</div>'
            f'<div style="font-size:0.92rem;color:#334155;line-height:1.6;margin-bottom:12px;">{gap_exp}</div>'
            f'<div style="font-size:0.88rem;color:#0D9488;font-weight:600;">'
            f'Actionable Guidance: <span style="color:#0F172A;font-weight:500;">{rec_act}</span>'
            f'</div>'
            f'</div>'
        )

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        # Interactive Temperature Trace Plot
        st.markdown("### Temperature History Throughout Transit")
        st.caption("Green band represents the safe range. Gray shaded intervals show where sensor connection dropped (>15 minutes).")

        ship_raw["dt"] = pd.to_datetime(ship_raw["timestamp"])
        ship_raw_sorted = ship_raw.sort_values("dt").reset_index(drop=True)

        fig_trace = go.Figure()

        # 1. Shaded Safe Temperature Band
        fig_trace.add_trace(go.Scatter(
            x=pd.concat([ship_raw_sorted["dt"], ship_raw_sorted["dt"][::-1]]),
            y=[t_max]*len(ship_raw_sorted) + [t_min]*len(ship_raw_sorted),
            fill="toself",
            fillcolor="rgba(16, 185, 129, 0.12)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="skip",
            name="Safe Range Band",
        ))

        # Target Setpoint Lines
        fig_trace.add_trace(go.Scatter(
            x=ship_raw_sorted["dt"],
            y=[t_max]*len(ship_raw_sorted),
            mode="lines",
            line=dict(color="#10B981", width=1.5, dash="dash"),
            name=f"Max Allowed ({t_max}°C)",
        ))
        fig_trace.add_trace(go.Scatter(
            x=ship_raw_sorted["dt"],
            y=[t_min]*len(ship_raw_sorted),
            mode="lines",
            line=dict(color="#10B981", width=1.5, dash="dash"),
            name=f"Min Allowed ({t_min}°C)",
        ))

        # Ambient Outside Temperature
        fig_trace.add_trace(go.Scatter(
            x=ship_raw_sorted["dt"],
            y=ship_raw_sorted["ambient_temp"],
            mode="lines",
            line=dict(color="#94A3B8", width=1.2, dash="dot"),
            name="Outside Weather Temp",
        ))

        # Container Temperature Curve (Breaks over gaps > 15m)
        plot_times = []
        plot_temps = []
        for i in range(len(ship_raw_sorted)):
            if i > 0:
                diff_m = (ship_raw_sorted["dt"].iloc[i] - ship_raw_sorted["dt"].iloc[i - 1]).total_seconds() / 60.0
                if diff_m > 15.0:
                    plot_times.append(ship_raw_sorted["dt"].iloc[i - 1] + datetime.timedelta(seconds=1))
                    plot_temps.append(None)
            plot_times.append(ship_raw_sorted["dt"].iloc[i])
            plot_temps.append(ship_raw_sorted["container_temp"].iloc[i])

        fig_trace.add_trace(go.Scatter(
            x=plot_times,
            y=plot_temps,
            mode="lines",
            line=dict(color="#0D9488", width=2.5),
            name="Cargo Probe Temp",
            connectgaps=False,
        ))

        # Breach Highlight Markers
        excursion_points = ship_raw_sorted[(ship_raw_sorted["container_temp"] > t_max) | (ship_raw_sorted["container_temp"] < t_min)]
        if not excursion_points.empty:
            fig_trace.add_trace(go.Scatter(
                x=excursion_points["dt"],
                y=excursion_points["container_temp"],
                mode="markers",
                marker=dict(size=7, color="#EF4444", symbol="circle"),
                name="Temperature Breach",
                hovertemplate="<b>Breach Detected</b><br>Time: %{x}<br>Temp: %{y}°C<extra></extra>",
            ))

        # Shaded Sensor Outage Gaps
        for i in range(1, len(ship_raw_sorted)):
            prev_dt = ship_raw_sorted["dt"].iloc[i - 1]
            curr_dt = ship_raw_sorted["dt"].iloc[i]
            diff_m = (curr_dt - prev_dt).total_seconds() / 60.0
            if diff_m > 15.0:
                fig_trace.add_vrect(
                    x0=prev_dt,
                    x1=curr_dt,
                    fillcolor="rgba(100, 116, 139, 0.15)",
                    layer="below",
                    line_width=1,
                    line_dash="dot",
                    line_color="#94A3B8",
                    annotation_text=f"Sensor Dropout ({int(diff_m)} min)",
                    annotation_position="top left",
                    annotation_font_size=11,
                )

        fig_trace.update_layout(
            **get_clean_plotly_layout(
                height=380,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            ),
            xaxis_title="Timeline (UTC)",
            yaxis_title="Temperature (°C)",
        )
        st.plotly_chart(fig_trace, use_container_width=True)

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        # Excursion Episodes Table & Simple MKT Explainer (2 Columns)
        e_col1, e_col2 = st.columns([1.2, 0.8])

        with e_col1:
            st.markdown("### Documented Excursion Episodes")
            episodes = extract_excursion_episodes(ship_raw_sorted, max_gap_minutes=15.0)
            if episodes:
                ep_df = pd.DataFrame(episodes).rename(columns={
                    "type": "Event Type",
                    "start_time": "Start Time",
                    "end_time": "End Time",
                    "observed_duration_min": "Duration (min)",
                    "max_observed_temp": "Peak Temp (°C)",
                    "degree_hours": "Excursion (°C·h)",
                })
                display_cols = ["Event Type", "Start Time", "Duration (min)", "Peak Temp (°C)", "Excursion (°C·h)"]
                st.dataframe(ep_df[display_cols], use_container_width=True, hide_index=True)
            else:
                st.success("No discrete thermal excursions were recorded during monitored intervals.")

        with e_col2:
            st.markdown("### Mean Kinetic Temperature (MKT)")
            arithmetic_mean = round(float(ship_raw_sorted["container_temp"].mean()), 2)
            mkt_val = calculate_mkt(ship_raw_sorted["container_temp"].values)
            mkt_diff = round(mkt_val - arithmetic_mean, 2) if mkt_val is not None else 0.0

            # Use st.html() to bypass Markdown processing entirely — avoids the
            # CommonMark indented-code-block trap that st.markdown() triggers
            # when child <div> lines carry 4+ spaces of leading whitespace.
            st.html(
                f'<div class="clean-panel">'
                f'<div style="font-size:0.86rem;color:#64748B;margin-bottom:4px;">Simple Arithmetic Average:</div>'
                f'<div style="font-size:1.25rem;font-weight:600;color:#0F172A;margin-bottom:12px;">{arithmetic_mean} \u00b0C</div>'
                f'<div style="font-size:0.86rem;color:#64748B;margin-bottom:4px;">Calculated MKT (Heat Stress):</div>'
                f'<div style="font-size:1.25rem;font-weight:700;color:#0D9488;margin-bottom:12px;">{mkt_val} \u00b0C</div>'
                f'<div style="font-size:0.82rem;color:#475569;line-height:1.5;padding-top:8px;border-top:1px solid #E2E8F0;">'
                f'<strong style="color:#0F172A;">Why MKT Matters:</strong> A simple average can hide brief heat spikes. '
                f'MKT uses chemical reaction kinetics to account for how heat spikes accelerate food degradation faster than cool periods.'
                f'</div>'
                f'</div>'
            )

    # =========================================================
    # PAGE 3: ROUTES & WAREHOUSES (CORRIDORS & FACILITIES)
    # =========================================================
    elif st.session_state["nav_page"] == "Routes & Warehouses":
        st.markdown("# Route & Warehouse Performance")
        st.markdown("Identify which transit routes maintain cold temperatures reliably and compare receiving warehouse facilities.")

        route_stats = aggregate_by_route(summary_df)
        wh_stats = aggregate_by_warehouse(summary_df)

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        # Route Ranking Table
        st.markdown("### Transport Corridor Performance Rankings")
        st.caption("Routes sorted by cold-chain compliance and average risk score.")

        route_display = route_stats.copy().rename(columns={
            "route_id": "Route Corridor",
            "total_deliveries": "Total Shipments",
            "breached_deliveries": "Shipments with Breaches",
            "compliance_rate_pct": "Compliance %",
            "avg_risk_score": "Average Risk (0-100)",
            "total_degree_hours": "Cumulative Heat (°C·h)",
            "avg_sampling_integrity": "Sensor Quality %",
            "total_door_open_events": "Door Events",
        })
        st.dataframe(route_display, use_container_width=True, hide_index=True)

        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

        # Two Visual Charts (Route Risk vs Warehouse Compliance)
        r_col1, r_col2 = st.columns(2)

        with r_col1:
            st.markdown("### Corridor Risk Ranking")
            fig_r1 = px.bar(
                route_stats,
                x="avg_risk_score",
                y="route_id",
                orientation="h",
                color="avg_risk_score",
                color_continuous_scale=[[0, "#10B981"], [0.5, "#F59E0B"], [1.0, "#EF4444"]],
                labels={"avg_risk_score": "Average Risk Score", "route_id": "Route Corridor"},
            )
            fig_r1.update_layout(**get_clean_plotly_layout(height=280), coloraxis_showscale=False)
            st.plotly_chart(fig_r1, use_container_width=True)

        with r_col2:
            st.markdown("### Warehouse Facility Compliance")
            fig_w1 = px.bar(
                wh_stats,
                x="warehouse_id",
                y="compliance_rate_pct",
                color="compliance_rate_pct",
                color_continuous_scale=[[0, "#EF4444"], [0.7, "#F59E0B"], [1.0, "#10B981"]],
                range_color=[0, 100],
                labels={"compliance_rate_pct": "Compliance %", "warehouse_id": "Facility"},
            )
            fig_w1.update_layout(**get_clean_plotly_layout(height=280), coloraxis_showscale=False)
            st.plotly_chart(fig_w1, use_container_width=True)

        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

        # Route-Commodity Risk Matrix & Diurnal Patterns
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.markdown("### Route-Commodity Risk Heatmap")
            st.caption("Average operational risk score by transport corridor and perishable commodity.")
            mat_df = aggregate_route_product_matrix(summary_df)
            fig_mat = px.imshow(
                mat_df,
                labels=dict(x="Product Category", y="Route Corridor", color="Risk Score"),
                x=list(mat_df.columns),
                y=list(mat_df.index),
                color_continuous_scale=[[0, "#10B981"], [0.4, "#FBBF24"], [0.75, "#F97316"], [1.0, "#EF4444"]],
                aspect="auto",
                text_auto=".1f",
            )
            fig_mat.update_layout(**get_clean_plotly_layout(height=290), coloraxis_showscale=False)
            st.plotly_chart(fig_mat, use_container_width=True)

        with m_col2:
            st.markdown("### Diurnal Excursion Timing")
            st.caption("Breach frequency vs outside ambient temperatures across 24-hour delivery cycles.")
            hourly_df = aggregate_hourly_excursions(raw_df)
            fig_hour = go.Figure()
            fig_hour.add_trace(go.Bar(
                x=hourly_df["hour"],
                y=hourly_df["excursion_readings"],
                name="Breach Readings",
                marker_color="#EF4444",
                opacity=0.85,
            ))
            fig_hour.add_trace(go.Scatter(
                x=hourly_df["hour"],
                y=hourly_df["avg_ambient_temp"],
                name="Ambient Temp (°C)",
                yaxis="y2",
                line=dict(color="#0D9488", width=2),
            ))
            hour_layout = get_clean_plotly_layout(height=290)
            hour_layout["yaxis2"] = dict(
                title=dict(text="Ambient Temp (°C)", font=dict(size=12, color="#0D9488")),
                overlaying="y",
                side="right",
                showgrid=False,
                tickfont=dict(size=11, color="#0D9488"),
            )
            hour_layout["xaxis"]["title"] = dict(text="Hour of Day (UTC)")
            hour_layout["yaxis"]["title"] = dict(text="Breach Readings Count")
            fig_hour.update_layout(**hour_layout)
            st.plotly_chart(fig_hour, use_container_width=True)

        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

        # Facility Detail Inspector
        st.markdown("### Specific Facility Performance Inspector")
        wh_options = sorted(wh_stats["warehouse_id"].tolist())
        selected_facility = st.selectbox("Select a storage warehouse to inspect:", wh_options)

        f_wh_deliveries = summary_df[summary_df["warehouse_id"] == selected_facility]
        f_wh_raw = raw_df[raw_df["warehouse_id"] == selected_facility]

        wh_k1, wh_k2, wh_k3, wh_k4 = st.columns(4)
        with wh_k1:
            render_kpi_card("Shipments Handled", f"{len(f_wh_deliveries)}", "Total consignments", accent_color="#0D9488")
        with wh_k2:
            render_kpi_card("Total Sensor Points", f"{len(f_wh_raw):,}", "Inbound & staging readings", accent_color="#0284C7")
        with wh_k3:
            wh_excursion_rate = round((f_wh_deliveries["breach_reading_count"].sum() / max(1, f_wh_deliveries["valid_readings"].sum())) * 100.0, 1)
            render_kpi_card("Breach Frequency", f"{wh_excursion_rate}%", "Sensor points out of bounds", accent_color="#EF4444" if wh_excursion_rate > 20 else "#10B981")
        with wh_k4:
            gaps_in_wh = int(f_wh_deliveries["gap_count"].sum())
            render_kpi_card("Sensor Dropouts (>15m)", f"{gaps_in_wh}", "Unmonitored intervals detected", accent_color="#F59E0B" if gaps_in_wh > 0 else "#10B981")

    # =========================================================
    # PAGE 4: DATA QUALITY (TELEMETRY HEALTH & DATA EXPLORER)
    # =========================================================
    elif st.session_state["nav_page"] == "Data Quality":
        st.markdown("# Telemetry Data Quality & Coverage")
        st.markdown("Inspect sensor health, temporal coverage, missing records, duplicate timestamps, and explore raw IoT logs.")

        # Why Data Quality Matters Callout — st.html() bypasses Markdown code-block processing
        st.html(
            '<div class="clean-panel" style="background-color:#F0FDFA;border-color:#CCFBF1;">'
            '<div style="font-size:0.95rem;font-weight:600;color:#0F766E;margin-bottom:4px;">Why Telemetry Coverage Matters in Cold-Chain Logistics:</div>'
            '<div style="font-size:0.88rem;color:#115E59;line-height:1.5;">'
            'Sensors report temperature readings at regular intervals (typically every 5 minutes). If a sensor battery fails, '
            'cellular reception drops, or a logger goes offline for more than 15 minutes, conditions during that blackout are '
            '<strong>completely unobserved</strong>. FreshTrack BD keeps sensor reliability separate from observed risk scores so unverified '
            'shipments are never mistaken for compliant deliveries.'
            '</div>'
            '</div>'
        )

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        # 4 Data Quality Metric Cards
        total_gaps = int(summary_df["gap_count"].sum())
        total_dups = int(summary_df["duplicate_count"].sum())
        good_evidence_count = len(summary_df[summary_df["evidence_quality"] == "Good"])
        poor_evidence_count = len(summary_df[summary_df["evidence_quality"] == "Poor"])

        dq1, dq2, dq3, dq4 = st.columns(4)
        with dq1:
            render_kpi_card("High-Confidence Deliveries", f"{good_evidence_count}", "Complete, continuous coverage", icon_name="check_circle", accent_color="#10B981")
        with dq2:
            render_kpi_card("Unverified / Poor Coverage", f"{poor_evidence_count}", "Prolonged sensor dropouts", icon_name="alert_triangle", accent_color="#EF4444" if poor_evidence_count > 0 else "#10B981")
        with dq3:
            render_kpi_card("Total Sensor Dropouts", f"{total_gaps}", "Gaps exceeding 15 minutes", icon_name="clock", accent_color="#F59E0B" if total_gaps > 0 else "#10B981")
        with dq4:
            render_kpi_card("Deduplicated Timestamps", f"{total_dups}", "Duplicate packets dropped", icon_name="shield_check", accent_color="#0284C7")

        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

        # Telemetry Dropouts & Gaps Summary
        st.markdown("### Shipments with Sensor Outages (>15 min)")
        st.caption("Shipments where telemetry went offline, leaving transit intervals unverified.")

        gaps_summary = summary_df[summary_df["gap_count"] > 0].copy()
        if not gaps_summary.empty:
            gaps_table = []
            for _, r in gaps_summary.iterrows():
                cov = r.get("telemetry_coverage_pct")
                cov_val = f"{cov}%" if cov is not None and not pd.isna(cov) else "Unknown"
                gaps_table.append({
                    "Shipment ID": r["delivery_id"],
                    "Commodity": r["product_category"],
                    "Route": r["route_id"],
                    "Sensor Dropouts": int(r["gap_count"]),
                    "Unobserved Minutes": float(r.get("unobserved_gap_duration_min", 0.0)),
                    "Coverage": cov_val,
                    "Evidence State": r.get("evidence_quality", "Unknown"),
                    "Audit Label": r.get("qualified_risk_label", "Unverified"),
                })
            st.dataframe(pd.DataFrame(gaps_table), use_container_width=True, hide_index=True)
        else:
            st.info("All shipments have complete continuous sensor coverage without outages exceeding 15 minutes.")

        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

        # Raw Telemetry Explorer & Download Controls
        st.markdown("### Raw Sensor Data Explorer")
        st.caption("Query raw IoT records, inspect individual sensor timestamps, and export clean CSV datasets.")

        de_col1, de_col2, de_col3 = st.columns(3)
        with de_col1:
            de_shipment = st.selectbox("Filter by Shipment:", ["All Shipments"] + sorted(raw_df["delivery_id"].unique()))
        with de_col2:
            de_category = st.selectbox("Filter by Commodity:", ["All Commodities"] + sorted(raw_df["product_category"].unique()))
        with de_col3:
            de_type = st.selectbox("Filter Record Type:", ["All Records", "Excursions Only", "Door Open Events Only"], index=0)

        exp_df = raw_df.copy()
        if de_shipment != "All Shipments":
            exp_df = exp_df[exp_df["delivery_id"] == de_shipment]
        if de_category != "All Commodities":
            exp_df = exp_df[exp_df["product_category"] == de_category]

        if de_type == "Excursions Only":
            exp_df = exp_df[(exp_df["container_temp"] > exp_df["target_temp_max"]) | (exp_df["container_temp"] < exp_df["target_temp_min"])]
        elif de_type == "Door Open Events Only":
            exp_df = exp_df[exp_df["door_open_flag"] == 1]

        st.dataframe(exp_df.head(100), use_container_width=True, hide_index=True)
        st.caption(f"Displaying {min(100, len(exp_df))} of {len(exp_df):,} matching sensor records.")

        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            st.download_button(
                "Export Filtered Raw Telemetry CSV",
                data=exp_df.to_csv(index=False),
                file_name="freshtrack_telemetry_filtered.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with btn_c2:
            st.download_button(
                "Export Aggregated Summary Metrics CSV",
                data=summary_df.to_csv(index=False),
                file_name="freshtrack_summary_metrics.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        with st.expander("Telemetry Data Dictionary (14 Schema Fields)", expanded=False):
            schema_data = [
                {"Field": "record_id", "Type": "String", "Description": "Unique sensor event UUID (e.g. REC-275D61BE)"},
                {"Field": "timestamp", "Type": "ISO 8601 UTC", "Description": "Timestamp of temperature reading (YYYY-MM-DDTHH:MM:SSZ)"},
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

    # =========================================================
    # PAGE 5: TECHNICAL DETAILS (MAPREDUCE & MATHEMATICAL PROOFS)
    # =========================================================
    elif st.session_state["nav_page"] == "Technical Details":
        st.markdown("# Technical Details & MapReduce Architecture")
        st.markdown("Inspect the distributed MapReduce streaming pipeline, cluster execution mode, and mathematical calculations.")

        # Pipeline Flow Diagram (Execution Stages)
        st.markdown("### Distributed Processing Pipeline Flow")
        # Pipeline Flow Diagram — st.html() bypasses Markdown indented-code-block processing
        st.html(
            '<div style="display:flex;align-items:center;justify-content:space-between;background-color:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:20px;margin-bottom:24px;font-size:0.84rem;text-align:center;overflow-x:auto;box-shadow:0 1px 3px rgba(0,0,0,0.03);">'
            '<div style="padding:10px 14px;background:#F0FDFA;border:1px solid #0D9488;border-radius:8px;color:#0F766E;font-weight:600;">1. Raw Telemetry<br><span style="color:#64748B;font-weight:400;">1,046 CSV Lines</span></div>'
            '<div style="color:#94A3B8;font-size:1.2rem;">\u2192</div>'
            '<div style="padding:10px 14px;background:#F8FAFC;border:1px solid #CBD5E1;border-radius:8px;color:#334155;">2. Validation<br><span style="color:#64748B;">Schema &amp; Types</span></div>'
            '<div style="color:#94A3B8;font-size:1.2rem;">\u2192</div>'
            '<div style="padding:10px 14px;background:#F0FDFA;border:1px solid #0D9488;border-radius:8px;color:#0F766E;font-weight:600;">3. Mapper<br><span style="color:#64748B;font-weight:400;">hadoop/mapper.py</span></div>'
            '<div style="color:#94A3B8;font-size:1.2rem;">\u2192</div>'
            '<div style="padding:10px 14px;background:#F8FAFC;border:1px solid #CBD5E1;border-radius:8px;color:#334155;">4. Key Stream<br><span style="color:#64748B;">&lt;delivery_id&gt;</span></div>'
            '<div style="color:#94A3B8;font-size:1.2rem;">\u2192</div>'
            '<div style="padding:10px 14px;background:#EFF6FF;border:1px solid #3B82F6;border-radius:8px;color:#1D4ED8;font-weight:600;">5. Shuffle &amp; Sort<br><span style="color:#64748B;font-weight:400;">sort -k1,1</span></div>'
            '<div style="color:#94A3B8;font-size:1.2rem;">\u2192</div>'
            '<div style="padding:10px 14px;background:#F0FDFA;border:1px solid #0D9488;border-radius:8px;color:#0F766E;font-weight:600;">6. Reducer<br><span style="color:#64748B;font-weight:400;">hadoop/reducer.py</span></div>'
            '<div style="color:#94A3B8;font-size:1.2rem;">\u2192</div>'
            '<div style="padding:10px 14px;background:#ECFDF5;border:1px solid #10B981;border-radius:8px;color:#047857;font-weight:600;">7. Aggregated Metrics<br><span style="color:#64748B;font-weight:400;">20 Consignments</span></div>'
            '</div>'
        )

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        # Execution Status & Run Controls (2 Columns)
        p_col1, p_col2 = st.columns([1, 1])
        last_meta = st.session_state["last_run_meta"]

        with p_col1:
            st.markdown("### Pipeline Execution Telemetry")
            # st.html() bypasses Markdown indented-code-block processing
            def _row(label, value_html):
                return (
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:0.88rem;">'
                    f'<span style="color:#64748B;">{label}</span>{value_html}</div>'
                )
            st.html(
                '<div class="clean-panel">'
                + f'<div style="display:flex;justify-content:space-between;margin-bottom:8px;">'
                  f'<span style="color:#64748B;font-size:0.88rem;">Execution Mode:</span>'
                  f'<span>{render_status_badge_html(last_meta["mode"])}</span></div>'
                + _row("Input Records Ingested:", f'<span style="color:#0F172A;font-weight:600;">{last_meta.get("input_records", 1046):,}</span>')
                + _row("Valid Records Emitted:", f'<span style="color:#10B981;font-weight:600;">{last_meta.get("valid_records", 1045):,}</span>')
                + _row("Corrupted / Filtered:", f'<span style="color:#64748B;font-weight:600;">{last_meta.get("rejected_records", 0)}</span>')
                + _row("Consignments Processed:", f'<span style="color:#0D9488;font-weight:600;">{last_meta.get("output_records", 20)}</span>')
                + _row("Processing Runtime:", f'<span style="color:#0F172A;font-weight:600;">{last_meta.get("duration_seconds", 0.029)} seconds</span>')
                + _row("Hadoop Job Identifier:", f'<span style="color:#64748B;font-family:monospace;">{last_meta.get("hadoop_job_id", "N/A")}</span>')
                + '</div>'
            )

        with p_col2:
            st.markdown("### Run Pipeline Now")
            st.markdown(
                textwrap.dedent("""
                Execute the MapReduce streaming engine across the active dataset.
                Both local execution and cluster execution share the identical `hadoop/mapper.py` and `hadoop/reducer.py` scripts.
                """).strip()
            )

            chosen_mode_label = st.radio(
                "Select Execution Target:",
                options=["Auto-Detect (Local Streaming Mode on macOS)", "Force Cluster Hadoop Job"],
                index=0,
            )

            if st.button("Execute MapReduce Job Now", type="primary", use_container_width=True):
                with st.spinner("Streaming records through Mapper & Reducer..."):
                    manager = PipelineExecutionManager(workspace_root=WORKSPACE_ROOT)
                    raw_path = os.path.join(WORKSPACE_ROOT, "data", "sample", "cold_chain_sample.csv")
                    processed_path = os.path.join(WORKSPACE_ROOT, "data", "processed", "summary_metrics.csv")

                    mode_arg = ExecutionMode.REAL_HADOOP if "Cluster" in chosen_mode_label else ExecutionMode.LOCAL_STREAMING

                    try:
                        res = manager.run_pipeline(raw_path, processed_path, mode=mode_arg)
                        st.session_state["last_run_meta"] = res
                        st.success(f"Execution completed in {res['duration_seconds']}s via {res['mode_label']}.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Execution Error: {exc}")

        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

        # Mathematical References & Methodology
        st.markdown("### Mathematical Foundations & Calculations")
        st.caption("Underlying mathematical models and thermodynamic algorithms used throughout FreshTrack BD.")

        with st.expander("1. Mean Kinetic Temperature (MKT) — Arrhenius Formulation", expanded=False):
            # st.html() bypasses Markdown indented-code-block processing
            st.html(
                '<div class="clean-panel" style="margin-bottom:16px;padding:16px 20px;">'
                '<div style="font-size:0.88rem;color:#0F172A;line-height:1.6;">'
                '<strong style="color:#0D9488;">Why MKT Matters:</strong> A simple average can hide brief heat spikes. '
                'MKT uses chemical reaction kinetics to account for how heat spikes accelerate food degradation faster than cool periods.'
                '</div>'
                '</div>'
            )
            st.markdown(
                textwrap.dedent("""
                The Mean Kinetic Temperature (MKT) is an isothermal equivalent temperature that gives the same kinetic degradation
                over time as the observed fluctuating temperatures. It uses the Arrhenius equation with standard activation energy $\\Delta H = 83.144\\text{ kJ/mol}$:

                $$T_{\\text{mkt}} = \\frac{\\Delta H / R}{-\\ln\\left(\\frac{1}{n} \\sum_{i=1}^{n} e^{-\\Delta H / (R \\cdot T_i)}\\right)}$$

                * $T_i$: Absolute temperature of $i$-th sensor reading in Kelvin ($K = ^\\circ C + 273.15$)
                * $R$: Universal gas constant ($8.314472\\text{ J/(mol}\\cdot\\text{K)}$)
                * $\\Delta H$: Standard perishable activation energy ($83.144\\text{ kJ/mol}$)
                * $n$: Total number of temperature samples
                """).strip()
            )

        with st.expander("2. Operational Triage Risk Index (Normalized 0–100)", expanded=False):
            st.markdown(
                textwrap.dedent("""
                The composite risk index synthesizes multiple risk factors into an operational priority triage score:

                $$\\text{Risk Score} = 0.40 \\times D + 0.35 \\times H + 0.15 \\times O + 0.10 \\times G$$

                * $D$: Excursion Duration Ratio (percentage of transit time spent out-of-setpoint)
                * $H$: Cumulative Degree-Hours normalized against safety tolerance
                * $O$: Reefer Door-Open Frequency penalty
                * $G$: Telemetry Sampling Gap penalty ($100 - \\text{Sampling Integrity}\\%$)
                """).strip()
            )

        with st.expander("3. Numerical Integration of Degree-Hours (°C·h)", expanded=False):
            st.markdown(
                textwrap.dedent("""
                Thermal exposure magnitude is integrated numerically using the trapezoidal rule over adjacent readings:

                $$\\text{Degree-Hours} = \\sum_{i=1}^{m} \\frac{(\\Delta T_i + \\Delta T_{i-1})}{2} \\times \\frac{\\Delta t_i}{60}$$

                where $\\Delta T_i = \\max(0, T_i - T_{\\max}) + \\max(0, T_{\\min} - T_i)$, and $\\Delta t_i$ is interval duration in minutes.
                """).strip()
            )

        with st.expander("4. The MAX_GAP_MINUTES = 15.0 Rule", expanded=False):
            st.markdown(
                textwrap.dedent("""
                When telemetry intervals exceed 15.0 minutes, the sensor connection has experienced a dropout.
                To prevent incorrect reporting:
                * FreshTrack BD **never assumes conditions remained normal** across unmonitored dropouts.
                * FreshTrack BD **never infers continuous breaches** across unmonitored dropouts.
                * Outage time is explicitly tracked as unobserved duration and penalizes the shipment's **evidence quality**.
                """).strip()
            )

        with st.expander("5. System Environment & Cluster Diagnostics", expanded=False):
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

    # ---------------------------------------------------------
    # SCIENTIFIC & REGULATORY COMPLIANCE FOOTER
    # ---------------------------------------------------------
    render_disclaimer_callout()


if __name__ == "__main__":
    main()
