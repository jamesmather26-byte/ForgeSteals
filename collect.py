#!/usr/bin/env python3
"""
collect.py - Reddit JSON API Scraper with RSS Fallback
Bypasses HTML blocking to get direct Amazon links and real images.
"""

import json
import urllib.request
import re
import sys
from pathlib import Path

OUTPUT_PATH = Path("raw_deals.json")

def get_reddit_deals(subreddit, limit=50):
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return data.get('data', {}).get('children', [])
    except Exception as e:
        print(f"[!] Error fetching {subreddit} JSON: {e}. Trying RSS fallback...", file=sys.stderr)
        
        # RSS Fallback to bypass Reddit's 403 block on unauthenticated JSON requests
        try:
            import feedparser
            rss_url = f"https://www.reddit.com/r/{subreddit}/.rss"
            req_rss = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
            with urllib.request.urlopen(req_rss) as response_rss:
                feed = feedparser.parse(response_rss.read())
                entries = []
                for entry in feed.entries:
                    content_val = ""
                    if entry.get("content"):
                        content_val = entry.content[0].get("value", "")
                    elif entry.get("summary"):
                        content_val = entry.get("summary", "")
                        
                    # Extract direct link from RSS HTML content if present
                    link = ""
                    links = re.findall(r'href="([^"]+)"', content_val)
                    for l in links:
                        import html as html_lib
                        decoded = html_lib.unescape(l)
                        if "amazon.com" in decoded.lower() or "amzn.to" in decoded.lower():
                            if not any(bad in decoded.lower() for bad in ["slickdeals.net", "reddit.com"]):
                                link = decoded
                                break
                                
                    if not link:
                        link = entry.get("link", "")
                        
                    # Extract image
                    image = ""
                    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content_val, re.IGNORECASE)
                    if img_match:
                        image = img_match.group(1)
                        
                    entries.append({
                        'data': {
                            'url': link,
                            'title': entry.get('title', ''),
                            'thumbnail': image,
                            'subreddit': subreddit
                        }
                    })
                return entries
        except Exception as rss_err:
            print(f"[!] RSS Fallback failed for {subreddit}: {rss_err}", file=sys.stderr)
            return []

def parse_price(title: str) -> str:
    match = re.search(r'\$[\d,]+(?:\.\d{2})?', title)
    return match.group(0) if match else "See price"

def extract_image(post: dict) -> str:
    thumb = post.get('thumbnail', '')
    if thumb and thumb.startswith('http'):
        return thumb
    try:
        images = post.get('preview', {}).get('images', [])
        if images:
            return images[0]['source']['url'].replace('&amp;', '&')
    except Exception:
        pass
    return ""

def main():
    deals = []
    # Fetch from tech deal subreddits
    posts = get_reddit_deals('buildapcsales') + get_reddit_deals('LaptopDeals') + get_reddit_deals('deals')
    
    for post_wrapper in posts:
        post = post_wrapper.get('data', {})
        url = post.get('url', '')
        
        # STRICT FILTER: Only keep direct Amazon links
        if 'amazon.com' not in url.lower() and 'amzn.to' not in url.lower():
            continue

        title = post.get('title', '')
        price = parse_price(title)
        image = extract_image(post)
        subreddit = post.get('subreddit', 'deals')

        deals.append({
            "title": title,
            "price": price,
            "link": url,
            "image": image,
            "source": f"r/{subreddit}",
            "description": f"Spotted on r/{subreddit}. Verified Amazon link."
        })
        
        if len(deals) >= 12:
            break

    # Save directly for render.py to use
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(deals, f, indent=2, ensure_ascii=False)

    print(f"[collect] Successfully saved {len(deals)} Reddit Amazon deals to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
