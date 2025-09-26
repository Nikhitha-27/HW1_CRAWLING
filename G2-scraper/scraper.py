#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G2 — Offline multi-page Yelp reviews extractor (matches your project layout).

Reads reviews from:
  - ../Q4-curl/listing_fr.html            (your Q4 file)
  - ../Q4-curl/listing_fr_10.html         (optional)
  - ../Q4-curl/listing_fr_20.html         (optional)
  - ./pages/*.html                        (optional folder of extra pages)

Merges and dedupes into: data.json (SLUview-ready) and data.csv
"""

import json, csv, html, re, sys
from pathlib import Path
from typing import List, Dict, Tuple
from bs4 import BeautifulSoup

# ---------- config: paths that match your screenshot ----------
Q4_DIR = Path("../Q4-curl")
DEFAULT_FILES = [
    Q4_DIR / "listing_fr.html",
    Q4_DIR / "listing_fr_10.html",
    Q4_DIR / "listing_fr_20.html",
]
PAGES_DIR = Path("./pages")   # any extra saved pages go here (*.html)

OUT_JSON = Path("data.json")
OUT_CSV  = Path("data.csv")

# ---------- helpers ----------
def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def unesc(s: str) -> str:
    return html.unescape(s or "")

def extract_reviews_from_html(raw_html: str) -> Tuple[List[Dict], Dict[str, str]]:
    """
    Parse Yelp embedded JSON from <script> tags (handles HTML-escaped and <!-- ... --> wrapped JSON).
    Returns (reviews, users_by_id)
    """
    soup = BeautifulSoup(raw_html, "lxml")
    reviews, users = [], {}

    for tag in soup.find_all("script"):
        txt = tag.string if tag.string is not None else tag.get_text()
        if not txt:
            continue
        u = unesc(txt).strip()
        if u.startswith("<!--") and u.endswith("-->"):
            u = u[4:-3].strip()
        # try parse as big object with keys like "Review:...", "User:..."
        try:
            data = json.loads(u)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue

        for key, val in data.items():
            if not isinstance(val, dict):
                continue
            t = val.get("__typename")
            if t == "Review":
                text = (val.get("text") or {}).get("full") or (val.get("text") or {}).get("plain") or ""
                if not text.strip():
                    continue
                rating = val.get("rating")
                date_local = (val.get("createdAt") or {}).get("localDateTimeForBusiness") \
                             or val.get("localizedDate") or ""
                review_id = val.get("encid") or val.get("reviewId") or key
                author_ref = ""
                a = val.get("author")
                if isinstance(a, dict) and "__ref" in a:
                    author_ref = a["__ref"].split(":", 1)[-1]
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

def attach_reviewers(reviews: List[Dict], users: Dict[str, str]) -> None:
    for r in reviews:
        if "author_ref" in r:
            r["reviewer"] = users.get(r.pop("author_ref", ""), "")

def dedupe_and_sort(reviews: List[Dict]) -> List[Dict]:
    seen, out = set(), []
    for r in reviews:
        if not r.get("text"):
            continue
        rid = r.get("review_id") or (r.get("reviewer","") + "|" + r.get("date_local",""))
        if rid in seen:
            continue
        seen.add(rid)
        out.append(r)
    out.sort(key=lambda x: x.get("date_local",""), reverse=True)
    return out

def write_outputs(reviews: List[Dict]) -> None:
    OUT_JSON.write_text(json.dumps({"count": len(reviews), "reviews": reviews}, ensure_ascii=False, indent=2), encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["review_id","reviewer","stars","date_local","text"])
        w.writeheader(); w.writerows(reviews)

def main():
    # Build the list of files to parse, in this order
    files = []
    files.extend([p for p in DEFAULT_FILES if p.exists()])
    if PAGES_DIR.exists():
        files.extend(sorted(PAGES_DIR.glob("*.html")))

    if not files:
        print("[ERROR] No HTML files found. Put your Q4 file at ../Q4-curl/listing_fr.html or add pages/*.html")
        sys.exit(1)

    print("[INFO] Reading these files:")
    for p in files:
        print("   -", p)

    all_reviews: List[Dict] = []
    user_map: Dict[str, str] = {}

    for fp in files:
        raw = fp.read_text(encoding="utf-8", errors="ignore")
        page_reviews, users = extract_reviews_from_html(raw)
        attach_reviewers(page_reviews, users)
        all_reviews.extend(page_reviews)
        # keep a global user cache in case you need it later
        user_map.update(users)
        print(f"[OK] {fp.name}: found {len(page_reviews)} reviews")

    final_reviews = dedupe_and_sort(all_reviews)
    print(f"[OK] Total unique reviews aggregated: {len(final_reviews)}")

    write_outputs(final_reviews)
    print(f"[DONE] Wrote {OUT_JSON} and {OUT_CSV}")
    if len(final_reviews) < 15:
        print("[NOTE] Fewer than 15 reviews. Save two more pages as:")
        print("       ../Q4-curl/listing_fr_10.html and ../Q4-curl/listing_fr_20.html")
        print("   or  put extra files in ./pages/ (e.g., page0.html, page10.html, page20.html) then rerun.")

if __name__ == "__main__":
    main()
