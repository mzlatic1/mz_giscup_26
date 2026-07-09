"""Input/output loading helpers for GIS Cup datasets."""

from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import Polygon, shape

from giscup.geometry import make_building
from giscup.models import Building, DatasetInfo


def load_buildings(path: str | Path, id_property: str = "id") -> tuple[list[Building], DatasetInfo]:
    """Load building polygons from a GeoJSON or any file supported by GeoPandas.

    GeoPandas/pyogrio is preferred because it preserves CRS metadata reliably. A
    small GeoJSON fallback is provided for environments where GeoPandas is not
    installed yet.
    """
    path = Path(path)
    try:
        import geopandas as gpd

        gdf = gpd.read_file(path)
        crs = str(gdf.crs) if gdf.crs is not None else None
        buildings: list[Building] = []
        for idx, row in gdf.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            if geom.geom_type != "Polygon":
                raise ValueError(f"Expected Polygon geometry, got {geom.geom_type!r} at row {idx}")
            if not geom.is_valid:
                raise ValueError(f"Invalid polygon at row {idx}")
            bid = row[id_property] if id_property in row else idx
            buildings.append(make_building(bid, geom))
        info = DatasetInfo(
            path=str(path),
            crs=crs,
            feature_count=len(buildings),
            geometry_types=sorted({b.polygon.geom_type for b in buildings}),
            id_property=id_property,
        )
        return buildings, info
    except ImportError:
        data = json.loads(path.read_text(encoding="utf-8"))
        crs = data.get("crs", {}).get("properties", {}).get("name")
        buildings = []
        for idx, feature in enumerate(data.get("features", [])):
            geom = shape(feature["geometry"])
            if not isinstance(geom, Polygon):
                raise ValueError(f"Expected Polygon geometry at feature {idx}")
            props = feature.get("properties", {})
            buildings.append(make_building(props.get(id_property, idx), geom))
        info = DatasetInfo(
            path=str(path),
            crs=crs,
            feature_count=len(buildings),
            geometry_types=sorted({b.polygon.geom_type for b in buildings}),
            id_property=id_property,
        )
        return buildings, info
