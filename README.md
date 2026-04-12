# 🌊 Semiconductor Physical Risk Atlas

Physical climate risk assessment for 13 critical semiconductor facilities across TSMC, ASML, Samsung, and Intel. Built on WRI Aqueduct 4.0 water stress and flood risk data. IFRS S2 aligned.

**Live demo:** [climate-physical-risk.streamlit.app](https://climate-physical-risk.streamlit.app)

---

## Why This Exists

According to the World Economic Forum (2024), over 40% of current semiconductor manufacturing facilities sit in watersheds projected to face severe water stress by 2030 40% (and over 25% of plants under construction face the same exposure!). TSMC's Arizona fab is rated high risk by TSMC's own ESG assessment. This tool doesn't stop at the hazard score, and instead translates it into financial exposure.

To elaborate, this project:

1. Joins facility locations to WRI Aqueduct 4.0 at **provincial level** (not country-level averages)
2. Translates hazard scores into **annual revenue at risk** using WRI's own disruption probability calibration
3. Uses **L2 revenue weighting** to reflect that semiconductor supply chain disruption is non-linear — one dominant node going offline cascades across the entire fabless customer ecosystem

Together with [Climate Factor Analyzer](https://climate-factor-analyzer.streamlit.app), this project covers both pillars of IFRS S2 physical and transition risk disclosure using only public data.

---

## Facility Database

13 facilities manually curated from public company filings and sustainability reports.

| Company | Facilities |
|---------|-----------|
| TSMC | Hsinchu, Taichung, Tainan (STSP), Phoenix (Fab 21), Kumamoto (JASM), Dresden |
| ASML | Veldhoven HQ, Linkou (Taoyuan), Tainan |
| Samsung | Hwaseong, Pyeongtaek |
| Intel | Chandler (Fab 52/62), Hillsboro (D1X) |

**Scope**: Advanced node facilities only. Intel's Ireland, Israel, and Malaysia fabs produce older nodes with market substitutes, which are deliberately excluded. The analytical focus is irreplaceable capacity, not average exposure.

---

## Key Results (Baseline, FY2023)

| Company | L2 Risk Score | Risk Label | Annual RaR |
|---------|--------------|------------|------------|
| Intel | 63.0 | High | $333M |
| ASML | 42.8 | Medium-High | $127M |
| Samsung | 33.3 | Medium | $221M |
| TSMC | 32.7 | Medium | $172M |

**Total annual revenue at risk across 13 facilities: $853M**

Intel scores highest despite TSMC's larger Taiwan concentration. This is because Intel's Chandler campus (Fab 52/62) accounts for a significant share of Intel's advanced node revenue, and Arizona's water stress score (4.75/5.0, Extremely High) is among the highest in the dataset.

---

## Methodology

### Physical Risk Score

Composite of WRI Aqueduct 4.0 Baseline Water Stress (BWS) and Riverine Flood Risk (RFR), normalized to 0–100:

```
Composite Score = (BWS × 0.70 + RFR × 0.30) / 5.0 × 100
```

**Why 70/30?** Semiconductor fabs require ultrapure water continuously for wafer cleaning, rendering, water availability an operational daily dependency, not an episodic risk. Flooding is partially mitigable via site engineering. TSMC, Intel, and Samsung all flag water availability (not flooding) as their primary physical risk in their ESG reports.

### Revenue at Risk

```
Annual RaR = disruption_probability × disruption_days × daily_facility_revenue
```

Where:
- `daily_facility_revenue = company_annual_revenue × facility_revenue_weight ÷ 365`
- `disruption_days = 14` (calibrated to TSMC 2021 Taiwan drought ~2 weeks, Intel 2021 Texas freeze ~1 week)
- `disruption_probability` mapped from BWS score per WRI technical guidance:

| BWS Score | Water Stress Level | Annual Disruption Probability |
|-----------|-------------------|------------------------------|
| < 1.0 | Low | 2% |
| 1.0 – 2.0 | Low-Medium | 5% |
| 2.0 – 3.0 | Medium | 10% |
| 3.0 – 4.0 | Medium-High | 15% |
| > 4.0 | Extremely High | 20% |

**Calibration anchor**: TSMC's Taiwan fabs score ~1.8 and experienced supply disruption during the 2021 drought, requiring water to be trucked in. This is consistent with a 5% annual disruption probability (serious drought roughly once per decade). All other thresholds scale from this anchor.

### ASML: Production Risk vs Service Risk

ASML's facility model differs from fab operators. All EUV and DUV systems are assembled and shipped exclusively from Veldhoven; San Diego (light sources) and Berlin (optics) manufacture components that feed into Veldhoven final assembly. 
Taiwan locations are field service offices, not production sites.

Revenue weights reflect this distinction: Veldhoven 0.94, Taiwan offices 0.03 each. 
A Veldhoven water supply disruption stops all machine shipments globally. A Taiwan office disruption affects field service only and is modeled accordingly.

### Company-Level Scoring (L1 and L2)

Two aggregation methods reported for transparency:

- **L1 (linear)**: Revenue-weighted average across facilities. Simple proportional contribution.
- **L2 (squared weights)**: Squares revenue weights before averaging, then renormalizes. Inflates the contribution of dominant facilities to reflect non-linear supply chain impact.

**L2 is the headline score.** A dominant fab going offline causes cascading downstream disruption disproportionate to its revenue share. L1 would understate this concentration risk.

### Revenue Weights

Facility revenue weights estimated from company annual reports, sustainability disclosures, and analyst consensus estimates. Intel weights sum to 0.60 (Chandler 0.35 + Hillsboro 0.25); remaining 0.40 represents Ireland, Israel, and Malaysia fabs not in scope. TSMC weights normalized programmatically to sum to 1.0 (raw sum 0.95 — 5% unattributed, likely corporate/IP revenue).

TSMC 2024 Annual Report confirms 69% of wafer revenue from advanced nodes (≤7nm). Facility weights reflect estimated node seniority based on public technical disclosures; no facility-level revenue is published by any of the four companies in scope.

---

## Taiwan Data Gap

WRI Aqueduct 4.0 does not include Taiwan in its provincial rankings dataset. Scores for Taiwan facilities are sourced from **TSMC's 2024 ESG Report Water Risk Assessment**, which uses WRI's own Aqueduct methodology for self-assessment.

ASML's Taiwan facilities (Linkou/Taoyuan and Tainan) use the same scores as co-located TSMC regions — water stress is a watershed characteristic, not a company characteristic.

**Limitation**: Self-reported scores are not independently verified and may reflect conservative estimates. The 2021 Taiwan drought, which forced TSMC to truck in water despite scores in the Low-Medium range, suggests actual stress for southern Taiwan fabs may be understated. These scores are treated as lower-bound estimates throughout.

---

## Score Validation

Samsung's 2025 Sustainability Report (DS Division Water Risk section) independently confirms Hwaseong and Pyeongtaek as Medium-High water stress using the WRI Aqueduct 
Water Risk Atlas. This is consistent with this model's BWS scores of 2.11 for both facilities. 
Samsung groups the two sites together in their own risk assessment, supporting the equal revenue weighting applied here.

TSMC's 2024 Sustainability Report independently confirms Taiwan fabs as mid-to-low risk and Arizona as high risk via WRI Aqueduct assessment. This is consistent with this 
model's BWS scores of 1.5–1.8 for Taiwan and 4.75 for Arizona.
---

## Data Sources

| Source | Used For |
|--------|----------|
| WRI Aqueduct 4.0 (Jul 2023) | Water stress + flood risk scores, provincial level |
| TSMC 2024 ESG Report | Taiwan facility scores, revenue weights |
| ASML 2023 Annual Report | Facility locations, revenue |
| Samsung Semiconductor 2023 | Facility locations, segment revenue ($57.5B semiconductor only) |
| Intel 2023 Annual Report | Facility locations, revenue ($54.2B) |

---

## Pipeline

```
facilities.csv          → join_aqueduct.py  → facilities_merged.csv
                                                      ↓
Aqueduct 4.0 xlsx       →                   scoring.py
                                                      ↓
                                            facilities_scored.csv
                                            company_scores.csv
                                                      ↓
                                            app.py (Streamlit)
```

### Run Locally

```bash
# Install dependencies
pip install streamlit pandas plotly openpyxl

# Step 1: Join Aqueduct data
python3 join_aqueduct.py

# Step 2: Compute scores
python3 scoring.py

# Step 3: Launch dashboard
streamlit run app.py
```

---

## Limitations

- **Transition risk excluded**: Physical risk only. For transition risk (carbon pricing, Paris alignment, Climate VaR), see [Climate Factor Analyzer](https://climate-factor-analyzer.streamlit.app).
- **Revenue weights are estimates**: Company filings do not disclose revenue by individual fab. Weights estimated from public disclosures and analyst consensus; documented per facility in `facilities.csv`.
- **Water recycling not modeled**: TSMC's ~90% water recycling rate is a material mitigating factor not captured in baseline scores. Disruption probability likely overstates short-term risk for fabs with mature recycling programs.
- **Province-level granularity**: Aqueduct scores represent province-level averages. Facility-specific watershed conditions may differ.
- **Baseline only**: Current version uses Aqueduct baseline (present-day) scores. SSP1/SSP2/SSP5 forward-looking scenario analysis (2030/2050) planned for next version.

---

## Framework

- **IFRS S2 (ISSB)** — Physical Risk Disclosure (effective January 2024)
- **WRI Aqueduct 4.0** — Water risk assessment framework
- **WRI disruption probability calibration** — Score-to-probability mapping

---

*Duru Sacinti · UC Berkeley Environmental Economics + Data Science*
*Data: WRI Aqueduct 4.0, Company ESG Reports 2023/2024*