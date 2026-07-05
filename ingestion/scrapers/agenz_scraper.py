"""
ingestion/scrapers/agenz_scraper.py
Agenz.ma scraper.

Confirmed against a live page dump (agenz_debug.html + card inspection):
  - Astro-based site (not Next.js) — no JSON payload, plain SSR HTML.
  - Listing links look like:
      /fr/annonces/immo-casablanca/vente-appartements/racine/427541
    which already encodes city, transaction, property type AND
    neighborhood — parsed straight from the URL.
  - The <a> tag (class "_locationAdress_...") only wraps the title/address
    text. Price, rooms, bathrooms and surface live in a sibling block
    several levels up (class "_details_inner_..."), and — important —
    price amount and "DH" currency are in TWO SEPARATE <span> tags, not
    one string. So we join the whole card's text into a single string
    and regex against that, instead of checking one stripped_string at
    a time (which never matches split tokens).
  - Card text looks like:
      "2 750 000 DH 3 CH 2 SDB 163 m² Appartement à vendre Casablanca
       -Racine Ascenseur 2ème étage Parking Balcons Non meublé ..."
    i.e. price, then "<n> CH" (chambres/bedrooms), "<n> SDB" (salles de
    bain/bathrooms), "<n> m²" (surface), then title/features.
  - Response encoding was being mis-detected (accents came out as
    mojibake), so we force UTF-8 before parsing.
"""
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from ingestion.scrapers.base_scraper import BaseScraper
from utils.helpers import clean_price, clean_surface, clean_rooms, detect_property_type
from utils.logger import log

CITY_SLUGS = {
    "casablanca": "immo-casablanca",
    "rabat":      "immo-rabat",
    "marrakech":  "immo-marrakech",
    "tanger":     "immo-tanger",
    "fes":        "immo-fes",
}

# /fr/annonces/immo-{city}/{txn}-{ptype}/{neighborhood}/{id}   (no /video suffix)
LISTING_RE = re.compile(
    r"/annonces/immo-(?P<city>[^/]+)/(?P<txn>vente|location)-(?P<ptype>[^/]+)"
    r"/(?P<neigh>[^/]+)/(?P<id>\d+)/?$"
)

PRICE_RE   = re.compile(r"([\d][\d\s\u202f]{2,})\s*DH\b", re.I)
SURFACE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*m\u00b2", re.I)   # m²
ROOMS_RE   = re.compile(r"(\d+)\s*CH\b", re.I)                  # chambres
BATHS_RE   = re.compile(r"(\d+)\s*SDB\b", re.I)                 # salles de bain


class AgenzScraper(BaseScraper):
    source_name = "agenz"

    def build_url(self, page: int, transaction: str = "vente") -> str:
        slug = CITY_SLUGS.get(self.city, f"immo-{self.city}")
        action = "louer" if transaction == "location" else "acheter"
        base = f"https://www.agenz.ma/fr/{action}/{slug}"
        return base if page == 1 else f"{base}?page={page}"

    def scrape_page(self, url: str) -> List[Dict]:
        resp = self.fetch(url)
        if not resp:
            return []
        resp.encoding = "utf-8"  # fix mojibake — site's real encoding is UTF-8

        soup = BeautifulSoup(resp.text, "lxml")

        seen_ids = set()
        results = []
        for a in soup.find_all("a", href=True):
            m = LISTING_RE.search(a["href"])
            if not m or m.group("id") in seen_ids:
                continue
            seen_ids.add(m.group("id"))
            parsed = self._parse(a, m)
            if parsed:
                results.append(parsed)
        return results

    def _find_card_container(self, anchor):
        """The <a> only wraps the title. Climb parents until we hit one
        whose combined text actually contains a price — that's the
        real listing card (holds price + CH/SDB/m² + title)."""
        node = anchor
        for _ in range(6):
            if node.parent is None:
                break
            node = node.parent
            joined = " ".join(node.stripped_strings)
            if PRICE_RE.search(joined):
                return node
        return anchor.parent or anchor

    def _parse(self, anchor, url_match) -> Optional[Dict]:
        try:
            href = anchor["href"]
            url = href if href.startswith("http") else f"https://www.agenz.ma{href}"

            card = self._find_card_container(anchor)
            # IMPORTANT: join into ONE string — price amount and "DH" are
            # in separate spans, so per-string matching misses them.
            full_text = " ".join(card.stripped_strings)

            title = anchor.get_text(strip=True) or None

            price_m   = PRICE_RE.search(full_text)
            surface_m = SURFACE_RE.search(full_text)
            rooms_m   = ROOMS_RE.search(full_text)
            baths_m   = BATHS_RE.search(full_text)

            raw_price   = f"{price_m.group(1).strip()} DH" if price_m else None
            raw_surface = f"{surface_m.group(1)} m²" if surface_m else None
            raw_rooms   = f"{rooms_m.group(1)} CH" if rooms_m else None

            # Neighborhood + property type + transaction come straight from
            # the URL — far more reliable than scraping card text.
            neighborhood = url_match.group("neigh").replace("-", " ").title()
            txn = "location" if url_match.group("txn") == "location" else "vente"
            ptype_slug = url_match.group("ptype")  # e.g. "appartements", "villas"

            if not title and not raw_price:
                return None

            return {
                "title":         title,
                "neighborhood":  neighborhood,
                "raw_price":     raw_price,
                "raw_surface":   raw_surface,
                "raw_rooms":     raw_rooms,
                "url":           url,
                "price":         clean_price(raw_price),
                "surface":       clean_surface(raw_surface),
                "rooms":         clean_rooms(raw_rooms),
                "bathrooms":     int(baths_m.group(1)) if baths_m else None,
                "property_type": detect_property_type(ptype_slug) if detect_property_type(ptype_slug) != "autre"
                                  else detect_property_type(title or ""),
                "transaction":   txn,
            }
        except Exception as e:
            log.debug(f"[agenz] parse error: {e}")
            return None