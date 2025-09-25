import requests, csv, json, time
from bs4 import BeautifulSoup

BASE_URL = "https://www.tripadvisor.com/Restaurant_Review-g44881-d441712-Reviews"
OUTPUT_CSV = "multi_reviews.csv"
OUTPUT_JSON = "multi_reviews.json"

def fetch_page(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def parse_reviews(html):
    soup = BeautifulSoup(html, "html.parser")
    reviews = []
    cards = soup.select('div[data-test-target="HR_CC_CARD"]')
    for c in cards:
        reviewer = c.select_one('a.ui_header_link')
        rating = c.select_one('span.ui_bubble_rating')
        date = c.select_one('span[data-test-target="review-date"]')
        text = c.select_one('q span')
        reviews.append({
            "reviewer": reviewer.get_text(strip=True) if reviewer else "",
            "rating": rating.get("class", [""])[1] if rating else "",
            "date": date.get_text(strip=True) if date else "",
            "text": text.get_text(strip=True) if text else ""
        })
    return reviews

all_reviews = []

# scrape 3 pages
for i in range(3):
    url = f"{BASE_URL}-or{i*10}.html"  # TripAdvisor uses -or10, -or20 for pagination
    print(f"Fetching page {i+1}: {url}")
    html = fetch_page(url)
    if not html: continue
    reviews = parse_reviews(html)
    all_reviews.extend(reviews)
    time.sleep(2)  # polite delay

# Write CSV
with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["reviewer","rating","date","text"])
    writer.writeheader()
    writer.writerows(all_reviews)

# Write JSON
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(all_reviews, f, indent=2, ensure_ascii=False)

print(f"Saved {len(all_reviews)} reviews to {OUTPUT_CSV} and {OUTPUT_JSON}")
