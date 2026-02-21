#!/bin/bash
# Format all frontend files in-place using Prettier.
# Requires Node.js and npm install to have been run.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

echo "Formatting frontend files with Prettier..."
npx prettier --write "frontend/**/*.{js,css,html}"
echo "Done. All frontend files formatted."
