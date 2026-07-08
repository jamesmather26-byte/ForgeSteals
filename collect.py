#!/usr/bin/env python3
import json
import os
import re
import html
import time
import requests
import feedparser

# Expanded target keywords to filter
KEYWORDS = [
    "GPU", "RTX", "AMD", "Steam Deck", "Legion Go", 
    "Ally", "Handheld", "Monitor", "SSD", "MacBook", "iPhone Air",
    "Apple", "iPhone", "iPad", "AirPods", "Nvidia", "Samsung", "Google", "Galaxy",
    "Laptop", "Desktop", "PC", "Processor", "CPU", "Keyboard", "Mouse", "Headset", "Storage"
]

# Apple-specific keywords for priority sorting boost
APPLE_KEYWORDS = ["apple", "macbook", "iphone", "ipad", "airpods", "iphone air"]

SUBREDDITS = ["buildapcsales", "deals", "LaptopDeals", "PCDeals"]
SLICKDEALS_RSS = "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1"

# Headers to prevent bot blocking (especially by Reddit)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 ForgeStealsBot/2.0"
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
                    "score": 50,  # Default mid-range score for Slickdeals frontpage
                    "timestamp": entry.get("published", "")
                })
        print(f"Collected {len(deals)} filtered Amazon deals from Slickdeals.")
        return deals
    except Exception as e:
        print(f"Error fetching Slickdeals RSS: {e}")
        return []

def collect_reddit_sub(sub):
    time.sleep(2.0)
    print(f"Fetching Reddit r/{sub} JSON...")
    deals = []
    
    # 1. Try JSON endpoint first (as requested)
    try:
        url = f"https://www.reddit.com/r/{sub}/.json"
        response = requests.get(url, headers=HEADERS, timeout=15)
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
                    score = post_data.get("score", 0)
                    deals.append({
                        "title": title,
                        "link": external_url,
                        "source": f"Reddit r/{sub}",
                        "score": score,
                        "timestamp": str(created_utc)
                    })
            print(f"Collected {len(deals)} filtered Amazon deals from Reddit r/{sub} (JSON).")
            return deals
        else:
            print(f"Reddit r/{sub} JSON returned status code {response.status_code}. Trying RSS fallback...")
    except Exception as e:
        print(f"Error fetching Reddit r/{sub} JSON: {e}. Trying RSS fallback...")
        
    # 2. Fallback to RSS endpoint if JSON endpoint fails
    time.sleep(2.0)
    try:
        reddit_rss = f"https://www.reddit.com/r/{sub}/.rss"
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
                    "source": f"Reddit r/{sub}",
                    "score": 10,  # Default lower rank for RSS entries (lack upvote score metadata)
                    "timestamp": pub_date
                })
        print(f"Collected {len(deals)} filtered Amazon deals from Reddit r/{sub} (RSS Fallback).")
        return deals
    except Exception as e:
        print(f"Error fetching Reddit r/{sub} RSS fallback: {e}")
        return []

def main():
    slickdeals = collect_slickdeals()
    
    all_deals = slickdeals
    for sub in SUBREDDITS:
        all_deals += collect_reddit_sub(sub)
        
    # Deduplicate deals by matching base link URLs
    seen_links = set()
    deduped_deals = []
    for deal in all_deals:
        clean_link = deal["link"].lower().split("?")[0].rstrip("/")
        if clean_link not in seen_links:
            seen_links.add(clean_link)
            deduped_deals.append(deal)
            
    # Sorting function:
    # 1. Apple-related deals priority (boosted to the top)
    # 2. Sort by discount percentage (from title) or upvote score, whichever is higher
    def sort_key(deal):
        title_lower = deal.get("title", "").lower()
        
        # Apple priority boost
        is_apple = any(ak in title_lower for ak in APPLE_KEYWORDS)
        apple_score = 0 if is_apple else 1
        
        # Percentage discount parsing (e.g., "34% off")
        discount = 0
        match = re.search(r'(\d+)\s*%\s*off', title_lower)
        if match:
            discount = int(match.group(1))
            
        # Score ranking
        rank_score = max(discount, deal.get("score", 0))
        
        return (apple_score, -rank_score)
        
    deduped_deals.sort(key=sort_key)
    
    # Save output to raw_deals.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "raw_deals.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(deduped_deals, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully saved {len(deduped_deals)} Amazon-only deals to {output_path}")

if __name__ == "__main__":
    main()
