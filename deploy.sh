#!/bin/bash
# deploy.sh - Clean daily automation runner

set -euo pipefail

echo "=== ForgeSteals RSS Pivot Deployment ==="
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"

python3 collect.py
python3 render.py

if [ ! -f "index.html" ] || [ ! -s "index.html" ]; then
    echo "ERROR: index.html missing or empty"
    exit 1
fi

echo "HTML verified ($(stat -f%s index.html) bytes)"

git add .
git commit -m "Pivot to RSS feed for stable prices" || echo "No changes to commit"
git push origin main

echo "=== Live on Cloudflare Pages / GitHub Pages ==="
