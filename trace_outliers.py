"""
trace_outliers.py — run from project root.

Replicates filter_outliers() step-by-step on real Agenz data, printing
the actual price stats per (city, transaction) group so we can see
exactly why it's collapsing almost everything to NaN.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
from database.models import SessionLocal, RawListing
from processing.cleaner import parse_fields, remove_duplicates
from config.settings import SURFACE_BOUNDS, ROOMS_BOUNDS

session = SessionLocal()
rows = session.query(RawListing).filter_by(source="agenz").all()
df = pd.DataFrame([{
    "raw_id": r.id, "source": r.source, "url": r.url,
    "title": r.title, "city": r.city, "neighborhood": r.neighborhood,
    "raw_price": r.raw_price, "raw_surface": r.raw_surface,
    "raw_rooms": r.raw_rooms, "scraped_at": r.scraped_at,
} for r in rows])
session.close()

df = parse_fields(df)
df = remove_duplicates(df)

print(f"price dtype: {df['price'].dtype}")
print(f"price describe:\n{df['price'].describe()}\n")
print(f"city value_counts:\n{df['city'].value_counts()}\n")
print(f"transaction value_counts:\n{df['transaction'].value_counts()}\n")

df.loc[df["surface"] < SURFACE_BOUNDS["min"], "surface"] = np.nan
df.loc[df["surface"] > SURFACE_BOUNDS["max"], "surface"] = np.nan
df.loc[df["rooms"]   < ROOMS_BOUNDS["min"],   "rooms"]   = np.nan
df.loc[df["rooms"]   > ROOMS_BOUNDS["max"],   "rooms"]   = np.nan

print("=== per (city, transaction) group ===")
for (city, txn), grp in df.groupby(["city", "transaction"]):
    valid_price = grp["price"].dropna()
    print(f"\ngroup city={city!r} txn={txn!r}  n={len(grp)}  valid_price_n={len(valid_price)}")
    if len(grp) < 10:
        print("  -> SKIPPED (fewer than 10 rows, kept as-is)")
        continue
    if len(valid_price) == 0:
        print("  -> ALL PRICES NaN IN THIS GROUP (quantile will be NaN!)")
        continue
    q1 = valid_price.quantile(0.05)
    q3 = valid_price.quantile(0.95)
    print(f"  q1(5%)={q1}  q3(95%)={q3}")
    kept = valid_price[(valid_price >= q1) & (valid_price <= q3)]
    print(f"  would keep {len(kept)} / {len(valid_price)} rows in this group")