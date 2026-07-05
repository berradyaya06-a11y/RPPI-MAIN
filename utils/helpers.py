"""utils/helpers.py — shared parsing and utility functions"""
import re, time, random, hashlib
from typing import Optional
from fake_useragent import UserAgent

_ua = None

def get_headers() -> dict:
    global _ua
    try:
        if _ua is None:
            _ua = UserAgent()
        ua = _ua.random
    except Exception:
        ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/120.0.0.0 Safari/537.36")
    return {
        "User-Agent":      ua,
        "Accept-Language": "fr-MA,fr;q=0.9,ar;q=0.8",
        "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
        "Connection":      "keep-alive",
    }

def polite_sleep(a=2.5, b=5.0):
    time.sleep(random.uniform(a, b))

def clean_price(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    text = text.replace("\xa0","").replace("\u202f","").replace(" ","").replace(",",".")
    nums = re.findall(r"\d+\.?\d*", text)
    if not nums:
        return None
    raw = "".join(n.replace(".","") for n in nums[:2]) if len(nums) > 1 else nums[0]
    try:
        return float(raw)
    except ValueError:
        return None

def clean_surface(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"(\d+[\.,]?\d*)\s*m", text, re.I)
    return float(m.group(1).replace(",",".")) if m else None

def clean_rooms(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else None

def detect_property_type(title: str) -> str:
    t = (title or "").lower()
    for kw, pt in [("studio","studio"),("villa","villa"),("riad","riad"),
                   ("duplex","duplex"),("penthouse","penthouse"),
                   ("terrain","terrain"),("bureau","bureau"),
                   ("appartement","appartement"),("appart","appartement"),
                   ("chambre","chambre")]:
        if kw in t:
            return pt
    return "autre"

def detect_transaction(title: str, price_text: str = "") -> str:
    c = (title + " " + price_text).lower()
    if any(k in c for k in ["location","louer","à louer","/mois","mensuel","locati"]):
        return "location"
    if any(k in c for k in ["vente","vendre","à vendre","achat","cession"]):
        return "vente"
    price = clean_price(price_text)
    if price:
        return "location" if price < 80000 else "vente"
    return "inconnu"

def make_hash(url: str, price, title: str) -> str:
    return hashlib.md5(f"{url or ''}{price or ''}{title or ''}".encode()).hexdigest()

def price_per_m2(price, surface) -> Optional[float]:
    if price and surface and surface > 0:
        return round(price / surface, 2)
    return None
