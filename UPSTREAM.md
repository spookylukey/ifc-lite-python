# Upstream Vendor State

This file tracks the state of the vendored `ifc-lite` code in `vendor/ifc-lite/`.

## Current upstream base

- **Repository**: https://github.com/louistrue/ifc-lite
- **Commit**: `18c6a37f1cc1426daa32ee60457dd0580a5257f5`
- **Date**: 2026-04-19 16:57:04 +0200
- **Message**: Claude/rebase window reveal cuts 09f8 f (#572)

## Local patches applied

Patches are stored in `vendor-patches/` and applied in alphabetical order
on top of the clean upstream snapshot.

- `001-add-property-sets-api.patch`: Adds `PropertySet` and `PropertyValue` types
  to the processing crate's `MeshData`, and builds structured property sets for
  ALL elements (not just IfcSpace/IfcZone). Source commit: adc52df.

- `002-add-include-geometry-properties-options.patch`: Adds `include_geometry`
  option to `StreamingOptions` in the processing crate (skip geometry extraction
  when false). Adds `process_ifc_text_with_options` / `process_ifc_file_with_options`
  to the engine crate accepting `include_properties` + `include_geometry` flags.
  Source commit: 62d203d.

## Notes

- The upstream `Cargo.toml` (workspace root) is deliberately removed during
  vendoring because our project defines its own workspace at the top level.
- The upstream `Cargo.lock` is also removed (we use our own).
- The `rust/engine/` crate was removed from upstream in commit e73ac093
  ("Unify geometry mesh-production path"). We still maintain a local copy
  because our PyO3 bindings depend on it. If upstream changes the processing
  API significantly, the engine crate may need manual updates.

## How to update

See `vendor-patches/README.md` for the full update process.
Quick version: `./scripts/update-vendor.sh`
