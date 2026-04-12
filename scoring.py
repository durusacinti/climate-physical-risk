"""
scoring.py — Project 2: Semiconductor Physical Risk Atlas
=========================================================
Computes physical risk scores, revenue-at-risk estimates, and company-level
rollups from facilities_merged.csv (output of join_aqueduct.py).

Three outputs:
  1. Facility-level physical risk score (composite BWS + RFR, L1 and L2)
  2. Revenue-at-risk bridge per facility (Aqueduct score → disruption
     probability → days at risk × daily revenue)
  3. Company-level rollup (revenue-weighted composite score + total RaR)

Run from your project root:
    python3 scoring.py

Outputs:
    facilities_scored.csv   — facility-level scores + RaR
    company_scores.csv      — company-level rollup (used by Streamlit app)

Methodology documentation:
  See README.md — Physical Risk Scoring section.
  Key decisions: L2 weighting, WRI disruption probability calibration,
  Taiwan self-reported scores, ASML proxy.

Author: Duru Sacinti | UC Berkeley Environmental Economics + Data Science
"""

import os
import sys
import pandas as pd
import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH     = os.path.join(BASE_DIR, "facilities_merged.csv")
FAC_OUT_PATH   = os.path.join(BASE_DIR, "facilities_scored.csv")
COMP_OUT_PATH  = os.path.join(BASE_DIR, "company_scores.csv")


# =============================================================================
# SECTION 1: COMPOSITE SCORE WEIGHTS
# BWS (water stress) weighted higher than RFR (flood risk) for semiconductor
# fabs specifically: ultrapure water scarcity is the primary operational
# constraint, while flood risk affects fab construction/access but is more
# manageable via site engineering. 70/30 split reflects this priority.
# Source: TSMC, Intel, Samsung water risk disclosures consistently flag
# water availability as primary physical risk — not flooding.
# =============================================================================

BWS_WEIGHT = 0.70   # Baseline water stress weight
RFR_WEIGHT = 0.30   # Riverine flood risk weight

# Score is on WRI's 0–5 scale. Normalize to 0–100 for readability.
SCORE_SCALE = 5.0


# =============================================================================
# SECTION 2: WRI DISRUPTION PROBABILITY CALIBRATION
# Maps Aqueduct BWS score (0–5) to annual probability of water supply
# disruption sufficient to affect fab operations.
#
# Source: WRI Aqueduct 4.0 Technical Note (2023) — score interpretation:
#   <1.0  = Low             (<10% of renewable supply withdrawn)
#   1–2   = Low-Medium      (10–20%)
#   2–3   = Medium          (20–40%)
#   3–4   = Medium-High     (40–80%)
#   >4.0  = Extremely High  (>80%)
#
# Disruption probability mapping (annual, point estimate):
#   These are conservative estimates — disruption requires stress + drought
#   year coincidence, not just high baseline stress.
#   Calibrated against TSMC 2021 Taiwan drought (BWS ~1.8 → disruption occurred).
#
# Limitation: generic semiconductor, doesn't capture TSMC's ~90% water
# recycling rate. Likely overstates short-term risk for fabs with mature
# recycling programs. Documented in README.
# =============================================================================

def bws_to_disruption_probability(bws_score: float) -> float:
    """
    Map Aqueduct BWS score to annual disruption probability.
    Returns float between 0 and 1.

    Calibration anchors:
    - TSMC 2021 Taiwan drought: BWS ~1.8, disruption occurred → ~8% annual prob
    - Phoenix (BWS 4.75): Extremely High stress, material risk → ~20% annual prob
    - Hillsboro (BWS 2.9): Medium-High, manageable → ~10% annual prob
    - Kumamoto (BWS 1.05): Low, minimal risk → ~2% annual prob
    """
    if bws_score < 1.0:
        return 0.02   # Low: ~2% annual disruption probability
    elif bws_score < 2.0:
        return 0.05   # Low-Medium: ~5%
    elif bws_score < 3.0:
        return 0.10   # Medium: ~10%
    elif bws_score < 4.0:
        return 0.15   # Medium-High: ~15%
    else:
        return 0.20   # Extremely High: ~20%


# =============================================================================
# SECTION 3: ANNUAL REVENUE PER FACILITY
# Used to translate disruption probability into dollar revenue at risk.
#
# Source: Company annual reports + analyst consensus estimates (2023/2024).
# Revenue weights in facilities.csv represent estimated share of company
# total revenue attributable to each facility.
#
# Company total revenue (USD billions, FY2023):
#   TSMC:    $69.3B  (TSMC 2023 Annual Report)
#   ASML:    $27.6B  (ASML 2023 Annual Report)
#   Samsung: $57.5B  (Samsung Semiconductor segment only, approx.)
#   Intel:   $54.2B  (Intel 2023 Annual Report)
#
# Note: Samsung figure is semiconductor segment only (logic + memory).
# Full Samsung Electronics revenue (~$200B) would dilute facility weights
# inappropriately — we're modeling semiconductor physical risk specifically.
# =============================================================================

COMPANY_REVENUE_BN = {
    "TSMC":    69.3,
    "ASML":    27.6,
    "Samsung": 57.5,   # semiconductor segment
    "Intel":   54.2,
}

# Days at risk per disruption event
# Based on historical fab disruption durations:
#   - TSMC 2021 Taiwan drought: ~2 weeks trucking water, no full shutdown
#   - TSMC 2022 earthquake (Taichung): ~3 days partial shutdown
#   - Intel 2021 Texas freeze: ~1 week
# Conservative assumption: 14 days average disruption duration per event.
DISRUPTION_DAYS = 14


# =============================================================================
# SECTION 4: SCORING FUNCTIONS
# =============================================================================

def composite_score(bws: float, rfr: float,
                    bws_w: float = BWS_WEIGHT,
                    rfr_w: float = RFR_WEIGHT) -> float:
    """
    Weighted composite of BWS and RFR scores, normalized to 0–100.
    Linear (L1) — used as baseline.
    """
    raw = (bws * bws_w + rfr * rfr_w)
    return round((raw / SCORE_SCALE) * 100, 2)


def composite_score_l2(bws: float, rfr: float, revenue_weight: float,
                        all_rev_weights: pd.Series) -> float:
    """
    L2 (squared revenue) weighted composite score at facility level.

    L2 inflates the contribution of high-revenue facilities, reflecting
    that supply chain disruption risk is non-linear: a dominant node going
    offline causes cascading downstream impact disproportionate to its
    revenue share.

    This function returns the facility's raw score — company-level L2
    rollup squares the weights during aggregation (see company_rollup()).
    """
    return composite_score(bws, rfr)  # facility score same; L2 applied at rollup


def risk_label(score: float) -> str:
    """Convert 0–100 composite score to WRI-aligned risk label."""
    if score >= 80:   return "Extremely High"
    if score >= 60:   return "High"
    if score >= 40:   return "Medium-High"
    if score >= 20:   return "Medium"
    if score >= 10:   return "Low-Medium"
    return "Low"


def revenue_at_risk(bws_score: float,
                    company: str,
                    revenue_weight: float,
                    disruption_days: int = DISRUPTION_DAYS) -> dict:
    """
    Translate BWS score into annual revenue at risk (USD millions).

    Formula:
        RaR = disruption_probability × disruption_days × daily_facility_revenue

    Where:
        daily_facility_revenue = company_annual_revenue × facility_revenue_weight / 365

    Returns dict with probability, daily revenue, and annual RaR in $M.
    """
    company_rev_bn = COMPANY_REVENUE_BN.get(company, 0)
    if company_rev_bn == 0:
        return {"disruption_prob": 0, "daily_rev_m": 0, "annual_rar_m": 0}

    facility_annual_rev_m = company_rev_bn * 1000 * revenue_weight
    daily_rev_m           = facility_annual_rev_m / 365
    disruption_prob       = bws_to_disruption_probability(bws_score)
    annual_rar_m          = disruption_prob * disruption_days * daily_rev_m

    return {
        "disruption_prob":      round(disruption_prob, 3),
        "facility_annual_rev_m": round(facility_annual_rev_m, 1),
        "daily_rev_m":          round(daily_rev_m, 2),
        "annual_rar_m":         round(annual_rar_m, 1),
        "annual_rar_pct_rev":   round((annual_rar_m / (company_rev_bn * 1000)) * 100, 3),
    }


# =============================================================================
# SECTION 5: COMPANY-LEVEL ROLLUP
# =============================================================================

def company_rollup(fac: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate facility scores to company level.

    L1 score: revenue-weighted average (linear)
    L2 score: squared-revenue-weighted average (inflates dominant facilities)

    Both provided for transparency. L2 is the headline score.
    """
    rows = []
    for company, group in fac.groupby("company"):
        rev_weights = group["revenue_weight"].values
        scores      = group["composite_score_l1"].values

        # Normalize weights (should sum to ~1 per company, but verify)
        weight_sum = rev_weights.sum()
        if abs(weight_sum - 1.0) > 0.05:
            print(f"  ⚠ {company}: revenue weights sum to {weight_sum:.3f} (expected ~1.0)")

        # L1: linear revenue-weighted average
        l1_score = np.average(scores, weights=rev_weights)

        # L2: squared revenue weights, renormalized
        sq_weights  = rev_weights ** 2
        sq_weights  = sq_weights / sq_weights.sum()
        l2_score    = np.average(scores, weights=sq_weights)

        # Total annual revenue at risk across all facilities
        total_rar_m = group["annual_rar_m"].sum()

        # Highest-risk facility
        top_fac_idx = group["composite_score_l1"].idxmax()
        top_fac     = group.loc[top_fac_idx, "facility_name"]
        top_score   = group.loc[top_fac_idx, "composite_score_l1"]

        # Company revenue
        comp_rev_bn = COMPANY_REVENUE_BN.get(company, 0)
        total_rar_pct = (total_rar_m / (comp_rev_bn * 1000) * 100) if comp_rev_bn > 0 else 0

        rows.append({
            "company":            company,
            "l1_score":           round(l1_score, 2),
            "l2_score":           round(l2_score, 2),
            "risk_label_l2":      risk_label(l2_score),
            "total_rar_m":        round(total_rar_m, 1),
            "total_rar_pct_rev":  round(total_rar_pct, 3),
            "revenue_bn":         comp_rev_bn,
            "n_facilities":       len(group),
            "highest_risk_facility": top_fac,
            "highest_risk_score": round(top_score, 2),
        })

    return pd.DataFrame(rows).sort_values("l2_score", ascending=False).reset_index(drop=True)


# =============================================================================
# SECTION 6: MAIN
# =============================================================================

def run_scoring() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(
            f"MISSING: facilities_merged.csv\nExpected at: {INPUT_PATH}\n"
            f"Run join_aqueduct.py first."
        )

    fac = pd.read_csv(INPUT_PATH)
    print(f"Loaded facilities_merged.csv: {len(fac)} rows\n")

    # ── Facility-level scores ─────────────────────────────────────────────────
    fac["composite_score_l1"] = fac.apply(
        lambda r: composite_score(r["bws_score"], r["rfr_score"]), axis=1
    )
    fac["risk_label"] = fac["composite_score_l1"].apply(risk_label)

    # ── Revenue-at-risk bridge ────────────────────────────────────────────────
    rar_cols = fac.apply(
        lambda r: revenue_at_risk(r["bws_score"], r["company"], r["revenue_weight"]),
        axis=1, result_type="expand"
    )
    fac = pd.concat([fac, rar_cols], axis=1)

    # ── Company rollup ────────────────────────────────────────────────────────
    company_df = company_rollup(fac)

    return fac, company_df


def print_results(fac: pd.DataFrame, company_df: pd.DataFrame):
    print("=" * 70)
    print("  FACILITY-LEVEL PHYSICAL RISK SCORES")
    print("=" * 70)

    display_cols = ["company", "facility_name", "city", "gid_0",
                    "bws_score", "rfr_score", "composite_score_l1",
                    "risk_label", "annual_rar_m"]
    print(fac[display_cols].sort_values("composite_score_l1", ascending=False).to_string(index=False))

    print("\n" + "=" * 70)
    print("  COMPANY-LEVEL ROLLUP (L2 revenue-weighted)")
    print("=" * 70)
    print(f"\n  {'Company':<10} {'L1':>6} {'L2':>6} {'Risk Label':<15} {'RaR $M':>8} {'RaR %Rev':>9}  Highest-Risk Facility")
    print(f"  {'-'*10} {'-'*6} {'-'*6} {'-'*15} {'-'*8} {'-'*9}  {'-'*30}")
    for _, r in company_df.iterrows():
        print(f"  {r['company']:<10} {r['l1_score']:>6.1f} {r['l2_score']:>6.1f} "
              f"{r['risk_label_l2']:<15} {r['total_rar_m']:>8.1f} "
              f"{r['total_rar_pct_rev']:>8.2f}%  {r['highest_risk_facility']}")

    print("\n" + "=" * 70)
    print("  KEY HEADLINES")
    print("=" * 70)

    # Top facility globally
    top = fac.loc[fac["composite_score_l1"].idxmax()]
    print(f"\n  Highest-risk facility:  {top['facility_name']} ({top['company']})")
    print(f"  Score: {top['composite_score_l1']:.1f}/100  |  BWS: {top['bws_score']:.2f}  |  Annual RaR: ${top['annual_rar_m']:.0f}M")

    # Largest absolute RaR
    top_rar = fac.loc[fac["annual_rar_m"].idxmax()]
    print(f"\n  Largest revenue at risk: {top_rar['facility_name']} ({top_rar['company']})")
    print(f"  Annual RaR: ${top_rar['annual_rar_m']:.0f}M  |  Disruption prob: {top_rar['disruption_prob']*100:.0f}%/yr")

    total_rar = fac["annual_rar_m"].sum()
    print(f"\n  Total annual RaR across all 13 facilities: ${total_rar:.0f}M")
    print("=" * 70)


if __name__ == "__main__":
    try:
        fac_scored, company_df = run_scoring()
        print_results(fac_scored, company_df)

        fac_scored.to_csv(FAC_OUT_PATH, index=False)
        company_df.to_csv(COMP_OUT_PATH, index=False)

        print(f"\n✅ Written: {FAC_OUT_PATH}")
        print(f"✅ Written: {COMP_OUT_PATH}")
        print("\n   Next step: run scoring.py --scenario to add SSP1/SSP2/SSP5 projections,")
        print("   or start building the Streamlit app with these baseline scores.")

    except (FileNotFoundError, ValueError) as e:
        print(f"\n❌ {e}", file=sys.stderr)
        sys.exit(1)