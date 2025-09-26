HW1 – Web Crawling and SLUview
Overview

This project implements a mini web-crawling assignment with multiple parts:

Q1: SLUview site (HTML/CSS/JSON/CSV integration).

Q2: Paper study of Towards Realistic and Reproducible Web Crawl Measurements.

Q3: Web Scraper browser extension (captured reviews from a business page).

Q4: Experiments with curl (headers, cookies, languages).

Q5: Parsing with BeautifulSoup (extracted structured reviews from Yelp).

G1 (Graduate): Ethics essay on crawling.

G2 (Graduate): Advanced multi-page scraper that collects ≥3 pages and produces ≥15 reviews.

Repository Structure
Hw1_Crawling/
│
├── index.html                # SLUview site
├── styles.css                # Styling
├── screenshots/              # Responsive screenshots (desktop/tablet/mobile)
│
├── Q4-curl/                  # curl experiments
│   ├── listing_fr.html
│   ├── listing_fr_10.html
│   ├── listing_fr_20.html
│   ├── cookies.txt
│   └── ... other variants
│
├── Q5-parse/                 # Parsing with BeautifulSoup
│   ├── parse.py
│   ├── parsed.json
│   └── parsed.csv
│
├── G2-scraper/               # Graduate multi-page scraper
│   ├── scraper.py
│   ├── data.json             # ≥15 reviews, SLUview-compatible
│   └── data.csv
│
├── paper_answers.pdf          # Q2 answers
├── slides.pdf                 # Paper presentation slides
├── video_link.txt             # Link to presentation recording
├── reflection.txt             # Reflection + ethics checklist
├── G1_essay.pdf               # Graduate ethics essay
└── .gitignore

How to Run
SLUview

Open index.html in a browser. It loads data.json / reviews.csv and renders reviews.

Q5 Parser
cd Q5-parse
python3 parse.py ../Q4-curl/listing_fr.html


Outputs: parsed.json, parsed.csv.

G2 Multi-Page Scraper
cd G2-scraper
python3 scraper.py --offline_dir ../Q4-curl


Collects ≥3 pages.

Outputs: data.json (for SLUview), data.csv.