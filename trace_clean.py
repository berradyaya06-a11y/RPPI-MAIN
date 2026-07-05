"""
trace_clean.py — run from project root.

Runs the cleaning pipeline stage-by-stage on Agenz raw rows ONLY and
prints how many survive each step, so we can see exactly where they
get dropped (bad parsing? outlier filter? dedup?).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from database.models import SessionLocal, RawListing, CleanListing
from processing.cleaner import parse_fields, remove_duplicates, filter_outliers, enrich

session = SessionLocal()

rows = session.query(RawListing).filter_by(source="agenz").all()
print(f"Total agenz rows in raw_listings: {len(rows)}")

if not rows:
    print("❌ No agenz rows in raw_listings at all — re-run ingestion first:")
    print("   python main.py --ingest --source agenz")
    sys.exit(0)

# Show 3 raw samples as-is
print("\n--- 3 raw samples ---")
for r in rows[:3]:
    print(f"  title={r.title!r}")
    print(f"  raw_price={r.raw_price!r}  raw_surface={r.raw_surface!r}  raw_rooms={r.raw_rooms!r}")
    print()

df = pd.DataFrame([{
    "raw_id": r.id, "source": r.source, "url": r.url,
    "title": r.title, "city": r.city, "neighborhood": r.neighborhood,
    "raw_price": r.raw_price, "raw_surface": r.raw_surface,
    "raw_rooms": r.raw_rooms, "scraped_at": r.scraped_at,
} for r in rows])

print(f"\nStage 0 (loaded):              {len(df)}")

df = parse_fields(df)
print(f"Stage 1 (after parse_fields):  {len(df)}  "
      f"(price non-null: {df['price'].notna().sum()}, "
      f"surface non-null: {df['surface'].notna().sum()})")

df = remove_duplicates(df)
print(f"Stage 2 (after dedup by url):  {len(df)}")

df = filter_outliers(df)
print(f"Stage 3 (after outlier filter): price non-null now: {df['price'].notna().sum()}")

df = enrich(df)
df_valid = df.dropna(subset=["price"])
print(f"Stage 4 (final, price required): {len(df_valid)} / {len(df)}")

if len(df_valid) == 0 and len(df) > 0:
    print("\n⚠️  All rows lost price somewhere. Sample of what parse_fields produced:")
    print(df[["title", "raw_price", "price", "raw_surface", "surface"]].head(5).to_string())

already_cleaned = {r[0] for r in session.query(CleanListing.raw_id)
                          .filter(CleanListing.source == "agenz").all()}
print(f"\nAlready in clean_listings for agenz: {len(already_cleaned)}")

session.close()