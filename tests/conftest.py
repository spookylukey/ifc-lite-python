"""Shared fixtures for ifc-lite tests.

Test IFC files are bundled in tests/fixtures/ and come from the IfcOpenShell
project (LGPL-3.0): https://github.com/IfcOpenShell/IfcOpenShell

- basic.ifc: from src/bonsai/test/files/basic.ifc (v0.8.0)
  A small IFC4 file with 3 elements: IfcSlab, IfcWall, IfcBeam.

- project0-openings.ifc: from src/bonsai/docs/tutorials/files/project0-openings.ifc (v0.8.0)
  A medium IFC4 file with walls, doors, windows, and openings.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def small_ifc_path() -> Path:
    """A small IFC4 file with 3 elements (slab, wall, beam)."""
    p = FIXTURES_DIR / "basic.ifc"
    if not p.exists():
        pytest.skip("basic.ifc not found in fixtures")
    return p


@pytest.fixture
def l_bar_ifc_path() -> Path:
    """An IFC4 file for a simple L-shaped IFCReinforcingBar."""
    p = FIXTURES_DIR / "L-BAR.ifc"
    if not p.exists():
        pytest.skip(f"{p.name} not found in fixtures")
    return p


@pytest.fixture
def medium_ifc_path() -> Path:
    """A medium IFC4 file with walls, doors, windows, and openings."""
    p = FIXTURES_DIR / "project0-openings.ifc"
    if not p.exists():
        pytest.skip("project0-openings.ifc not found in fixtures")
    return p
