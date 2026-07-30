#!/usr/bin/env bash
# Publish kx-defender to registry.npmjs.org (fixes npx E404)
set -euo pipefail
cd "$(dirname "$0")/.."
npm whoami >/dev/null || { echo "Run: npm login"; exit 1; }
npm publish --access public
echo
echo "Published. Install with:"
echo "  npx --yes kx-defender add --all -g"
