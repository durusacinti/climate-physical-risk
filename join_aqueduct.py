"""
join_aqueduct.py — Project 2: Semiconductor Physical Risk Atlas
===============================================================
Joins WRI Aqueduct 4.0 water stress + flood risk scores to facility database.
Handles Taiwan data gap via TSMC self-reported scores (TSMC ESG 2024).

Aqueduct 4.0 schema note: long format — one row per province per indicator.
Must pivot on indicator_name to extract bws and rfr scores.

Run from your project root:
    python3 join_aqueduct.py

Outputs:
    facilities_merged.csv — ready for scoring pipeline
"""

import os
import sys
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
FACILITIES_PATH = os.path.join(BASE_DIR, "facilities.csv")
AQUEDUCT_PATH   = os.path.join(BASE_DIR, "Aqueduct40_rankings_download_Y2023M07D05.xlsx")
OUTPUT_PATH     = os.path.join(BASE_DIR, "facilities_merged.csv")

# ── Taiwan fallback scores ─────────────────────────────────────────────────────
# Taiwan (TWN) is absent from Aqueduct 4.0 provincial data.
# Source: TSMC 2024 ESG Report — Water Risk Assessment section.
# WRI qualitative labels converted to numeric scale (0–5):
#   "Low-Medium" → ~1.5, "Medium" → 2.5, "High" → 3.5, "Extremely High" → 4.5
# Tainan receives slightly higher BWS (1.8) reflecting documented 2021 drought
# and its southern Taiwan location (drier watershed). Methodological choice —
# documented in README.
TAIWAN_FALLBACK = {
    "Hsinchu":  {"bws_score": 1.5, "rfr_score": 1.2},
    "Taichung": {"bws_score": 1.5, "rfr_score": 1.4},
    "Tainan":   {"bws_score": 1.8, "rfr_score": 1.6},
    "Taoyuan":  {"bws_score": 1.5, "rfr_score": 1.3},
}

# Aqueduct indicator names to extract (long-format sheet)
BWS_INDICATOR = "bws"
RFR_INDICATOR = "rfr"


def load_and_pivot(path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load Aqueduct xlsx and pivot from long to wide format.
    Returns (prov_wide, country_wide) with columns: gid_0, name_1, bws_score, rfr_score.
    """
    print("Loading Aqueduct 4.0 xlsx (this may take ~15 seconds)...")
    xl = pd.ExcelFile(path)
    print(f"  Sheets: {xl.sheet_names}")

    aq_prov    = pd.read_excel(path, sheet_name="province_baseline")
    aq_country = pd.read_excel(path, sheet_name="country_baseline")

    # Show available indicators
    indicators = aq_prov["indicator_name"].unique()
    print(f"\n  Available indicators ({len(indicators)} total):")
    for ind in sorted(indicators):
        print(f"    {ind}")

    # Confirm target indicators exist
    for ind in [BWS_INDICATOR, RFR_INDICATOR]:
        if ind not in indicators:
            raise ValueError(
                f"\nIndicator '{ind}' not found in province_baseline sheet.\n"
                f"Available indicators printed above — update BWS_INDICATOR / RFR_INDICATOR."
            )

    print(f"\n  Using: '{BWS_INDICATOR}' for water stress")
    print(f"  Using: '{RFR_INDICATOR}' for flood risk")

    def pivot_sheet(df, id_cols):
        filtered = df[df["indicator_name"].isin([BWS_INDICATOR, RFR_INDICATOR])].copy()
        pivoted = filtered.pivot_table(
            index=id_cols,
            columns="indicator_name",
            values="score",
            aggfunc="first"
        ).reset_index()
        pivoted.columns.name = None
        pivoted = pivoted.rename(columns={
            BWS_INDICATOR: "bws_score",
            RFR_INDICATOR: "rfr_score",
        })
        return pivoted

    prov_wide    = pivot_sheet(aq_prov,    id_cols=["gid_0", "name_1"])
    country_wide = pivot_sheet(aq_country, id_cols=["gid_0"])

    print(f"\n  Province wide: {len(prov_wide)} rows")
    print(f"  Country wide:  {len(country_wide)} rows")

    return prov_wide, country_wide


def join_facility(row: pd.Series,
                  prov_wide: pd.DataFrame,
                  country_wide: pd.DataFrame) -> dict | None:
    """Province-level join, country-level fallback."""
    iso3     = row["gid_0"]
    province = str(row.get("province", "")).strip()

    if province:
        mask = (prov_wide["gid_0"] == iso3) & (prov_wide["name_1"].str.lower() == province.lower())
        match = prov_wide[mask]
        if not match.empty:
            r = match.iloc[0]
            return {"bws_score": r["bws_score"], "rfr_score": r["rfr_score"], "join_level": "province"}

    mask = country_wide["gid_0"] == iso3
    if mask.any():
        r = country_wide[mask].iloc[0]
        return {"bws_score": r["bws_score"], "rfr_score": r["rfr_score"], "join_level": "country_fallback"}

    return None


def run_join() -> pd.DataFrame:
    for path, label in [(FACILITIES_PATH, "facilities.csv"), (AQUEDUCT_PATH, "Aqueduct xlsx")]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"MISSING: {label}\nExpected at: {path}")

    fac = pd.read_csv(FACILITIES_PATH)
    print(f"\nLoaded facilities.csv: {len(fac)} rows")
    print(fac[["company", "facility_name", "city", "province", "gid_0"]].to_string())

    prov_wide, country_wide = load_and_pivot(AQUEDUCT_PATH)

    for col in ["bws_score", "rfr_score", "join_level"]:
        if col not in fac.columns:
            fac[col] = None

    errors = []

    # Taiwan: hardcoded fallback
    taiwan_mask = fac["gid_0"] == "TWN"
    for idx, row in fac[taiwan_mask].iterrows():
        city = str(row.get("city", "")).strip()
        fallback = TAIWAN_FALLBACK.get(city)
        if fallback is None:
            errors.append(f"  Row {idx}: Taiwan city '{city}' not in TAIWAN_FALLBACK")
            continue
        fac.at[idx, "bws_score"]  = fallback["bws_score"]
        fac.at[idx, "rfr_score"]  = fallback["rfr_score"]
        fac.at[idx, "join_level"] = "taiwan_self_reported"

    # Non-Taiwan: Aqueduct join
    for idx, row in fac[~taiwan_mask].iterrows():
        result = join_facility(row, prov_wide, country_wide)
        if result is None:
            iso3  = row["gid_0"]
            avail = prov_wide[prov_wide["gid_0"] == iso3]["name_1"].tolist()
            errors.append(
                f"  Row {idx}: {row.get('facility_name')} ({row.get('province')}, {iso3})\n"
                f"    Available provinces for {iso3}: {avail}"
            )
        else:
            fac.at[idx, "bws_score"]  = result["bws_score"]
            fac.at[idx, "rfr_score"]  = result["rfr_score"]
            fac.at[idx, "join_level"] = result["join_level"]

    if errors:
        raise ValueError("JOIN FAILED:\n" + "\n".join(errors))

    for col in ["bws_score", "rfr_score"]:
        nulls = fac[fac[col].isnull()]
        if not nulls.empty:
            raise ValueError(f"UNRESOLVED NULLS in {col}:\n{nulls[['facility_name','gid_0']]}")

    return fac


def print_dq_report(fac: pd.DataFrame):
    print("\n" + "=" * 60)
    print("  AQUEDUCT JOIN — DATA QUALITY REPORT")
    print("=" * 60)
    jl = fac["join_level"]
    print(f"  Total facilities:            {len(fac)}")
    print(f"  Taiwan (self-reported):      {(jl == 'taiwan_self_reported').sum()}")
    print(f"  Aqueduct province join:      {(jl == 'province').sum()}")
    print(f"  Aqueduct country fallback:   {(jl == 'country_fallback').sum()}")
    print(f"\n  BWS score range: {fac['bws_score'].min():.2f} – {fac['bws_score'].max():.2f}")
    print(f"  RFR score range: {fac['rfr_score'].min():.2f} – {fac['rfr_score'].max():.2f}")
    print(f"\n  Null bws_score: {fac['bws_score'].isnull().sum()} (must be 0)")
    print(f"  Null rfr_score: {fac['rfr_score'].isnull().sum()} (must be 0)")

    cfl = fac[jl == "country_fallback"]
    if not cfl.empty:
        print(f"\n  ⚠ Lower-confidence (country fallback):")
        for _, r in cfl.iterrows():
            print(f"    {r['facility_name']} ({r['province']}, {r['gid_0']})")

    print("\n  Sanity checks:")
    for _, r in fac.iterrows():
        name = r.get("facility_name", "")
        bws  = float(r.get("bws_score", 0))
        if any(x in name for x in ["Phoenix", "Chandler"]):
            flag = "✅" if bws > 3.5 else f"⚠ UNEXPECTED (expected >3.5, got {bws:.2f})"
            print(f"    {name}: BWS={bws:.2f}  {flag}")
        if "Hillsboro" in name:
            flag = "✅" if bws < 1.5 else f"⚠ UNEXPECTED (expected <1.5, got {bws:.2f})"
            print(f"    {name}: BWS={bws:.2f}  {flag}")
        if "Tainan" in name:
            flag = "✅" if 1.5 <= bws <= 2.5 else f"⚠ Check Taiwan fallback"
            print(f"    {name}: BWS={bws:.2f}  {flag}")

    print("\n  Full merged table:")
    cols = [c for c in ["company","facility_name","city","gid_0","bws_score","rfr_score","join_level"] if c in fac.columns]
    print(fac[cols].to_string(index=False))
    print("=" * 60)


if __name__ == "__main__":
    try:
        fac_merged = run_join()
        print_dq_report(fac_merged)
        fac_merged.to_csv(OUTPUT_PATH, index=False)
        print(f"\n✅ Written: {OUTPUT_PATH}")
        print("   Next step: run scoring.py to compute composite risk scores.")
    except (FileNotFoundError, ValueError) as e:
        print(f"\n❌ {e}", file=sys.stderr)
        sys.exit(1)