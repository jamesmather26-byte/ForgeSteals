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

if [[ "$OSTYPE" == "darwin"* ]]; then
    SIZE=$(stat -f %z index.html)
else
    SIZE=$(stat -c %s index.html)
fi
echo "HTML verified ($SIZE bytes)"

git add .
git commit -m "Pivot to RSS feed for stable prices" || echo "No changes to commit"
git push origin main

echo "=== Live on Cloudflare Pages / GitHub Pages ==="
