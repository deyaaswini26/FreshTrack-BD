"""
FreshTrack BD — Industrial Dark Theme & Design System
Strict enterprise industrial palette:
- Main Background: #0B1220
- Sidebar Background: #101A2B
- Primary Surface: #151F30
- Secondary Surface: #1B293B
- Primary Text: #F1F5F9
- Secondary Text: #94A3B8
- Borders & Dividers: #2A394D
- Accent Teal: #2DD4BF
- Status Colors: Green (#4ADE80), Amber (#FBBF24), Orange (#FB923C), Red (#F87171), Blue (#60A5FA)
"""

INDUSTRIAL_THEME_CSS = """
<style>
/* Import Inter Font & Material Symbols */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

/* Global Reset & Base Styling */
html, body, .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    background-color: #0B1220 !important;
    color: #F1F5F9 !important;
}

/* Preserve Material Icons and Symbols */
[data-testid="stIconMaterial"],
span[data-testid="stIconMaterial"],
[data-testid="stExpanderToggleIcon"],
[data-testid="stExpanderToggleIcon"] *,
i.material-icons,
.material-icons,
.material-symbols-rounded,
.material-symbols-outlined,
button[data-testid*="stSidebarCollapseButton"] span,
button[data-testid="baseButton-headerNoPadding"] span {
    font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
}

/* Sidebar Styling */
button[data-testid="stSidebarCollapseButton"] {
    display: none !important;
}

section[data-testid="stSidebar"] {
    background-color: #101A2B !important;
    border-right: 1px solid #2A394D !important;
}

section[data-testid="stSidebar"] > div {
    padding-top: 1.5rem !important;
    padding-left: 1.25rem !important;
    padding-right: 1.25rem !important;
}

/* Global Content Container Margins */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1440px !important;
}

/* Enterprise Header Bar */
.global-header-bar {
    background-color: #151F30;
    border: 1px solid #2A394D;
    border-radius: 6px;
    padding: 12px 18px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.header-breadcrumb {
    font-size: 0.85rem;
    font-weight: 500;
    color: #94A3B8;
    display: flex;
    align-items: center;
    gap: 8px;
}

.header-breadcrumb .active-crumb {
    color: #F1F5F9;
    font-weight: 600;
}

/* Compact Industrial KPI Metric Cards */
.kpi-card {
    background-color: #151F30;
    border: 1px solid #2A394D;
    border-radius: 6px;
    padding: 14px 16px;
    min-height: 104px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    transition: border-color 0.15s ease;
}

.kpi-card:hover {
    border-color: #3B5373;
}

.kpi-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}

.kpi-title {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94A3B8;
}

.kpi-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 4px;
    background: rgba(45, 212, 191, 0.08);
}

.kpi-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: #F1F5F9;
    line-height: 1.1;
    margin: 4px 0;
}

.kpi-caption {
    font-size: 0.74rem;
    color: #94A3B8;
    line-height: 1.3;
}

/* Industrial Status Badges */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    padding: 3px 10px;
    border-radius: 4px;
    text-transform: uppercase;
}

.badge-real-hadoop {
    background-color: rgba(74, 222, 128, 0.12);
    color: #4ADE80;
    border: 1px solid #4ADE80;
}

.badge-local-streaming {
    background-color: rgba(251, 191, 36, 0.12);
    color: #FBBF24;
    border: 1px solid #FBBF24;
}

.badge-sample-output {
    background-color: rgba(96, 165, 250, 0.12);
    color: #60A5FA;
    border: 1px solid #60A5FA;
}

.badge-error {
    background-color: rgba(248, 113, 113, 0.12);
    color: #F87171;
    border: 1px solid #F87171;
}

/* Surface Containers & Panels */
.industrial-panel {
    background-color: #151F30;
    border: 1px solid #2A394D;
    border-radius: 6px;
    padding: 18px 20px;
    margin-bottom: 20px;
}

.panel-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #F1F5F9;
    margin-bottom: 4px;
}

.panel-subtitle {
    font-size: 0.8rem;
    color: #94A3B8;
    margin-bottom: 14px;
}

/* Operational Alert Items */
.alert-card {
    background-color: #1B293B;
    border: 1px solid #2A394D;
    border-left-width: 4px;
    border-radius: 4px;
    padding: 12px 16px;
    margin-bottom: 10px;
}

.alert-critical {
    border-left-color: #F87171;
}

.alert-warning {
    border-left-color: #FBBF24;
}

.alert-info {
    border-left-color: #60A5FA;
}

.alert-title {
    font-size: 0.86rem;
    font-weight: 600;
    color: #F1F5F9;
    margin-bottom: 4px;
}

.alert-evidence {
    font-size: 0.78rem;
    color: #94A3B8;
    margin-bottom: 4px;
    line-height: 1.4;
}

.alert-rec {
    font-size: 0.74rem;
    color: #2DD4BF;
    font-style: italic;
}

/* Regulatory Disclaimer Notice */
.disclaimer-container {
    background-color: #101A2B;
    border: 1px solid #2A394D;
    border-radius: 6px;
    padding: 12px 18px;
    font-size: 0.76rem;
    color: #94A3B8;
    line-height: 1.4;
    margin-top: 24px;
}

/* Streamlit Native Overrides for Industrial Precision */
div[data-testid="stHorizontalBlock"] {
    gap: 12px !important;
}

/* Buttons */
button[kind="primary"] {
    background-color: #2DD4BF !important;
    color: #0B1220 !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 4px !important;
}

button[kind="primary"]:hover {
    background-color: #14B8A6 !important;
}

button[kind="secondary"] {
    background-color: #1B293B !important;
    color: #F1F5F9 !important;
    border: 1px solid #2A394D !important;
    border-radius: 4px !important;
}

button[kind="secondary"]:hover {
    border-color: #2DD4BF !important;
    color: #2DD4BF !important;
}

/* Dataframe & Tables */
div[data-testid="stDataFrame"] {
    border: 1px solid #2A394D !important;
    border-radius: 6px !important;
    overflow: hidden;
}

/* Native Metrics Styling */
div[data-testid="stMetric"] {
    background-color: #151F30 !important;
    border: 1px solid #2A394D !important;
    border-radius: 6px !important;
    padding: 10px 14px !important;
}

div[data-testid="stMetricLabel"] {
    font-size: 0.76rem !important;
    color: #94A3B8 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
}

div[data-testid="stMetricValue"] {
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    color: #F1F5F9 !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

/* Tabs */
button[data-baseweb="tab"] {
    color: #94A3B8 !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    padding: 10px 16px !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #2DD4BF !important;
    border-bottom-color: #2DD4BF !important;
}
</style>
"""

DARK_THEME_CSS = INDUSTRIAL_THEME_CSS
