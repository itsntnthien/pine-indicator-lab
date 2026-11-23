"""Check exported Pine event invariants; this does not certify OHLC/ATR parity or fills."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path

from check_intraday_parity import epoch, number
from workspace import sha


def check(path, feed, minutes, tick):
    if feed not in ('OANDA:XAUUSD', 'FOREXCOM:NAS100') or minutes not in (5, 15):
        raise ValueError('Unsupported feed/pair')
    if not math.isfinite(tick) or tick <= 0:
        raise ValueError('Invalid tick')
    tf = 60 if minutes == 5 else 240
    prefix = f'{feed}:{tf}>{minutes}:'
    setups, opens, consumed, coverage = {}, {}, set(), Counter()
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    if not rows or set(rows[0]) != {'Date', 'Message'}:
        raise ValueError('Expected nonempty Pine Logs export: Date,Message')
    for row in rows:
        fields = row['Message'].split('|')
        if len(fields) not in (6, 8) or fields[0] not in ('SETUP', 'OPEN'):
            raise ValueError('Unexpected log or runtime error')
        kind, ident = fields[:2]
        if not ident.startswith(prefix):
            raise ValueError('Wrong feed/pair')
        confirmed, side = map(int, ident[len(prefix):].split(':'))
        if side not in (-1, 1):
            raise ValueError('Invalid side')
        stamp = epoch(row['Date'])
        if kind == 'SETUP':
            if len(fields) != 8 or ident in setups or not 0 < confirmed - stamp <= minutes * 60000:
                raise ValueError('Duplicate setup or invalid confirmation time')
            close, atr, extreme, stop, target = map(number, fields[2:7])
            if any(v is None or v <= 0 for v in (close, atr, extreme, stop)):
                raise ValueError('Missing or invalid required price/ATR')
            raw = extreme - side * max(.1 * atr, tick)
            expected = (math.floor(raw / tick + 1e-9) if side == 1 else math.ceil(raw / tick - 1e-9)) * tick
            if abs(expected - stop) > tick * 1e-6 or side * (close - stop) <= 0:
                raise ValueError('Incorrect outward stop/risk')
            if target is not None and side * (target - close) < tick - 1e-8:
                raise ValueError('Target on wrong side')
            sources = fields[7].split(',')
            for source in sources:
                if source in consumed:
                    raise ValueError('A source produced more than one setup')
                source_prefix = f'{feed}:{tf}:'
                if not source.startswith(source_prefix):
                    raise ValueError('Wrong source feed/timeframe')
                zone_kind, zone_side, anchor, available = source[len(source_prefix):].split(':')
                if zone_kind not in ('BSL', 'SSL', 'SR', 'OB', 'FVG', 'SD') or int(zone_side) != side or not int(anchor) < int(available) <= stamp:
                    raise ValueError('Future or invalid source')
                consumed.add(source)
                coverage[zone_kind] += 1
            coverage['BUY' if side == 1 else 'SELL'] += 1
            coverage['multi_source'] += len(sources) > 1
            coverage['missing_tp'] += target is None
            setups[ident] = (side, confirmed, stop, target)
        else:
            if len(fields) != 6 or ident not in setups or ident in opens:
                raise ValueError('Orphan or duplicate open')
            at, price, rr = map(number, fields[2:5])
            if at != stamp or at < confirmed or price is None or price <= 0 or fields[5] not in ('true', 'false'):
                raise ValueError('Invalid open observation')
            _, _, stop, target = setups[ident]
            risk = side * (price - stop)
            reward = side * (target - price) if target is not None else None
            expected_rr = reward / risk if risk > 0 and reward is not None and reward > 0 else None
            if (rr is None) != (expected_rr is None) or (rr is not None and abs(rr - expected_rr) > 1e-7):
                raise ValueError('Incorrect RR at next open')
            adverse = risk <= 0 or (reward is not None and reward <= 0)
            if (fields[5] == 'true') != adverse:
                raise ValueError('Incorrect adverse-gap flag')
            coverage['adverse_open'] += adverse
            coverage['low_rr_open'] += rr is not None and rr < 1.5
            opens[ident] = tuple(fields[2:])
    return {'status': 'PASS_LOG_INVARIANTS', 'file': str(path), 'sha256': sha(Path(path)),
            'feed': feed, 'minutes': minutes, 'tick': tick, 'setups': len(setups), 'opens': len(opens),
            'without_open': sorted(set(setups) - set(opens)), 'coverage': dict(coverage),
            'limits': 'Checks logged arithmetic, identity and availability only; not OHLC parity, replay, realtime alerts or fills.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--feed', required=True)
    parser.add_argument('--minutes', type=int, required=True)
    parser.add_argument('--tick', type=float, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.path.resolve() == args.output.resolve():
        parser.error('Output cannot overwrite input')
    report = check(args.path, args.feed, args.minutes, args.tick)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
