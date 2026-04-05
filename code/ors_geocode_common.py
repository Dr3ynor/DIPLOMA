"""Společné parsování odpovědí ORS Geocode (GeoJSON)."""

from __future__ import annotations

from typing import Any


def first_label_from_ors_geocode_geojson(data: dict[str, Any]) -> str | None:
    """Vrátí první rozumný popisek z GeoJSON FeatureCollection, nebo None."""
    features = data.get("features")
    if not isinstance(features, list):
        return None
    for f in features:
        if not isinstance(f, dict):
            continue
        geom = f.get("geometry")
        if not isinstance(geom, dict) or geom.get("type") != "Point":
            continue
        props = f.get("properties")
        if not isinstance(props, dict):
            continue
        label = (
            props.get("label")
            or props.get("name")
            or props.get("street")
            or ""
        )
        if not isinstance(label, str):
            label = str(label)
        s = label.strip()
        if s:
            return s
    return None
