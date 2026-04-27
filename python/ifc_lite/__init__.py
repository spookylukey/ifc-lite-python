"""ifc-lite: High-performance Python bindings for the ifc-lite IFC parser."""

from __future__ import annotations

from ifc_lite._core import (
    IfcModel,
    MeshData,
    OpeningFilterMode,
    PropertySet,
    PropertyValue,
    process_file,
    process_text,
    version,
)

__all__ = [
    "IfcModel",
    "MeshData",
    "OpeningFilterMode",
    "PropertySet",
    "PropertyValue",
    "process_file",
    "process_text",
    "version",
]
