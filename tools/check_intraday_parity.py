"""Compare full native TradingView CSV exports with the causal oracle; fail closed."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from datetime import datetime
import json
import math
from pathlib import Path
import sys

from workspace import ROOT, local, sha
sys.path.insert(0, str(ROOT))
from src.intraday.reference import Bar, Context, EntryEngine


def number(value):
    if value is None or value.strip().lower() in ('', 'nan', 'na', 'n/a'):
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('Nonfinite export value')
    return result


def epoch(value):
    try:
        result = float(value)
        if not math.isfinite(result):
            raise ValueError('Invalid epoch')
        return int(round(result * (1 if result > 1e11 else 1000)))
    except ValueError:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            raise ValueError('Export timestamps require an explicit timezone')
        return int(stamp.timestamp() * 1000)


def read_export(path, feed, minutes, token):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError('Empty export')
    feed_code = {'OANDA:XAUUSD': 1, 'FOREXCOM:NAS100': 2}[feed]
    bars, tick = [], None
    for i, row in enumerate(rows):
        for key, expected in [('Audit source index', i), ('Audit feed', feed_code), ('Audit minutes', minutes),
                              ('Audit standard chart', 1), ('Audit build token', token)]:
            if number(row.get(key)) != expected:
                raise ValueError(f'{path}: {key} mismatch at row {i}; export the full loaded history from the correct build/feed')
        actual_tick = number(row.get('Audit tick'))
        if actual_tick is None or actual_tick <= 0 or (tick is not None and tick != actual_tick):
            raise ValueError('Missing or changing tick size')
        tick = actual_tick
        close_epoch = number(row.get('Audit close epoch'))
        if close_epoch is None:
            raise ValueError('Missing native close timestamp; do not infer session boundaries')
        b = Bar(epoch(row['time']), int(round(close_epoch*1000)), *(float(row[k]) for k in ('open', 'high', 'low', 'close')))
        b.validate()
        if bars and b.time < bars[-1].end:
            raise ValueError('Unordered/overlapping export')
        bars.append(b)
    return bars, rows, tick


def compare(ltf_path, htf_path, feed, minutes, token):
    if minutes not in (5, 15):
        raise ValueError('Only M5/M15 entry parity is supported')
    htf_minutes = 60 if minutes == 5 else 240
    ltf, rows, tick = read_export(ltf_path, feed, minutes, token)
    htf, _, htf_tick = read_export(htf_path, feed, htf_minutes, token)
    if htf_tick != tick:
        raise ValueError('HTF/LTF tick metadata differs')
    ctx = Context(feed, htf_minutes, tick)
    engine = EntryEngine(ctx, minutes)
    cursor, errors, comparisons = 0, [], 0
    for i, (bar, row) in enumerate(zip(ltf, rows)):
        while cursor < len(htf) and htf[cursor].end <= bar.time:
            ctx.on_close(htf[cursor])
            cursor += 1
        signal = engine.on_close(bar)
        observation = engine.observations[-1] if engine.observations and engine.observations[-1].at == bar.time else None
        expected = {
            'Audit HTF source index': cursor-1 if cursor else None,
            'Audit ATR14 LTF': engine.series.atr, 'Audit ATR14 HTF': ctx.series.atr,
            'Audit hướng HTF': ctx.bias, 'Audit signal': signal.side if signal else 0,
            'Audit SL xác nhận': signal.stop if signal else None,
            'Audit TP xác nhận': signal.target if signal else None,
            'Audit cực trị nhịp': signal.extreme if signal else None,
            'Audit open nến sau': observation.price if observation else None,
        }
        for column, value in expected.items():
            if column not in row:
                raise ValueError(f'Missing audit column: {column}')
            actual = number(row[column])
            comparisons += 1
            equal = actual is None and value is None or actual is not None and value is not None and abs(actual-value) <= max(1e-8, tick*1e-6)
            if not equal:
                errors.append({'row': i, 'open_epoch_ms': bar.time, 'column': column, 'expected': value, 'native': actual})
    # A numerical PASS with no events is insufficient evidence for setup parity.
    status = 'FAIL' if errors else 'PASS' if engine.setups else 'INSUFFICIENT_EVENTS'
    return {
        'status': status, 'feed': feed, 'pair': f'{htf_minutes}>{minutes}', 'build_token': token,
        'ltf_sha256': sha(ltf_path), 'htf_sha256': sha(htf_path), 'rows': len(ltf), 'comparisons': comparisons,
        'mismatch_count': len(errors), 'first_mismatches': errors[:50],
        'setups': [asdict(s) for s in engine.setups], 'open_observations': [asdict(o) for o in engine.observations],
        'covered_directions': sorted({s.side for s in engine.setups}),
        'limitations': 'CSV numerical parity only; does not prove realtime alert delivery, Bar Replay, all source IDs, fills, or profitability.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ltf', type=Path, required=True)
    parser.add_argument('--htf', type=Path, required=True)
    parser.add_argument('--feed', choices=['OANDA:XAUUSD', 'FOREXCOM:NAS100'], required=True)
    parser.add_argument('--minutes', type=int, choices=[5, 15], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in (args.ltf.resolve(), args.htf.resolve()):
        parser.error('Output must not overwrite either raw input export')
    manifest = json.loads((ROOT / 'dist/intraday/ICT_INTRADAY_EXPERIMENTAL.build.json').read_text(encoding='utf-8'))
    try:
        if sha(local(manifest['output'])) != manifest['sha256'] or any(sha(local(p)) != digest for p, digest in manifest['inputs'].items()):
            raise ValueError('Build or sources changed; rebuild before comparison')
        result = compare(args.ltf, args.htf, args.feed, args.minutes, manifest['build_token'])
    except (ValueError, KeyError, OSError) as exc:
        result = {'status': 'INVALID_INPUT', 'reason': str(exc)}
    result['pine_sha256'] = manifest['sha256']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'reason', 'mismatch_count') if k in result}, ensure_ascii=False))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
