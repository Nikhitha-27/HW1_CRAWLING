#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q5 — Parse reviews from Yelp HTML saved in Q4.
Defaults to ../Q4-curl/listing_fr.html (your screenshot layout).

Outputs: parsed.json and parsed.csv in the current (Q5-parse) folder.
Extracted fields per review: reviewer, stars, date_local, text
Plus business fields on each row: business_name, overall_rating, total_review_count, priceRange
"""

import sys, re, json, csv, html
from pathlib import Path

from bs4 import BeautifulSoup

# ---------- config ----------
DEFAULT_INPUT = Path("../Q4-curl/listing_fr.html")  # <- matches your screenshot
JSON_OUT = Path("parsed.json")
CSV_OUT  = Path("parsed.csv")

# ---------- helpers ----------
def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def unesc(s: str) -> str:
    return html.unescape(s or "")

def extract_business_info(soup: BeautifulSoup) -> dict:
    """Prefer JSON-LD; fall back to page header."""
    info = {"name":"", "overall_rating":"", "total_review_count":"", "priceRange":""}
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string)
        except Exception:
            continue
        if isinstance(data, dict) and data.get("@type") in {"LocalBusiness","Restaurant","Organization"}:
            info["name"] = info["name"] or data.get("name","") or ""
            agg = data.get("aggregateRating") or {}
            if isinstance(agg, dict):
                rv = agg.get("ratingValue")
                rc = agg.get("reviewCount")
                info["overall_rating"] = info["overall_rating"] or (str(rv) if rv is not None else "")
                info["total_review_count"] = info["total_review_count"] or (str(rc) if rc is not None else "")
            pr = data.get("priceRange")
            if pr:
                info["priceRange"] = pr
    if not info["name"]:
        h = soup.find(["h1","h2"])
        if h: info["name"] = norm(h.get_text(" ", strip=True))
    return info

def parse_embedded_json(html_text: str) -> tuple[list[dict], dict]:
    """
    Parse Yelp's embedded Apollo-style JSON from <script> tags.
    Handles HTML-escaped JSON and <!-- ... --> wrappers.
    Returns (reviews, users_by_id).
    """
    soup = BeautifulSoup(html_text, "lxml")
    reviews, users = [], {}

    # collect script contents
    for tag in soup.find_all("script"):
        content = tag.string if tag.string is not None else tag.get_text()
        if not content:
            continue
        u = unesc(content).strip()

        # Some payloads are wrapped as HTML comments: <!-- { ... } -->
        if u.startswith("<!--") and u.endswith("-->"):
            u = u[4:-3].strip()

        # Try parse as JSON object with many cache entries:
        # {"Review:xxxx": {...}, "User:yyyy": {...}, ...}
        try:
            data = json.loads(u)
        except Exception:
            # Not a pure JSON blob; skip
            continue

        if not isinstance(data, dict):
            continue

        for key, val in data.items():
            if not isinstance(val, dict):
                continue

            t = val.get("__typename")
            if t == "Review":
                # Prefer text.full, fallback to text.plain
                text = (val.get("text") or {}).get("full") or (val.get("text") or {}).get("plain") or ""
                rating = val.get("rating")
                date_local = (val.get("createdAt") or {}).get("localDateTimeForBusiness") or val.get("localizedDate") or ""
                review_id = val.get("encid") or val.get("reviewId") or key

                author_ref = ""
                a = val.get("author")
                if isinstance(a, dict) and "__ref" in a:
                    author_ref = a["__ref"].split(":", 1)[-1]

                if text and norm(text):
                    reviews.append({
                        "review_id": review_id,
                        "author_ref": author_ref,
                        "stars": rating,
                        "date_local": date_local,
                        "text": norm(text),
                    })

            elif t == "User":
                uid = key.split(":", 1)[-1]
                display = unesc(val.get("displayName") or "")
                if uid and display:
                    users[uid] = display

    return reviews, users

def dom_fallback_extract(soup: BeautifulSoup) -> list[dict]:
    """
    Very light DOM fallback for mobile/AMP pages that contain inline review cards.
    This only runs if the embedded JSON path yielded 0 results.
    """
    out = []
    # Look for containers that have 'star rating' (English) or 'étoile' (French) and a paragraph.
    def looks_like_card(tag):
        try:
            has_star = tag.find(attrs={"aria-label": re.compile(r"(star rating|étoile)", re.I)}) is not None
            has_p = tag.find("p") is not None
            return has_star and has_p
        except Exception:
            return False

    for t in soup.find_all(["article","section","div","li"]):
        if not looks_like_card(t):
            continue
        # stars
        stars = ""
        star_el = t.find(attrs={"aria-label": re.compile(r"(star rating|étoile)", re.I)})
        if star_el:
            label = star_el.get("aria-label", "") or star_el.get_text(" ", strip=True)
            m = re.search(r"([0-9]+(?:[.,][0-9]+)?)", label)
            if m:
                stars = m.group(1).replace(",", ".")

        # date (loose)
        date = ""
        for d in t.find_all(["time","span","div"]):
            s = d.get_text(" ", strip=True)
            if re.search(r"\b20\d{2}\b", s) or re.search(r"(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)", s, re.I):
                date = s
                break

        # reviewer
        reviewer = ""
        a = t.find("a", href=re.compile(r"/user_details", re.I))
        if a and a.get_text(strip=True):
            reviewer = norm(a.get_text(" ", strip=True))

        # text
        ps = [norm(p.get_text(" ", strip=True)) for p in t.find_all("p")]
        ps = [p for p in ps if p]
        text = max(ps, key=len) if ps else ""

        if text:
            out.append({
                "review_id": "",
                "reviewer": reviewer,
                "stars": stars,
                "date_local": date,
                "text": text
            })

    return out

def main():
    in_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    if not in_path.exists():
        sys.exit(f"Input file not found: {in_path}")

    raw = in_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(raw, "lxml")

    # 1) Embedded JSON path
    reviews, users = parse_embedded_json(raw)
    for r in reviews:
        r["reviewer"] = users.get(r.pop("author_ref", ""), "")

    # 2) DOM fallback (only if needed)
    if not reviews:
        reviews = dom_fallback_extract(soup)

    # Business info for extra fields
    biz = extract_business_info(soup)

    # Sort newest first if dates look sortable
    reviews.sort(key=lambda r: r.get("date_local",""), reverse=True)

    # Save JSON
    JSON_OUT.write_text(
        json.dumps({"business": biz, "count": len(reviews), "reviews": reviews}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # Save CSV
    fields = ["review_id","reviewer","stars","date_local","text","business_name","overall_rating","total_review_count","priceRange"]
    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in reviews:
            row = {
                **r,
                "business_name": biz.get("name",""),
                "overall_rating": biz.get("overall_rating",""),
                "total_review_count": biz.get("total_review_count",""),
                "priceRange": biz.get("priceRange",""),
            }
            w.writerow(row)

    print(f"Parsed {len(reviews)} reviews → {CSV_OUT}, {JSON_OUT}")
    if len(reviews) < 5:
        print("Note: If you still see <5, re-fetch via m.yelp.com/AMP with cookies and run again; this parser will pick them up.")

if __name__ == "__main__":
    main()
