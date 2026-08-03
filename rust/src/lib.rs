// Python bindings for ifc-lite using PyO3

use ifc_lite_engine::{
    process_ifc_file, process_ifc_file_with_options, process_ifc_text,
    process_ifc_text_with_options,
    EngineResult, MeshData, OpeningFilterMode,
};
use ifc_lite_geometry::TessellationQuality;
use pyo3::exceptions::PyIOError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
// ─── Helper: convert MeshData → Python dict ───────────────────────────────

fn mesh_to_pydict(py: Python<'_>, m: &MeshData) -> PyResult<Py<PyDict>> {
    let d = PyDict::new(py);
    d.set_item("express_id", m.express_id)?;
    d.set_item("ifc_type", &m.ifc_type)?;
    d.set_item("global_id", &m.global_id)?;
    d.set_item("name", &m.name)?;
    d.set_item("presentation_layer", &m.presentation_layer)?;
    d.set_item("positions", m.positions.as_slice())?;
    d.set_item("normals", m.normals.as_slice())?;
    d.set_item("indices", m.indices.as_slice())?;
    d.set_item("color", m.color.as_slice())?;
    d.set_item("material_name", &m.material_name)?;
    d.set_item("geometry_item_id", m.geometry_item_id)?;
    match &m.properties {
        Some(props) => {
            let pd = PyDict::new(py);
            for (k, v) in props {
                pd.set_item(k, v)?;
            }
            d.set_item("properties", pd)?;
        }
        None => {
            d.set_item("properties", py.None())?;
        }
    }
    match &m.property_sets {
        Some(psets) => {
            let py_psets = PyList::new(
                py,
                psets.iter().map(|pset| {
                    let pd = PyDict::new(py);
                    pd.set_item("name", &pset.name).unwrap();
                    let props = PyList::new(
                        py,
                        pset.properties.iter().map(|prop| {
                            let p = PyDict::new(py);
                            p.set_item("name", &prop.name).unwrap();
                            p.set_item("value", &prop.value).unwrap();
                            p
                        }).collect::<Vec<_>>(),
                    ).unwrap();
                    pd.set_item("properties", props).unwrap();
                    pd
                }).collect::<Vec<_>>(),
            )?;
            d.set_item("property_sets", py_psets)?;
        }
        None => {
            d.set_item("property_sets", py.None())?;
        }
    }
    Ok(d.into())
}

fn result_to_pydict(py: Python<'_>, r: &EngineResult) -> PyResult<Py<PyDict>> {
    let d = PyDict::new(py);

    let meshes = PyList::new(
        py,
        r.meshes
            .iter()
            .map(|m| mesh_to_pydict(py, m))
            .collect::<PyResult<Vec<_>>>()?,
    )?;
    d.set_item("meshes", meshes)?;
    d.set_item("mesh_coordinate_space", &r.mesh_coordinate_space)?;
    d.set_item("site_transform", &r.site_transform)?;
    d.set_item("building_transform", &r.building_transform)?;

    // metadata
    let meta = PyDict::new(py);
    meta.set_item("schema_version", &r.metadata.schema_version)?;
    meta.set_item("entity_count", r.metadata.entity_count)?;
    meta.set_item("geometry_entity_count", r.metadata.geometry_entity_count)?;
    let coord = PyDict::new(py);
    coord.set_item(
        "origin_shift",
        r.metadata.coordinate_info.origin_shift.as_slice(),
    )?;
    coord.set_item(
        "is_geo_referenced",
        r.metadata.coordinate_info.is_geo_referenced,
    )?;
    meta.set_item("coordinate_info", coord)?;
    d.set_item("metadata", meta)?;

    // stats
    let stats = PyDict::new(py);
    stats.set_item("total_meshes", r.stats.total_meshes)?;
    stats.set_item("total_vertices", r.stats.total_vertices)?;
    stats.set_item("total_triangles", r.stats.total_triangles)?;
    stats.set_item("parse_time_ms", r.stats.parse_time_ms)?;
    stats.set_item("entity_scan_time_ms", r.stats.entity_scan_time_ms)?;
    stats.set_item("lookup_time_ms", r.stats.lookup_time_ms)?;
    stats.set_item("preprocess_time_ms", r.stats.preprocess_time_ms)?;
    stats.set_item("geometry_time_ms", r.stats.geometry_time_ms)?;
    stats.set_item("total_time_ms", r.stats.total_time_ms)?;
    stats.set_item("from_cache", r.stats.from_cache)?;
    d.set_item("stats", stats)?;

    Ok(d.into())
}

// ─── Python-visible functions ─────────────────────────────────────────────

/// Process an IFC file from disk. Returns a dict with meshes, metadata, stats.
#[pyfunction]
#[pyo3(signature = (path, /, include_properties=true, include_geometry=true, tessellation_quality=2)
)]
fn process_file(
    py: Python<'_>,
    path: &str,
    include_properties: bool,
    include_geometry: bool,
    tessellation_quality: u8,
) -> PyResult<Py<PyDict>> {
    let tessellation_quality = TessellationQuality::from_index(tessellation_quality);
    let result = if include_properties && include_geometry && tessellation_quality == TessellationQuality::Medium {
        process_ifc_file(path).map_err(|e| PyIOError::new_err(e.to_string()))?
    } else {
        process_ifc_file_with_options(
            path,
            OpeningFilterMode::Default,
            include_properties,
            include_geometry,
            tessellation_quality,
        )
            .map_err(|e| PyIOError::new_err(e.to_string()))?
    };
    result_to_pydict(py, &result)
}

/// Process IFC content from a string. Returns a dict with meshes, metadata, stats.
#[pyfunction]
#[pyo3(signature = (content, /, include_properties=true, include_geometry=true, tessellation_quality=2)
)]
fn process_text(
    py: Python<'_>,
    content: &str,
    include_properties: bool,
    include_geometry: bool,
    tessellation_quality: u8,
) -> PyResult<Py<PyDict>> {
    let tessellation_quality = TessellationQuality::from_index(tessellation_quality);
    let result = if include_properties && include_geometry && tessellation_quality == TessellationQuality::Medium {
        process_ifc_text(content)
    } else {
        process_ifc_text_with_options(
            content,
            OpeningFilterMode::Default,
            include_properties,
            include_geometry,
            tessellation_quality,
        )
    };
    result_to_pydict(py, &result)
}

/// Process IFC content with an opening filter mode.
/// filter_mode: 0 = Default, 1 = IgnoreAll, 2 = IgnoreOpaque
#[pyfunction]
#[pyo3(signature = (content, filter_mode, /, include_properties=true, include_geometry=true, tessellation_quality=2)
)]
fn process_text_filtered(
    py: Python<'_>,
    content: &str,
    filter_mode: u8,
    include_properties: bool,
    include_geometry: bool,
    tessellation_quality: u8,
) -> PyResult<Py<PyDict>> {
    let tessellation_quality = TessellationQuality::from_index(tessellation_quality);
    let mode = match filter_mode {
        0 => OpeningFilterMode::Default,
        1 => OpeningFilterMode::IgnoreAll,
        2 => OpeningFilterMode::IgnoreOpaque,
        _ => {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "filter_mode must be 0 (Default), 1 (IgnoreAll), or 2 (IgnoreOpaque)",
            ))
        }
    };
    let result = process_ifc_text_with_options(
        content,
        mode,
        include_properties,
        include_geometry,
        tessellation_quality,
    );
    result_to_pydict(py, &result)
}

/// Return the version of the underlying ifc-lite engine.
#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

// ─── Module definition ───────────────────────────────────────────────────

#[pymodule]
fn _ifc_lite(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(process_file, m)?)?;
    m.add_function(wrap_pyfunction!(process_text, m)?)?;
    m.add_function(wrap_pyfunction!(process_text_filtered, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;
    Ok(())
}
