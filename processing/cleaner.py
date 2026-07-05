"""
processing/cleaner.py
Phase 5 — Data Quality Framework
Implements: deduplication, outlier detection (IQR + bounds),
missing data handling, variable typing, enrichment.
"""
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional
from database.models import SessionLocal, RawListing, CleanListing
from utils.helpers import clean_price, clean_surface, clean_rooms, detect_property_type, detect_transaction, price_per_m2
from utils.logger import log
from config.settings import PRICE_BOUNDS, SURFACE_BOUNDS, ROOMS_BOUNDS, CITIES


def load_raw(session) -> pd.DataFrame:
    cleaned_ids = {r[0] for r in session.query(CleanListing.raw_id).all()}
    rows = session.query(RawListing).all()
    data = []
    for r in rows:
        if r.id in cleaned_ids:
            continue
        data.append({
            "raw_id": r.id, "source": r.source, "url": r.url,
            "title": r.title, "city": r.city, "neighborhood": r.neighborhood,
            "raw_price": r.raw_price, "raw_surface": r.raw_surface,
            "raw_rooms": r.raw_rooms, "scraped_at": r.scraped_at,
        })
    df = pd.DataFrame(data) if data else pd.DataFrame()
    log.info(f"[cleaner] Loaded {len(df)} new raw rows")
    return df


def parse_fields(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["price"]         = df["raw_price"].apply(clean_price)
    df["surface"]       = df["raw_surface"].apply(clean_surface)
    df["rooms"]         = df["raw_rooms"].apply(clean_rooms)
    df["property_type"] = df["title"].apply(lambda t: detect_property_type(t or ""))
    df["transaction"]   = df.apply(
        lambda r: detect_transaction(r["title"] or "", r["raw_price"] or ""), axis=1)
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    # Prefer the most complete row for a given URL: an older scrape
    # (e.g. before a scraper bugfix) may have NULL price/surface for
    # the same listing URL as a later, correct scrape. Sort so a row
    # WITH a valid price wins over one without, and among equally
    # complete rows the most recently scraped one wins — THEN dedup.
    df = df.sort_values(
        by=["price", "scraped_at"],
        ascending=[False, False],
        na_position="last",
    )
    df = df.drop_duplicates(subset=["url"], keep="first")
    log.info(f"[cleaner] Dedup: {before} → {len(df)}")
    return df


def filter_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Phase 5: Two-stage outlier detection.
    Stage 1: Hard bounds (business rules from settings).
    Stage 2: IQR per city × transaction (statistical method).
    Justification: IMF RPPI Handbook recommends combined approach.
    """
    before = len(df)

    # Stage 1 — hard bounds
    PRICE_BOUNDS = {

    "location": {"min": 1500,   "max": 80000},
    "vente":    {"min": 100000, "max": 30000000},
}
    

    df.loc[df["surface"] < SURFACE_BOUNDS["min"], "surface"] = np.nan
    df.loc[df["surface"] > SURFACE_BOUNDS["max"], "surface"] = np.nan
    df.loc[df["rooms"]   < ROOMS_BOUNDS["min"],   "rooms"]   = np.nan
    df.loc[df["rooms"]   > ROOMS_BOUNDS["max"],   "rooms"]   = np.nan

    # Stage 2 — IQR per city × transaction (5th–95th percentile)
    for (city, txn), grp in df.groupby(["city", "transaction"]):
        if len(grp) < 10:
            continue
        q1 = grp["price"].quantile(0.05)
        q3 = grp["price"].quantile(0.95)
        mask = (df["city"] == city) & (df["transaction"] == txn)
        df.loc[mask & (df["price"] < q1), "price"] = np.nan
        df.loc[mask & (df["price"] > q3), "price"] = np.nan

    after = len(df.dropna(subset=["price"]))
    log.info(f"[cleaner] Outlier filter: {before} → {after} with valid price")
    return df


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived and temporal variables."""
    df = df.copy()
    df["price_per_m2"] = df.apply(lambda r: price_per_m2(r["price"], r["surface"]), axis=1)
    df.loc[df["transaction"] == "location", "price_per_m2"] = np.nan
    df["log_price"]    = df["price"].apply(lambda p: np.log(p) if p and p > 0 else np.nan)

    # Temporal variables from scraped_at
    df["scraped_at"]   = pd.to_datetime(df["scraped_at"], errors="coerce")
    df["year"]         = df["scraped_at"].dt.year
    df["month"]        = df["scraped_at"].dt.month
    df["quarter"]      = df["scraped_at"].dt.quarter
    df["year_quarter"] = df["year"].astype(str) + "-Q" + df["quarter"].astype(str)

    # Region from city
    city_region = {c: v["region"] for c, v in CITIES.items()}
    df["region"] = df["city"].map(city_region)

    # Coordinates from city
    df["latitude"]  = df["city"].map({c: v["lat"] for c, v in CITIES.items()})
    df["longitude"] = df["city"].map({c: v["lon"] for c, v in CITIES.items()})

    # Quality score (completeness 0–1)
    key_fields = ["price","surface","rooms","property_type","city","neighborhood"]
    df["quality_score"] = df[key_fields].notna().mean(axis=1)

    df["city"] = df["city"].str.lower().str.strip()
    return df


def save_clean(df: pd.DataFrame, session) -> int:
    inserted = 0
    for _, row in df.iterrows():
        def v(col):
            val = row.get(col)
            return None if (val is None or (isinstance(val, float) and np.isnan(val))) else val

        session.add(CleanListing(
            raw_id=v("raw_id"), source=v("source"), url=v("url"), title=v("title"),
            city=v("city"), neighborhood=v("neighborhood"), region=v("region"),
            latitude=v("latitude"), longitude=v("longitude"),
            property_type=v("property_type"), transaction=v("transaction"),
            surface=v("surface"), rooms=int(v("rooms")) if v("rooms") else None,
            price=v("price"), price_per_m2=v("price_per_m2"), log_price=v("log_price"),
            scraped_at=v("scraped_at"),
            year=int(v("year")) if v("year") else None,
            month=int(v("month")) if v("month") else None,
            quarter=int(v("quarter")) if v("quarter") else None,
            year_quarter=v("year_quarter"),
            quality_score=v("quality_score"),
            processed_at=datetime.utcnow(),
        ))
        inserted += 1
    session.commit()
    return inserted


def run_cleaning():
    log.info("=== Phase 5: Data Cleaning Pipeline ===")
    session = SessionLocal()
    df = load_raw(session)
    if df.empty:
        log.info("[cleaner] Nothing to clean.")
        session.close()
        return 0

    df = parse_fields(df)
    df = remove_duplicates(df)
    df = filter_outliers(df)
    df = enrich(df)

    df_valid = df.dropna(subset=["price"])
    log.info(f"[cleaner] Valid records: {len(df_valid)} / {len(df)}")

    inserted = save_clean(df_valid, session)

    # Save CSV snapshot
    from config.settings import CLEAN_DIR
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
    out = CLEAN_DIR / f"clean_{ts}.csv"
    df_valid.to_csv(out, index=False, encoding="utf-8")
    log.success(f"[cleaner] Saved {inserted} records → {out}")

    session.close()
    return inserted