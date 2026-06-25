"""Tests for the high-level IfcModel API."""

from __future__ import annotations

from pathlib import Path

import ifc_lite
from ifc_lite._core import (
    CoordinateInfo,
    IfcModel,
    MeshData,
    ModelMetadata,
    OpeningFilterMode,
    ProcessingStats,
    PropertySet,
    PropertyValue,
)


def test_version() -> None:
    assert isinstance(ifc_lite.version(), str)


def test_from_file(small_ifc_path: Path) -> None:
    model = IfcModel.from_file(small_ifc_path)
    assert isinstance(model, IfcModel)
    assert len(model.meshes) == 5  # 3 instances + 2 type-products
    assert isinstance(model.meshes[0], MeshData)


def test_from_text(small_ifc_path: Path) -> None:
    content = small_ifc_path.read_text(encoding="utf-8", errors="replace")
    model = IfcModel.from_text(content)
    assert len(model.meshes) == 5  # 3 instances + 2 type-products


def test_from_file_with_filter(small_ifc_path: Path) -> None:
    model = IfcModel.from_file(small_ifc_path, opening_filter=OpeningFilterMode.IGNORE_ALL)
    assert len(model.meshes) == 5  # no openings in this file anyway


def test_ifc_types(small_ifc_path: Path) -> None:
    model = IfcModel.from_file(small_ifc_path)
    assert sorted(model.ifc_types) == [
        "IfcBeam",
        "IfcSlab",
        "IfcSlabType",
        "IfcWall",
        "IfcWallType",
    ]


def test_elements_by_type(small_ifc_path: Path) -> None:
    model = IfcModel.from_file(small_ifc_path)
    walls = model.elements_by_type("IfcWall")
    assert len(walls) == 1
    assert all(m.ifc_type == "IfcWall" for m in walls)
    assert model.elements_by_type("IfcReinforcingBar") == []


def test_element_by_express_id(small_ifc_path: Path) -> None:
    model = IfcModel.from_file(small_ifc_path)
    mesh = model.element_by_express_id(79)
    assert mesh is not None
    assert mesh.express_id == 79
    assert model.element_by_express_id(99999) is None


def test_element_by_global_id(small_ifc_path: Path) -> None:
    model = IfcModel.from_file(small_ifc_path)
    mesh = model.element_by_global_id("20Njb8mHv8v9ESSk_1YM2m")
    assert mesh is not None
    assert mesh.express_id == 79
    assert model.element_by_global_id("nonexistent") is None


def test_mesh_data_properties(small_ifc_path: Path) -> None:
    model = IfcModel.from_file(small_ifc_path)
    m = model.meshes[0]
    assert m.vertex_count == len(m.positions) // 3
    assert m.triangle_count == len(m.indices) // 3
    assert m.vertex_count > 0
    assert m.triangle_count > 0
    assert len(m.color) == 4
    assert all(0.0 <= c <= 1.0 for c in m.color)


def test_metadata(small_ifc_path: Path) -> None:
    model = IfcModel.from_file(small_ifc_path)
    assert isinstance(model.metadata, ModelMetadata)
    assert model.metadata.schema_version == "IFC4"
    assert model.metadata.entity_count > 0
    assert isinstance(model.metadata.coordinate_info, CoordinateInfo)


def test_stats(small_ifc_path: Path) -> None:
    model = IfcModel.from_file(small_ifc_path)
    assert isinstance(model.stats, ProcessingStats)
    assert model.stats.total_meshes == 5
    assert model.stats.total_vertices > 0


def test_convenience_functions(small_ifc_path: Path) -> None:
    model = ifc_lite.process_file(small_ifc_path)
    assert isinstance(model, IfcModel)
    assert len(model.meshes) == 5

    content = small_ifc_path.read_text(encoding="utf-8", errors="replace")
    model2 = ifc_lite.process_text(content)
    assert len(model2.meshes) == 5


def test_medium_file(medium_ifc_path: Path) -> None:
    model = IfcModel.from_file(medium_ifc_path)
    assert "IfcWall" in model.ifc_types
    assert "IfcDoor" in model.ifc_types
    assert len(model.meshes) > 10


def test_from_text_with_filter(small_ifc_path: Path) -> None:
    content = small_ifc_path.read_text(encoding="utf-8", errors="replace")
    model = IfcModel.from_text(content, opening_filter=OpeningFilterMode.IGNORE_ALL)
    assert len(model.meshes) == 5


def test_model_repr(small_ifc_path: Path) -> None:
    content = small_ifc_path.read_text(encoding="utf-8", errors="replace")
    model = IfcModel.from_text(content, opening_filter=OpeningFilterMode.IGNORE_ALL)
    assert len(repr(model)) < 100


def test_property_sets_on_wall(medium_ifc_path: Path) -> None:
    """Wall elements should have structured property sets."""
    model = IfcModel.from_file(medium_ifc_path)
    wall = model.element_by_global_id("1Bg6FSoNzDMwh2dHDeO2B3")
    assert wall is not None
    assert wall.property_sets is not None
    assert len(wall.property_sets) >= 1

    pset = wall.property_sets[0]
    assert isinstance(pset, PropertySet)
    assert pset.name == "EPset_Parametric"
    assert len(pset.properties) >= 1

    prop = pset.properties[0]
    assert isinstance(prop, PropertyValue)
    assert prop.name == "Engine"
    assert prop.value == "Bonsai.DumbLayer2"


def test_property_sets_all_walls_have_psets(medium_ifc_path: Path) -> None:
    """All walls in the medium fixture should have EPset_Parametric."""
    model = IfcModel.from_file(medium_ifc_path)
    walls = model.elements_by_type("IfcWall")
    assert len(walls) > 0
    for wall in walls:
        assert wall.property_sets is not None, f"Wall #{wall.express_id} has no property_sets"
        pset_names = [ps.name for ps in wall.property_sets]
        assert "EPset_Parametric" in pset_names, (
            f"Wall #{wall.express_id} missing EPset_Parametric, has: {pset_names}"
        )


def test_property_sets_none_for_elements_without(small_ifc_path: Path) -> None:
    """Elements with no property sets should have property_sets=None."""
    model = IfcModel.from_file(small_ifc_path)
    # The basic.ifc file may or may not have property sets
    for mesh in model.meshes:
        # property_sets should be None or a list, never something else
        assert mesh.property_sets is None or isinstance(mesh.property_sets, list)


def test_property_sets_exported_from_package() -> None:
    """PropertySet and PropertyValue should be importable from ifc_lite."""
    from ifc_lite import PropertySet as PS
    from ifc_lite import PropertyValue as PV

    assert PS is PropertySet
    assert PV is PropertyValue


# -- load_geometry=False tests --------------------------------------------------


def test_load_geometry_false_from_file(small_ifc_path: Path) -> None:
    """load_geometry=False should return elements with empty geometry.

    Note: more elements may appear than with load_geometry=True because
    entities whose geometry turns out to be empty (e.g. IfcSite,
    IfcElementAssembly) are normally filtered out during extraction but
    are included when geometry is skipped.
    """
    model = IfcModel.from_file(small_ifc_path, load_geometry=False)
    # At least the 3 real geometry elements, possibly more
    assert len(model.meshes) >= 3
    for mesh in model.meshes:
        assert mesh.vertex_count == 0
        assert mesh.triangle_count == 0
        assert mesh.positions == []
        assert mesh.normals == []
        assert mesh.indices == []


def test_load_geometry_false_preserves_metadata(small_ifc_path: Path) -> None:
    """Metadata should still be populated when geometry is skipped."""
    model = IfcModel.from_file(small_ifc_path, load_geometry=False)
    # Should include at least the 3 real element types
    for expected_type in ["IfcBeam", "IfcSlab", "IfcWall"]:
        assert expected_type in model.ifc_types
    for mesh in model.meshes:
        assert mesh.express_id > 0
        assert mesh.ifc_type != ""
        assert mesh.global_id is not None
        assert mesh.name is not None


def test_load_geometry_false_from_text(small_ifc_path: Path) -> None:
    content = small_ifc_path.read_text(encoding="utf-8", errors="replace")
    model = IfcModel.from_text(content, load_geometry=False)
    assert len(model.meshes) >= 3
    for mesh in model.meshes:
        assert mesh.vertex_count == 0


def test_load_geometry_false_with_opening_filter(small_ifc_path: Path) -> None:
    model = IfcModel.from_file(
        small_ifc_path,
        opening_filter=OpeningFilterMode.IGNORE_ALL,
        load_geometry=False,
    )
    assert len(model.meshes) >= 3
    for mesh in model.meshes:
        assert mesh.vertex_count == 0


def test_load_geometry_false_preserves_properties(medium_ifc_path: Path) -> None:
    """Property sets should still be populated when geometry is skipped."""
    model = IfcModel.from_file(medium_ifc_path, load_geometry=False)
    wall = model.element_by_global_id("1Bg6FSoNzDMwh2dHDeO2B3")
    assert wall is not None
    assert wall.vertex_count == 0
    assert wall.property_sets is not None
    assert len(wall.property_sets) >= 1
    pset_names = [ps.name for ps in wall.property_sets]
    assert "EPset_Parametric" in pset_names


def test_convenience_process_file_load_geometry_false(small_ifc_path: Path) -> None:
    model = ifc_lite.process_file(small_ifc_path, load_geometry=False)
    assert len(model.meshes) >= 3
    for mesh in model.meshes:
        assert mesh.vertex_count == 0


def test_convenience_process_text_load_geometry_false(small_ifc_path: Path) -> None:
    content = small_ifc_path.read_text(encoding="utf-8", errors="replace")
    model = ifc_lite.process_text(content, load_geometry=False)
    assert len(model.meshes) >= 3
    for mesh in model.meshes:
        assert mesh.vertex_count == 0


# -- load_properties=False tests ------------------------------------------------


def test_load_properties_false_from_file(medium_ifc_path: Path) -> None:
    """load_properties=False should return elements with no property sets."""
    model = IfcModel.from_file(medium_ifc_path, load_properties=False)
    assert len(model.meshes) > 0
    for mesh in model.meshes:
        assert mesh.properties is None
        assert mesh.property_sets is None


def test_load_properties_false_preserves_geometry(medium_ifc_path: Path) -> None:
    """Geometry should still be populated when properties are skipped."""
    model = IfcModel.from_file(medium_ifc_path, load_properties=False)
    walls = model.elements_by_type("IfcWall")
    assert len(walls) > 0
    for wall in walls:
        assert wall.vertex_count > 0
        assert wall.triangle_count > 0


def test_load_properties_false_from_text(medium_ifc_path: Path) -> None:
    content = medium_ifc_path.read_text(encoding="utf-8", errors="replace")
    model = IfcModel.from_text(content, load_properties=False)
    for mesh in model.meshes:
        assert mesh.property_sets is None


def test_load_properties_false_with_opening_filter(medium_ifc_path: Path) -> None:
    model = IfcModel.from_file(
        medium_ifc_path,
        opening_filter=OpeningFilterMode.IGNORE_ALL,
        load_properties=False,
    )
    for mesh in model.meshes:
        assert mesh.property_sets is None


def test_convenience_process_file_load_properties_false(medium_ifc_path: Path) -> None:
    model = ifc_lite.process_file(medium_ifc_path, load_properties=False)
    for mesh in model.meshes:
        assert mesh.property_sets is None


# -- Combined load_geometry=False + load_properties=False ----------------------


def test_load_both_false(medium_ifc_path: Path) -> None:
    """Both flags False should give metadata-only elements."""
    model = IfcModel.from_file(
        medium_ifc_path,
        load_geometry=False,
        load_properties=False,
    )
    assert len(model.meshes) > 0
    for mesh in model.meshes:
        assert mesh.vertex_count == 0
        assert mesh.property_sets is None
        assert mesh.express_id > 0
        assert mesh.ifc_type != ""


def test_load_both_false_still_has_metadata(medium_ifc_path: Path) -> None:
    model = IfcModel.from_file(
        medium_ifc_path,
        load_geometry=False,
        load_properties=False,
    )
    assert isinstance(model.metadata, ModelMetadata)
    assert model.metadata.schema_version == "IFC4"
    assert model.metadata.entity_count > 0
    assert isinstance(model.stats, ProcessingStats)
