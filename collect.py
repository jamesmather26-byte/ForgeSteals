#!/usr/bin/env python3
import json
import os
import re
import html
import requests
import feedparser

# Expanded target keywords to filter
KEYWORDS = [
    "GPU", "RTX", "AMD", "Steam Deck", "Legion Go", 
    "Ally", "Handheld", "Monitor", "SSD", "MacBook", "iPhone Air",
    "Apple", "iPhone", "iPad", "AirPods", "Nvidia", "Samsung", "Google", "Galaxy"
]

# Apple-specific keywords for priority sorting boost
APPLE_KEYWORDS = ["apple", "macbook", "iphone", "ipad", "airpods", "iphone air"]

# URLs
SLICKDEALS_RSS = "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1"
REDDIT_JSON = "https://www.reddit.com/r/buildapcsales/.json"

# Headers to prevent bot blocking (especially by Reddit)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 ForgeStealsBot/1.0"
}

def title_contains_keyword(title):
    title_lower = title.lower()
    for kw in KEYWORDS:
        if kw.lower() in title_lower:
            return True
    return False

def is_direct_amazon_link(url):
    if not url:
        return False
    url_lower = url.lower()
    # Must contain amazon.com or amzn.to
    if "amazon.com" not in url_lower and "amzn.to" not in url_lower:
        return False
    # Discard if it contains redirect pages or other domains
    for bad in ["slickdeals.net", "reddit.com", "newegg.com", "bestbuy.com", "target.com", "walmart.com"]:
        if bad in url_lower:
            return False
    return True

def extract_amazon_link_from_html(html_content):
    if not html_content:
        return None
    # Find all href links
    links = re.findall(r'href="([^"]+)"', html_content)
    for link in links:
        decoded_link = html.unescape(link)
        if is_direct_amazon_link(decoded_link):
            return decoded_link
    return None

def collect_slickdeals():
    print("Fetching Slickdeals RSS feed...")
    try:
        response = requests.get(SLICKDEALS_RSS, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        deals = []
        for entry in feed.entries:
            title = entry.get("title", "")
            
            # Check title keywords first
            if not title_contains_keyword(title):
                continue
                
            # Attempt to extract direct Amazon link
            link = entry.get("link", "")
            if not is_direct_amazon_link(link):
                # Try from summary/content
                content = entry.get("summary", "") or entry.get("description", "")
                link = extract_amazon_link_from_html(content)
                
            if link:
                deals.append({
                    "title": title,
                    "link": link,
                    "source": "Slickdeals",
                    "timestamp": entry.get("published", "")
                })
        print(f"Collected {len(deals)} filtered Amazon deals from Slickdeals.")
        return deals
    except Exception as e:
        print(f"Error fetching Slickdeals RSS: {e}")
        return []

def collect_reddit():
    print("Fetching Reddit r/buildapcsales JSON...")
    deals = []
    
    # 1. Try JSON endpoint first (as requested)
    try:
        response = requests.get(REDDIT_JSON, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            for post in posts:
                post_data = post.get("data", {})
                if post_data.get("stickied", False):
                    continue
                    
                title = post_data.get("title", "")
                if not title_contains_keyword(title):
                    continue
                    
                external_url = post_data.get("url", "")
                if is_direct_amazon_link(external_url):
                    created_utc = post_data.get("created_utc", "")
                    deals.append({
                        "title": title,
                        "link": external_url,
                        "source": "Reddit r/buildapcsales",
                        "timestamp": str(created_utc)
                    })
            print(f"Collected {len(deals)} filtered Amazon deals from Reddit (JSON).")
            return deals
        else:
            print(f"Reddit JSON returned status code {response.status_code}. Trying RSS fallback...")
    except Exception as e:
        print(f"Error fetching Reddit JSON: {e}. Trying RSS fallback...")
        
    # 2. Fallback to RSS endpoint if JSON endpoint fails
    try:
        reddit_rss = "https://www.reddit.com/r/buildapcsales/.rss"
        response = requests.get(reddit_rss, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        for entry in feed.entries:
            title = entry.get("title", "")
            if not title_contains_keyword(title):
                continue
                
            # Parse external link from the content value HTML
            content_val = ""
            if entry.get("content"):
                content_val = entry.content[0].get("value", "")
            elif entry.get("summary"):
                content_val = entry.get("summary", "")
                
            link = extract_amazon_link_from_html(content_val)
            
            if link:
                pub_date = entry.get("updated", "") or entry.get("published", "")
                deals.append({
                    "title": title,
                    "link": link,
                    "source": "Reddit r/buildapcsales",
                    "timestamp": pub_date
                })
        print(f"Collected {len(deals)} filtered Amazon deals from Reddit (RSS Fallback).")
        return deals
    except Exception as e:
        print(f"Error fetching Reddit RSS fallback: {e}")
        return []

def main():
    slickdeals = collect_slickdeals()
    reddit_deals = collect_reddit()
    
    all_deals = slickdeals + reddit_deals
    
    # Priority sorting rule: Apple deals first
    def sort_key(deal):
        title_lower = deal.get("title", "").lower()
        is_apple = any(ak in title_lower for ak in APPLE_KEYWORDS)
        # 0 for Apple (boosted to top), 1 for non-Apple
        return 0 if is_apple else 1
        
    all_deals.sort(key=sort_key)
    
    # Save output to raw_deals.json in the same folder as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "raw_deals.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_deals, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully saved {len(all_deals)} Amazon-only deals to {output_path} (Apple deals boosted).")

if __name__ == "__main__":
    main()
