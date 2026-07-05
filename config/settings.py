"""
config/settings.py
Central configuration for Morocco RPPI project.
All constants, paths, URLs, and statistical parameters.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────
BASE_DIR      = Path(__file__).resolve().parent.parent
DATA_DIR      = BASE_DIR / "data"
RAW_DIR       = DATA_DIR / "raw"
CLEAN_DIR     = DATA_DIR / "clean"
EXPORT_DIR    = DATA_DIR / "exports"
SNAPSHOT_DIR  = DATA_DIR / "snapshots"
LOG_DIR       = BASE_DIR / "logs"
MODEL_DIR     = BASE_DIR / "ml" / "models"
DOCS_DIR      = BASE_DIR / "docs"

for _d in [RAW_DIR, CLEAN_DIR, EXPORT_DIR, SNAPSHOT_DIR, LOG_DIR, MODEL_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ── Database ──────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR}/data/rppi_maroc.db"

# ── Project metadata (Phase 1) ────────────────────────────
PROJECT = {
    "name":         "Observatoire des Prix Immobiliers — Maroc",
    "version":      "1.0.0",
    "base_year":    2024,
    "base_period":  "2024-Q1",        
    "base_quarter": "2024-Q1",
    "scope":        "Morocco national + Casablanca + Rabat",
    "audience":     "HCP / NSO / Students",
    "type":         "Experimental Statistics",
    "methodology":  "Hedonic Time Dummy Method",
    "reference":    "IMF RPPI Handbook 2013 / Eurostat HPPI Guide",
}

# ── Cities covered ────────────────────────────────────────
CITIES = {
    "casablanca": {"lat": 33.5731, "lon": -7.5898, "region": "Grand Casablanca-Settat"},
    "rabat":      {"lat": 34.0209, "lon": -6.8416, "region": "Rabat-Salé-Kénitra"},
    "marrakech":  {"lat": 31.6295, "lon": -7.9811, "region": "Marrakech-Safi"},
    "tanger":     {"lat": 35.7595, "lon": -5.8340, "region": "Tanger-Tétouan-Al Hoceïma"},
    "fes":        {"lat": 34.0181, "lon": -5.0078, "region": "Fès-Meknès"},
}

# ── Scraping ──────────────────────────────────────────────
REQUEST_DELAY_MIN  = 2.5
REQUEST_DELAY_MAX  = 5.0
REQUEST_TIMEOUT    = 20
MAX_RETRIES        = 3
MAX_PAGES_PER_CITY = 15

SOURCES = {
    "mubawab": {
        "url_vente":    "https://www.mubawab.ma/fr/ct/{city}/immobilier-a-vendre",
        "url_location": "https://www.mubawab.ma/fr/ct/{city}/immobilier-a-louer",
        "pagination":   ":p:{page}",
        "enabled":      True,
    },
    "agenz": {
        "url_vente":    "https://www.agenz.ma/fr/acheter/immo-{city}",
        "url_location": "https://www.agenz.ma/fr/louer/immo-{city}",
        "pagination":   "?page={page}",
        "enabled":      True, 
    },
}

# ── Phase 4: Statistical data model ───────────────────────
# Variable classification following IMF RPPI Handbook

TARGET_VARIABLES = ["price", "price_per_m2", "log_price"]

STRUCTURAL_VARIABLES = [
    "surface",       # m²
    "rooms",         # number of rooms
    "bedrooms",      # number of bedrooms
    "bathrooms",     # number of bathrooms
    "floor",         # floor level
    "property_type", # appartement / villa / studio / riad
]

LOCATION_VARIABLES = [
    "city",
    "neighborhood",
    "latitude",
    "longitude",
    "region",
]

TEMPORAL_VARIABLES = [
    "scraped_at",    # listing date (proxy)
    "year",
    "month",
    "quarter",
    "year_quarter",  # e.g. "2024-Q1"
]

TRANSACTION_TYPES = ["location", "vente"]

PROPERTY_TYPES = [
    "appartement", "villa", "studio", "riad",
    "duplex", "penthouse", "terrain", "bureau",
]

# ── Phase 5: Data quality bounds ──────────────────────────
PRICE_BOUNDS = {
    "location": {"min": 1_000,   "max": 80_000},   # DH/month
    "vente":    {"min": 100_000, "max": 30_000_000}, # DH total
}
SURFACE_BOUNDS    = {"min": 15,  "max": 2_000}  # m²
ROOMS_BOUNDS      = {"min": 1,   "max": 20}
PRICE_M2_BOUNDS   = {
    "location": {"min": 10,    "max": 500},    # DH/m²/month
    "vente":    {"min": 1_000, "max": 50_000}, # DH/m²
}

# ── Phase 7: Hedonic model parameters ─────────────────────
HEDONIC = {
    "model":         "semi-log-OLS",  # ln(price) ~ structural + location + time
    "target":        "log_price",
    "features":      ["surface", "rooms", "property_type", "city", "year_quarter"],
    "test_size":     0.2,
    "random_state":  42,
}

# ── Phase 9: Index parameters ─────────────────────────────
INDEX = {
    "method":        "time_dummy",   # IMF recommended for web-scraped data
    "base_period":   "2024-Q1",
    "base_value":    100.0,
    "frequency":     "quarterly",
}

# ── Dashboard ─────────────────────────────────────────────
DASHBOARD_TITLE = "🏠 Indice des Prix Résidentiels — Maroc"
DASHBOARD_PORT  = 8501