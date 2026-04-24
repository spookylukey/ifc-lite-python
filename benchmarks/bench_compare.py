#!/usr/bin/env python3
"""Benchmark: ifc-lite vs IfcOpenShell for common IFC operations.

Usage:
    python benchmarks/bench_compare.py [IFC_DIR]

IFC_DIR is a required positional argument pointing to a directory of .ifc files.

Requires both `ifc-lite` and `ifcopenshell` to be installed.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


def _has_ifcopenshell() -> bool:
    try:
        import ifcopenshell  # noqa: F401

        return True
    except ImportError:
        return False


def _has_ifc_lite() -> bool:
    try:
        import ifc_lite  # noqa: F401

        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# ifc-lite benchmarks
# ---------------------------------------------------------------------------


def bench_ifc_lite_load(path: Path) -> dict[str, Any]:
    """Benchmark: load + full geometry processing."""
    import ifc_lite

    t0 = time.perf_counter()
    model = ifc_lite.process_file(path)
    elapsed = time.perf_counter() - t0
    return {
        "time_s": elapsed,
        "meshes": len(model.meshes),
        "vertices": model.stats.total_vertices,
        "triangles": model.stats.total_triangles,
    }


def bench_ifc_lite_elements_by_type(path: Path) -> dict[str, Any]:
    """Benchmark: load + extract elements grouped by type."""
    import ifc_lite

    t0 = time.perf_counter()
    model = ifc_lite.process_file(path)
    types = model.ifc_types
    type_counts = {t: len(model.elements_by_type(t)) for t in types}
    elapsed = time.perf_counter() - t0
    return {"time_s": elapsed, "types": type_counts}


def bench_ifc_lite_geometry(path: Path) -> dict[str, Any]:
    """Benchmark: load + access geometry data for all elements."""
    import ifc_lite

    t0 = time.perf_counter()
    model = ifc_lite.process_file(path)
    total_pos = 0
    total_idx = 0
    for m in model.meshes:
        total_pos += len(m.positions)
        total_idx += len(m.indices)
    elapsed = time.perf_counter() - t0
    return {"time_s": elapsed, "total_position_floats": total_pos, "total_indices": total_idx}


def bench_ifc_lite_metadata(path: Path) -> dict[str, Any]:
    """Benchmark: load + extract metadata for all elements."""
    import ifc_lite

    t0 = time.perf_counter()
    model = ifc_lite.process_file(path)
    elements = []
    for m in model.meshes:
        elements.append(
            {
                "express_id": m.express_id,
                "ifc_type": m.ifc_type,
                "name": m.name,
                "global_id": m.global_id,
                "properties": m.properties,
            }
        )
    elapsed = time.perf_counter() - t0
    return {"time_s": elapsed, "element_count": len(elements)}


# ---------------------------------------------------------------------------
# IfcOpenShell benchmarks
# ---------------------------------------------------------------------------


def bench_ios_load(path: Path) -> dict[str, Any]:
    """Benchmark: load IFC file with IfcOpenShell."""
    import ifcopenshell

    t0 = time.perf_counter()
    ifc = ifcopenshell.open(str(path))
    elapsed = time.perf_counter() - t0
    entities = list(ifc)
    return {"time_s": elapsed, "entities": len(entities)}


def bench_ios_elements_by_type(path: Path) -> dict[str, Any]:
    """Benchmark: load + extract elements grouped by type."""
    import ifcopenshell

    t0 = time.perf_counter()
    ifc = ifcopenshell.open(str(path))
    type_counts: dict[str, int] = defaultdict(int)
    for entity in ifc:
        type_counts[entity.is_a()] += 1
    elapsed = time.perf_counter() - t0
    return {"time_s": elapsed, "types": dict(type_counts)}


def bench_ios_geometry(path: Path) -> dict[str, Any]:
    """Benchmark: load + extract triangulated geometry with IfcOpenShell."""
    import ifcopenshell
    import ifcopenshell.geom

    t0 = time.perf_counter()
    ifc = ifcopenshell.open(str(path))
    settings = ifcopenshell.geom.settings()
    settings.set("mesher-linear-deflection", 0.01)
    settings.set("use-world-coords", True)

    total_verts = 0
    total_faces = 0
    mesh_count = 0

    products = ifc.by_type("IfcProduct")
    for product in products:
        if product.Representation is None:
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
        except Exception:
            continue
        geom = shape.geometry
        verts = geom.verts
        faces = geom.faces
        total_verts += len(verts) // 3
        total_faces += len(faces) // 3
        mesh_count += 1

    elapsed = time.perf_counter() - t0
    return {
        "time_s": elapsed,
        "meshes": mesh_count,
        "vertices": total_verts,
        "triangles": total_faces,
    }


def bench_ios_metadata(path: Path) -> dict[str, Any]:
    """Benchmark: load + extract properties for all products."""
    import ifcopenshell

    t0 = time.perf_counter()
    ifc = ifcopenshell.open(str(path))
    elements = []
    for product in ifc.by_type("IfcProduct"):
        info: dict[str, Any] = {"id": product.id(), "type": product.is_a()}
        if hasattr(product, "Name"):
            info["name"] = product.Name
        if hasattr(product, "GlobalId"):
            info["global_id"] = product.GlobalId
        # Get property sets
        props: dict[str, str] = {}
        for rel in getattr(product, "IsDefinedBy", []):
            if hasattr(rel, "RelatingPropertyDefinition"):
                pdef = rel.RelatingPropertyDefinition
                if hasattr(pdef, "HasProperties"):
                    for prop in pdef.HasProperties:
                        if hasattr(prop, "NominalValue") and prop.NominalValue:
                            props[prop.Name] = str(prop.NominalValue.wrappedValue)
        info["properties"] = props
        elements.append(info)
    elapsed = time.perf_counter() - t0
    return {"time_s": elapsed, "element_count": len(elements)}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

BENCHMARKS = {
    "load": (bench_ifc_lite_load, bench_ios_load),
    "elements_by_type": (bench_ifc_lite_elements_by_type, bench_ios_elements_by_type),
    "geometry": (bench_ifc_lite_geometry, bench_ios_geometry),
    "metadata": (bench_ifc_lite_metadata, bench_ios_metadata),
}


def run_benchmark(
    name: str,
    fn: Any,
    path: Path,
    warmup: int,
    iterations: int,
) -> dict[str, Any]:
    # Warmup
    for _ in range(warmup):
        fn(path)
    # Timed runs
    times = []
    last_result = None
    for _ in range(iterations):
        result = fn(path)
        times.append(result["time_s"])
        last_result = result
    assert last_result is not None
    return {
        "name": name,
        "mean_s": statistics.mean(times),
        "median_s": statistics.median(times),
        "min_s": min(times),
        "max_s": max(times),
        "stdev_s": statistics.stdev(times) if len(times) > 1 else 0.0,
        "iterations": iterations,
        "details": {k: v for k, v in last_result.items() if k != "time_s"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark ifc-lite vs IfcOpenShell")
    parser.add_argument(
        "ifc_dir",
        nargs="?",
        help="Directory containing .ifc files (required)",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        help="Specific .ifc filenames to benchmark (default: auto-select)",
    )
    parser.add_argument("--warmup", type=int, default=1, help="Warmup iterations")
    parser.add_argument("--iterations", type=int, default=5, help="Timed iterations")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    ifc_dir = Path(args.ifc_dir)
    if not ifc_dir.is_dir():
        print(f"Error: {ifc_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    have_lite = _has_ifc_lite()
    have_ios = _has_ifcopenshell()

    if not have_lite:
        print("Warning: ifc-lite not installed, skipping ifc-lite benchmarks", file=sys.stderr)
    if not have_ios:
        print(
            "Warning: ifcopenshell not installed, skipping IfcOpenShell benchmarks",
            file=sys.stderr,
        )
    if not have_lite and not have_ios:
        print("Error: neither ifc-lite nor ifcopenshell installed", file=sys.stderr)
        sys.exit(1)

    # Select files
    if args.files:
        ifc_files = [ifc_dir / f for f in args.files]
    else:
        # Auto-select: small, medium, large
        all_files = sorted(ifc_dir.glob("*.ifc"), key=lambda f: f.stat().st_size)
        if not all_files:
            print(f"No .ifc files found in {ifc_dir}", file=sys.stderr)
            sys.exit(1)
        # Pick up to 3 representative files
        selected = []
        if len(all_files) >= 1:
            selected.append(all_files[0])  # smallest
        if len(all_files) >= 3:
            selected.append(all_files[len(all_files) // 2])  # median
        if len(all_files) >= 2:
            selected.append(all_files[-1])  # largest
        ifc_files = selected

    all_results: list[dict[str, Any]] = []

    for ifc_path in ifc_files:
        if not ifc_path.exists():
            print(f"Warning: {ifc_path} not found, skipping", file=sys.stderr)
            continue

        size_kb = ifc_path.stat().st_size / 1024
        print(f"\n{'=' * 70}")
        print(f"File: {ifc_path.name} ({size_kb:.1f} KB)")
        print(f"{'=' * 70}")

        for bench_name, (lite_fn, ios_fn) in BENCHMARKS.items():
            print(f"\n--- {bench_name} ---")
            file_result: dict[str, Any] = {
                "file": ifc_path.name,
                "file_size_kb": size_kb,
                "benchmark": bench_name,
            }

            if have_lite:
                try:
                    r = run_benchmark(
                        f"ifc-lite/{bench_name}",
                        lite_fn,
                        ifc_path,
                        args.warmup,
                        args.iterations,
                    )
                    file_result["ifc_lite"] = r
                    print(
                        f"  ifc-lite:      {r['mean_s'] * 1000:8.2f} ms "
                        f"(median={r['median_s'] * 1000:.2f}, "
                        f"min={r['min_s'] * 1000:.2f}, max={r['max_s'] * 1000:.2f})"
                    )
                except Exception as e:
                    print(f"  ifc-lite:      ERROR - {e}")
                    file_result["ifc_lite_error"] = str(e)

            if have_ios:
                try:
                    r = run_benchmark(
                        f"ifcopenshell/{bench_name}",
                        ios_fn,
                        ifc_path,
                        args.warmup,
                        args.iterations,
                    )
                    file_result["ifcopenshell"] = r
                    print(
                        f"  IfcOpenShell:  {r['mean_s'] * 1000:8.2f} ms "
                        f"(median={r['median_s'] * 1000:.2f}, "
                        f"min={r['min_s'] * 1000:.2f}, max={r['max_s'] * 1000:.2f})"
                    )
                except Exception as e:
                    print(f"  IfcOpenShell:  ERROR - {e}")
                    file_result["ifcopenshell_error"] = str(e)

            if "ifc_lite" in file_result and "ifcopenshell" in file_result:
                speedup = file_result["ifcopenshell"]["mean_s"] / max(
                    file_result["ifc_lite"]["mean_s"], 1e-9
                )
                file_result["speedup"] = speedup
                print(f"  Speedup:       {speedup:.1f}x")

            all_results.append(file_result)

    if args.json:
        print("\n" + json.dumps(all_results, indent=2))

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    for r in all_results:
        if "speedup" in r:
            print(
                f"  {r['file']:40s} {r['benchmark']:20s} "
                f"ifc-lite={r['ifc_lite']['mean_s'] * 1000:8.2f}ms "
                f"IOS={r['ifcopenshell']['mean_s'] * 1000:8.2f}ms "
                f"speedup={r['speedup']:.1f}x"
            )


if __name__ == "__main__":
    main()
