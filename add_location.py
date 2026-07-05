"""
add_location_data.py
Adds rental listings from Mubawab using the correct location URLs.
Run once: python add_location_data.py
Keeps all existing data, just adds more rentals on top.
"""

import sys, os, re, time, random
sys.path.insert(0, os.path.dirname(__file__))

import requests
from bs4 import BeautifulSoup
from database.models import init_db, SessionLocal, RawListing
from utils.helpers import get_headers, clean_price, clean_surface, clean_rooms, detect_property_type, make_hash
from utils.logger import log
from datetime import datetime

init_db()

CITIES = ["casablanca", "rabat", "marrakech", "tanger"]
MAX_PAGES = 15

# Correct Mubawab location URLs (confirmed working June 2026)
LOCATION_URLS = {
    "casablanca": "https://www.mubawab.ma/fr/ct/casablanca/immobilier-a-louer",
    "rabat":      "https://www.mubawab.ma/fr/ct/rabat/immobilier-a-louer",
    "marrakech":  "https://www.mubawab.ma/fr/ct/marrakech/immobilier-a-louer",
    "tanger":     "https://www.mubawab.ma/fr/ct/tanger/immobilier-a-louer",
}


def scrape_page(url):
    resp = requests.get(url, headers=get_headers(), timeout=20)
    if resp.status_code != 200:
        return []
    soup = BeautifulSoup(resp.text, "lxml")
    cards = (soup.find_all("li",  class_=re.compile(r"listingBox", re.I)) or
             soup.find_all("div", class_=re.compile(r"listingBox", re.I)))
    results = []
    for card in cards:
        title_tag = card.find(["h2","h3"]) or card.find(class_=re.compile(r"listingH\b|title", re.I))
        title = title_tag.get_text(strip=True) if title_tag else None

        raw_price = None
        for txt in card.stripped_strings:
            if re.search(r"\d[\d\s,]+(?:DH|MAD)", txt, re.I):
                raw_price = txt; break

        raw_surface = None
        for txt in card.stripped_strings:
            if "m²" in txt:
                raw_surface = txt; break

        raw_rooms = None
        for txt in card.stripped_strings:
            if re.search(r"\d+\s*(chambre|pièce|ch\.)", txt, re.I):
                raw_rooms = txt; break

        link = card.find("a", href=True)
        href = link["href"] if link else ""
        listing_url = href if href.startswith("http") else f"https://www.mubawab.ma{href}"

        price = clean_price(raw_price)

        # Only keep real rental prices: 1500–80000 DH/month
        if not price or price < 1500 or price > 80000:
            continue

        if not title and not raw_price:
            continue

        results.append({
            "title":         title,
            "raw_price":     raw_price,
            "raw_surface":   raw_surface,
            "raw_rooms":     raw_rooms,
            "url":           listing_url,
            "price":         price,
            "surface":       clean_surface(raw_surface),
            "rooms":         clean_rooms(raw_rooms),
            "property_type": detect_property_type(title or ""),
            "transaction":   "location",
        })
    return results


def save(listings, city, session):
    inserted = 0
    for l in listings:
        h = make_hash(l.get("url",""), l.get("price"), l.get("title",""))
        try:
            if session.query(RawListing).filter_by(listing_hash=h).first():
                continue
            session.add(RawListing(
                source       = "mubawab",
                url          = l.get("url"),
                listing_hash = h,
                title        = l.get("title"),
                city         = city,
                raw_price    = l.get("raw_price"),
                raw_surface  = l.get("raw_surface"),
                raw_rooms    = l.get("raw_rooms"),
                scraped_at   = datetime.utcnow(),
            ))
            session.flush()
            inserted += 1
        except Exception:
            session.rollback()
    session.commit()
    return inserted


session = SessionLocal()
total = 0

print("="*55)
print("  Adding location data from Mubawab")
print("="*55)

for city in CITIES:
    base_url = LOCATION_URLS[city]
    city_total = 0
    print(f"\n[{city}] scraping location...")

    for page in range(1, MAX_PAGES + 1):
        url = base_url if page == 1 else f"{base_url}:p:{page}"
        listings = scrape_page(url)
        if not listings:
            print(f"  page {page}: empty, stopping")
            break
        inserted = save(listings, city, session)
        city_total += inserted
        print(f"  page {page}: {len(listings)} found → {inserted} new saved")
        time.sleep(random.uniform(2.5, 4.5))

    total += city_total
    print(f"  ✅ {city}: {city_total} new location listings added")

session.close()

print(f"\n{'='*55}")
print(f"  TOTAL NEW LOCATION LISTINGS: {total}")
print(f"{'='*55}")
print(f"\nNow run:")
print(f"  python main.py --clean")
