import argparse
from pathlib import Path
from .detect import run_detection
from .parse_nmea import parse_nmea_file


def main():
    ap = argparse.ArgumentParser(prog='aisguard', description='AISGuard CLI')
    sub = ap.add_subparsers(dest='cmd', required=True)

    ap_detect = sub.add_parser('detect', help='Detect anomalies in AIS CSV tracks')
    ap_detect.add_argument('--in', dest='inp', required=True, help='Input CSV path')
    ap_detect.add_argument('--report', required=True, help='Output JSON report path')
    ap_detect.add_argument('--plot', required=False, help='Output PNG plot path')
    ap_detect.add_argument('--max-speed', type=float, default=45.0, help='Max plausible speed (knots)')
    ap_detect.add_argument('--max-jump', type=float, default=20.0, help='Max distance jump between points (km)')

    ap_parse = sub.add_parser('parse', help='Validate NMEA and export basic stats')
    ap_parse.add_argument('--in', dest='inp', required=True, help='Input NMEA text file')
    ap_parse.add_argument('--out', required=False, help='Optional CSV export of valid lines')

    args = ap.parse_args()

    if args.cmd == 'detect':
        inp = Path(args.inp)
        report = Path(args.report)
        plot = Path(args.plot) if args.plot else None
        report.parent.mkdir(parents=True, exist_ok=True)
        if plot:
            plot.parent.mkdir(parents=True, exist_ok=True)
        run_detection(inp, report, plot, max_speed_knots=args.max_speed, max_jump_km=args.max_jump)
    elif args.cmd == 'parse':
        inp = Path(args.inp)
        out = Path(args.out) if args.out else None
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
        parse_nmea_file(inp, out)

if __name__ == '__main__':
    main()
