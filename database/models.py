"""
database/models.py
Full database schema for Morocco RPPI project.
Follows Phase 4 statistical data model.
4 tables: raw_listings, clean_listings, price_history, scrape_logs
"""

from datetime import datetime
from sqlalchemy import (Column, Integer, Float, String, Text,
                        DateTime, Boolean, UniqueConstraint, Index,
                        create_engine)
from sqlalchemy.orm import declarative_base, sessionmaker
from config.settings import DATABASE_URL

Base = declarative_base()


class RawListing(Base):
    """Raw scraped data — never modified after insert."""
    __tablename__ = "raw_listings"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    source        = Column(String(50),  nullable=False)
    url           = Column(Text)
    listing_hash  = Column(String(32),  unique=True)
    title         = Column(Text)
    city          = Column(String(100))
    neighborhood  = Column(String(200))
    raw_price     = Column(String(100))
    raw_surface   = Column(String(100))
    raw_rooms     = Column(String(50))
    scraped_at    = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_raw_city",    "city"),
        Index("ix_raw_source",  "source"),
        Index("ix_raw_scraped", "scraped_at"),
    )


class CleanListing(Base):
    """
    Phase 4 statistical data model.
    All variables classified per IMF RPPI Handbook.
    """
    __tablename__ = "clean_listings"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    raw_id         = Column(Integer)

    # ── Source ────────────────────────────────────────────
    source         = Column(String(50))
    url            = Column(Text)
    title          = Column(Text)

    # ── Location variables ────────────────────────────────
    city           = Column(String(100))
    neighborhood   = Column(String(200))
    region         = Column(String(200))
    latitude       = Column(Float)
    longitude      = Column(Float)

    # ── Structural variables ──────────────────────────────
    property_type  = Column(String(50))
    transaction    = Column(String(20))   # location / vente
    surface        = Column(Float)        # m²
    rooms          = Column(Integer)
    bedrooms       = Column(Integer)
    bathrooms      = Column(Integer)
    floor          = Column(Integer)

    # ── Target variables ──────────────────────────────────
    price          = Column(Float)        # DH
    price_per_m2   = Column(Float)        # DH/m²
    log_price      = Column(Float)        # ln(price) for hedonic model

    # ── Temporal variables ────────────────────────────────
    scraped_at     = Column(DateTime)
    year           = Column(Integer)
    month          = Column(Integer)
    quarter        = Column(Integer)
    year_quarter   = Column(String(10))   # e.g. "2024-Q1"

    # ── Quality flags ─────────────────────────────────────
    is_outlier     = Column(Boolean, default=False)
    is_duplicate   = Column(Boolean, default=False)
    quality_score  = Column(Float)        # 0-1 completeness score
    processed_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_clean_city",        "city"),
        Index("ix_clean_transaction", "transaction"),
        Index("ix_clean_type",        "property_type"),
        Index("ix_clean_yearq",       "year_quarter"),
        Index("ix_clean_scraped",     "scraped_at"),
    )


class PriceIndex(Base):
    """
    Phase 9: RPPI values by period, city, transaction, property type.
    Time dummy method output — base period = 2024-Q1 = 100.
    """
    __tablename__ = "price_index"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    year_quarter    = Column(String(10),  nullable=False)  # "2024-Q1"
    city            = Column(String(100), nullable=False)
    transaction     = Column(String(20),  nullable=False)  # location / vente
    property_type   = Column(String(50))
    index_value     = Column(Float)        # base 100
    avg_price       = Column(Float)
    median_price    = Column(Float)
    avg_price_m2    = Column(Float)
    median_price_m2 = Column(Float)
    listing_count   = Column(Integer)
    computed_at     = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("year_quarter","city","transaction","property_type",
                         name="uq_index"),
        Index("ix_idx_city_yearq", "city", "year_quarter"),
    )


class ScrapeLog(Base):
    """One row per scraper run — for monitoring."""
    __tablename__ = "scrape_logs"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    source           = Column(String(50))
    city             = Column(String(100))
    started_at       = Column(DateTime)
    finished_at      = Column(DateTime)
    pages_scraped    = Column(Integer, default=0)
    records_found    = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    errors           = Column(Integer, default=0)
    status           = Column(String(20), default="running")


engine       = create_engine(DATABASE_URL, echo=False,
               connect_args={"check_same_thread": False}
               if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created / verified.")
