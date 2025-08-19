from __future__ import annotations
from pathlib import Path
from typing import Dict, List
import json
import pandas as pd
from .detect import Incident


def export_geojson(tracks: Dict[int, pd.DataFrame], incidents: List[Incident], out_path: Path) -> None:
    """Export tracks (as LineString per MMSI) and incidents (as Point) into a single FeatureCollection."""
    features: List[dict] = []

    # Lines per MMSI
    for mmsi, g in tracks.items():
        coords = [[float(lon), float(lat)] for lon, lat in zip(g["lon"], g["lat"])]
        if len(coords) < 2:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {"mmsi": int(mmsi)}
        })

    # Points for incidents
    for inc in incidents:
        # find row in track for ts_curr (best-effort)
        g = tracks.get(inc.mmsi)
        lon = lat = None
        if g is not None and "ts" in g.columns and len(g) > 0 and inc.ts_curr:
            try:
                row = g[g["ts"].astype(str) == inc.ts_curr]
                if not row.empty:
                    lat = float(row.iloc[0]["lat"])
                    lon = float(row.iloc[0]["lon"])
            except Exception:
                pass
        if lat is None or lon is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {"type": inc.type, "mmsi": inc.mmsi, "ts": inc.ts_curr, **inc.details}
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, indent=2), encoding="utf-8")
