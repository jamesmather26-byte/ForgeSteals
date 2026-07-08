#!/usr/bin/env python3
"""
render.py - Clean production static site builder
Loads 12 deals from raw_deals.json and renders a beautiful dark tech/gaming index.html with images + affiliate links.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

CONFIG_PATH = Path("config.json")
RAW_PATH = Path("raw_deals.json")
OUTPUT_PATH = Path("index.html")

def make_affiliate_link(link: str, tag: str) -> str:
    if not tag or tag == "forgesteals-20" or not link:
        return link
    if "amazon." not in link.lower() and "amzn." not in link.lower():
        return link
    try:
        parsed = urlparse(link)
        qs = parse_qs(parsed.query)
        qs["tag"] = [tag]
        new_query = urlencode(qs, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    except Exception:
        return link

def main():
    if not RAW_PATH.exists():
        print("raw_deals.json not found. Run collect.py first.", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    affiliate_tag = config.get("amazon_affiliate_tag", "forgesteals-20")

    with open(RAW_PATH, "r", encoding="utf-8") as f:
        deals = json.load(f)

    if not deals:
        print("No deals to render", file=sys.stderr)
        sys.exit(1)

    last_updated = datetime.now().strftime("%b %d, %Y • %H:%M UTC")

    cards_html = ""
    for deal in deals:
        aff_link = make_affiliate_link(deal.get("link", "#"), affiliate_tag)
        title = deal.get("title", "Deal")[:110]
        price = deal.get("price", "See price")
        image = deal.get("image", "")
        desc = deal.get("description", "Strong value in today's feed.")
        source = deal.get("source", "Slickdeals")

        img_html = ""
        if image:
            img_html = f'<img src="{image}" alt="{title}" class="w-full h-48 object-cover rounded-2xl mb-4 border border-zinc-800" loading="lazy" onerror="this.style.display=\'none\'">'
        else:
            img_html = '<div class="w-full h-48 bg-zinc-900 rounded-2xl mb-4 flex items-center justify-center border border-zinc-800"><span class="text-4xl">🖥️</span></div>'

        cards_html += f"""
    <div class="group bg-zinc-900 border border-zinc-800 hover:border-zinc-700 rounded-3xl overflow-hidden flex flex-col transition-all duration-200 hover:-translate-y-px">
        {img_html}
        <div class="px-6 pb-6 flex flex-col flex-1">
            <div class="flex items-start justify-between gap-3 mb-3">
                <h3 class="font-semibold text-[17px] leading-tight text-white pr-1 line-clamp-3">{title}</h3>
                <div class="shrink-0 px-4 py-1 rounded-2xl bg-emerald-500 text-emerald-950 font-mono text-xl font-semibold tracking-tighter whitespace-nowrap self-start">{price}</div>
            </div>
            
            <p class="text-zinc-400 text-[13.5px] leading-relaxed mb-5 flex-1">{desc}</p>
            
            <div class="mt-auto flex items-center justify-between pt-4 border-t border-zinc-800">
                <div class="text-[10px] px-3 py-1 rounded-full bg-zinc-800 text-zinc-400 font-medium tracking-wider">{source}</div>
                <a href="{aff_link}" target="_blank" rel="noopener noreferrer sponsored"
                   class="inline-flex items-center justify-center gap-2 px-7 py-3 rounded-2xl bg-white hover:bg-zinc-100 active:bg-zinc-200 text-zinc-950 font-semibold text-sm tracking-[0.5px] transition-colors">
                    SHOP NOW <span class="text-lg">→</span>
                </a>
            </div>
        </div>
    </div>
    """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ForgeSteals • Daily Tech & Gaming Hardware Deals</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&display=swap');
body {{ font-family: 'Inter', system-ui, sans-serif; }}
.font-display {{ font-family: 'Space Grotesk', 'Inter', system-ui, sans-serif; }}
</style>
</head>
<body class="bg-zinc-950 text-zinc-200">
<div class="max-w-7xl mx-auto px-6 pt-10 pb-20">
    <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-10">
        <div>
            <div class="flex items-center gap-3 mb-2">
                <div class="w-10 h-10 rounded-2xl bg-emerald-500 flex items-center justify-center">
                    <span class="text-emerald-950 text-4xl font-bold tracking-[-3px]">F</span>
                </div>
                <div class="font-display text-5xl font-semibold tracking-[-2.5px]">ForgeSteals</div>
            </div>
            <p class="text-emerald-400 text-lg">12 fresh tech & gaming hardware deals • Updated from public RSS</p>
        </div>
        <div class="text-right">
            <div class="text-xs text-zinc-500">LAST REFRESH</div>
            <div class="font-mono text-sm text-zinc-400">{last_updated}</div>
        </div>
    </div>

    <div class="mb-8 px-5 py-4 rounded-3xl bg-zinc-900 border border-zinc-800 text-sm text-zinc-400">
        <strong class="text-zinc-300">Affiliate Disclosure:</strong> This site uses affiliate links (including Amazon Associates). We may earn a commission at no extra cost to you. All prices pulled directly from verified public RSS feeds. Always confirm current pricing and stock on the retailer site.
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {cards_html}
    </div>

    <div class="mt-16 text-center text-xs text-zinc-500">
        Powered by public RSS feeds • Zero scraping of retailer HTML • Fully automated daily
    </div>
</div>
</body>
</html>"""

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[render] Generated clean {OUTPUT_PATH} with {len(deals)} cards")

if __name__ == "__main__":
    main()
