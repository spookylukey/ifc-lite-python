"""Higher-level Python wrapper around the native _ifc_lite extension."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ifc_lite import _ifc_lite as _native


class OpeningFilterMode(enum.IntEnum):
    """Opening/void filter mode for geometry processing."""

    DEFAULT = 0
    IGNORE_ALL = 1
    IGNORE_OPAQUE = 2


@dataclass
class MeshData:
    """A single mesh element extracted from an IFC file."""

    express_id: int
    ifc_type: str
    global_id: str | None
    name: str | None
    presentation_layer: str | None
    positions: list[float]
    normals: list[float]
    indices: list[int]
    color: tuple[float, float, float, float]
    material_name: str | None
    geometry_item_id: int | None
    properties: dict[str, str] | None

    @staticmethod
    def from_dict(d: dict[str, Any]) -> MeshData:
        """Construct a MeshData from a raw dict returned by the native layer."""
        return MeshData(
            express_id=d["express_id"],
            ifc_type=d["ifc_type"],
            global_id=d.get("global_id"),
            name=d.get("name"),
            presentation_layer=d.get("presentation_layer"),
            positions=list(d["positions"]),
            normals=list(d["normals"]),
            indices=list(d["indices"]),
            color=tuple(d["color"]),  # type: ignore[arg-type]
            material_name=d.get("material_name"),
            geometry_item_id=d.get("geometry_item_id"),
            properties=d.get("properties"),
        )

    @property
    def vertex_count(self) -> int:
        """Number of vertices (positions / 3)."""
        return len(self.positions) // 3

    @property
    def triangle_count(self) -> int:
        """Number of triangles (indices / 3)."""
        return len(self.indices) // 3


@dataclass
class CoordinateInfo:
    """Coordinate system metadata."""

    origin_shift: tuple[float, float, float]
    is_geo_referenced: bool


@dataclass
class ModelMetadata:
    """Model-level metadata extracted from the IFC file."""

    schema_version: str
    entity_count: int
    geometry_entity_count: int
    coordinate_info: CoordinateInfo


@dataclass
class ProcessingStats:
    """Timing and size statistics from geometry processing."""

    total_meshes: int
    total_vertices: int
    total_triangles: int
    parse_time_ms: int
    entity_scan_time_ms: int
    lookup_time_ms: int
    preprocess_time_ms: int
    geometry_time_ms: int
    total_time_ms: int
    from_cache: bool


@dataclass(repr=False)
class IfcModel:
    """High-level wrapper for a parsed IFC model.

    Example::

        model = IfcModel.from_file("building.ifc")
        for mesh in model.meshes:
            print(mesh.ifc_type, mesh.name)

        walls = model.elements_by_type("IfcWall")
    """

    meshes: list[MeshData]
    mesh_coordinate_space: str | None
    site_transform: list[float] | None
    building_transform: list[float] | None
    metadata: ModelMetadata
    stats: ProcessingStats
    _type_index: dict[str, list[MeshData]] = field(  # pyright: ignore[reportUnknownVariableType]
        init=False, repr=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        idx: dict[str, list[MeshData]] = {}
        for m in self.meshes:
            idx.setdefault(m.ifc_type, []).append(m)
        self._type_index = idx

    # -- constructors --------------------------------------------------------

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        opening_filter: OpeningFilterMode = OpeningFilterMode.DEFAULT,
    ) -> IfcModel:
        """Load and process an IFC file from disk."""
        if opening_filter == OpeningFilterMode.DEFAULT:
            raw = _native.process_file(str(path))
        else:
            content = Path(path).read_text(encoding="utf-8", errors="replace")
            raw = _native.process_text_filtered(content, int(opening_filter))
        return cls._from_raw(raw)

    @classmethod
    def from_text(
        cls,
        content: str,
        *,
        opening_filter: OpeningFilterMode = OpeningFilterMode.DEFAULT,
    ) -> IfcModel:
        """Load and process IFC content from a string."""
        if opening_filter == OpeningFilterMode.DEFAULT:
            raw = _native.process_text(content)
        else:
            raw = _native.process_text_filtered(content, int(opening_filter))
        return cls._from_raw(raw)

    # -- queries -------------------------------------------------------------

    @property
    def ifc_types(self) -> list[str]:
        """All distinct IFC types present in the model."""
        return sorted(self._type_index.keys())

    def elements_by_type(self, ifc_type: str) -> list[MeshData]:
        """Return all mesh elements matching the given IFC type name."""
        return self._type_index.get(ifc_type, [])

    def element_by_express_id(self, express_id: int) -> MeshData | None:
        """Look up a single element by its express ID."""
        for m in self.meshes:
            if m.express_id == express_id:
                return m
        return None

    def element_by_global_id(self, global_id: str) -> MeshData | None:
        """Look up a single element by its IFC GlobalId."""
        for m in self.meshes:
            if m.global_id == global_id:
                return m
        return None

    # -- internals -----------------------------------------------------------

    @classmethod
    def _from_raw(cls, raw: dict[str, Any]) -> IfcModel:
        meshes = [MeshData.from_dict(m) for m in raw["meshes"]]
        meta_raw = raw["metadata"]
        ci_raw = meta_raw["coordinate_info"]
        coord = CoordinateInfo(
            origin_shift=tuple(ci_raw["origin_shift"]),  # type: ignore[arg-type]
            is_geo_referenced=ci_raw["is_geo_referenced"],
        )
        metadata = ModelMetadata(
            schema_version=meta_raw["schema_version"],
            entity_count=meta_raw["entity_count"],
            geometry_entity_count=meta_raw["geometry_entity_count"],
            coordinate_info=coord,
        )
        stats_raw = raw["stats"]
        stats = ProcessingStats(
            total_meshes=stats_raw["total_meshes"],
            total_vertices=stats_raw["total_vertices"],
            total_triangles=stats_raw["total_triangles"],
            parse_time_ms=stats_raw["parse_time_ms"],
            entity_scan_time_ms=stats_raw["entity_scan_time_ms"],
            lookup_time_ms=stats_raw["lookup_time_ms"],
            preprocess_time_ms=stats_raw["preprocess_time_ms"],
            geometry_time_ms=stats_raw["geometry_time_ms"],
            total_time_ms=stats_raw["total_time_ms"],
            from_cache=stats_raw["from_cache"],
        )
        return cls(
            meshes=meshes,
            mesh_coordinate_space=raw.get("mesh_coordinate_space"),
            site_transform=raw.get("site_transform"),
            building_transform=raw.get("building_transform"),
            metadata=metadata,
            stats=stats,
        )


# -- module-level convenience functions ----------------------------------------


def process_file(
    path: str | Path,
    *,
    opening_filter: OpeningFilterMode = OpeningFilterMode.DEFAULT,
) -> IfcModel:
    """Load and process an IFC file. Convenience alias for IfcModel.from_file."""
    return IfcModel.from_file(path, opening_filter=opening_filter)


def process_text(
    content: str,
    *,
    opening_filter: OpeningFilterMode = OpeningFilterMode.DEFAULT,
) -> IfcModel:
    """Process IFC text content. Convenience alias for IfcModel.from_text."""
    return IfcModel.from_text(content, opening_filter=opening_filter)


def version() -> str:
    """Return the version of the underlying ifc-lite native library."""
    return _native.version()  # type: ignore[no-any-return]
