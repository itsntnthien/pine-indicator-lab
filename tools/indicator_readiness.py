"""Reproducible development-only inventory and volatility survey; no backtest."""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import quantiles
import sys

from workspace import ROOT, load, local, sha

REFERENCE = ROOT / 'references/workspace/TradingView/SMC-PRO-XAUUSD'
sys.path.insert(0, str(REFERENCE))
from calibration.pivot.engine.features import true_ranges, causal_atr
from calibration.pivot.engine.types import Bar

TIMEFRAMES = {'M5': 5, 'M15': 15, 'H1': 60, 'H4': 240}
PREFIX = 'TradingView/SMC-PRO-XAUUSD/calibration/datasets/processed/dupoin/DUPOIN_XAUUSDV_MULTI_TF_2020_2025_V1/'
START = datetime(2022, 1, 1, tzinfo=timezone.utc)
END = datetime(2023, 1, 1, tzinfo=timezone.utc)


def wilder_atr(ranges, period=14):
    if period < 1 or any(not math.isfinite(v) or v < 0 for v in ranges):
        raise ValueError('ATR requires a positive period and finite nonnegative ranges')
    result = [None] * len(ranges)
    if len(ranges) >= period:
        value = sum(ranges[:period]) / period
        result[period - 1] = value
        for i in range(period, len(ranges)):
            value += (ranges[i] - value) / period
            result[i] = value
    return result


def distribution(values):
    if len(values) < 2 or not all(math.isfinite(v) for v in values):
        raise ValueError('At least two finite observations required')
    q = quantiles(values, n=100, method='inclusive')
    return {key: round(q[index - 1], 8) for key, index in [('p10', 10), ('p50', 50), ('p90', 90), ('p95', 95)]}


def catalog_entry(rows, original):
    matches = [r for r in rows if r['origin'] == 'workspace' and r['original_path'] == original]
    if len(matches) != 1:
        raise ValueError(f'Expected one workspace source: {original}')
    row = matches[0]
    if sha(local(row['path'])) != row['version_sha256']:
        raise ValueError(f'Source integrity mismatch: {original}')
    return row


def read_bars(path, timeframe):
    bars, statuses, spread, components = [], Counter(), [], Counter()
    minutes = TIMEFRAMES[timeframe]
    with path.open(encoding='utf-8', newline='') as handle:
        for row in csv.DictReader(handle):
            stamp = datetime.fromisoformat(row['timestamp'])
            if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
                raise ValueError('UTC-aware timestamps required')
            if not START <= stamp < END:
                raise ValueError('Only the explicit 2022 development window is allowed')
            if stamp.second or stamp.microsecond or (stamp.hour * 60 + stamp.minute) % minutes:
                raise ValueError('Timestamp is not aligned with the UTC timeframe')
            if bars and stamp <= bars[-1].timestamp:
                raise ValueError('Duplicate or unordered timestamp')
            o, h, lo, c = (float(row[k]) for k in ('open', 'high', 'low', 'close'))
            if not all(math.isfinite(v) and v > 0 for v in (o, h, lo, c)) or h < max(o, c, lo) or lo > min(o, c, h):
                raise ValueError('Invalid or nonfinite OHLC')
            if (row['provider'], row['provider_instrument'], row['timeframe'], row['timezone'], row['price_semantics']) != ('DUPOIN', 'XAUUSD.v', timeframe, 'UTC', 'MT5_BROKER_CHART_BARS'):
                raise ValueError('Mixed or unexpected feed metadata')
            count, closed = int(row['component_count']), int(row['session_closed_component_count'])
            if count <= 0 or closed < 0 or count + closed != minutes or int(row['expected_open_component_count']) != minutes:
                raise ValueError('Unexpected component accounting; inspect aggregation contract')
            status = row['completeness_status']
            if status not in {'COMPLETE_OPEN_SESSION', 'COMPLETE_SESSION_AWARE'}:
                raise ValueError('Incomplete or unknown source bar')
            if (status == 'COMPLETE_OPEN_SESSION') != (closed == 0):
                raise ValueError('Completeness status disagrees with session accounting')
            points = float(row['spread'])
            if not math.isfinite(points) or points < 0:
                raise ValueError('Invalid spread')
            spread.append(points)
            statuses[status] += 1
            components['observed_m1'] += count
            components['declared_session_closed_m1'] += closed
            bars.append(Bar(stamp, o, h, lo, c, timeframe, 'READINESS_2022'))
    if len(bars) < 101:
        raise ValueError('Not enough development bars')
    return bars, statuses, spread, components


def survey(rows, timeframe):
    source = catalog_entry(rows, PREFIX + f'derived/{timeframe}/2022/dupoin_XAUUSDv_{timeframe}_2022.csv')
    profile = {'M5': 'SE', 'M15': 'SE', 'H1': 'WE', 'H4': 'WE'}[timeframe]
    partition = catalog_entry(rows, PREFIX + f'partitions/{profile}_{timeframe}_calibration.json')
    policy = json.loads(local(partition['path']).read_text(encoding='utf-8'))
    if policy['partition_id'] != 'calibration' or not (datetime.fromisoformat(policy['eligible_feature_start']) <= START < END <= datetime.fromisoformat(policy['eligible_label_end'])):
        raise ValueError('Requested interval is not eligible calibration data')
    key = f'derived/{timeframe}/2022/dupoin_XAUUSDv_{timeframe}_2022.csv'
    if policy['source_hashes'][key] != source['version_sha256']:
        raise ValueError('Partition does not bind this source hash')
    bars, statuses, spreads, components = read_bars(local(source['path']), timeframe)
    ranges = true_ranges(bars)
    atr = wilder_atr(ranges)
    # shortcut: 2022-only seed; use prior verified bars when proving native Pine parity.
    eligible = range(100, len(bars))
    samples = [atr[i] for i in eligible]
    atr_bps = [atr[i] / bars[i].close * 10000 for i in eligible]
    legacy_atr = causal_atr(bars, 14)
    delta = [abs(atr[i] - legacy_atr[i].value) / atr[i] * 100 for i in eligible if atr[i] > 0]
    gaps = [int((b.timestamp - a.timestamp).total_seconds() / 60) for a, b in zip(bars, bars[1:]) if b.timestamp - a.timestamp != timedelta(minutes=TIMEFRAMES[timeframe])]
    return {
        'timeframe': timeframe, 'source': source, 'partition_source': partition,
        'rows': len(bars), 'first_open_utc': bars[0].timestamp.isoformat(), 'last_open_utc': bars[-1].timestamp.isoformat(),
        'strict_quality_check': 'PASS', 'declared_completeness': dict(statuses), 'components': dict(components),
        'nonstandard_intervals_including_sessions': len(gaps), 'largest_open_to_open_gap_minutes': max(gaps, default=0),
        'warmup_bars_excluded': 100, 'atr_samples': len(samples),
        'atr14_wilder_price_units': distribution(samples), 'atr14_wilder_basis_points_of_close': distribution(atr_bps),
        'sma_vs_wilder_absolute_relative_difference_percent': distribution(delta),
        'spread_field_broker_points_not_price': distribution(spreads),
        'volume_policy': 'tick_volume is feed activity, real_volume is not used',
        'session_policy': 'trust hash-bound declared session completeness; calendar not independently certified',
        'pivot_right_3_delay_minutes_after_anchor_close_if_contiguous': 3 * TIMEFRAMES[timeframe],
        'pivot_right_5_delay_minutes_after_anchor_close_if_contiguous': 5 * TIMEFRAMES[timeframe],
    }


def main():
    datasets = load('datasets.json')['datasets']
    candidates = load('candidates.json')['candidates']
    inventory = []
    for item in candidates:
        path = local(item['source'])
        content = path.read_text(encoding='utf-8-sig')
        inventory.append({'id': item['id'], 'source': item['source'], 'sha256': sha(path),
                          'registered_hash_matches': sha(path) == item['source_sha256'],
                          'lines': len(content.splitlines()), 'input_calls_text_count': content.count('input.'),
                          'pine_version': item['pine_version'], 'native_compile': item['native_compile']})
    if not all(c['registered_hash_matches'] for c in inventory):
        raise ValueError('Candidate snapshot has changed')
    stored = {r['path']: r for r in datasets}
    missing = [p for p in stored if not local(p).is_file()]
    if missing:
        raise ValueError(f'Missing catalog storage: {missing}')
    names = ('nas100', 'us100', 'ustec', 'nasdaq', 'ndx', 'nq1')
    nas = [r['path'] for r in stored.values() if any(n in (r['original_path'] + ' ' + r['path']).lower() for n in names)]
    result = {
        'schema_version': 1, 'status': 'RESEARCH_ONLY_NOT_RELEASE',
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'scope': {'markets': ['XAUUSD', 'NAS100'], 'feeds': ['OANDA:XAUUSD', 'FOREXCOM:NAS100'], 'platform': 'TradingView Pine v6', 'context': ['H1', 'H4'], 'entry': ['M5', 'M15']},
        'method': 'Descriptive 2022 DUPOIN data only; Wilder ATR14 seeded with first 14 TR mean; omit first 100 bars; inclusive linear percentiles; no parameter selection or profit calculation.',
        'inventory': {'catalog_records': len(datasets), 'distinct_storage_paths': len(stored), 'existing_storage_paths': len(stored),
                      'provider_labels_from_catalog': dict(Counter(r['provider_label_from_path'] for r in stored.values())),
                      'nas100_named_storage_paths': nas, 'candidates': inventory, 'unique_candidate_hashes': len({c['sha256'] for c in inventory})},
        'surveys': [survey(datasets, tf) for tf in TIMEFRAMES],
        'verification': load_verification(),
        'limitations': ['No NAS100 OHLC identified by catalog/name search; no numeric NAS100 calibration.',
                       'No native Pine compilation or profitability verification.', 'No locked holdout price files opened by this survey.',
                       'DUPOIN 2022 statistics are not current TradingView feed parameters.',
                       'Spread field has no verified point-size conversion here; costs and sizing are not computed.',
                       'UTC H4 buckets require comparison with the selected TradingView feed session boundaries.'],
        'implementation_hashes': {p: sha(local(p)) for p in ['tools/indicator_readiness.py', 'tools/workspace.py', 'catalog/candidates.json', 'catalog/datasets.json',
            'references/workspace/TradingView/SMC-PRO-XAUUSD/calibration/pivot/engine/features.py']},
    }
    output = ROOT / 'research/indicator-foundation-20261113/measurements.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(output)
    for s in result['surveys']:
        print(s['timeframe'], s['rows'], 'ATR14', s['atr14_wilder_price_units'])


def load_verification():
    return json.loads((ROOT / 'evidence/verification/summary.json').read_text(encoding='utf-8'))


if __name__ == '__main__':
    main()
