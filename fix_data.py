"""
fix_data.py
Fixes all 6 data problems identified in the diagnosis.
Run once: python fix_data.py
"""
import sys, os
sys.path.insert(0, os.path.expanduser("~/Downloads/rppi_maroc"))

import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path

CSV_IN  = "data/clean/clean_20260609_2146.csv"
CSV_OUT = "data/clean/rppi_fixed.csv"

print("Loading data...")
df = pd.read_csv(CSV_IN)
print(f"  Rows loaded: {len(df)}")

# ── FIX 1: Re-classify 'inconnu' using price threshold ────
# Mubawab Morocco: rentals are always < 80,000 DH/month
# Sales are always >= 80,000 DH total
print("\nFIX 1: Re-classifying 'inconnu' transactions...")
before_inc = (df['transaction'] == 'inconnu').sum()

df.loc[(df['transaction'] == 'inconnu') & (df['price'] < 80000),  'transaction'] = 'location'
df.loc[(df['transaction'] == 'inconnu') & (df['price'] >= 80000), 'transaction'] = 'vente'

remaining = (df['transaction'] == 'inconnu').sum()
print(f"  Before: {before_inc} inconnu rows")
print(f"  After:  {remaining} inconnu rows remaining")
print(f"  Transaction breakdown now: {df['transaction'].value_counts().to_dict()}")

# ── FIX 2: Recompute price_per_m2 only for vente ──────────
# For location: price/m² per month is misleading, set to None
print("\nFIX 2: Fixing price_per_m2 (only meaningful for vente)...")
df.loc[df['transaction'] == 'location', 'price_per_m2'] = np.nan
# Recalculate for vente
mask_vente = (df['transaction'] == 'vente') & df['price'].notna() & df['surface'].notna() & (df['surface'] > 0)
df.loc[mask_vente, 'price_per_m2'] = (df.loc[mask_vente, 'price'] / df.loc[mask_vente, 'surface']).round(2)
print(f"  Vente price/m² median: {df[df['transaction']=='vente']['price_per_m2'].median():,.0f} DH/m²")

# ── FIX 3: Better outlier removal per transaction ─────────
print("\nFIX 3: Re-applying outlier bounds per transaction type...")
bounds = {
    'location': {'min': 1500,    'max': 80000},
    'vente':    {'min': 100000,  'max': 30000000},
}
for txn, b in bounds.items():
    mask = df['transaction'] == txn
    bad_low  = mask & (df['price'] < b['min'])
    bad_high = mask & (df['price'] > b['max'])
    n_removed = bad_low.sum() + bad_high.sum()
    df.loc[bad_low | bad_high, 'price'] = np.nan
    print(f"  {txn}: removed {n_removed} out-of-bounds prices")

# IQR per city × transaction
print("  Applying IQR 5th-95th percentile per city × transaction...")
total_iqr = 0
for (city, txn), grp in df.groupby(['city','transaction']):
    if len(grp) < 10:
        continue
    q1 = grp['price'].quantile(0.05)
    q3 = grp['price'].quantile(0.95)
    mask = (df['city'] == city) & (df['transaction'] == txn)
    n = ((df.loc[mask, 'price'] < q1) | (df.loc[mask, 'price'] > q3)).sum()
    df.loc[mask & ((df['price'] < q1) | (df['price'] > q3)), 'price'] = np.nan
    total_iqr += n
print(f"  IQR removed {total_iqr} additional outliers")

# ── FIX 4: Drop rows with no price after cleaning ─────────
before = len(df)
df = df.dropna(subset=['price'])
print(f"\nFIX 4: Dropped {before - len(df)} rows with no valid price")
print(f"  Remaining: {len(df)} rows")

# ── FIX 5: Add a proper monthly_price column for location ──
print("\nFIX 5: Adding monthly_rent column for location listings...")
df['monthly_rent'] = np.where(df['transaction'] == 'location', df['price'], np.nan)

# ── FIX 6: Recalculate quality score ──────────────────────
print("\nFIX 6: Recalculating quality scores...")
key_fields = ['price','surface','rooms','property_type','city','neighborhood']
df['quality_score'] = df[key_fields].notna().mean(axis=1)

# ── SUMMARY ───────────────────────────────────────────────
print("\n" + "="*55)
print("  FINAL DATASET SUMMARY")
print("="*55)
print(f"  Total valid records:  {len(df):,}")
for txn, grp in df.groupby('transaction'):
    prices = grp['price'].dropna()
    print(f"\n  [{txn.upper()}] n={len(prices):,}")
    print(f"    Median price:  {prices.median():>12,.0f} DH")
    print(f"    Mean price:    {prices.mean():>12,.0f} DH")
    print(f"    Min:           {prices.min():>12,.0f} DH")
    print(f"    Max:           {prices.max():>12,.0f} DH")
    if txn == 'vente':
        ppm2 = grp['price_per_m2'].dropna()
        if len(ppm2):
            print(f"    Median DH/m²:  {ppm2.median():>12,.0f} DH/m²")

print(f"\n  Cities: {df['city'].value_counts().to_dict()}")
print(f"  Quality score: {df['quality_score'].mean():.0%}")
print(f"  Note: All data is 2026-Q2 (single snapshot)")
print(f"  → Need multiple months for RPPI time series")

df.to_csv(CSV_OUT, index=False)
print(f"\n✅ Fixed CSV saved → {CSV_OUT}")
