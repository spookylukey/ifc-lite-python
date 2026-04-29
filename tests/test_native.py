"""Tests for the low-level native _ifc_lite bindings."""

from __future__ import annotations

from pathlib import Path

import pytest
from ifc_lite import _ifc_lite as _native


def test_version() -> None:
    v = _native.version()
    assert isinstance(v, str)
    assert len(v) > 0


def test_process_file(small_ifc_path: Path) -> None:
    result = _native.process_file(str(small_ifc_path))
    assert isinstance(result, dict)
    assert "meshes" in result
    assert "metadata" in result
    assert "stats" in result
    assert len(result["meshes"]) == 3


def test_process_text(small_ifc_path: Path) -> None:
    content = small_ifc_path.read_text(encoding="utf-8", errors="replace")
    result = _native.process_text(content)
    assert isinstance(result, dict)
    assert len(result["meshes"]) == 3


def test_process_text_filtered(small_ifc_path: Path) -> None:
    content = small_ifc_path.read_text(encoding="utf-8", errors="replace")
    result = _native.process_text_filtered(content, 0)
    assert isinstance(result, dict)
    assert len(result["meshes"]) == 3


def test_process_text_filtered_invalid_mode(small_ifc_path: Path) -> None:
    content = small_ifc_path.read_text(encoding="utf-8", errors="replace")
    with pytest.raises(ValueError, match="filter_mode"):
        _native.process_text_filtered(content, 99)


def test_process_file_not_found() -> None:
    with pytest.raises(OSError):
        _native.process_file("/nonexistent/path.ifc")


def test_mesh_data_fields(small_ifc_path: Path) -> None:
    result = _native.process_file(str(small_ifc_path))
    mesh = result["meshes"][0]
    assert isinstance(mesh["express_id"], int)
    assert isinstance(mesh["ifc_type"], str)
    assert isinstance(mesh["positions"], list)
    assert isinstance(mesh["normals"], list)
    assert isinstance(mesh["indices"], list)
    assert isinstance(mesh["color"], list)
    assert len(mesh["color"]) == 4
    # positions should be x,y,z triplets
    assert len(mesh["positions"]) % 3 == 0
    assert len(mesh["normals"]) % 3 == 0
    assert len(mesh["indices"]) % 3 == 0


def test_metadata_fields(small_ifc_path: Path) -> None:
    result = _native.process_file(str(small_ifc_path))
    meta = result["metadata"]
    assert meta["schema_version"] == "IFC4"
    assert meta["entity_count"] > 0
    assert meta["geometry_entity_count"] > 0
    coord = meta["coordinate_info"]
    assert len(coord["origin_shift"]) == 3
    assert isinstance(coord["is_geo_referenced"], bool)


def test_stats_fields(small_ifc_path: Path) -> None:
    result = _native.process_file(str(small_ifc_path))
    stats = result["stats"]
    assert stats["total_meshes"] == 3
    assert stats["total_vertices"] > 0
    assert stats["total_triangles"] > 0
    assert isinstance(stats["total_time_ms"], int)


def test_property_sets_in_native_output(medium_ifc_path: Path) -> None:
    """Native output should include property_sets for elements that have them."""
    result = _native.process_file(str(medium_ifc_path))
    # Find wall #143 (global_id 1Bg6FSoNzDMwh2dHDeO2B3)
    wall = next(
        (m for m in result["meshes"] if m.get("global_id") == "1Bg6FSoNzDMwh2dHDeO2B3"),
        None,
    )
    assert wall is not None
    psets: list[dict[str, object]] = wall["property_sets"]  # type: ignore[assignment]
    assert isinstance(psets, list)
    assert len(psets) >= 1
    first_pset = psets[0]
    assert first_pset["name"] == "EPset_Parametric"
    first_props: list[dict[str, str]] = first_pset["properties"]  # type: ignore[assignment]
    assert len(first_props) >= 1
    assert first_props[0]["name"] == "Engine"
    assert first_props[0]["value"] == "Bonsai.DumbLayer2"


def test_process_file_no_geometry(small_ifc_path: Path) -> None:
    result = _native.process_file(str(small_ifc_path), include_geometry=False)
    assert len(result["meshes"]) >= 3
    for mesh in result["meshes"]:
        assert mesh["positions"] == []
        assert mesh["normals"] == []
        assert mesh["indices"] == []
        assert isinstance(mesh["express_id"], int)
        assert isinstance(mesh["ifc_type"], str)


def test_process_text_no_geometry(small_ifc_path: Path) -> None:
    content = small_ifc_path.read_text(encoding="utf-8", errors="replace")
    result = _native.process_text(content, include_geometry=False)
    assert len(result["meshes"]) >= 3
    for mesh in result["meshes"]:
        assert mesh["positions"] == []


def test_process_file_no_properties(medium_ifc_path: Path) -> None:
    result = _native.process_file(str(medium_ifc_path), include_properties=False)
    for mesh in result["meshes"]:
        assert mesh["properties"] is None
        assert mesh["property_sets"] is None


def test_process_text_filtered_no_geometry(small_ifc_path: Path) -> None:
    content = small_ifc_path.read_text(encoding="utf-8", errors="replace")
    result = _native.process_text_filtered(content, 0, include_geometry=False)
    assert len(result["meshes"]) >= 3
    for mesh in result["meshes"]:
        assert mesh["positions"] == []


def test_process_text_filtered_no_properties(medium_ifc_path: Path) -> None:
    content = medium_ifc_path.read_text(encoding="utf-8", errors="replace")
    result = _native.process_text_filtered(content, 0, include_properties=False)
    for mesh in result["meshes"]:
        assert mesh["property_sets"] is None
