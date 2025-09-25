from pathlib import Path
from bs4 import BeautifulSoup
import csv, json, re

# ---- config: point to your saved SingleFile page ----
IN = Path("../Q4-curl/BRD.html")  # file sits in Q5-parse
CSV_OUT = Path("parsed.csv")
JSON_OUT = Path("parsed.json")

# ---- helpers ----
def clean(s): 
    return re.sub(r"\s+", " ", (s or "")).strip()

def bubbles_to_stars(el):
    """TripAdvisor uses classes like bubble_50, bubble_45... -> 5.0, 4.5"""
    if not el: return ""
    cls = " ".join(el.get("class", []))
    m = re.search(r"bubble_(\d+)", cls)
    return (int(m.group(1)) / 10) if m else ""

# ---- load html ----
html = IN.read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "html.parser")

# ---- business-level fields (optional but counts toward >=6 fields) ----
# These vary; we try a few fallbacks.
biz_name = clean((soup.select_one("h1") or {}).get_text() if soup.select_one("h1") else "")
overall_rating = bubbles_to_stars(soup.select_one("span.ui_bubble_rating"))
price = ""
category = ""
city = ""

# try common chips near header
chips = [clean(x.get_text()) for x in soup.select("span, div") if x and x.get_text() and len(x.get_text())<=30]
for c in chips:
    if c in ("$", "$$", "$$$", "$$$$"): price = c
    # crude guesses—ok for class project:
    if c.lower() in ("seafood", "restaurants", "bars"): category = c
    if "st. louis" in c.lower(): city = c

# ---- reviews ----
rows = []
cards = (soup.select('div[data-test-target="HR_CC_CARD"]')
         or soup.select('div[data-reviewid]')
         or soup.select('div[data-test-target="review"]'))

def pull(card):
    reviewer = card.select_one('a.ui_header_link, [data-test-target="reviewer-info"] a')
    rating = card.select_one('span.ui_bubble_rating')
    date = card.select_one('span[data-test-target="review-date"], span.ratingDate')
    text = (card.select_one('q.QewHA.H4._a > span')
            or card.select_one('q > span')
            or card.find('q')
            or card.find('p'))
    title = card.select_one('a.Qwuub, a[rel="nofollow"], .KgQgP')

    d = {
        "business_name": biz_name,
        "business_category": category,
        "business_city": city,
        "business_price": price,
        "overall_rating": overall_rating,

        "reviewer": clean(reviewer.get_text(strip=True)) if reviewer else "",
        "rating_stars": bubbles_to_stars(rating) if rating else "",
        "date": clean(date.get_text(strip=True)) if date else "",
        "title": clean(title.get_text(strip=True)) if title else "",
        "text": clean(text.get_text(" ", strip=True)) if text else "",
    }
    # keep only reasonably complete reviews
    if d["rating_stars"] and len(d["text"]) >= 20:
        return d

for c in cards:
    row = pull(c)
    if row: rows.append(row)

# If fewer than 5, try a fallback: start from bubbles and walk up
if len(rows) < 5:
    for bub in soup.select("span.ui_bubble_rating"):
        block = bub
        # climb up a few levels to a card-like container
        for _ in range(8):
            if not block or block.name in ("div","article","section"):
                break
            block = block.parent
        if not block: continue
        row = pull(block)
        if row: rows.append(row)

# ---- write outputs ----
fields = ["business_name","business_category","business_city","business_price","overall_rating",
          "reviewer","rating_stars","date","title","text"]

with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k,"") for k in fields})

JSON_OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"Parsed {len(rows)} reviews -> {CSV_OUT} / {JSON_OUT}")
if len(rows) < 5:
    print("NOTE: <5 reviews. Ensure the saved page shows several expanded reviews before saving (SingleFile).")
