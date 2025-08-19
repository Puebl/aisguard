import argparse
from pathlib import Path
from .detect import run_detection
from .parse_nmea import parse_nmea_file
from .convert import convert_nmea_to_csv


def main():
    ap = argparse.ArgumentParser(prog='aisguard', description='AISGuard CLI')
    sub = ap.add_subparsers(dest='cmd', required=True)

    ap_detect = sub.add_parser('detect', help='Detect anomalies in AIS CSV tracks')
    ap_detect.add_argument('--in', dest='inp', required=True, help='Input CSV path')
    ap_detect.add_argument('--report', required=True, help='Output JSON report path')
    ap_detect.add_argument('--plot', required=False, help='Output PNG plot path')
    ap_detect.add_argument('--max-speed', type=float, default=45.0, help='Max plausible speed (knots)')
    ap_detect.add_argument('--max-jump', type=float, default=20.0, help='Max distance jump between points (km)')
    ap_detect.add_argument('--geojson', required=False, help='Optional GeoJSON export path')
    ap_detect.add_argument('--kml', required=False, help='Optional KML export path')
    ap_detect.add_argument('--ml', action='store_true', help='Enable ML anomaly scoring (IsolationForest)')
    ap_detect.add_argument('--ml-contamination', type=float, default=0.02, help='Contamination rate for IsolationForest (0..0.5)')

    ap_parse = sub.add_parser('parse', help='Validate NMEA and export basic stats')
    ap_parse.add_argument('--in', dest='inp', required=True, help='Input NMEA text file')
    ap_parse.add_argument('--out', required=False, help='Optional CSV export of valid lines')

    ap_convert = sub.add_parser('convert', help='Convert AIS NMEA to CSV (mmsi,lat,lon,ts,sog,cog)')
    ap_convert.add_argument('--in', dest='inp', required=True, help='Input NMEA text file')
    ap_convert.add_argument('--out', required=True, help='Output CSV path')
    ap_convert.add_argument('--start-ts', required=False, help='ISO8601 start timestamp to assign sequential times (e.g., 2024-05-01T00:00:00Z)')
    ap_convert.add_argument('--step-sec', type=int, default=1, help='Seconds between sequential timestamps')

    args = ap.parse_args()

    if args.cmd == 'detect':
        inp = Path(args.inp)
        report = Path(args.report)
        plot = Path(args.plot) if args.plot else None
        geojson = Path(args.geojson) if getattr(args, 'geojson', None) else None
        kml = Path(args.kml) if getattr(args, 'kml', None) else None
        report.parent.mkdir(parents=True, exist_ok=True)
        if plot:
            plot.parent.mkdir(parents=True, exist_ok=True)
        if geojson:
            geojson.parent.mkdir(parents=True, exist_ok=True)
        if kml:
            kml.parent.mkdir(parents=True, exist_ok=True)
        run_detection(
            inp,
            report,
            plot,
            out_geojson=geojson,
            out_kml=kml,
            max_speed_knots=args.max_speed,
            max_jump_km=args.max_jump,
            use_ml=args.ml,
            ml_contamination=args.ml_contamination,
        )
    elif args.cmd == 'parse':
        inp = Path(args.inp)
        out = Path(args.out) if args.out else None
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
        parse_nmea_file(inp, out)
    elif args.cmd == 'convert':
        inp = Path(args.inp)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        convert_nmea_to_csv(inp, out, start_ts=getattr(args, 'start_ts', None), step_sec=getattr(args, 'step_sec', 1))

if __name__ == '__main__':
    main()
