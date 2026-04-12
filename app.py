"""
app.py — Project 2: Semiconductor Physical Risk Atlas
======================================================
Streamlit dashboard visualizing physical climate risk for semiconductor
facilities. Reads from facilities_scored.csv and company_scores.csv
(outputs of scoring.py).

Run:
    streamlit run app.py
"""

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Semiconductor Physical Risk Atlas",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

/* Dark analytical theme */
.stApp {
    background-color: #0a0e1a;
    color: #c8d0e0;
}

[data-testid="stSidebar"] {
    background-color: #0d1220;
    border-right: 1px solid #1e2640;
}

/* Metric cards */
[data-testid="stMetric"] {
    background-color: #111827;
    border: 1px solid #1e2d4a;
    border-radius: 4px;
    padding: 12px 16px;
}

[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.4rem !important;
    color: #e2e8f0;
}

[data-testid="stMetricLabel"] {
    font-size: 0.7rem !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748b;
}

[data-testid="stMetricLabel"] p {
    font-size: 0.6rem !important;
    white-space: nowrap !important;
}

/* Headers */
h1, h2, h3 {
    font-family: 'IBM Plex Sans', sans-serif;
    font-weight: 600;
    color: #e2e8f0;
    letter-spacing: -0.02em;
}

/* Risk badges */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 3px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    font-weight: 500;
    letter-spacing: 0.04em;
}
.badge-eh  { background: #450a0a; color: #fca5a5; border: 1px solid #7f1d1d; }
.badge-h   { background: #431407; color: #fdba74; border: 1px solid #7c2d12; }
.badge-mh  { background: #422006; color: #fcd34d; border: 1px solid #78350f; }
.badge-m   { background: #1e3a5f; color: #93c5fd; border: 1px solid #1e40af; }
.badge-lm  { background: #14532d; color: #86efac; border: 1px solid #166534; }
.badge-l   { background: #1a2e1a; color: #6ee7b7; border: 1px solid #065f46; }

/* Section divider */
.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #334155;
    border-bottom: 1px solid #1e2640;
    padding-bottom: 6px;
    margin-bottom: 16px;
    margin-top: 24px;
}

/* Data source note */
.source-note {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: #334155;
    margin-top: 4px;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid #1e2640;
}
</style>
""", unsafe_allow_html=True)


# ── Data loading ──────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@st.cache_data
def load_data():
    fac_path  = os.path.join(BASE_DIR, "facilities_scored.csv")
    comp_path = os.path.join(BASE_DIR, "company_scores.csv")

    if not os.path.exists(fac_path) or not os.path.exists(comp_path):
        st.error("❌ Run `python3 scoring.py` first to generate scored data files.")
        st.stop()

    fac  = pd.read_csv(fac_path)
    comp = pd.read_csv(comp_path)
    return fac, comp

fac, comp = load_data()

# ── Color mapping ─────────────────────────────────────────────────────────────
RISK_COLORS = {
    "Extremely High": "#ef4444",
    "High":           "#f97316",
    "Medium-High":    "#eab308",
    "Medium":         "#3b82f6",
    "Low-Medium":     "#22c55e",
    "Low":            "#6ee7b7",
}

COMPANY_COLORS = {
    "TSMC":    "#38bdf8",
    "ASML":    "#a78bfa",
    "Samsung": "#34d399",
    "Intel":   "#fb923c",
}

def risk_badge(label: str) -> str:
    cls = {
        "Extremely High": "badge-eh",
        "High":           "badge-h",
        "Medium-High":    "badge-mh",
        "Medium":         "badge-m",
        "Low-Medium":     "badge-lm",
        "Low":            "badge-l",
    }.get(label, "badge-m")
    return f"<span class='badge {cls}'>{label}</span>"


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🌊 Physical Risk Atlas")
    st.markdown("<p class='source-note'>IFRS S2 Physical Risk · WRI Aqueduct 4.0</p>",
                unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("**Filter by company**")
    companies = ["All"] + sorted(fac["company"].unique().tolist())
    selected_company = st.selectbox("", companies, label_visibility="collapsed")

    st.markdown("**Filter by risk level**")
    risk_levels = ["All"] + list(RISK_COLORS.keys())
    selected_risk = st.selectbox("", risk_levels, label_visibility="collapsed", key="risk_filter")

    st.markdown("---")
    st.markdown("""
<p class='source-note'>
DATA SOURCES<br><br>
WRI Aqueduct 4.0 (Jul 2023)<br>
TSMC ESG Report 2024<br>
ASML Annual Report 2023<br>
Samsung Semiconductor 2023<br>
Intel Annual Report 2023<br><br>
FRAMEWORK<br><br>
IFRS S2 Physical Risk Disclosure<br>
WRI disruption probability calibration<br>
Revenue weights: company filings +<br>
analyst consensus estimates<br><br>
Taiwan scores: TSMC self-reported<br>
WRI methodology assessment.<br>
Treated as lower-bound estimates.
</p>
""", unsafe_allow_html=True)


# ── Filter data ───────────────────────────────────────────────────────────────
fac_filtered = fac.copy()
if selected_company != "All":
    fac_filtered = fac_filtered[fac_filtered["company"] == selected_company]
if selected_risk != "All":
    fac_filtered = fac_filtered[fac_filtered["risk_label"] == selected_risk]


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## Semiconductor Physical Risk Atlas")
st.markdown(
    "Water stress and flood risk exposure for 13 critical semiconductor facilities · "
    "WRI Aqueduct 4.0 · IFRS S2 aligned"
)
st.markdown("<div class='section-label'>Portfolio Summary</div>", unsafe_allow_html=True)

# ── Top-line metrics ──────────────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Facilities Assessed", f"{len(fac)}")
m2.metric("Total Annual RaR", f"${fac['annual_rar_m'].sum():.0f}M",
          help="Revenue at risk from water supply disruption across all facilities")
m3.metric("High+ Risk Facilities",
          f"{len(fac[fac['risk_label'].isin(['High','Extremely High'])])}",
          help="Facilities scoring High or Extremely High on composite BWS+RFR score")
m4.metric("Highest-Risk Company", comp.iloc[0]["company"],
          help="L2 revenue-weighted composite score")
m5.metric("Highest-Risk Facility",
          fac.loc[fac["composite_score_l1"].idxmax(), "facility_name"].split("(")[0].strip())


# ══════════════════════════════════════════════════════════════════════════════
# MAP
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div class='section-label'>Geographic Exposure</div>", unsafe_allow_html=True)

map_fig = px.scatter_mapbox(
    fac_filtered,
    lat="lat", lon="lon",
    color="risk_label",
    size="composite_score_l1",
    size_max=28,
    hover_name="facility_name",
    hover_data={
        "company": True,
        "bws_score": ":.2f",
        "rfr_score": ":.2f",
        "composite_score_l1": ":.1f",
        "annual_rar_m": ":.1f",
        "risk_label": True,
        "lat": False,
        "lon": False,
    },
    color_discrete_map=RISK_COLORS,
    mapbox_style="open-street-map",
    zoom=0.8,
    center={"lat": 25, "lon": -10},
    labels={
        "risk_label": "Risk Level",
        "composite_score_l1": "Risk Score",
        "bws_score": "Water Stress",
        "rfr_score": "Flood Risk",
        "annual_rar_m": "Annual RaR ($M)",
        "company": "Company",
    },
)
map_fig.update_layout(
    height=480,
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    paper_bgcolor="#0a0e1a",
    plot_bgcolor="#0a0e1a",
    legend=dict(
        bgcolor="#111827",
        bordercolor="#1e2640",
        borderwidth=1,
        font=dict(color="#c8d0e0", size=11),
    ),
)
st.plotly_chart(map_fig, use_container_width=True)
st.markdown("<p class='source-note'>Bubble size proportional to composite risk score · Hover for details</p>",
            unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# FACILITY TABLE + COMPANY ROLLUP
# ══════════════════════════════════════════════════════════════════════════════
col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown("<div class='section-label'>Facility Risk Scores</div>", unsafe_allow_html=True)

    display = fac_filtered[[
        "company", "facility_name", "city", "gid_0",
        "bws_score", "rfr_score", "composite_score_l1", "risk_label", "annual_rar_m"
    ]].sort_values("composite_score_l1", ascending=False).copy()

    display.columns = ["Company", "Facility", "City", "ISO3",
                       "BWS", "RFR", "Score", "Risk Label", "RaR $M"]
    display["BWS"]   = display["BWS"].round(2)
    display["RFR"]   = display["RFR"].round(2)
    display["Score"] = display["Score"].round(1)
    display["RaR $M"] = display["RaR $M"].round(1)

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score /100", min_value=0, max_value=100, format="%.1f"
            ),
            "RaR $M": st.column_config.NumberColumn("RaR $M", format="$%.1f"),
        }
    )
    st.markdown(
        "<p class='source-note'>BWS = Baseline Water Stress · RFR = Riverine Flood Risk · "
        "Score = 70% BWS + 30% RFR, normalized 0–100 · "
        "RaR = WRI disruption probability × 14-day event × daily facility revenue</p>",
        unsafe_allow_html=True
    )

with col_right:
    st.markdown("<div class='section-label'>Company Rollup (L2 Weighted)</div>",
                unsafe_allow_html=True)

    for _, row in comp.iterrows():
        color = COMPANY_COLORS.get(row["company"], "#94a3b8")
        badge = risk_badge(row["risk_label_l2"])
        st.markdown(f"""
<div style='background:#111827; border:1px solid #1e2640; border-left: 3px solid {color};
     border-radius:4px; padding:12px 16px; margin-bottom:8px;'>
  <div style='display:flex; justify-content:space-between; align-items:center;'>
    <span style='font-weight:600; color:{color}; font-size:0.95rem;'>{row["company"]}</span>
    {badge}
  </div>
  <div style='display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-top:10px;'>
    <div>
      <div style='font-size:0.65rem; color:#475569; text-transform:uppercase; letter-spacing:0.08em;'>L2 Score</div>
      <div style='font-family:IBM Plex Mono,monospace; font-size:1.1rem; color:#e2e8f0;'>{row["l2_score"]:.1f}</div>
    </div>
    <div>
      <div style='font-size:0.65rem; color:#475569; text-transform:uppercase; letter-spacing:0.08em;'>Annual RaR</div>
      <div style='font-family:IBM Plex Mono,monospace; font-size:1.1rem; color:#e2e8f0;'>${row["total_rar_m"]:.0f}M</div>
    </div>
    <div>
      <div style='font-size:0.65rem; color:#475569; text-transform:uppercase; letter-spacing:0.08em;'>% Revenue</div>
      <div style='font-family:IBM Plex Mono,monospace; font-size:1.1rem; color:#e2e8f0;'>{row["total_rar_pct_rev"]:.2f}%</div>
    </div>
  </div>
  <div style='font-size:0.7rem; color:#475569; margin-top:8px;'>
    Highest risk: {row["highest_risk_facility"].split("(")[0].strip()}
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown(
        "<p class='source-note'>L2 = squared revenue-weighted score · inflates dominant "
        "facilities to reflect non-linear supply chain disruption risk</p>",
        unsafe_allow_html=True
    )


# ══════════════════════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div class='section-label'>Risk Decomposition</div>", unsafe_allow_html=True)

chart_left, chart_right = st.columns(2)

with chart_left:
    # BWS vs RFR scatter — each facility as a point
    scatter = px.scatter(
        fac_filtered,
        x="bws_score", y="rfr_score",
        color="company",
        size="annual_rar_m",
        size_max=30,
        text="city",
        color_discrete_map=COMPANY_COLORS,
        labels={
            "bws_score": "Baseline Water Stress (0–5)",
            "rfr_score": "Riverine Flood Risk (0–5)",
            "annual_rar_m": "Annual RaR $M",
            "company": "Company",
        },
        title="Water Stress vs Flood Risk by Facility",
    )
    scatter.update_traces(textposition="top center", textfont=dict(size=9, color="#94a3b8"))
    scatter.update_layout(
        height=320,
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#c8d0e0", size=11),
        title=dict(font=dict(size=13, color="#e2e8f0")),
        xaxis=dict(gridcolor="#1e2640", zerolinecolor="#1e2640"),
        yaxis=dict(gridcolor="#1e2640", zerolinecolor="#1e2640"),
        legend=dict(bgcolor="#0a0e1a", bordercolor="#1e2640", borderwidth=1),
        margin=dict(t=40, b=40, l=40, r=20),
    )
    # Add quadrant lines at score midpoints
    scatter.add_hline(y=2.5, line_dash="dot", line_color="#334155", line_width=1)
    scatter.add_vline(x=2.5, line_dash="dot", line_color="#334155", line_width=1)
    st.plotly_chart(scatter, use_container_width=True)
    st.markdown("<p class='source-note'>Bubble size = annual revenue at risk · "
                "Dotted lines = medium risk threshold (2.5/5.0)</p>",
                unsafe_allow_html=True)

with chart_right:
    # Revenue at risk by facility — horizontal bar
    rar_sorted = fac_filtered.sort_values("annual_rar_m", ascending=True)
    bar = go.Figure(go.Bar(
        x=rar_sorted["annual_rar_m"],
        y=rar_sorted["facility_name"].str.split("(").str[0].str.strip(),
        orientation="h",
        marker=dict(
            color=[COMPANY_COLORS.get(c, "#94a3b8") for c in rar_sorted["company"]],
            opacity=0.85,
        ),
        text=[f"${v:.0f}M" for v in rar_sorted["annual_rar_m"]],
        textposition="outside",
        textfont=dict(size=10, color="#94a3b8"),
    ))
    bar.update_layout(
        title="Annual Revenue at Risk by Facility ($M)",
        height=320,
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#c8d0e0", size=10),
        title_font=dict(size=13, color="#e2e8f0"),
        xaxis=dict(
            gridcolor="#1e2640", zerolinecolor="#1e2640",
            title="Annual Revenue at Risk ($M)"
        ),
        yaxis=dict(gridcolor="#1e2640"),
        margin=dict(t=40, b=40, l=10, r=60),
    )
    st.plotly_chart(bar, use_container_width=True)
    st.markdown("<p class='source-note'>WRI disruption probability × 14-day event × "
                "daily facility revenue · Color = company</p>",
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# METHODOLOGY FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
with st.expander("📐 Methodology & Data Sources"):
    st.markdown("""
**Physical Risk Score**
Composite of WRI Aqueduct 4.0 Baseline Water Stress (BWS, 70%) and Riverine Flood Risk (RFR, 30%),
normalized to 0–100. Water stress weighted higher reflecting semiconductor fabs' primary operational
constraint: ultrapure water availability, not flooding. Source: TSMC, Intel, Samsung ESG reports
consistently rank water availability as primary physical risk.

**Revenue at Risk**
`RaR = disruption_probability × 14 days × daily_facility_revenue`

Disruption probabilities mapped from WRI Aqueduct score thresholds per WRI technical guidance:
<1.0 → 2% · 1–2 → 5% · 2–3 → 10% · 3–4 → 15% · >4 → 20% annual probability.
14-day disruption duration calibrated to historical events: TSMC 2021 Taiwan drought (~2 weeks),
Intel 2021 Texas freeze (~1 week). Limitation: does not capture TSMC's ~90% water recycling rate,
which likely overstates short-term disruption risk for fabs with mature recycling programs.

**Revenue Weights**
Facility revenue weights estimated from company annual reports, sustainability disclosures, and
analyst consensus. TSMC weights normalized to sum to 1.0 (raw sum 0.95 — 5% unattributed to
specific facility, likely corporate/IP revenue). Source documented per facility in facilities.csv.

**Taiwan Scores**
WRI Aqueduct 4.0 does not cover Taiwan at provincial level. Scores sourced from TSMC 2024 ESG
Report WRI self-assessment. Treated as lower-bound estimates. The 2021 Taiwan drought —
which forced TSMC to truck in water — suggests actual stress may be understated for Tainan.

**L2 Weighting**
Company-level scores use squared revenue weights (L2) to reflect non-linear supply chain disruption
risk: a dominant node going offline causes cascading impact disproportionate to its revenue share.
L1 (linear) scores provided alongside for transparency.

**Framework**: IFRS S2 Physical Risk Disclosure · WRI Aqueduct 4.0 (2023) · Company ESG Reports 2023/2024
    """)

st.markdown(
    "<p class='source-note' style='text-align:center; margin-top:12px;'>"
    "Duru Sacinti · UC Berkeley Environmental Economics + Data Science · "
    "Data: WRI Aqueduct 4.0, Company ESG Reports 2023/2024"
    "</p>",
    unsafe_allow_html=True
)