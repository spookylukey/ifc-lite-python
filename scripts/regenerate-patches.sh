#!/usr/bin/env bash
# regenerate-patches.sh — Regenerate vendor-patches/ from git history.
#
# After manually resolving a patch conflict (or adding a new local change to
# the vendored code), run this script to regenerate the patch files in
# vendor-patches/ so they match the current state of the code.
#
# This script works by diffing the current vendor/ifc-lite/ Rust files against
# the clean upstream snapshot commit. It produces ONE patch per original patch
# file (preserving the numbering/naming convention), but you can also use it
# to create new patches.
#
# Usage:
#   ./scripts/regenerate-patches.sh
#
# How it works:
#   1. Finds the most recent "vendor: update ifc-lite to upstream" commit
#      (the clean upstream snapshot before patches were applied)
#   2. For each subsequent commit that touched vendor/ifc-lite/rust/,
#      generates a patch file
#   3. Writes them to vendor-patches/ with sequential numbering

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PATCHES_DIR="$ROOT_DIR/vendor-patches"

cd "$ROOT_DIR"

# Find the clean upstream snapshot commit
# It's the most recent commit whose message starts with "vendor: update ifc-lite to upstream"
UPSTREAM_COMMIT=$(git log --oneline --grep="^vendor: update ifc-lite to upstream" --format="%H" | head -1)

if [ -z "$UPSTREAM_COMMIT" ]; then
    echo "ERROR: Cannot find a 'vendor: update ifc-lite to upstream' commit."
    echo "This script requires the update-vendor.sh workflow to have been run at least once."
    exit 1
fi

echo "Found clean upstream snapshot: $(git log --oneline -1 "$UPSTREAM_COMMIT")"
echo ""

# Find all commits after the upstream snapshot that modified vendor/ifc-lite/rust/
# (These are our patch commits, in chronological order)
PATCH_COMMITS=$(git log --format="%H" --reverse "$UPSTREAM_COMMIT"..HEAD -- vendor/ifc-lite/rust/)

if [ -z "$PATCH_COMMITS" ]; then
    echo "No commits found that modify vendor/ifc-lite/rust/ after the upstream snapshot."
    echo "Nothing to regenerate."
    exit 0
fi

# Remove old patches
rm -f "$PATCHES_DIR"/*.patch

# Generate new patches
COUNTER=1
for commit in $PATCH_COMMITS; do
    msg=$(git log --format="%s" -1 "$commit")
    # Create a slug from the commit message
    slug=$(echo "$msg" | sed 's/^vendor: re-apply patch //;s/\.patch.*//;s/^[0-9]*-//' | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-')
    if [ -z "$slug" ]; then
        slug="patch"
    fi
    padded=$(printf "%03d" $COUNTER)
    patch_file="$PATCHES_DIR/${padded}-${slug}.patch"

    echo "  Generating: $(basename "$patch_file")"
    echo "    From commit: $(git log --oneline -1 "$commit")"

    # Generate diff for just this commit's changes to vendor/ifc-lite/
    git diff "$commit~1..$commit" -- vendor/ifc-lite/ | \
        sed 's|a/vendor/ifc-lite/|a/|;s|b/vendor/ifc-lite/|b/|' > "$patch_file"

    COUNTER=$((COUNTER + 1))
done

echo ""
echo "Regenerated $((COUNTER - 1)) patch(es) in vendor-patches/"
echo ""
echo "Don't forget to commit the updated patches:"
echo "  git add vendor-patches/"
echo "  git commit -m 'vendor: regenerate patches'"
