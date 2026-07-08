#!/usr/bin/env python3
import json
import os
import re
import html
import time
import random
import requests
import feedparser

# Target keywords to filter
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
    # Skip JSON endpoint to avoid 403 blocks and save rate-limit quota for RSS
    time.sleep(5.0)
    print(f"Fetching Reddit r/{sub} RSS...")
    deals = []
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
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
        print(f"Collected {len(deals)} filtered Amazon deals from Reddit r/{sub} (RSS).")
        return deals
    except Exception as e:
        print(f"Error fetching Reddit r/{sub} RSS: {e}")
        return []

def extract_amazon_price(html_content):
    html_clean = re.sub(r'\s+', ' ', html_content)
    price = None
    
    # Selector pattern checks matching checkout price elements
    patterns = [
        r'class="[^"]*(?:apexPriceToPay|priceToPay)[^"]*"[^>]*>\s*<span class="a-offscreen">\$([\d\.,]+)</span>',
        r'<span class="[^"]*(?:apexPriceToPay|priceToPay)[^"]*"[^>]*>.*?\$([\d\.,]+)',
        r'<span class="a-price(?!.*a-text-price)(?!.*basisPrice)"[^>]*>\s*<span class="a-offscreen">\$([\d\.,]+)</span>',
        r'<span class="a-price-whole">([\d\.,]+)<span class="a-price-decimal">\.</span></span>\s*<span class="a-price-fraction">(\d{2})</span>'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html_clean)
        if match:
            if len(match.groups()) == 2:
                price_str = f"{match.group(1)}.{match.group(2)}"
            else:
                price_str = match.group(1)
            
            price_str = re.sub(r'[^\d\.]', '', price_str)
            try:
                price = float(price_str)
                if price > 0:
                    break
            except ValueError:
                continue
                
    if not price:
        return None
        
    # Check for coupon codes or percentage discounts
    coupon_match = re.search(r'(?:Apply|Save)\s*\$(\d+(?:\.\d{2})?)\s*(?:with\s*)?coupon', html_content, re.IGNORECASE)
    if coupon_match:
        try:
            coupon_val = float(coupon_match.group(1))
            print(f"    Found dollar coupon discount: -${coupon_val}")
            price -= coupon_val
        except ValueError:
            pass
    else:
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

def generate_html(deals):
    cards_html = ""
    for idx, deal in enumerate(deals):
        title = html.escape(deal.get("title", ""))
        link = html.escape(deal.get("link", ""))
        
        # Affiliate tracking tag mapping
        if "?" in link:
            aff_link = f"{link}&tag=forgesteals-20"
        else:
            aff_link = f"{link}?tag=forgesteals-20"
            
        price = deal.get("price", "0.00")
        
        # Category deduction
        category = "Hardware"
        title_lower = title.lower()
        if "gpu" in title_lower or "rtx" in title_lower or "radeon" in title_lower or "nvidia" in title_lower:
            category = "GPU"
        elif "monitor" in title_lower or "display" in title_lower:
            category = "Monitor"
        elif "ssd" in title_lower or "nvme" in title_lower or "storage" in title_lower:
            category = "Storage"
        elif "laptop" in title_lower or "macbook" in title_lower:
            category = "Laptop"
        elif "pc" in title_lower or "desktop" in title_lower or "mini pc" in title_lower:
            category = "Mini PC"
        elif "watch" in title_lower:
            category = "Watch"
        elif "ipad" in title_lower or "tablet" in title_lower:
            category = "Tablet"
        elif "phone" in title_lower or "pixel" in title_lower or "galaxy" in title_lower or "iphone" in title_lower:
            category = "Phone"
        elif "charger" in title_lower or "charging" in title_lower or "accessory" in title_lower:
            category = "Accessory"
            
        pitch = f"A verified premium hardware discount on the {title}. This item has been live status-checked for availability and true checkout pricing."
        
        is_apple = any(ak in title_lower for ak in APPLE_KEYWORDS)
        is_featured = is_apple or idx == 0
        
        featured_badge = ""
        border_class = "border-slate-800/80"
        if is_featured:
            featured_badge = """
                <div class="absolute top-0 right-0 bg-brand-500 text-white font-extrabold text-[9px] uppercase tracking-widest px-3 py-1 rounded-bl-lg shadow-sm">
                    Featured
                </div>
            """
            border_class = "border-brand-500/25"
            
        cards_html += f"""
            <!-- Deal Card -->
            <div class="group bg-slate-900/40 border {border_class} rounded-2xl p-5 flex flex-col justify-between hover:border-brand-500/30 transition-all duration-300 transform hover:-translate-y-1 glow-hover relative overflow-hidden">
                {featured_badge}
                <div>
                    <div class="flex items-center justify-between gap-2 mb-4">
                        <span class="px-2.5 py-0.5 rounded-full bg-brand-500/10 text-brand-500 font-semibold text-xs border border-brand-500/20">{category}</span>
                        <div class="px-3 py-1 rounded-lg bg-brand-500/15 border border-brand-500/30 text-brand-400 font-bold text-sm text-glow">
                            ${price}
                        </div>
                    </div>
                    <h3 class="text-base font-semibold text-white group-hover:text-brand-400 transition-colors duration-200 line-clamp-2 min-h-[3rem] font-display mb-3">
                        {title}
                    </h3>
                    <p class="text-slate-400 text-xs leading-relaxed mb-4">
                        {pitch}
                    </p>
                </div>
                <div class="mt-4 pt-4 border-t border-slate-800/40 flex items-center justify-between gap-4">
                    <span class="text-[10px] text-slate-500 uppercase tracking-wide font-semibold">Verified Deal</span>
                    <a href="{aff_link}" target="_blank" rel="noopener noreferrer" class="px-4 py-2 rounded-lg bg-brand-500 text-white font-medium text-xs hover:bg-brand-600 transition-all duration-200 shadow-md shadow-brand-500/10 hover:shadow-brand-500/20">
                        Shop Deal
                    </a>
                </div>
            </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ForgeSteals | Daily Curated Tech & Hardware Deals</title>
    <!-- Meta tags for SEO -->
    <meta name="description" content="Handpicked daily deals on top tech, GPUs, monitors, laptops, SSDs and gaming gear. ForgeSteals curation filters the noise so you get the best hardware discounts.">
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['Outfit', 'sans-serif'],
                        display: ['Space Grotesk', 'sans-serif'],
                    }},
                    colors: {{
                        brand: {{
                            50: '#fff7ed',
                            100: '#ffedd5',
                            500: '#f97316', // Orange
                            600: '#ea580c',
                            950: '#431407',
                        }},
                        darkbg: '#0a0f1d',
                    }}
                }}
            }}
        }}
    </script>
    <style>
        .glow-hover:hover {{
            box-shadow: 0 0 25px rgba(249, 115, 22, 0.25);
        }}
        .text-glow {{
            text-shadow: 0 0 15px rgba(249, 115, 22, 0.4);
        }}
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: #0a0f1d;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #1e293b;
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #f97316;
        }}
    </style>
</head>
<body class="bg-darkbg text-slate-100 min-h-screen relative overflow-x-hidden font-sans selection:bg-brand-500 selection:text-white">

    <!-- Glowing Background Blobs -->
    <div class="absolute top-[-10%] left-[-10%] w-[60%] h-[50%] bg-brand-500/5 rounded-full blur-[140px] pointer-events-none"></div>
    <div class="absolute bottom-[20%] right-[-10%] w-[50%] h-[50%] bg-purple-500/5 rounded-full blur-[140px] pointer-events-none"></div>

    <!-- Required Affiliate Disclosure Message at the top -->
    <div class="bg-slate-900/90 border-b border-slate-800/80 backdrop-blur-md py-2.5 px-4 text-center text-xs text-slate-400 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto flex items-center justify-center gap-2">
            <span class="inline-block px-1.5 py-0.5 rounded bg-brand-500/10 text-brand-500 font-semibold text-[10px] uppercase tracking-wider border border-brand-500/20">Disclosure</span>
            <p>ForgeSteals is reader-supported. When you buy through our links, we may earn an affiliate commission at no extra cost to you.</p>
        </div>
    </div>

    <!-- Header / Hero Section -->
    <header class="py-12 md:py-16 border-b border-slate-900 relative">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <!-- Brand Logo / Name -->
            <div class="inline-flex items-center gap-3 mb-4">
                <div class="w-12 h-12 rounded-xl bg-gradient-to-tr from-brand-600 to-amber-500 flex items-center justify-center shadow-lg shadow-brand-500/25">
                    <!-- Anvil/Spark SVG Icon -->
                    <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path>
                    </svg>
                </div>
                <h1 class="text-4xl md:text-5xl font-extrabold font-display tracking-tight text-white">
                    Forge<span class="text-transparent bg-clip-text bg-gradient-to-r from-brand-500 to-amber-400">Steals</span>
                </h1>
            </div>
            
            <p class="max-w-xl mx-auto text-lg text-slate-400 font-light mt-2">
                Daily curated hardware and accessory deals, hand-forged for gamers, creators, and enthusiasts.
            </p>
            
            <div class="flex justify-center items-center gap-6 mt-6 text-sm text-slate-500">
                <span class="flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
                    Updated Daily
                </span>
                <span class="border-l border-slate-800 h-4"></span>
                <span>Verified Discounts | Hand-picked Hardware Deals</span>
            </div>
        </div>
    </header>

    <!-- Main Grid Section -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        
        <!-- Section Title -->
        <div class="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
                <h2 class="text-2xl font-bold font-display text-white flex items-center gap-2">
                    <span class="w-1.5 h-6 bg-brand-500 rounded"></span>
                    Today's Curated Steals
                </h2>
                <p class="text-slate-400 text-sm mt-1">Verified Amazon hardware discounts (no dead links)</p>
            </div>
            <div class="text-xs text-slate-500">
                Showing the top {len(deals)} verified deals
            </div>
        </div>

        <!-- Cards Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {cards_html}
        </div>

    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-900 bg-slate-950/60 backdrop-blur-md mt-20 py-8 text-center text-xs text-slate-500 relative">
        <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <p>&copy; 2026 ForgeSteals. All rights reserved.</p>
            <div class="flex justify-center gap-6">
                <a href="#" class="hover:text-brand-500 transition-colors duration-200">Privacy Policy</a>
                <a href="#" class="hover:text-brand-500 transition-colors duration-200">Terms of Service</a>
                <a href="#" class="hover:text-brand-500 transition-colors duration-200">Contact Us</a>
            </div>
        </div>
    </footer>

</body>
</html>"""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_html_path = os.path.join(script_dir, "index.html")
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Dynamically generated clean index.html with {len(deals)} verified deals.")

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
                
                # Robust Dead-Link and Error Page Detection (Dogs, SORRY, 404)
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
                    if "SORRY" in r.text: reasons.append("SORRY error text")
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
    
    # Generate index.html dynamically
    generate_html(verified_deals)

if __name__ == "__main__":
    main()
