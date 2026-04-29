# Investigation: Optional Loading of Geometry and Property Sets

## Summary

Both options are feasible. Skipping property sets can be done entirely in the
Python layer today (zero Rust changes). Skipping geometry requires a small
Rust-side change but is straightforward.

---

## 1. Skipping Property Sets

### How it works today

The Rust `StreamingOptions` struct already has an `include_properties: bool`
field (default `true`). When `false`, the entity scan loop skips
`IFCPROPERTYSET`, `IFCRELDEFINESBYPROPERTIES`, and all `IFCPROPERTY*` entities
entirely, and the post-scan `assign_space_zone_properties` /
`assign_element_property_sets` calls are skipped.

This means the Rust engine already supports this — we just aren't exposing
it through the Python bindings.

### Current Python call path

```
process_file(path)
  → _native.process_file(str(path))          # no options
  → engine: process_ifc_file(path)
  → engine: process_ifc_text(content)
  → processing: process_geometry(content)     # always include_properties=true
```

The non-streaming `process_geometry()` and `process_geometry_filtered()` call
`process_geometry_streaming_filtered_with_options()` with hardcoded
`StreamingOptions::default()` (which has `include_properties: true`).

### What needs to change

**Option A: Python-only approach (no Rust changes, strip in Python)**

We could simply set `mesh.properties = None` and `mesh.property_sets = None`
in `MeshData.from_dict()` when the caller requests no properties. This avoids
all Rust/build changes but **still pays the cost** of parsing properties in Rust.

**Option B: Rust + Python approach (real performance win)**

Pass `include_properties` through to the Rust engine:

1. **Engine layer** (`vendor/ifc-lite/rust/engine/src/lib.rs`): The engine's
   non-streaming functions (`process_ifc_text`, `process_ifc_file`) don't
   accept options. We'd either:
   - Add new `_with_options` variants, or
   - Route through the existing streaming path with `include_properties: false`
     (the simpler approach — `process_geometry_filtered` already does this).

2. **PyO3 bindings** (`rust/src/lib.rs`): Add an `include_properties` parameter
   to `process_file` and `process_text` (or add new functions).

3. **Python layer** (`python/ifc_lite/_core.py`): Add `load_properties: bool =
   True` parameter to `IfcModel.from_file()`, `IfcModel.from_text()`,
   `process_file()`, `process_text()`.

### Recommendation

Option B is straightforward and gives a real performance benefit for large
files with many property sets. The `include_properties` plumbing already exists
in the processing crate; we just need to thread it through the engine → PyO3 →
Python layers.

### Estimated effort: Small

- Engine: ~10 lines (add `process_ifc_text_with_options` or similar)
- PyO3: ~15 lines (add parameter to existing functions or new functions)
- Python: ~10 lines (add parameter, pass through)
- Tests: ~20 lines

---

## 2. Skipping Geometry

### How it works today

Geometry extraction is the most expensive part of processing. It happens in
the parallel geometry loop in
`process_geometry_streaming_filtered_with_options()` (lines ~1230-1400 of
`processor.rs`). This loop iterates over `entity_jobs`, calls
`process_entity_job()` for each, which decodes entities and runs the geometry
router.

There is **no existing option** to skip geometry. The entire pipeline is
designed around producing `MeshData` with positions/normals/indices.

### What needs to change

We need a way to produce `MeshData` objects with metadata (express_id,
ifc_type, global_id, name, property_sets) but **empty geometry fields**
(positions=[], normals=[], indices=[], default color).

**Approach: Add `include_geometry: bool` to `StreamingOptions`**

1. **Processing crate** (`vendor/ifc-lite/rust/processing/src/processor.rs`):
   Add `include_geometry: bool` to `StreamingOptions` (default `true`). When
   `false`:
   - Skip the `process_entity_job()` call in the parallel geometry loop
   - Instead, emit a `MeshData` with empty positions/normals/indices from each
     job's metadata (express_id, ifc_type, global_id, name, properties)
   - Skip faceted brep preprocessing, void processing, etc.
   - This preserves the entity scan phase (which discovers elements, their
     types, and IDs) and the property assignment phase.

2. **Engine layer**: Same pattern as property sets — add `_with_options`
   functions or thread through streaming options.

3. **PyO3 + Python layers**: Add `load_geometry: bool = True` parameter.

### Key consideration: What does "no geometry" mean for `MeshData`?

The `MeshData` struct currently couples element metadata with geometry. Two
approaches:

- **A) Keep MeshData, empty geometry**: Return `MeshData` with empty
  `positions`/`normals`/`indices` and `vertex_count=0`. Simple, no API change.
  Callers check `vertex_count > 0` if they need geometry.

- **B) Separate ElementData from MeshData**: A cleaner abstraction but a bigger
  API change. Not needed for an initial implementation.

### Recommendation

Approach A (empty geometry in MeshData) is pragmatic and non-breaking. The Rust
change is moderate — we need to ensure the entity scan still runs (it does
regardless) and that metadata (global_id, name) is resolved even without
geometry. Looking at the code, the metadata population phase (Phase 1/Phase 2
in the chunk loop, lines ~1268-1320) happens **before** geometry extraction, so
we can still run it and then skip the `process_entity_job()` call.

Specifically, when `include_geometry` is false, the chunk loop would:
1. Still run the parallel metadata population (global_id, name, color, etc.)
2. Instead of calling `process_entity_job()`, emit a `MeshData::new()` with
   empty geometry but with all the metadata fields populated.

### Estimated effort: Medium

- Processing crate: ~30 lines (new field + conditional in chunk loop)
- Engine: ~10 lines
- PyO3: ~15 lines
- Python: ~10 lines
- Tests: ~30 lines

---

## 3. Combined API Design

The cleanest Python API would be:

```python
# Full load (current default behavior)
model = ifc_lite.process_file("building.ifc")

# Metadata + properties only (no geometry) — fast scan
model = ifc_lite.process_file("building.ifc", load_geometry=False)

# Geometry only (no property sets) — slightly faster for large files
model = ifc_lite.process_file("building.ifc", load_properties=False)

# Metadata only (no geometry, no properties) — fastest
model = ifc_lite.process_file(
    "building.ifc",
    load_geometry=False,
    load_properties=False,
)
```

The same parameters would appear on `process_text()`, `IfcModel.from_file()`,
and `IfcModel.from_text()`.

---

## 4. Implementation Plan

### Phase 1: Property set skipping (can do now)
1. Add `include_properties` parameter to engine functions
2. Thread through PyO3 bindings
3. Add `load_properties` parameter to Python API
4. Tests

### Phase 2: Geometry skipping
1. Add `include_geometry` to `StreamingOptions` in processing crate
2. Implement skip logic in chunk loop
3. Thread through engine → PyO3 → Python
4. Tests

### Vendor code changes

Both phases require changes to vendored upstream code:
- `vendor/ifc-lite/rust/processing/src/processor.rs` (StreamingOptions + logic)
- `vendor/ifc-lite/rust/engine/src/lib.rs` (new entry points or options)

These are already modified from upstream (per README), so further changes are
expected.

---

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Property skip breaks downstream | Low | Low | Default is `True` (backward compat) |
| Geometry skip produces confusing empty MeshData | Medium | Low | Document clearly; `vertex_count=0` is obvious |
| Upstream merge conflicts | Medium | Low | Changes are isolated to options plumbing |
| Build/compile issues with Rust changes | Low | Medium | Incremental changes, test after each phase |
