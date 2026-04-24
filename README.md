# ifc-lite

High-performance Python bindings for the [ifc-lite](https://github.com/louistrue/ifc-lite) IFC parser.

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
```

## API

### Module-level functions

- `ifc_lite.process_file(path)` – Load and process an IFC file from disk
- `ifc_lite.process_text(content)` – Process IFC content from a string
- `ifc_lite.version()` – Get the native library version

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
