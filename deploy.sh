#!/bin/bash
# Move to the directory where this script is located
cd "$(dirname "$0")"

# Run git operations
git add .
git commit -m "Daily deals update"
git push origin main
