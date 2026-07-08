#!/usr/bin/env python3
"""
render.py - Clean production static site builder
Loads premium curated hardware products from products.json and renders a beautiful dark tech/gaming index.html.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

PRODUCTS_PATH = Path("products.json")
OUTPUT_PATH = Path("index.html")

def main():
    if not PRODUCTS_PATH.exists():
        print("products.json not found. Please create it first.", file=sys.stderr)
        sys.exit(1)

    with open(PRODUCTS_PATH, "r", encoding="utf-8") as f:
        products = json.load(f)

    if not products:
        print("No products to render", file=sys.stderr)
        sys.exit(1)

    # Use standard clean Eastern Time month/year format
    current_date = datetime.now().strftime("%B %Y")

    cards_html = ""
    for product in products:
        title = product.get("title", "Premium Deal")
        price = product.get("price", "See price")
        image = product.get("image", "")
        desc = product.get("description", "")
        source = product.get("source", "Boutique Curated")
        link = product.get("link", "#")

        img_html = ""
        if image:
            img_html = f'<img src="{image}" alt="{title}" class="w-full h-56 object-cover rounded-2xl mb-4 border border-zinc-800" loading="lazy" onerror="this.style.display=\'none\'">'
        else:
            img_html = '<div class="w-full h-56 bg-zinc-900 rounded-2xl mb-4 flex items-center justify-center border border-zinc-800"><span class="text-4xl">🖥️</span></div>'

        cards_html += f"""
    <!-- Curated Product Card -->
    <div class="group bg-zinc-900 border border-zinc-800 hover:border-zinc-700 rounded-3xl overflow-hidden flex flex-col transition-all duration-200 hover:-translate-y-px p-6">
        {img_html}
        <div class="flex flex-col flex-1">
            <div class="flex items-start justify-between gap-4 mb-4">
                <!-- Breathing room for titles with full wrapping -->
                <h3 class="font-semibold text-lg leading-snug text-white flex-1">{title}</h3>
                <div class="shrink-0 px-4 py-1.5 rounded-2xl bg-emerald-500 text-emerald-950 font-mono text-lg font-bold tracking-tighter whitespace-nowrap self-start">{price}</div>
            </div>
            
            <!-- Full description, no truncation/cut-off text -->
            <p class="text-zinc-400 text-sm leading-relaxed mb-6 flex-1">{desc}</p>
            
            <div class="mt-auto flex items-center justify-between pt-4 border-t border-zinc-800">
                <div class="text-[10px] px-3 py-1 rounded-full bg-zinc-800 text-zinc-400 font-semibold tracking-wider uppercase">{source}</div>
                <a href="{link}" target="_blank" rel="noopener noreferrer sponsored"
                   class="inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-2xl bg-white hover:bg-zinc-100 active:bg-zinc-200 text-zinc-950 font-bold text-sm tracking-[0.5px] transition-colors">
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
<title>ForgeSteals • Curated Premium Hardware Boutique</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
body {{ font-family: 'Inter', system-ui, sans-serif; }}
.font-display {{ font-family: 'Space Grotesk', 'Inter', system-ui, sans-serif; }}
</style>
</head>
<body class="bg-zinc-950 text-zinc-200 min-h-screen">
<div class="max-w-7xl mx-auto px-6 pt-12 pb-24">
    <!-- Header Section -->
    <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-12">
        <div>
            <div class="flex items-center gap-3.5 mb-2.5">
                <div class="w-11 h-11 rounded-2xl bg-emerald-500 flex items-center justify-center shadow-lg shadow-emerald-500/10">
                    <span class="text-emerald-950 text-4xl font-bold tracking-[-3px] select-none">F</span>
                </div>
                <div class="font-display text-5xl font-bold tracking-[-2.5px] text-white">ForgeSteals</div>
            </div>
            <p class="text-emerald-400 text-lg font-medium">Boutique Curated Hardware Showcase</p>
        </div>
        <div class="text-left md:text-right">
            <div class="text-xs text-zinc-500 font-bold tracking-wider uppercase mb-1">CURATED SELECTION</div>
            <div class="font-display text-xl text-zinc-300 font-semibold">{current_date}</div>
        </div>
    </div>

    <!-- Disclosure Banner -->
    <div class="mb-10 px-6 py-4 rounded-3xl bg-zinc-900 border border-zinc-800 text-sm text-zinc-400 leading-relaxed">
        <strong class="text-zinc-300">Affiliate Disclosure:</strong> ForgeSteals is a curated boutique storefront. When you purchase through our links, we may earn a commission from our retail partners (including Amazon Associates) at no additional cost to you. All prices are verified and hand-curated.
    </div>

    <!-- Grid Layout -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 gap-8">
        {cards_html}
    </div>

    <!-- Footer -->
    <div class="mt-20 text-center text-xs text-zinc-600 font-medium">
        Hand-curated with precision • Exclusive boutique selection • Updated regularly for July 2026
    </div>
</div>
</body>
</html>"""

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[render] Generated curated index.html with {len(products)} products")

if __name__ == "__main__":
    main()
