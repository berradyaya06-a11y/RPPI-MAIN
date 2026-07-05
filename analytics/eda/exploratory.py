"""
analytics/eda/exploratory.py
Phase 6 — Exploratory Data Analysis
Distribution, temporal, spatial, and correlation analysis.
Outputs: EDA report CSV + printed summary.
"""
import numpy as np
import pandas as pd
from database.models import SessionLocal, CleanListing
from config.settings import EXPORT_DIR
from utils.logger import log
from datetime import datetime


def load_clean() -> pd.DataFrame:
    session = SessionLocal()
    rows = session.query(CleanListing).all()
    session.close()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([{
        "city": r.city, "region": r.region,
        "transaction": r.transaction, "property_type": r.property_type,
        "price": r.price, "surface": r.surface, "price_per_m2": r.price_per_m2,
        "log_price": r.log_price, "rooms": r.rooms,
        "year": r.year, "month": r.month, "quarter": r.quarter,
        "year_quarter": r.year_quarter, "quality_score": r.quality_score,
        "neighborhood": r.neighborhood,
    } for r in rows])


def distribution_analysis(df: pd.DataFrame) -> dict:
    """Price distribution by city and transaction type."""
    stats = {}
    for (city, txn), grp in df.groupby(["city", "transaction"]):
        prices = grp["price"].dropna()
        ppm2   = grp["price_per_m2"].dropna()
        if len(prices) == 0:
            continue
        stats[f"{city}_{txn}"] = {
            "n":              len(prices),
            "mean":           round(prices.mean(), 0),
            "median":         round(prices.median(), 0),
            "std":            round(prices.std(), 0),
            "q25":            round(prices.quantile(0.25), 0),
            "q75":            round(prices.quantile(0.75), 0),
            "min":            round(prices.min(), 0),
            "max":            round(prices.max(), 0),
            "mean_ppm2":      round(ppm2.mean(), 0) if len(ppm2) else None,
            "median_ppm2":    round(ppm2.median(), 0) if len(ppm2) else None,
        }
    return stats


def temporal_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly and quarterly price evolution."""
    df_t = df.dropna(subset=["price","year_quarter"])
    result = (df_t.groupby(["year_quarter","city","transaction"])
              .agg(
                  avg_price=("price","mean"),
                  median_price=("price","median"),
                  avg_ppm2=("price_per_m2","mean"),
                  count=("price","count"),
              )
              .reset_index()
              .sort_values(["city","transaction","year_quarter"]))
    result["avg_price"]    = result["avg_price"].round(0)
    result["median_price"] = result["median_price"].round(0)
    result["avg_ppm2"]     = result["avg_ppm2"].round(0)
    return result


def market_segmentation(df: pd.DataFrame) -> pd.DataFrame:
    """Listings breakdown by property type per city."""
    return (df.groupby(["city","transaction","property_type"])
            .agg(count=("price","count"), median_price=("price","median"),
                 median_ppm2=("price_per_m2","median"))
            .reset_index()
            .sort_values(["city","transaction","count"], ascending=[True,True,False]))


def completeness_report(df: pd.DataFrame) -> pd.DataFrame:
    """Phase 5 quality check — missing values per field."""
    cols = ["price","surface","rooms","property_type","city","neighborhood",
            "price_per_m2","log_price","year_quarter"]
    report = pd.DataFrame({
        "field":    cols,
        "n_total":  len(df),
        "n_valid":  [df[c].notna().sum() for c in cols],
        "pct_missing": [round(df[c].isna().mean()*100, 1) for c in cols],
    })
    return report


def run_eda():
    log.info("=== Phase 6: Exploratory Data Analysis ===")
    df = load_clean()
    if df.empty:
        log.warning("[EDA] No clean data found. Run --clean first.")
        return

    ts = datetime.utcnow().strftime("%Y%m%d")

    # 1. Distribution
    dist = distribution_analysis(df)
    log.info(f"\n{'='*55}\n  Price distribution by city × transaction\n{'='*55}")
    for key, s in dist.items():
        log.info(f"  {key}: n={s['n']} | median={s['median']:,.0f} DH | "
                 f"ppm2={s['median_ppm2']:,.0f} DH/m²" if s['median_ppm2'] else
                 f"  {key}: n={s['n']} | median={s['median']:,.0f} DH")

    # 2. Temporal
    temp = temporal_analysis(df)
    temp.to_csv(EXPORT_DIR / f"eda_temporal_{ts}.csv", index=False)
    log.info(f"\n  Temporal analysis → {EXPORT_DIR}/eda_temporal_{ts}.csv")

    # 3. Segmentation
    seg = market_segmentation(df)
    seg.to_csv(EXPORT_DIR / f"eda_segmentation_{ts}.csv", index=False)
    log.info(f"  Segmentation → {EXPORT_DIR}/eda_segmentation_{ts}.csv")

    # 4. Completeness
    comp = completeness_report(df)
    comp.to_csv(EXPORT_DIR / f"eda_quality_{ts}.csv", index=False)
    log.info(f"  Quality report → {EXPORT_DIR}/eda_quality_{ts}.csv")
    log.info(f"\n  Missing values summary:")
    for _, row in comp.iterrows():
        bar = "█" * int((100 - row.pct_missing) / 5)
        log.info(f"    {row.field:<20} {100-row.pct_missing:>5.1f}% complete  {bar}")

    # 5. Summary
    log.info(f"\n{'='*55}")
    log.info(f"  Total listings analysed : {len(df):,}")
    log.info(f"  Cities                  : {df['city'].nunique()}")
    log.info(f"  Transaction types       : {df['transaction'].unique().tolist()}")
    log.info(f"  Property types          : {df['property_type'].nunique()}")
    log.info(f"  Date range              : {df['year_quarter'].min()} → {df['year_quarter'].max()}")
    log.info(f"  Avg quality score       : {df['quality_score'].mean():.2f}")
    log.info(f"{'='*55}")

    log.success("[EDA] Phase 6 complete.")
    return dist, temp, seg, comp
