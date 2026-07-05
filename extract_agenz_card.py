"""
extract_agenz_card.py — run from your project root, next to agenz_debug.html
(the file debug_agenz.py already saved).

Finds one real listing-card container in the saved HTML and prints its
full markup, so we can see exactly where price/surface/rooms live.
"""
import re
from bs4 import BeautifulSoup

with open("agenz_debug.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")

# Find a real listing link (not /login, not /video)
target = None
for a in soup.find_all("a", href=True):
    href = a["href"]
    if re.search(r"/annonces/immo-[^/]+/(vente|location)-[^/]+/[^/]+/\d+/?$", href):
        target = a
        break

if not target:
    print("❌ No listing link found matching the expected URL pattern.")
    raise SystemExit(1)

print(f"✅ Found listing link: {target['href']}\n")

# Climb up parents and print each level's class + a text snippet,
# so we can see exactly which ancestor contains the price.
node = target
for depth in range(8):
    if node is None:
        break
    classes = node.get("class", [])
    text_snippet = node.get_text(" ", strip=True)[:150]
    print(f"--- depth {depth} | tag=<{node.name}> class={classes} ---")
    print(f"    text: {text_snippet}")
    node = node.parent

# Print the full HTML of the container 3 levels up (usually the full card)
print("\n\n========== FULL HTML 3 LEVELS UP ==========\n")
container = target
for _ in range(3):
    if container.parent:
        container = container.parent
print(str(container)[:3000])