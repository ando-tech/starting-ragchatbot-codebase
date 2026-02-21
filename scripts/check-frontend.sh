#!/bin/bash
# Run all frontend code quality checks (Prettier format check + ESLint).
# Exits with a non-zero code if any check fails.
# Requires Node.js and npm install to have been run.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

PASS=0
FAIL=0

echo "========================================"
echo " Frontend Quality Checks"
echo "========================================"

# --- Prettier format check ---
echo ""
echo "[1/2] Checking formatting with Prettier..."
if npx prettier --check "frontend/**/*.{js,css,html}"; then
    echo "  PASS: All files are correctly formatted."
    PASS=$((PASS + 1))
else
    echo "  FAIL: Formatting issues found. Run scripts/format-frontend.sh to fix."
    FAIL=$((FAIL + 1))
fi

# --- ESLint ---
echo ""
echo "[2/2] Linting JavaScript with ESLint..."
if npx eslint frontend/; then
    echo "  PASS: No linting errors."
    PASS=$((PASS + 1))
else
    echo "  FAIL: ESLint reported issues. See output above."
    FAIL=$((FAIL + 1))
fi

# --- Summary ---
echo ""
echo "========================================"
echo " Results: $PASS passed, $FAIL failed"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
