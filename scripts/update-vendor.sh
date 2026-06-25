#!/usr/bin/env bash
# update-vendor.sh — Pull the latest ifc-lite upstream Rust source and
#                     re-apply our local patches.
#
# Usage:
#   ./scripts/update-vendor.sh                    # update to latest upstream main
#   ./scripts/update-vendor.sh <commit-or-tag>    # update to a specific revision
#
# Prerequisites:
#   - git
#   - A clean working tree (no uncommitted changes)
#
# What it does:
#   1. Clones upstream ifc-lite (shallow) into a temp directory
#   2. Checks out the requested revision
#   3. Replaces vendor/ifc-lite/ with the upstream content
#   4. Removes files we don't need (Cargo.toml at vendor root, etc.)
#   5. Commits the clean upstream snapshot
#   6. Applies each patch from vendor-patches/ in order
#   7. If a patch fails, drops you into conflict-resolution mode
#
# After running, review the result, run tests, and push.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR_DIR="$ROOT_DIR/vendor/ifc-lite"
PATCHES_DIR="$ROOT_DIR/vendor-patches"
UPSTREAM_STATE="$ROOT_DIR/UPSTREAM.md"
UPSTREAM_REPO="https://github.com/louistrue/ifc-lite.git"
TMP_DIR="$(mktemp -d)"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

# ── Pre-flight checks ──────────────────────────────────────────────────

if ! git -C "$ROOT_DIR" diff --quiet HEAD 2>/dev/null; then
    echo "ERROR: Working tree is not clean. Commit or stash changes first."
    exit 1
fi

TARGET_REF="${1:-main}"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ifc-lite vendor update                                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Upstream repo : $UPSTREAM_REPO"
echo "Target ref    : $TARGET_REF"
echo ""

# ── Step 1: Clone upstream ─────────────────────────────────────────────

echo "[1/6] Cloning upstream..."
git clone --quiet "$UPSTREAM_REPO" "$TMP_DIR/upstream"
cd "$TMP_DIR/upstream"
git checkout --quiet "$TARGET_REF"

UPSTREAM_COMMIT=$(git rev-parse HEAD)
UPSTREAM_SHORT=$(git rev-parse --short HEAD)
UPSTREAM_DATE=$(git log -1 --format='%ci' HEAD)
UPSTREAM_MSG=$(git log -1 --format='%s' HEAD)

echo "  Resolved to: $UPSTREAM_SHORT ($UPSTREAM_MSG)"
echo "  Date:        $UPSTREAM_DATE"
echo ""

# ── Step 2: Replace vendor directory ───────────────────────────────────

echo "[2/6] Replacing vendor/ifc-lite/ with upstream content..."
cd "$ROOT_DIR"

# Remove old vendor content (keep the directory)
rm -rf "$VENDOR_DIR"
mkdir -p "$VENDOR_DIR"

# Copy upstream content
cp -a "$TMP_DIR/upstream/." "$VENDOR_DIR/"

# Remove upstream's .git directory
rm -rf "$VENDOR_DIR/.git"

# ── Step 3: Remove files that conflict with our workspace ──────────────

echo "[3/6] Removing files that conflict with our workspace setup..."

# The upstream Cargo.toml defines its own workspace which conflicts with ours.
# We manage the workspace from the project root Cargo.toml.
rm -f "$VENDOR_DIR/Cargo.toml"

# Also remove the upstream Cargo.lock since we have our own at root
rm -f "$VENDOR_DIR/Cargo.lock"

echo ""

# ── Step 4: Commit clean upstream snapshot ─────────────────────────────

echo "[4/6] Committing clean upstream snapshot..."
git add -A vendor/ifc-lite/
git commit -m "vendor: update ifc-lite to upstream $UPSTREAM_SHORT

Upstream commit: $UPSTREAM_COMMIT
Upstream date:   $UPSTREAM_DATE
Upstream msg:    $UPSTREAM_MSG

This is the clean upstream snapshot before our patches are re-applied."

echo ""

# ── Step 5: Update UPSTREAM.md ─────────────────────────────────────────

echo "[5/6] Updating UPSTREAM.md..."

# Read patch descriptions for UPSTREAM.md
PATCH_LIST=""
for patch_file in "$PATCHES_DIR"/*.patch; do
    [ -f "$patch_file" ] || continue
    patch_name=$(basename "$patch_file")
    # Extract the first line of the patch (usually the diff header) or use filename
    # Try to get a description from the filename
    desc=$(echo "$patch_name" | sed 's/^[0-9]*-//;s/\.patch$//;s/-/ /g')
    PATCH_LIST="$PATCH_LIST\n- \`$patch_name\`: $desc"
done

cat > "$UPSTREAM_STATE" << EOF
# Upstream Vendor State

This file tracks the state of the vendored \`ifc-lite\` code in \`vendor/ifc-lite/\`.

## Current upstream base

- **Repository**: https://github.com/louistrue/ifc-lite
- **Commit**: \`$UPSTREAM_COMMIT\`
- **Date**: $UPSTREAM_DATE
- **Message**: $UPSTREAM_MSG

## Local patches applied

Patches are stored in \`vendor-patches/\` and applied in alphabetical order
on top of the clean upstream snapshot.
$(echo -e "$PATCH_LIST")

## How to update

See \`vendor-patches/README.md\` for the full update process.
Quick version: \`./scripts/update-vendor.sh\`
EOF

git add UPSTREAM.md
git commit -m "vendor: update UPSTREAM.md for $UPSTREAM_SHORT"

echo ""

# ── Step 6: Apply patches ──────────────────────────────────────────────

echo "[6/6] Applying local patches..."

PATCH_COUNT=0
FAILED_PATCH=""

for patch_file in "$PATCHES_DIR"/*.patch; do
    [ -f "$patch_file" ] || continue
    patch_name=$(basename "$patch_file")
    PATCH_COUNT=$((PATCH_COUNT + 1))

    echo "  Applying: $patch_name"

    if git apply --check --directory=vendor/ifc-lite "$patch_file" 2>/dev/null; then
        git apply --directory=vendor/ifc-lite "$patch_file"
        git add -A vendor/ifc-lite/
        git commit -m "vendor: re-apply patch $patch_name"
        echo "    ✓ Applied cleanly"
    else
        echo ""
        echo "╔══════════════════════════════════════════════════════════════╗"
        echo "║  PATCH CONFLICT                                             ║"
        echo "╚══════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Patch '$patch_name' does not apply cleanly."
        echo ""
        echo "The clean upstream snapshot has been committed. You need to"
        echo "manually resolve the conflict."
        echo ""
        echo "Steps to resolve:"
        echo "  1. Review what the patch intended to do:"
        echo "       cat $patch_file"
        echo ""
        echo "  2. Apply it with conflict markers (if possible):"
        echo "       git apply --directory=vendor/ifc-lite --3way $patch_file"
        echo "     or apply it partially and fix by hand:"
        echo "       git apply --directory=vendor/ifc-lite --reject $patch_file"
        echo "       # Then fix the .rej files manually"
        echo ""
        echo "  3. After resolving, commit the result:"
        echo "       git add -A vendor/ifc-lite/"
        echo "       git commit -m 'vendor: re-apply patch $patch_name (resolved conflicts)'"
        echo ""
        echo "  4. Apply remaining patches manually:"
        remaining=false
        for remaining_patch in "$PATCHES_DIR"/*.patch; do
            rp_name=$(basename "$remaining_patch")
            if [ "$rp_name" \> "$patch_name" ]; then
                echo "       git apply --directory=vendor/ifc-lite $remaining_patch"
                echo "       git add -A vendor/ifc-lite/"
                echo "       git commit -m 'vendor: re-apply patch $rp_name'"
                remaining=true
            fi
        done
        if [ "$remaining" = false ]; then
            echo "       (no remaining patches)"
        fi
        echo ""
        echo "  5. Update the patch files if the code changed significantly:"
        echo "       ./scripts/regenerate-patches.sh"
        echo ""
        echo "  6. Run tests to verify everything works:"
        echo "       uv run pytest"
        echo ""
        FAILED_PATCH="$patch_name"
        exit 1
    fi
done

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  UPDATE COMPLETE                                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Upstream: $UPSTREAM_SHORT ($UPSTREAM_MSG)"
echo "Patches:  $PATCH_COUNT applied successfully"
echo ""
echo "Next steps:"
echo "  1. Check that Cargo.toml workspace deps are still compatible"
echo "  2. Update Cargo.lock:  cargo update"
echo "  3. Build:              uv run maturin develop --release"
echo "  4. Run tests:          uv run pytest"
echo "  5. If all good, push!"
echo ""
