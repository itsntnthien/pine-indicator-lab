"""Reuse two catalogued OANDA validation exports for offline regression, never native parity."""
from collections import Counter
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from workspace import ROOT, sha
from check_intraday_parity import epoch
sys.path.insert(0, str(ROOT))
from src.intraday.reference import Bar, Context, replay
from calibration.pivot.data.resampler import resample
from calibration.pivot.domain.models import OHLCBar

SOURCES = {5: 'validation/phase16b-tradingview/pre-class-b-fix-14ec2e9/XAUUSD_OANDA_M5.csv',
           15: 'validation/phase16b-tradingview/XAUUSD_OANDA_M15.csv'}


def check(minutes, catalog):
    item = next(x for x in catalog if x['origin'] == 'workspace' and x['original_path'] == SOURCES[minutes])
    if item['split_label_from_path'] != 'validation':
        raise ValueError('Only the named legacy validation witnesses may be used')
    path = ROOT / item['path']
    if sha(path) != item['version_sha256']:
        raise ValueError('Legacy source hash mismatch')
    with path.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    bars = []
    for row in rows:
        stamp = epoch(row['time'])
        bar = Bar(stamp, stamp + minutes * 60000, *(float(row[k]) for k in ('open', 'high', 'low', 'close')))
        bar.validate()
        if stamp % (minutes * 60000) or (bars and stamp < bars[-1].end):
            raise ValueError('Unaligned, overlapping or unordered source')
        bars.append(bar)
    tf = 60 if minutes == 5 else 240
    legacy = [OHLCBar(datetime.fromtimestamp(b.time / 1000, timezone.utc), b.open, b.high, b.low, b.close,
                      timeframe=f'M{minutes}', provider='OANDA', symbol='XAUUSD', source_hash=item['version_sha256']) for b in bars]
    omitted = []
    grouped = resample(legacy, tf, tf // minutes, component_minutes=minutes, audit=omitted)
    higher = [Bar(int(b.timestamp.timestamp()*1000), int(b.timestamp.timestamp()*1000)+tf*60000,
                  b.open, b.high, b.low, b.close) for b in grouped]
    # shortcut: UTC-derived HTF and nominal closes are regression inputs, never certified broker candles.
    engine = replay(Context('OANDA:XAUUSD', tf, .001), minutes, higher, bars)
    repeated = replay(Context('OANDA:XAUUSD', tf, .001), minutes, higher, bars)
    if engine.setups != repeated.setups or engine.observations != repeated.observations:
        raise AssertionError('Offline reload changed events')
    prefix_counts = []
    for cutoff in (len(bars)//3, 2*len(bars)//3, len(bars)-1):
        partial = replay(Context('OANDA:XAUUSD', tf, .001), minutes, higher, bars[:cutoff])
        expected = [s for s in engine.setups if s.confirm_index < cutoff]
        expected_opens = [o for o in engine.observations if o.at <= bars[cutoff-1].time]
        if partial.setups != expected or partial.observations != expected_opens:
            raise AssertionError('Future data changed historical events')
        prefix_counts.append(len(partial.setups))
    consumed = set()
    kinds = Counter()
    for setup in engine.setups:
        if not setup.sources or setup.side * (setup.reference_close - setup.stop) <= 0:
            raise AssertionError('Invalid setup')
        for source in setup.sources:
            if source in consumed or int(source.rsplit(':', 1)[1]) > bars[setup.confirm_index].time:
                raise AssertionError('Source repeated or used before availability')
            consumed.add(source)
            kinds[source.split(':')[3]] += 1
    return {'status': 'PASS_OFFLINE_REGRESSION', 'path': item['path'], 'sha256': item['version_sha256'],
            'minutes': minutes, 'rows': len(bars), 'derived_htf_rows': len(higher), 'omitted_incomplete_htf': len(omitted),
            'first_open': bars[0].time, 'last_open': bars[-1].time, 'setups': len(engine.setups),
            'directions': dict(Counter(s.side for s in engine.setups)), 'source_kinds': dict(kinds),
            'prefix_counts': prefix_counts, 'events': [asdict(s) for s in engine.setups],
            'limitations': ['UTC-anchored derived HTF; not native feed session parity',
                            'Nominal LTF close timestamps; historical tick assumed 0.001',
                            'Legacy prices only; old indicator columns are not expected signals',
                            'No P/L, parameter selection, NAS evidence, or holdout evaluation']}


if __name__ == '__main__':
    catalog = json.loads((ROOT / 'catalog/datasets.json').read_text(encoding='utf-8'))['datasets']
    results = [check(m, catalog) for m in SOURCES]
    target = ROOT / 'evidence/intraday/native-20261114/legacy-regression.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps([{k:v for k,v in r.items() if k != 'events'} for r in results], ensure_ascii=False))
