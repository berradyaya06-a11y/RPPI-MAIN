"""
ingestion/scrapers/mubawab_scraper.py
Mubawab.ma — confirmed working, plain requests, no browser needed.
34 listings per page, paginated, covers location + vente.
"""
import re, time, random
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from ingestion.scrapers.base_scraper import BaseScraper
from utils.helpers import clean_price, clean_surface, clean_rooms, detect_property_type, detect_transaction
from utils.logger import log

# https://agenz.ma/

class MubawabScraper(BaseScraper):
    source_name = "mubawab"

    def build_url(self, page: int, transaction: str = "vente") -> str:
        slug = "immobilier-a-louer" if transaction == "location" else "immobilier-a-vendre"
        base = f"https://www.mubawab.ma/fr/ct/{self.city}/{slug}"
        return base if page == 1 else f"{base}:p:{page}"

    def scrape_page(self, url: str) -> List[Dict]:
        resp = self.fetch(url)
        if not resp:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        cards = (soup.find_all("li",  class_=re.compile(r"listingBox", re.I)) or
                 soup.find_all("div", class_=re.compile(r"listingBox", re.I)))
        return [r for r in [self._parse(c) for c in cards] if r]

    def _parse(self, card) -> Optional[Dict]:
        try:
            title_tag = (card.find(["h2","h3"]) or
                         card.find(class_=re.compile(r"listingH\b|title", re.I)))
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

            # Neighborhood — look for known Moroccan district names
            neighborhood = None
            for txt in card.stripped_strings:
                if re.search(r"(agdal|hay riad|souissi|hassan|maarif|ain diab|"
                             r"guéliz|hivernage|palmeraie|bourgogne|mabella|"
                             r"kénitra|fès|médina|corniche)", txt, re.I):
                    neighborhood = txt.strip()[:100]
                    break

            link = card.find("a", href=True)
            href = link["href"] if link else ""
            url  = href if href.startswith("http") else f"https://www.mubawab.ma{href}"

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
                "property_type": detect_property_type(title or ""),
                "transaction":   detect_transaction(title or "", raw_price or ""),
            }
        except Exception as e:
            log.debug(f"[mubawab] parse error: {e}")
            return None
