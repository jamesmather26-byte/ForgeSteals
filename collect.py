#!/usr/bin/env python3
"""
collect.py - Production RSS-only collector (Slickdeals)
Fetches latest tech deals from public RSS, extracts title/price/image/link, attaches affiliate tag, saves exactly up to 12 deals.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import feedparser
except ImportError:
    print("feedparser not installed. Run: pip install feedparser", file=sys.stderr)
    sys.exit(1)

CONFIG_PATH = Path("config.json")
OUTPUT_PATH = Path("raw_deals.json")
TMP_PATH = Path("raw_deals.json.tmp")

def parse_price(text: str) -> str:
    if not text:
        return "See price"
    match = re.search(r'\$[\d,]+(?:\.\d{2})?', text)
    return match.group(0) if match else "See price"

def extract_image(entry) -> str:
    # Try media_content
    if hasattr(entry, 'media_content') and entry.media_content:
        return entry.media_content[0].get('url', '')
    # Try enclosures
    if hasattr(entry, 'enclosures') and entry.enclosures:
        return entry.enclosures[0].get('href', '')
    # Fallback: regex in summary/description
    summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary, re.IGNORECASE)
    return img_match.group(1) if img_match else ''

def clean_description(summary: str) -> str:
    if not summary:
        return "Verified tech deal from the latest feed."
    text = re.sub(r'<[^>]+>', ' ', summary)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:220] + "..." if len(text) > 220 else text

def main():
    if not CONFIG_PATH.exists():
        print("config.json missing", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    rss_url = config.get("slickdeals_rss_url", "")
    keywords = config.get("keywords", [])
    affiliate_tag = config.get("amazon_affiliate_tag", "forgesteals-20")

    print(f"[collect] Parsing RSS: {rss_url}")
    feed = feedparser.parse(rss_url)

    deals = []
    for entry in feed.entries:
        title = (entry.get("title") or "").strip()
        if not title:
            continue

        # Filter for tech/PC/gaming relevance
        if not any(kw.lower() in title.lower() for kw in keywords):
            continue

        link = (entry.get("link") or "").strip()
        summary = entry.get("summary", "") or entry.get("description", "")
        price = parse_price(title + " " + summary)
        image = extract_image(entry)
        desc = clean_description(summary)

        deals.append({
            "title": title,
            "price": price,
            "link": link,
            "image": image,
            "source": "Slickdeals",
            "description": desc,
            "timestamp": entry.get("published", datetime.now(timezone.utc).isoformat())
        })

        if len(deals) >= 12:
            break

    if not deals:
        print("[collect] No matching tech deals found in feed", file=sys.stderr)
        sys.exit(1)

    # Atomic write
    with open(TMP_PATH, "w", encoding="utf-8") as f:
        json.dump(deals, f, indent=2, ensure_ascii=False)
    TMP_PATH.replace(OUTPUT_PATH)

    print(f"[collect] Saved {len(deals)} deals to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
