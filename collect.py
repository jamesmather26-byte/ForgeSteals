#!/usr/bin/env python3
import json
import os
import re
import html
import time
import random
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

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]

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
    if "amazon.com" not in url_lower and "amzn.to" not in url_lower:
        return False
    for bad in ["slickdeals.net", "reddit.com", "newegg.com", "bestbuy.com", "target.com", "walmart.com"]:
        if bad in url_lower:
            return False
    return True

def extract_amazon_link_from_html(html_content):
    if not html_content:
        return None
    links = re.findall(r'href="([^"]+)"', html_content)
    for link in links:
        decoded_link = html.unescape(link)
        if is_direct_amazon_link(decoded_link):
            return decoded_link
    return None

def collect_slickdeals():
    print("Fetching Slickdeals RSS feed...")
    try:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        response = requests.get(SLICKDEALS_RSS, headers=headers, timeout=15)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        deals = []
        for entry in feed.entries:
            title = entry.get("title", "")
            if not title_contains_keyword(title):
                continue
                
            link = entry.get("link", "")
            if not is_direct_amazon_link(link):
                content = entry.get("summary", "") or entry.get("description", "")
                link = extract_amazon_link_from_html(content)
                
            if link:
                deals.append({
                    "title": title,
                    "link": link,
                    "source": "Slickdeals",
                    "score": 50,
                    "timestamp": entry.get("published", "")
                })
        print(f"Collected {len(deals)} filtered Amazon deals from Slickdeals.")
        return deals
    except Exception as e:
        print(f"Error fetching Slickdeals RSS: {e}")
        return []

def collect_reddit_sub(sub):
    time.sleep(3.0) # sleep to avoid hitting Reddit's rate limit
    print(f"Fetching Reddit r/{sub} JSON...")
    deals = []
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    # 1. Try JSON endpoint first
    try:
        url = f"https://www.reddit.com/r/{sub}/.json"
        response = requests.get(url, headers=headers, timeout=15)
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
        
    # 2. Fallback to RSS endpoint
    time.sleep(3.0)
    try:
        reddit_rss = f"https://www.reddit.com/r/{sub}/.rss"
        response = requests.get(reddit_rss, headers=headers, timeout=15)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        for entry in feed.entries:
            title = entry.get("title", "")
            if not title_contains_keyword(title):
                continue
                
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
                    "score": 10,
                    "timestamp": pub_date
                })
        print(f"Collected {len(deals)} filtered Amazon deals from Reddit r/{sub} (RSS Fallback).")
        return deals
    except Exception as e:
        print(f"Error fetching Reddit r/{sub} RSS fallback: {e}")
        return []

def extract_amazon_price(html_content):
    # Clean up excessive spacing for easier regex matching
    html_clean = re.sub(r'\s+', ' ', html_content)
    price = None
    
    # Priority 1: Look for dynamic deal/checkout price classes (avoiding basisPrice and a-text-price)
    patterns = [
        r'class="[^"]*(?:apexPriceToPay|priceToPay)[^"]*"[^>]*>\s*<span class="a-offscreen">\$([\d\.,]+)</span>',
        r'<span class="[^"]*(?:apexPriceToPay|priceToPay)[^"]*"[^>]*>.*?\$([\d\.,]+)',
        # Priority 2: Standard display price, excluding strike-through MSRP
        r'<span class="a-price(?!.*a-text-price)(?!.*basisPrice)"[^>]*>\s*<span class="a-offscreen">\$([\d\.,]+)</span>',
        # Priority 3: Whole and fraction price tag fallbacks
        r'<span class="a-price-whole">([\d\.,]+)<span class="a-price-decimal">\.</span></span>\s*<span class="a-price-fraction">(\d{2})</span>'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html_clean)
        if match:
            if len(match.groups()) == 2:
                price_str = f"{match.group(1)}.{match.group(2)}"
            else:
                price_str = match.group(1)
            
            # Remove commas or formatting characters
            price_str = re.sub(r'[^\d\.]', '', price_str)
            try:
                price = float(price_str)
                if price > 0:
                    break
            except ValueError:
                continue
                
    if not price:
        return None
        
    # Check for prominent coupons and apply them to the checkout price
    # Dollar discount coupons (e.g., "Save $10 with coupon" or "Apply $10 coupon")
    coupon_match = re.search(r'(?:Apply|Save)\s*\$(\d+(?:\.\d{2})?)\s*(?:with\s*)?coupon', html_content, re.IGNORECASE)
    if coupon_match:
        try:
            coupon_val = float(coupon_match.group(1))
            print(f"    Found dollar coupon discount: -${coupon_val}")
            price -= coupon_val
        except ValueError:
            pass
    else:
        # Percentage discount coupons (e.g., "Save 10% with coupon")
        pct_match = re.search(r'Save\s*(\d+)\s*%\s*(?:with\s*)?coupon', html_content, re.IGNORECASE)
        if pct_match:
            try:
                pct_val = float(pct_match.group(1))
                discount_amount = price * (pct_val / 100.0)
                print(f"    Found percentage coupon discount: -{pct_val}% (-${discount_amount:.2f})")
                price -= discount_amount
            except ValueError:
                pass
                
    return f"{price:.2f}"

def main():
    slickdeals = collect_slickdeals()
    
    all_deals = slickdeals
    for sub in SUBREDDITS:
        all_deals += collect_reddit_sub(sub)
        
    # Deduplicate deals by base link URLs
    seen_links = set()
    deduped_deals = []
    for deal in all_deals:
        clean_link = deal["link"].lower().split("?")[0].rstrip("/")
        if clean_link not in seen_links:
            seen_links.add(clean_link)
            deduped_deals.append(deal)
            
    # Candidate sorting
    def sort_key(deal):
        title_lower = deal.get("title", "").lower()
        is_apple = any(ak in title_lower for ak in APPLE_KEYWORDS)
        apple_score = 0 if is_apple else 1
        
        discount = 0
        match = re.search(r'(\d+)\s*%\s*off', title_lower)
        if match:
            discount = int(match.group(1))
            
        rank_score = max(discount, deal.get("score", 0))
        return (apple_score, -rank_score)
        
    deduped_deals.sort(key=sort_key)
    
    # Live Amazon Verification & Price Scraping
    verified_deals = []
    print("Starting Multi-Subreddit Live Amazon Verification...")
    for deal in deduped_deals:
        if len(verified_deals) >= 12:
            break
            
        url = deal["link"]
        print(f"Verifying link and parsing live price: {deal['title'][:50]}... ({url})")
        time.sleep(2.5) # rate limit buffer for Amazon
        
        html_content = ""
        success = False
        for attempt in range(3):
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            try:
                r = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
                text_lower = r.text.lower()
                
                is_dead = (r.status_code == 404 or 
                    "we couldn't find that page" in text_lower or 
                    "meet the dogs of amazon" in text_lower or 
                    "SORRY" in r.text or # SORRY is capitalized on error pages
                    "/error/" in r.url or 
                    "/not-found" in r.url or
                    "currently unavailable" in text_lower)
                    
                if is_dead:
                    reasons = []
                    if r.status_code == 404: reasons.append("404 status")
                    if "we couldn't find that page" in text_lower: reasons.append("page not found text")
                    if "meet the dogs of amazon" in text_lower: reasons.append("dogs of amazon text")
                    if "SORRY" in r.text: reasons.append("sorry text")
                    if "/error/" in r.url: reasons.append("/error/ in url")
                    if "/not-found" in r.url: reasons.append("/not-found in url")
                    if "currently unavailable" in text_lower: reasons.append("currently unavailable text")
                    print(f"  Failed: Dead link, Amazon error, or Currently Unavailable. Reasons: {reasons}. Status: {r.status_code}, Length: {len(r.text)}, URL: {r.url}")
                    break
                    
                if "captcha" in text_lower or "validatecaptcha" in text_lower:
                    print(f"  Attempt {attempt+1} got Captcha block. Retrying...")
                    time.sleep(2.0)
                    continue
                    
                if r.status_code == 200:
                    html_content = r.text
                    success = True
                    break
            except Exception as e:
                print(f"  Attempt {attempt+1} error: {e}")
                time.sleep(2.0)
                
        if not success:
            print("  Skipping: Link failed status verification.")
            continue
            
        # Price extraction
        price = extract_amazon_price(html_content)
        if not price:
            print("  Skipping: Price could not be parsed or found on page.")
            continue
            
        print(f"  Verified! Live Price: ${price}")
        deal["price"] = price
        verified_deals.append(deal)
        
    # Re-sort final verified list
    verified_deals.sort(key=sort_key)
    
    # Save output to raw_deals.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "raw_deals.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(verified_deals, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully verified and saved {len(verified_deals)} Amazon-only deals to {output_path}")

if __name__ == "__main__":
    main()
