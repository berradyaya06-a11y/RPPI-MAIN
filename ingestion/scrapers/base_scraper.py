"""ingestion/scrapers/base_scraper.py — abstract base class"""
import time, random, requests
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional
from config.settings import REQUEST_DELAY_MIN, REQUEST_DELAY_MAX, REQUEST_TIMEOUT, MAX_RETRIES
from utils.helpers import get_headers
from utils.logger import log

class BaseScraper(ABC):
    source_name: str = "base"

    def __init__(self, city: str, max_pages: int = 15):
        self.city      = city
        self.max_pages = max_pages
        self.session   = requests.Session()
        self.session.headers.update(get_headers())
        self._errors   = 0

    @abstractmethod
    def build_url(self, page: int, transaction: str) -> str: ...

    @abstractmethod
    def scrape_page(self, url: str) -> List[Dict]: ...

    def fetch(self, url: str) -> Optional[requests.Response]:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self.session.headers.update(get_headers())
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 404:
                    log.warning(f"[{self.source_name}] 404: {url}")
                    return None
                if resp.status_code in (429, 503):
                    time.sleep(30 * attempt)
                    continue
                resp.raise_for_status()
                return resp
            except requests.exceptions.RequestException as e:
                log.warning(f"[{self.source_name}] attempt {attempt}: {e}")
                time.sleep(5 * attempt)
        self._errors += 1
        return None

    def add_metadata(self, listing: Dict) -> Dict:
        listing["source"]     = self.source_name
        listing["city"]       = self.city
        listing["scraped_at"] = datetime.utcnow().isoformat()
        return listing

    def run(self) -> List[Dict]:
        all_listings = []
        for transaction in ["location", "vente"]:
            log.info(f"[{self.source_name}][{self.city}] {transaction}...")
            for page in range(1, self.max_pages + 1):
                url      = self.build_url(page, transaction)
                listings = self.scrape_page(url)
                if not listings:
                    break
                stamped = [self.add_metadata(l) for l in listings]
                all_listings.extend(stamped)
                log.info(f"  page {page}: {len(listings)} listings")
                time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))
        log.success(f"[{self.source_name}][{self.city}] total: {len(all_listings)}")
        return all_listings
