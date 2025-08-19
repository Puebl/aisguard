from __future__ import annotations
from pathlib import Path
from typing import Dict, List
import xml.etree.ElementTree as ET
import pandas as pd
from .detect import Incident


KML_NS = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", KML_NS)


def _kml_elem(tag: str, text: str | None = None):
    el = ET.Element(f"{{{KML_NS}}}{tag}")
    if text is not None:
        el.text = text
    return el


def export_kml(tracks: Dict[int, pd.DataFrame], incidents: List[Incident], out_path: Path) -> None:
    kml = _kml_elem("kml")
    doc = _kml_elem("Document")
    kml.append(doc)

    # Styles
    def add_style(id_, color, width="2"):
        st = _kml_elem("Style")
        st.set("id", id_)
        ls = _kml_elem("LineStyle")
        ls.append(_kml_elem("color", color))  # aabbggrr
        ls.append(_kml_elem("width", width))
        st.append(ls)
        doc.append(st)

    add_style("track", "ff00ffff", "2")  # yellow lines
    add_style("incident", "ff0000ff", "3")  # red lines (unused for points)

    # Track LineStrings
    for mmsi, g in tracks.items():
        if len(g) < 2:
            continue
        pm = _kml_elem("Placemark")
        pm.append(_kml_elem("name", str(mmsi)))
        styleurl = _kml_elem("styleUrl", "#track")
        pm.append(styleurl)
        ls = _kml_elem("LineString")
        coords = _kml_elem("coordinates")
        coords.text = " ".join([f"{lon},{lat},0" for lon, lat in zip(g["lon"], g["lat"])])
        ls.append(coords)
        pm.append(ls)
        doc.append(pm)

    # Incident points
    # build lookup for coordinates by (mmsi, ts)
    for inc in incidents:
        g = tracks.get(inc.mmsi)
        if g is None or "ts" not in g.columns:
            continue
        try:
            row = g[g["ts"].astype(str) == inc.ts_curr]
            if row.empty:
                continue
            lat = float(row.iloc[0]["lat"])  # type: ignore
            lon = float(row.iloc[0]["lon"])  # type: ignore
        except Exception:
            continue
        pm = _kml_elem("Placemark")
        pm.append(_kml_elem("name", f"{inc.type} ({inc.mmsi})"))
        desc = _kml_elem("description", str(inc.details))
        pm.append(desc)
        point = _kml_elem("Point")
        point.append(_kml_elem("coordinates", f"{lon},{lat},0"))
        pm.append(point)
        doc.append(pm)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(kml)
    tree.write(out_path, encoding="utf-8", xml_declaration=True)
