"""
debug_agenz.py — run this from your project root to inspect what Agenz
actually returns, so we can fix the scraper's selectors.

Usage:
    python debug_agenz.py

It will:
  1. Fetch one Agenz listing page (same headers/session as the real scraper)
  2. Save the raw HTML to agenz_debug.html so you can open it in a browser
  3. Tell you whether __NEXT_DATA__ was found and print its top-level keys
  4. Print the first 3 candidate "card" elements' raw text so we can see
     what price/surface/rooms actually look like on the page
"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bs4 import BeautifulSoup
from ingestion.scrapers.agenz_scraper import AgenzScraper

CITY = "casablanca"
TRANSACTION = "vente"

scraper = AgenzScraper(city=CITY, max_pages=1)
url = scraper.build_url(1, TRANSACTION)
print(f"Fetching: {url}\n")

resp = scraper.fetch(url)
if resp is None:
    print("❌ fetch() returned None — request failed, blocked, or non-200 status.")
    print("   Check your internet connection / try opening the URL in a browser.")
    sys.exit(1)

html = resp.text
with open("agenz_debug.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"✅ Saved raw HTML to agenz_debug.html ({len(html):,} chars)\n")

# --- Check for __NEXT_DATA__ ---
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
if m:
    print("✅ __NEXT_DATA__ script tag FOUND.")
    try:
        data = json.loads(m.group(1))
        page_props = data.get("props", {}).get("pageProps", {})
        print(f"   pageProps top-level keys: {list(page_props.keys())}")
    except json.JSONDecodeError as e:
        print(f"   ⚠️ but JSON did not parse: {e}")
else:
    print("❌ __NEXT_DATA__ NOT found — site may render listings differently "
          "(different framework, or JS-rendered client-side with no SSR payload).")

print()

# --- Check candidate HTML cards (the fallback path) ---
soup = BeautifulSoup(html, "lxml")
cards = (soup.find_all("a", href=re.compile(r"/annonce|/listing|/bien", re.I)) or
         soup.find_all(["article", "div"], class_=re.compile(r"card|listing|annonce", re.I)))
print(f"HTML fallback found {len(cards)} candidate card elements.\n")

for i, c in enumerate(cards[:3], start=1):
    print(f"--- Card {i} ---")
    print("href:", c.get("href") if c.name == "a" else (c.find("a", href=True) or {}).get("href"))
    print("text sample:", " | ".join(list(c.stripped_strings)[:15]))
    print()

print("Open agenz_debug.html in a browser (or a text editor + Ctrl-F for 'DH')")
print("to see the real price/surface markup, then share this script's output back.")