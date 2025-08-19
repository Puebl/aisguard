from __future__ import annotations
from pathlib import Path
from typing import Optional
import csv
from datetime import datetime, timedelta, timezone

# pyais provides decoding of AIS NMEA payloads
try:
    from pyais import decode
except Exception:  # pragma: no cover
    decode = None


def convert_nmea_to_csv(inp: Path, out_csv: Path, start_ts: Optional[str] = None, step_sec: int = 1) -> None:
    """
    Convert NMEA AIS lines to a simple CSV with columns: mmsi,lat,lon,ts,sog,cog
    - If `start_ts` is provided (ISO 8601), timestamps are assigned sequentially with `step_sec` between messages.
    - Only messages with position (types 1,2,3) are exported.
    - Enriches with optional fields if present: heading, nav_status, rot, name, callsign, ship_type, dim_a, dim_b, dim_c, dim_d
    """
    if decode is None:
        raise RuntimeError("pyais is not installed. Install it via requirements.txt")

    ts0: Optional[datetime] = None
    if start_ts:
        ts0 = datetime.fromisoformat(start_ts.replace('Z', '+00:00')).astimezone(timezone.utc)

    out_csv.parent.mkdir(parents=True, exist_ok=True)

    # cache last known static info by MMSI (from msg type 5)
    static_info = {}

    with inp.open('r', encoding='utf-8', errors='ignore') as fr, out_csv.open('w', encoding='utf-8', newline='') as fw:
        w = csv.writer(fw)
        w.writerow([
            "mmsi", "lat", "lon", "ts", "sog", "cog",
            "heading", "nav_status", "rot",
            "name", "callsign", "ship_type", "dim_a", "dim_b", "dim_c", "dim_d"
        ])  # header
        t = ts0
        idx = 0
        for raw in fr:
            raw = raw.strip()
            if not raw or not raw.startswith('!'):
                continue
            try:
                decoded = decode(raw)
            except Exception:
                continue
            if decoded is None:
                continue
            try:
                msg_type = int(decoded.get('msg_type'))
            except Exception:
                msg_type = None

            # Collect static info (type 5)
            if msg_type == 5:
                mmsi5 = decoded.get('mmsi')
                if mmsi5 is not None:
                    static_info[int(mmsi5)] = {
                        'name': decoded.get('name'),
                        'callsign': decoded.get('callsign'),
                        'ship_type': decoded.get('ship_type'),
                        'dim_a': decoded.get('dim_a'),
                        'dim_b': decoded.get('dim_b'),
                        'dim_c': decoded.get('dim_c'),
                        'dim_d': decoded.get('dim_d'),
                    }
                continue  # do not output a row for static message

            if msg_type in (1, 2, 3):  # position reports
                mmsi = decoded.get('mmsi')
                lat = decoded.get('y')
                lon = decoded.get('x')
                sog = decoded.get('sog')  # knots
                cog = decoded.get('cog')  # degrees
                heading = decoded.get('true_heading')
                nav_status = decoded.get('nav_status')
                rot = decoded.get('rot')

                if mmsi is None or lat is None or lon is None:
                    continue

                ts_str = ''
                if t is not None:
                    ts_str = t.isoformat().replace('+00:00', 'Z')
                    t = t + timedelta(seconds=step_sec)
                elif 'timestamp' in decoded:  # seconds within minute; not absolute
                    # leave blank to avoid wrong absolute time
                    ts_str = ''

                st = static_info.get(int(mmsi), {})
                w.writerow([
                    int(mmsi), float(lat), float(lon), ts_str,
                    sog if sog is not None else '',
                    cog if cog is not None else '',
                    heading if heading is not None else '',
                    nav_status if nav_status is not None else '',
                    rot if rot is not None else '',
                    st.get('name', ''), st.get('callsign', ''), st.get('ship_type', ''),
                    st.get('dim_a', ''), st.get('dim_b', ''), st.get('dim_c', ''), st.get('dim_d', ''),
                ])
                idx += 1

    # done
