from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Dict
import csv

@dataclass
class NmeaRow:
    raw: str
    valid_checksum: bool
    talker: str
    sentence: str
    channel: Optional[str]
    frag_count: Optional[int]
    frag_num: Optional[int]
    payload_len: Optional[int]
    fill_bits: Optional[int]


def _nmea_checksum_valid(line: str) -> bool:
    try:
        if '*' not in line:
            return False
        body, csum = line.strip().split('*', 1)
        if body.startswith('!') or body.startswith('$'):
            body = body[1:]
        calc = 0
        for ch in body:
            calc ^= ord(ch)
        got = int(csum[:2], 16)
        return calc == got
    except Exception:
        return False


def _parse_fields(line: str) -> Dict:
    # Expected like: !AIVDM,2,1,1,A,55NBsv01... ,0*5C
    try:
        no_csum = line.strip().split('*', 1)[0]
        parts = no_csum.split(',')
        head = parts[0]  # !AIVDM or !AIVDO
        talker = head[1:3] if len(head) >= 3 else ''
        sentence = head[3:] if len(head) > 3 else ''
        frag_count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        frag_num = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
        channel = parts[4] if len(parts) > 4 and parts[4] else None
        payload = parts[5] if len(parts) > 5 else ''
        fill_bits = int(parts[6]) if len(parts) > 6 and parts[6].isdigit() else None
        return {
            'talker': talker,
            'sentence': sentence,
            'frag_count': frag_count,
            'frag_num': frag_num,
            'channel': channel,
            'payload_len': len(payload),
            'fill_bits': fill_bits,
        }
    except Exception:
        return {
            'talker': '', 'sentence': '', 'frag_count': None, 'frag_num': None,
            'channel': None, 'payload_len': None, 'fill_bits': None
        }


def parse_nmea_file(inp: Path, out_csv: Optional[Path] = None):
    rows: List[NmeaRow] = []
    total = 0
    valid = 0
    with inp.open('r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if not (line.startswith('!AI') or line.startswith('!BS') or line.startswith('!AB') or line.startswith('!AIV')):
                # keep only AIS-like NMEA for stats
                continue
            total += 1
            ok = _nmea_checksum_valid(line)
            if ok:
                valid += 1
            meta = _parse_fields(line)
            rows.append(NmeaRow(
                raw=line,
                valid_checksum=ok,
                talker=meta['talker'],
                sentence=meta['sentence'],
                channel=meta['channel'],
                frag_count=meta['frag_count'],
                frag_num=meta['frag_num'],
                payload_len=meta['payload_len'],
                fill_bits=meta['fill_bits'],
            ))

    print(f"[parse] lines: {total}, valid checksum: {valid} ({(valid/total*100 if total else 0):.1f}%)")

    if out_csv:
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open('w', encoding='utf-8', newline='') as fw:
            w = csv.DictWriter(fw, fieldnames=[
                'raw','valid_checksum','talker','sentence','channel','frag_count','frag_num','payload_len','fill_bits'
            ])
            w.writeheader()
            for r in rows:
                w.writerow(asdict(r))
