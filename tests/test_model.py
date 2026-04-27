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
)


def test_version() -> None:
    assert isinstance(ifc_lite.version(), str)


def test_from_file(small_ifc_path: Path) -> None:
    model = IfcModel.from_file(small_ifc_path)
    assert isinstance(model, IfcModel)
    assert len(model.meshes) == 3
    assert isinstance(model.meshes[0], MeshData)


def test_from_text(small_ifc_path: Path) -> None:
    content = small_ifc_path.read_text(encoding="utf-8", errors="replace")
    model = IfcModel.from_text(content)
    assert len(model.meshes) == 3


def test_from_file_with_filter(small_ifc_path: Path) -> None:
    model = IfcModel.from_file(small_ifc_path, opening_filter=OpeningFilterMode.IGNORE_ALL)
    assert len(model.meshes) == 3  # no openings in this file anyway


def test_ifc_types(small_ifc_path: Path) -> None:
    model = IfcModel.from_file(small_ifc_path)
    assert sorted(model.ifc_types) == ["IfcBeam", "IfcSlab", "IfcWall"]


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
    assert model.stats.total_meshes == 3
    assert model.stats.total_vertices > 0


def test_convenience_functions(small_ifc_path: Path) -> None:
    model = ifc_lite.process_file(small_ifc_path)
    assert isinstance(model, IfcModel)
    assert len(model.meshes) == 3

    content = small_ifc_path.read_text(encoding="utf-8", errors="replace")
    model2 = ifc_lite.process_text(content)
    assert len(model2.meshes) == 3


def test_medium_file(medium_ifc_path: Path) -> None:
    model = IfcModel.from_file(medium_ifc_path)
    assert "IfcWall" in model.ifc_types
    assert "IfcDoor" in model.ifc_types
    assert len(model.meshes) > 10


def test_from_text_with_filter(small_ifc_path: Path) -> None:
    content = small_ifc_path.read_text(encoding="utf-8", errors="replace")
    model = IfcModel.from_text(content, opening_filter=OpeningFilterMode.IGNORE_ALL)
    assert len(model.meshes) == 3


def test_model_repr(small_ifc_path: Path) -> None:
    content = small_ifc_path.read_text(encoding="utf-8", errors="replace")
    model = IfcModel.from_text(content, opening_filter=OpeningFilterMode.IGNORE_ALL)
    assert len(repr(model)) < 100
    
