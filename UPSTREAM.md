# Upstream Vendor State

This file tracks the state of the vendored `ifc-lite` code in `vendor/ifc-lite/`.

## Current upstream base

- **Repository**: https://github.com/louistrue/ifc-lite
- **Commit**: `68b27030f41659c8046e1eb1bfada8ad32cef52c`
- **Date**: 2026-06-25 07:03:14 +0200
- **Message**: fix(viewer): honour Show Annotations toggle for IfcAnnotation 3D meshes (#1356)

## Local patches applied

Patches are stored in `vendor-patches/` and applied in alphabetical order
on top of the clean upstream snapshot.

- `001-add-property-sets-api.patch`: Adds `PropertySet` and `PropertyValue` types
  to the processing crate's `MeshData`, and builds structured property sets for
  ALL elements (not just IfcSpace/IfcZone). Also wires through `ElementMeshMetadata`
  in the refactored `element.rs` module.

- `002-add-include-geometry-properties-options.patch`: Adds `include_geometry`
  option to `StreamingOptions` in the processing crate (skip geometry extraction
  when false). Restores the `rust/engine/` crate (removed from upstream) with
  `process_ifc_text_with_options` / `process_ifc_file_with_options` accepting
  `include_properties` + `include_geometry` flags. Updates engine API calls for
  the upstream `&str` → `&[u8]` parameter changes.

## Notes

- The upstream `Cargo.toml` (workspace root) is deliberately removed during
  vendoring because our project defines its own workspace at the top level.
- The upstream `Cargo.lock` is also removed (we use our own).
- The `rust/engine/` crate was removed from upstream. We still maintain a local
  copy because our PyO3 bindings depend on it. If upstream changes the processing
  API significantly, the engine crate may need manual updates.
- Workspace version was updated from 2.1.9 to 4.1.0 to match upstream crate
  dependency requirements.
- `workspace.lints.clippy` section was added to support upstream crates that
  inherit workspace lints.

## How to update

See `vendor-patches/README.md` for the full update process.
Quick version: `./scripts/update-vendor.sh`
