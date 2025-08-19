from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
try:
    from sklearn.ensemble import IsolationForest
except Exception:  # pragma: no cover
    IsolationForest = None
from .geojson import export_geojson
from .kml import export_kml

EARTH_R_KM = 6371.0088


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    c = 2*np.arcsin(np.sqrt(a))
    return EARTH_R_KM * c


@dataclass
class Incident:
    type: str  # e.g., "speed_excess", "teleport", "bad_order"
    mmsi: int
    ts_prev: Optional[str]
    ts_curr: str
    details: Dict[str, Any]


def run_detection(
    inp_csv: Path,
    out_json: Path,
    out_plot: Optional[Path],
    out_geojson: Optional[Path] = None,
    out_kml: Optional[Path] = None,
    max_speed_knots: float = 45.0,
    max_jump_km: float = 20.0,
    use_ml: bool = False,
    ml_contamination: float = 0.02,
):
    df = pd.read_csv(inp_csv)
    required = {"mmsi", "lat", "lon", "ts"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    # ensure types
    df = df.copy()
    df["mmsi"] = df["mmsi"].astype(int)
    df["lat"] = df["lat"].astype(float)
    df["lon"] = df["lon"].astype(float)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")

    # drop invalid timestamps
    df = df.dropna(subset=["ts"]).sort_values(["mmsi", "ts"])  # sort by time per MMSI

    incidents: List[Incident] = []
    summary = {"total_points": int(len(df)), "mmsi_count": int(df["mmsi"].nunique()), "flags": {"speed_excess": 0, "teleport": 0, "bad_order": 0, "ml_outlier": 0}}

    # group by MMSI and scan sequences
    groups = df.groupby("mmsi", sort=False)
    plot_tracks: Dict[int, pd.DataFrame] = {}

    segment_features = []  # collect features per segment for ML
    seg_index = []  # references to (mmsi, ts_prev, ts_curr)
    for mmsi, g in groups:
        g = g.sort_values("ts").reset_index(drop=True)
        plot_tracks[mmsi] = g
        # compute deltas
        for i in range(1, len(g)):
            prev = g.iloc[i-1]
            curr = g.iloc[i]
            if curr.ts < prev.ts:
                incidents.append(Incident(type="bad_order", mmsi=int(mmsi), ts_prev=prev.ts.isoformat(), ts_curr=curr.ts.isoformat(), details={}))
                summary["flags"]["bad_order"] += 1
                continue
            dt_s = (curr.ts - prev.ts).total_seconds()
            if dt_s <= 0:
                continue
            dist_km = float(haversine_km(prev.lat, prev.lon, curr.lat, curr.lon))
            speed_kts = (dist_km / (dt_s / 3600.0)) * 0.539957  # km/h -> knots

            # teleport check
            if dist_km > max_jump_km:
                incidents.append(Incident(type="teleport", mmsi=int(mmsi), ts_prev=prev.ts.isoformat(), ts_curr=curr.ts.isoformat(), details={"dist_km": round(dist_km,2)}))
                summary["flags"]["teleport"] += 1
            # speed check
            if speed_kts > max_speed_knots:
                incidents.append(Incident(type="speed_excess", mmsi=int(mmsi), ts_prev=prev.ts.isoformat(), ts_curr=curr.ts.isoformat(), details={"speed_kts": round(speed_kts,2), "dist_km": round(dist_km,2), "dt_s": int(dt_s)}))
                summary["flags"]["speed_excess"] += 1

            # collect features for ML
            if use_ml:
                segment_features.append([
                    dist_km,
                    dt_s,
                    speed_kts,
                    float(curr.lat),
                    float(curr.lon),
                ])
                seg_index.append((int(mmsi), prev.ts.isoformat(), curr.ts.isoformat()))

    report = {"input": str(inp_csv), "summary": summary, "incidents": [asdict(x) for x in incidents]}
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if out_plot is not None:
        _plot_tracks(plot_tracks, incidents, out_plot)

    # Optional ML anomaly scoring on segments
    if use_ml and segment_features and IsolationForest is not None:
        X = np.array(segment_features, dtype=float)
        try:
            iso = IsolationForest(contamination=max(0.001, min(0.5, float(ml_contamination))), random_state=42)
            y = iso.fit_predict(X)  # -1 outlier
            for flag, (mmsi, ts_prev, ts_curr), feats in zip(y, seg_index, segment_features):
                if flag == -1:
                    incidents.append(Incident(
                        type="ml_outlier",
                        mmsi=int(mmsi),
                        ts_prev=ts_prev,
                        ts_curr=ts_curr,
                        details={"features": {"dist_km": round(feats[0],2), "dt_s": int(feats[1]), "speed_kts": round(feats[2],2)}}
                    ))
                    summary["flags"]["ml_outlier"] += 1
        except Exception:
            pass

    # Overwrite JSON to include ML incidents if added
    report = {"input": str(inp_csv), "summary": summary, "incidents": [asdict(x) for x in incidents]}
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Optional GeoJSON export
    if out_geojson is not None:
        export_geojson(plot_tracks, incidents, out_geojson)

    # Optional KML export
    if out_kml is not None:
        export_kml(plot_tracks, incidents, out_kml)


def _plot_tracks(tracks: Dict[int, pd.DataFrame], incidents: List[Incident], out_path: Path):
    plt.figure(figsize=(8, 6))
    # prepare incident points set
    inc_key = {(inc.mmsi, inc.ts_curr) for inc in incidents}
    for mmsi, g in tracks.items():
        # lines
        plt.plot(g["lon"], g["lat"], '-', linewidth=1, alpha=0.6, label=f"{mmsi}")
        # mark incident points in red
        if inc_key:
            mask = [ (int(mmsi), pd.Timestamp(t).isoformat()) in inc_key for t in g["ts"] ]
            gg = g[mask]
            if not gg.empty:
                plt.scatter(gg["lon"], gg["lat"], c='red', s=16, zorder=3)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("AIS Tracks with Anomalies")
    if len(tracks) <= 10:
        plt.legend(fontsize=8)
    plt.grid(True, alpha=0.3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
