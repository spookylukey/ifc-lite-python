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

- `001-add-property-sets-api.patch`: add property sets api
- `002-add-include-geometry-properties-options.patch`: add include geometry properties options

## How to update

See `vendor-patches/README.md` for the full update process.
Quick version: `./scripts/update-vendor.sh`
