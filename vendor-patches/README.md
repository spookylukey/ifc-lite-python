# Vendor Patches

This directory contains patches that are applied on top of the upstream
[ifc-lite](https://github.com/louistrue/ifc-lite) Rust source code after it is
vendored into `vendor/ifc-lite/`.

See `UPSTREAM.md` (project root) for the current upstream commit and patch list.

## Patch format

Each `.patch` file is a unified diff with paths relative to `vendor/ifc-lite/`.
They are applied in alphabetical order (hence the `NNN-` numeric prefix).

## How to update upstream

### Automated (happy path)

```bash
# Update to latest upstream main:
./scripts/update-vendor.sh

# Or update to a specific commit/tag:
./scripts/update-vendor.sh v4.1.0
./scripts/update-vendor.sh abc123def
```

The script will:
1. Clone the upstream repo
2. Replace `vendor/ifc-lite/` with the new upstream content
3. Commit the clean upstream snapshot
4. Re-apply each patch from this directory
5. Update `UPSTREAM.md`

If all patches apply cleanly, you just need to:
```bash
# Check workspace Cargo.toml still has correct crate paths/versions
# (upstream may have added/removed crates or changed versions)
vim Cargo.toml

# Update Cargo.lock
cargo update

# Build
uv run maturin develop --release

# Test
uv run pytest
```

### When patches conflict

If a patch doesn't apply cleanly, the script stops and prints instructions.
The clean upstream snapshot is already committed, so you can see exactly what
changed upstream.

To resolve:

1. **Understand what changed**: Compare the patch against the new upstream:
   ```bash
   cat vendor-patches/001-add-property-sets-api.patch
   # Look at the upstream file it patches:
   cat vendor/ifc-lite/rust/processing/src/processor.rs
   ```

2. **Try applying with conflict markers**:
   ```bash
   git apply --directory=vendor/ifc-lite --3way vendor-patches/001-add-property-sets-api.patch
   ```
   This gives you `<<<`/`>>>`-style conflict markers to resolve.

3. **Or apply with reject files**:
   ```bash
   git apply --directory=vendor/ifc-lite --reject vendor-patches/001-add-property-sets-api.patch
   ```
   This applies what it can and creates `.rej` files for the rest.

4. **Or apply manually**: Read the patch, understand the intent, and make the
   equivalent changes by hand on the new upstream code.

5. **Commit the resolved result**:
   ```bash
   git add -A vendor/ifc-lite/
   git commit -m "vendor: re-apply patch 001-add-property-sets-api.patch (resolved conflicts)"
   ```

6. **Apply remaining patches** (if any).

7. **Regenerate patch files** to match the new code:
   ```bash
   ./scripts/regenerate-patches.sh
   git add vendor-patches/
   git commit -m "vendor: regenerate patches after upstream update"
   ```

8. **Build and test**:
   ```bash
   uv run maturin develop --release
   uv run pytest
   ```

### Things that may need manual attention after an update

- **Cargo.toml workspace**: If upstream adds new crates or changes versions,
  update the root `Cargo.toml` workspace members and dependencies.

- **Engine crate**: The `rust/engine/` crate was removed from upstream. We
  maintain our own copy. If the processing crate API changes, the engine crate
  will need updates. Key things to watch:
  - `StreamingOptions` struct fields
  - `process_geometry_*` function signatures
  - `MeshData` struct fields
  - Imports/re-exports from `ifc_lite_processing`

- **PyO3 bindings**: If `MeshData` gains new fields upstream, you may want to
  expose them in `rust/src/lib.rs` and `python/ifc_lite/_core.py`.

- **Rust toolchain**: Check `vendor/ifc-lite/rust-toolchain.toml` for any
  toolchain version changes.

## Adding a new patch

1. Make your changes to files in `vendor/ifc-lite/rust/`
2. Commit with a descriptive message:
   ```bash
   git add vendor/ifc-lite/rust/
   git commit -m "vendor: add support for XYZ"
   ```
3. Regenerate patch files:
   ```bash
   ./scripts/regenerate-patches.sh
   git add vendor-patches/
   git commit -m "vendor: regenerate patches (added XYZ)"
   ```
4. Update the patch list in `UPSTREAM.md`

## Current patches

### 001-add-property-sets-api.patch

**Purpose**: Add structured property set extraction for all IFC elements.

Upstream only populates `MeshData.properties` for IfcSpace/IfcZone elements.
This patch adds `PropertySet` and `PropertyValue` types, a
`MeshData.property_sets` field, and builds property sets for every element
via the `RelDefinesByProperties` relationships.

**Files modified**:
- `rust/processing/src/processor.rs` — adds `build_property_sets_by_entity()`,
  `assign_element_property_sets()`, and wires them into the processing pipeline
- `rust/processing/src/types/mesh.rs` — adds `PropertyValue`, `PropertySet`
  structs and `MeshData.property_sets` field

### 002-add-include-geometry-properties-options.patch

**Purpose**: Allow skipping geometry extraction and/or property parsing.

Adds `include_geometry` to `StreamingOptions` in the processing crate. When
false, geometry extraction is skipped and `MeshData` objects are returned with
empty geometry but fully populated metadata. Also adds convenience functions
`process_ifc_text_with_options` / `process_ifc_file_with_options` to the engine
crate.

**Files modified**:
- `rust/processing/src/processor.rs` — adds `include_geometry` to
  `StreamingOptions`, skips geometry loop when false, adds
  `process_geometry_streaming_filtered_with_options`
- `rust/engine/src/lib.rs` — adds `include_geometry` to `StreamOptions`,
  adds `process_ifc_text_with_options` / `process_ifc_file_with_options`
