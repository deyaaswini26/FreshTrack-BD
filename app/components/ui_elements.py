"""
FreshTrack BD — Enterprise UI Components & Layouts
Renders clean line SVG icons (no emojis), global headers, compact KPI cards,
operational alert banners, and standard Plotly industrial themes.
"""

from typing import Any, Dict, Optional
import streamlit as st

# Clean Line SVG Icons (Stroke-based, industrial look)
SVG_ICONS = {
    "snowflake": """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2DD4BF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="22"></line><line x1="2" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line><line x1="19.07" y1="4.93" x2="4.93" y2="19.07"></line></svg>""",
    "thermometer": """<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2DD4BF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"></path></svg>""",
    "check_circle": """<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#4ADE80" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>""",
    "alert_triangle": """<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#F87171" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>""",
    "clock": """<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#FBBF24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>""",
    "activity": """<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>""",
    "truck": """<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2DD4BF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="3" width="15" height="13"></rect><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon><circle cx="5.5" cy="18.5" r="2.5"></circle><circle cx="18.5" cy="18.5" r="2.5"></circle></svg>""",
    "server": """<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2DD4BF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>""",
    "database": """<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2DD4BF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>""",
}


def render_status_badge_html(mode: str) -> str:
    """Returns HTML for execution mode badge."""
    mode_upper = mode.upper()
    if "REAL_HADOOP" in mode_upper:
        return '<span class="status-badge badge-real-hadoop">● REAL_HADOOP</span>'
    elif "LOCAL_STREAMING" in mode_upper:
        return '<span class="status-badge badge-local-streaming">● LOCAL_STREAMING</span>'
    elif "SAMPLE" in mode_upper:
        return '<span class="status-badge badge-sample-output">● SAMPLE_OUTPUT</span>'
    else:
        return f'<span class="status-badge badge-error">● {mode}</span>'


def render_global_header(
    page_name: str,
    dataset_name: str = "cold_chain_sample.csv",
    last_run_meta: Optional[Dict[str, Any]] = None,
):
    """Renders persistent enterprise header with breadcrumbs, execution badge, and metadata."""
    active_mode = last_run_meta.get("mode", "LOCAL_STREAMING") if last_run_meta else "LOCAL_STREAMING"
    badge_html = render_status_badge_html(active_mode)

    timestamp_str = ""
    if last_run_meta and "finish_time_iso" in last_run_meta:
        timestamp_str = f"Last Processed: {last_run_meta['finish_time_iso']}"
    elif last_run_meta and "timestamp" in last_run_meta:
        timestamp_str = f"Last Processed: {last_run_meta['timestamp']}"
    else:
        timestamp_str = "Last Processed: Precomputed Sample"

    latency_str = ""
    if last_run_meta and "duration_seconds" in last_run_meta:
        latency_str = f" • Latency: {last_run_meta['duration_seconds']}s"

    html = f"""
    <div class="global-header-bar">
        <div>
            <div class="header-breadcrumb">
                <span>FreshTrack BD</span>
                <span style="color: #475569;">/</span>
                <span class="active-crumb">{page_name}</span>
            </div>
            <div style="font-size: 0.74rem; color: #64748B; margin-top: 3px;">
                Dataset: <span style="color: #94A3B8;">{dataset_name}</span> (SYNTHETIC) • {timestamp_str}{latency_str}
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
            {badge_html}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_kpi_card(
    title: str,
    value: str,
    caption: str = "",
    icon_name: str = "activity",
    accent_color: str = "#2A394D",
):
    """Renders a compact, industrial metric card."""
    svg_icon = SVG_ICONS.get(icon_name, SVG_ICONS["activity"])
    html = f"""
    <div class="kpi-card" style="border-top: 2px solid {accent_color};">
        <div class="kpi-header">
            <span class="kpi-title">{title}</span>
            <span class="kpi-icon">{svg_icon}</span>
        </div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-caption">{caption}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_alert_item(severity: str, title: str, evidence: str, recommendation: str):
    """Renders a single data-driven operational alert card."""
    sev_class = "alert-info"
    if severity == "CRITICAL":
        sev_class = "alert-critical"
    elif severity == "WARNING":
        sev_class = "alert-warning"

    html = f"""
    <div class="alert-card {sev_class}">
        <div class="alert-title">[{severity}] {title}</div>
        <div class="alert-evidence">{evidence}</div>
        <div class="alert-rec">Action: {recommendation}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_disclaimer_callout():
    """Renders academic & regulatory compliance disclaimer."""
    html = """
    <div class="disclaimer-container">
        <span style="color: #FBBF24; font-weight: 600;">Regulatory Scope & Methodology Notice (USP &lt;1079&gt; / FDA Guidelines):</span>
        FreshTrack BD analyzes physical time-temperature compliance and cumulative thermal exposure (°C·h)
        against specified setpoints. These metrics assess operational cold-chain integrity. They do not constitute
        biological assays or direct microbial food spoilage predictions, which require direct laboratory validation.
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def get_industrial_plotly_layout(
    height: Optional[int] = None,
    legend: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Returns standardized dark industrial Plotly layout dictionary."""
    base_legend = {
        "font": {"size": 11, "color": "#F1F5F9"},
        "bgcolor": "rgba(21, 31, 48, 0.8)",
        "bordercolor": "#2A394D",
        "borderwidth": 1,
    }
    if legend:
        base_legend.update(legend)

    layout = {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(21, 31, 48, 0.6)",
        "font": {"family": "Inter, sans-serif", "color": "#94A3B8", "size": 12},
        "xaxis": {
            "gridcolor": "#2A394D",
            "zerolinecolor": "#2A394D",
            "tickfont": {"size": 11, "color": "#94A3B8"},
            "title_font": {"size": 12, "color": "#F1F5F9"},
        },
        "yaxis": {
            "gridcolor": "#2A394D",
            "zerolinecolor": "#2A394D",
            "tickfont": {"size": 11, "color": "#94A3B8"},
            "title_font": {"size": 12, "color": "#F1F5F9"},
        },
        "legend": base_legend,
        "margin": {"l": 40, "r": 20, "t": 35, "b": 35},
        "hoverlabel": {
            "bgcolor": "#1B293B",
            "bordercolor": "#2DD4BF",
            "font": {"family": "Inter, sans-serif", "size": 12, "color": "#F1F5F9"},
        },
    }
    if height:
        layout["height"] = height
    return layout
