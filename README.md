# ifc-lite

High-performance Python bindings for the [ifc-lite](https://github.com/louistrue/ifc-lite) IFC parser.


## Relationship with upstream

This Python version is not released or maintained by the original authors of
ifc-lite. It is a modified version, released under the same licence.

The Rust code is basically copied from upstream, but with some changes:

- The `MeshData` object exposes `property_sets` as an attribute, and the Rust
  code has been changed to populate this for all elements.
- Added `include_geometry` option to `StreamingOptions` in the processing
  crate. When `false`, geometry extraction is skipped and `MeshData` objects
  are returned with empty geometry but fully populated metadata.
- Added `process_ifc_text_with_options` and `process_ifc_file_with_options` to
  the engine crate for non-streaming use with `include_properties` and
  `include_geometry` flags.

These changes are based on the current needs of the maintainers, and are
provisional, while we are still in the evaluation stage for this new library.


## Installation

```bash
pip install ifc-lite
```

## Quick Start

```python
import ifc_lite

# Load an IFC file
model = ifc_lite.process_file("building.ifc")

# List all IFC types in the model
print(model.ifc_types)

# Get all reinforcing bars
bars = model.elements_by_type("IfcReinforcingBar")
for bar in bars:
    print(f"{bar.name}: {bar.vertex_count} vertices, {bar.triangle_count} triangles")
    print(f"  Properties: {bar.properties}")

# Access geometry (vertex positions, normals, triangle indices)
for mesh in model.meshes:
    positions = mesh.positions  # flat list of x,y,z triplets
    normals = mesh.normals      # flat list of nx,ny,nz triplets
    indices = mesh.indices      # triangle indices
    color = mesh.color          # RGBA tuple

# Load metadata + properties only (skip expensive geometry extraction)
model = ifc_lite.process_file("building.ifc", load_geometry=False)

# Load geometry only (skip property set parsing)
model = ifc_lite.process_file("building.ifc", load_properties=False)

# Fastest: metadata only (no geometry, no properties)
model = ifc_lite.process_file(
    "building.ifc", load_geometry=False, load_properties=False
)
```

## API

### Module-level functions

- `ifc_lite.process_file(path, *, load_geometry=True, load_properties=True)` – Load and process an IFC file from disk
- `ifc_lite.process_text(content, *, load_geometry=True, load_properties=True)` – Process IFC content from a string
- `ifc_lite.version()` – Get the native library version

Optional keyword arguments:
- `load_geometry` – When `False`, skip geometry extraction. `MeshData` elements will have empty `positions`/`normals`/`indices` but full metadata. Significantly faster for large files.
- `load_properties` – When `False`, skip property set parsing. `MeshData` elements will have `properties=None` and `property_sets=None`.

### IfcModel

- `model.meshes` – List of all `MeshData` elements
- `model.ifc_types` – All distinct IFC type names
- `model.elements_by_type(type_name)` – Filter elements by IFC type
- `model.element_by_express_id(id)` – Lookup by express ID
- `model.element_by_global_id(gid)` – Lookup by IFC GlobalId
- `model.metadata` – Schema version, entity counts, coordinate info
- `model.stats` – Processing timing statistics

### MeshData

- `mesh.express_id`, `mesh.ifc_type`, `mesh.global_id`, `mesh.name`
- `mesh.positions`, `mesh.normals`, `mesh.indices`, `mesh.color`
- `mesh.properties` – IFC property set values (dict or None)
- `mesh.vertex_count`, `mesh.triangle_count`

## License

MPL-2.0 (same as upstream ifc-lite)
