#!/usr/bin/env bash
# Deploy Modal app
# Usage: bash modal_deploy.sh

set -euo pipefail

if ! command -v modal >/dev/null 2>&1; then
  echo "Modal CLI not found. Install with: pip install modal"
  exit 1
fi

echo "Deploying Modal app..."
modal deploy modal_app.py
echo "Done."


