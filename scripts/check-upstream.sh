#!/usr/bin/env bash
# check-upstream.sh — Show what’s changed in upstream ifc-lite since our base.
#
# Usage:
#   ./scripts/check-upstream.sh           # show Rust-relevant changes
#   ./scripts/check-upstream.sh --all     # show all upstream changes

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
UPSTREAM_REPO="https://github.com/louistrue/ifc-lite.git"
TMP_DIR="$(mktemp -d)"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

# Read current base commit from UPSTREAM.md
BASE_COMMIT=$(grep -oP '(?<=\*\*Commit\*\*: `)[a-f0-9]+' "$ROOT_DIR/UPSTREAM.md" | head -1)

if [ -z "$BASE_COMMIT" ]; then
    echo "ERROR: Cannot read base commit from UPSTREAM.md"
    exit 1
fi

echo "Current base: $BASE_COMMIT"
echo "Fetching upstream..."
echo ""

git clone --quiet "$UPSTREAM_REPO" "$TMP_DIR/upstream"
cd "$TMP_DIR/upstream"

LATEST=$(git rev-parse HEAD)
LATEST_SHORT=$(git rev-parse --short HEAD)

if [ "$BASE_COMMIT" = "$LATEST" ]; then
    echo "Already up to date with upstream main."
    exit 0
fi

COMMIT_COUNT=$(git rev-list --count "$BASE_COMMIT..$LATEST")
echo "Upstream is $COMMIT_COUNT commits ahead (latest: $LATEST_SHORT)"
echo ""

if [ "${1:-}" = "--all" ]; then
    echo "All commits since our base:"
    echo ""
    git log --oneline "$BASE_COMMIT..$LATEST"
else
    echo "Commits affecting Rust code (rust/) since our base:"
    echo ""
    git log --oneline "$BASE_COMMIT..$LATEST" -- rust/
    echo ""

    echo "Files changed in rust/:"
    git diff --stat "$BASE_COMMIT..$LATEST" -- rust/
fi
