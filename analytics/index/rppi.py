"""
analytics/index/rppi.py
Phase 9 — Price Index Construction and Storage
Saves computed RPPI values to price_index table.
Computes: National + Regional + City level indices.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from database.models import SessionLocal, CleanListing, PriceIndex
from config.settings import EXPORT_DIR, INDEX
from utils.logger import log


def load_clean_for_index() -> pd.DataFrame:
    session = SessionLocal()
    rows = session.query(CleanListing).filter(
        CleanListing.price.isnot(None),
        CleanListing.year_quarter.isnot(None),
    ).all()
    session.close()
    return pd.DataFrame([{
        "city": r.city, "region": r.region,
        "transaction": r.transaction, "property_type": r.property_type,
        "price": r.price, "price_per_m2": r.price_per_m2,
        "year_quarter": r.year_quarter,
    } for r in rows])


def compute_simple_index(df: pd.DataFrame, base_period: str = "2024-Q1") -> pd.DataFrame:
    """
    Simple median price index — used alongside hedonic for comparison.
    index_t = 100 × (median_price_t / median_price_base)
    """
    results = []
    for (city, txn, ptype), grp in df.groupby(["city","transaction","property_type"]):
        base = grp[grp["year_quarter"] == base_period]["price"].median()
        if pd.isna(base) or base == 0:
            continue
        for yq, sub in grp.groupby("year_quarter"):
            prices = sub["price"].dropna()
            ppm2   = sub["price_per_m2"].dropna()
            if len(prices) == 0:
                continue
            results.append({
                "year_quarter":    yq,
                "city":            city,
                "transaction":     txn,
                "property_type":   ptype,
                "index_value":     round(100 * prices.median() / base, 2),
                "avg_price":       round(prices.mean(), 0),
                "median_price":    round(prices.median(), 0),
                "avg_price_m2":    round(ppm2.mean(), 0) if len(ppm2) else None,
                "median_price_m2": round(ppm2.median(), 0) if len(ppm2) else None,
                "listing_count":   len(prices),
            })
    return pd.DataFrame(results)


def save_index(index_df: pd.DataFrame, session) -> int:
    inserted = 0
    for _, row in index_df.iterrows():
        exists = session.query(PriceIndex).filter_by(
            year_quarter  = row["year_quarter"],
            city          = row["city"],
            transaction   = row["transaction"],
            property_type = row["property_type"],
        ).first()
        if exists:
            continue
        def v(col):
            val = row.get(col)
            return None if (val is None or (isinstance(val, float) and np.isnan(val))) else val

        session.add(PriceIndex(
            year_quarter    = v("year_quarter"),
            city            = v("city"),
            transaction     = v("transaction"),
            property_type   = v("property_type"),
            index_value     = v("index_value"),
            avg_price       = v("avg_price"),
            median_price    = v("median_price"),
            avg_price_m2    = v("avg_price_m2"),
            median_price_m2 = v("median_price_m2"),
            listing_count   = int(v("listing_count")) if v("listing_count") else None,
        ))
        inserted += 1
    session.commit()
    return inserted


def run_index():
    log.info("=== Phase 9: RPPI Index Construction ===")
    session = SessionLocal()
    df = load_clean_for_index()

    if df.empty:
        log.warning("[index] No data. Run --clean first.")
        session.close()
        return

    index_df = compute_simple_index(df, INDEX["base_period"])
    log.info(f"[index] Computed {len(index_df)} index rows")

    inserted = save_index(index_df, session)
    log.success(f"[index] {inserted} new index rows saved")

    # Export
    ts  = datetime.utcnow().strftime("%Y%m%d")
    out = EXPORT_DIR / f"rppi_index_{ts}.csv"
    index_df.to_csv(out, index=False)
    log.info(f"[index] Exported → {out}")

   # Print summary
    if not index_df.empty and "city" in index_df.columns and "transaction" in index_df.columns:
        log.info(f"\n  RPPI Summary (simple median method):")
        summary = (index_df.groupby(["city","transaction"])
                   .agg(periods=("year_quarter","nunique"),
                        latest_index=("index_value","last"))
                   .reset_index())
        for _, row in summary.iterrows():
            log.info(f"  {row.city:<15} {row.transaction:<10} "
                     f"periods={row.periods}  latest index={row.latest_index:.1f}")
    else:
        log.info("  No index data to summarize yet.")

    session.close()
