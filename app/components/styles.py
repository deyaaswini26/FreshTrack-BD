"""
FreshTrack BD — Clean, Modern, Spacious Light Theme & Design System
Palette:
- Background: #F8FAFC (Slate 50)
- Surface / Cards: #FFFFFF
- Subtle Borders: #E2E8F0 (Slate 200)
- Primary Text: #0F172A (Slate 900)
- Secondary Text: #475569 (Slate 600)
- Muted Text: #64748B (Slate 500)
- Primary Accent: #0D9488 (Teal 600)
- Accent Tint: #F0FDFA (Teal 50)
- Accent Hover: #0F766E (Teal 700)
- Status Colors:
  * Good / Compliant: #166534 on #DCFCE7 (border #BBF7D0)
  * Warning / Limited: #92400E on #FEF3C7 (border #FDE68A)
  * Alert / Poor / High: #991B1B on #FEE2E2 (border #FECACA)
  * Info / Unknown: #334155 on #F1F5F9 (border #CBD5E1)
"""

CLEAN_LIGHT_THEME_CSS = """
<style>
/* Import Inter Font & Material Symbols */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

/* Global Reset & Base Typography */
html, body, .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    background-color: #F8FAFC !important;
    color: #0F172A !important;
    -webkit-font-smoothing: antialiased;
}

/* Material Icons Safety */
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
    background-color: #FFFFFF !important;
    border-right: 1px solid #E2E8F0 !important;
}

section[data-testid="stSidebar"] > div {
    padding-top: 2rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
}

/* Sidebar Radio Navigation Styling */
section[data-testid="stSidebar"] .stRadio label {
    font-size: 0.92rem !important;
    font-weight: 500 !important;
    color: #475569 !important;
    padding: 6px 10px !important;
    border-radius: 8px !important;
    transition: all 0.15s ease !important;
}

section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover {
    background-color: #F1F5F9 !important;
    color: #0F172A !important;
}

/* Global Content Container */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 3.5rem !important;
    padding-left: 2.5rem !important;
    padding-right: 2.5rem !important;
    max-width: 1320px !important;
}

/* Clean Header Bar */
.global-header-bar {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 16px 24px;
    margin-bottom: 28px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.header-breadcrumb {
    font-size: 0.95rem;
    font-weight: 500;
    color: #64748B;
    display: flex;
    align-items: center;
    gap: 8px;
}

.header-breadcrumb .active-crumb {
    color: #0F172A;
    font-weight: 600;
}

/* Spacious, Restrained KPI Metric Cards */
.kpi-card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 20px 22px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    transition: box-shadow 0.2s ease, border-color 0.2s ease;
}

.kpi-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
    border-color: #CBD5E1;
}

.kpi-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.kpi-title {
    font-size: 0.84rem;
    font-weight: 600;
    color: #475569;
    letter-spacing: -0.01em;
}

.kpi-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 6px;
    background: #F0FDFA;
}

.kpi-value {
    font-size: 2rem;
    font-weight: 700;
    color: #0F172A;
    line-height: 1.2;
    margin: 6px 0;
    letter-spacing: -0.02em;
}

.kpi-caption {
    font-size: 0.82rem;
    color: #64748B;
    line-height: 1.4;
}

/* Status Badges */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 9999px;
    letter-spacing: 0.02em;
}

.badge-real-hadoop {
    background-color: #DCFCE7;
    color: #166534;
    border: 1px solid #BBF7D0;
}

.badge-local-streaming {
    background-color: #FEF3C7;
    color: #92400E;
    border: 1px solid #FDE68A;
}

.badge-sample-output {
    background-color: #E0F2FE;
    color: #0369A1;
    border: 1px solid #BAE6FD;
}

.badge-error {
    background-color: #FEE2E2;
    color: #991B1B;
    border: 1px solid #FECACA;
}

/* White Surface Containers & Panels */
.clean-panel {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.panel-title {
    font-size: 1.15rem;
    font-weight: 600;
    color: #0F172A;
    margin-bottom: 4px;
    letter-spacing: -0.01em;
}

.panel-subtitle {
    font-size: 0.88rem;
    color: #64748B;
    margin-bottom: 18px;
    line-height: 1.5;
}

/* Operational Alert Items */
.alert-card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-left-width: 4px;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 14px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.alert-critical {
    border-left-color: #EF4444;
    background-color: #FEF2F2;
}

.alert-warning {
    border-left-color: #F59E0B;
    background-color: #FFFBEB;
}

.alert-info {
    border-left-color: #0284C7;
    background-color: #F0F9FF;
}

.alert-title {
    font-size: 0.94rem;
    font-weight: 600;
    color: #0F172A;
    margin-bottom: 6px;
}

.alert-evidence {
    font-size: 0.85rem;
    color: #475569;
    margin-bottom: 6px;
    line-height: 1.5;
}

.alert-rec {
    font-size: 0.84rem;
    color: #0D9488;
    font-weight: 500;
}

/* Methodology Callout */
.disclaimer-container {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 16px 20px;
    font-size: 0.84rem;
    color: #64748B;
    line-height: 1.5;
    margin-top: 28px;
}

/* Streamlit Native Element Overrides */
div[data-testid="stHorizontalBlock"] {
    gap: 18px !important;
}

/* Buttons */
button[kind="primary"] {
    background-color: #0D9488 !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.5rem 1.25rem !important;
    transition: background-color 0.15s ease !important;
}

button[kind="primary"]:hover {
    background-color: #0F766E !important;
}

button[kind="secondary"] {
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 8px !important;
    padding: 0.5rem 1.25rem !important;
    font-weight: 500 !important;
}

button[kind="secondary"]:hover {
    border-color: #0D9488 !important;
    color: #0D9488 !important;
    background-color: #F0FDFA !important;
}

/* Dataframe & Tables */
div[data-testid="stDataFrame"] {
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    background-color: #FFFFFF !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

/* Native Metrics Styling */
div[data-testid="stMetric"] {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
}

div[data-testid="stMetricLabel"] {
    font-size: 0.84rem !important;
    color: #64748B !important;
    font-weight: 500 !important;
}

div[data-testid="stMetricValue"] {
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    color: #0F172A !important;
}

/* Tabs */
button[data-baseweb="tab"] {
    color: #64748B !important;
    font-weight: 500 !important;
    font-size: 0.94rem !important;
    padding: 10px 18px !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #0D9488 !important;
    border-bottom-color: #0D9488 !important;
    font-weight: 600 !important;
}

/* Expander */
div[data-testid="stExpander"] {
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    background-color: #FFFFFF !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}
</style>
"""

# Backwards compatibility alias
INDUSTRIAL_THEME_CSS = CLEAN_LIGHT_THEME_CSS
DARK_THEME_CSS = CLEAN_LIGHT_THEME_CSS
