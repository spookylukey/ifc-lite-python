"""Type stubs for the native _ifc_lite extension module."""

from typing import Any

from ifc_lite._core import TessellationQuality

def process_file(
    path: str,
    /,
    include_properties: bool = True,
    include_geometry: bool = True,
    tessellation_quality: TessellationQuality = TessellationQuality.MEDIUM,
) -> dict[str, Any]: ...
def process_text(
    content: str,
    /,
    include_properties: bool = True,
    include_geometry: bool = True,
    tessellation_quality: TessellationQuality = TessellationQuality.MEDIUM,
) -> dict[str, Any]: ...
def process_text_filtered(
    content: str,
    filter_mode: int,
    /,
    include_properties: bool = True,
    include_geometry: bool = True,
    tessellation_quality: TessellationQuality = TessellationQuality.MEDIUM,
) -> dict[str, Any]: ...
def version() -> str: ...
