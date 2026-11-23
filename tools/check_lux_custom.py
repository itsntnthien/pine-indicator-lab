"""Observation regression and optional official Pine semantic analysis; never chart execution."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from workspace import ROOT, sha
from build_lux_custom import build, OUTPUT
from check_intraday_legacy import SOURCES
from check_intraday_parity import epoch
sys.path.insert(0, str(ROOT))
from src.lux_custom.reference import Observer
from src.intraday.reference import Bar

EVIDENCE = ROOT / 'evidence/lux_custom'
ENDPOINT = 'https://pine-facade.tradingview.com/pine-facade/translate_light/'


def dump(name, value):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def regression(minutes, catalog):
    item = next(x for x in catalog if x['origin'] == 'workspace' and x['original_path'] == SOURCES[minutes])
    path = ROOT / item['path']
    if item['split_label_from_path'] != 'validation' or sha(path) != item['version_sha256']:
        raise ValueError('Unexpected validation dataset or hash')
    bars = []
    with path.open(encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            stamp = epoch(row['time'])
            if stamp % (minutes * 60000):
                raise ValueError('Unaligned price timestamp')
            bars.append(Bar(stamp, stamp + minutes * 60000, *(float(row[k]) for k in ('open', 'high', 'low', 'close'))))
    full = Observer(.001)
    for bar in bars:
        result = full.on_close(bar)
        assert result['confirmed_at'] == bar.end
        assert result['pool_count'] <= 40 and result['region_count'] <= 64
    cuts = [len(bars)//3, 2*len(bars)//3, len(bars)-1, len(bars)]
    for cutoff in cuts:
        prefix = Observer(.001)
        for bar in bars[:cutoff]:
            prefix.on_close(bar)
        assert prefix.observations == full.observations[:cutoff], 'Future data or reload changed events'
    events = {key: dict(Counter(row[key] for row in full.observations))
              for key in ('internal_break', 'swing_break', 'sweep_mask', 'equal_mask')}
    assert all(events[key].get(side, 0) > 0 for key in ('internal_break', 'swing_break') for side in (-1, 1))
    return {'status': 'PASS_OFFLINE_OBSERVATION', 'minutes': minutes, 'rows': len(bars),
            'path': item['path'], 'sha256': item['version_sha256'], 'prefix_cutoffs': cuts,
            'first_open': bars[0].time, 'last_close': bars[-1].end, 'events': events,
            'inversions': sum(x['inversions'] for x in full.observations),
            'max_regions': max(x['region_count'] for x in full.observations),
            'max_pools': max(x['pool_count'] for x in full.observations),
            'observations_sha256': hashlib.sha256(json.dumps(full.observations, sort_keys=True).encode()).hexdigest()}


def analyze(source):
    request = Request(ENDPOINT, data=urlencode({'source': source}).encode(), headers={
        'Content-Type': 'application/x-www-form-urlencoded', 'Origin': 'https://www.tradingview.com',
        'User-Agent': 'Mozilla/5.0'})
    with urlopen(request, timeout=45) as response:
        return json.load(response)


def diagnostics(response):
    result = response.get('result')
    if not response.get('success') or not isinstance(result, dict):
        raise ValueError('Pine analysis response unsuccessful or malformed')
    return result.get('errors2', []) + result.get('errors', [])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pine', action='store_true', help='Send the built source to official public semantic analysis')
    args = parser.parse_args()
    manifest = build()
    catalog = json.loads((ROOT / 'catalog/datasets.json').read_text(encoding='utf-8'))['datasets']
    report = {'source_sha256': manifest['sha256'], 'datasets': [regression(m, catalog) for m in SOURCES],
              'scope': 'Chart structure, liquidity and region lifecycle; Python oracle only',
              'limitations': ['No native Pine parity or chart render', 'No NAS historical data in this check',
                              'HTF narrative tested with fixtures, not these chart-only CSV replays',
                              'Nominal bar closes; historical tick assumed 0.001', 'No P/L or win-rate assessment']}
    dump('offline-regression.json', report)
    print(json.dumps({'offline': 'PASS', 'rows': sum(x['rows'] for x in report['datasets']),
                      'source_sha256': manifest['sha256']}))
    if args.pine:
        negative = analyze('//@version=6\nindicator("Negative control")\nplot(observer_undefined_variable)\n')
        response = analyze(OUTPUT.read_text(encoding='utf-8'))
        errors = diagnostics(response)
        negative_errors = diagnostics(negative)
        dump('pine-analysis.json', {'source_sha256': manifest['sha256'], 'endpoint': ENDPOINT,
                                   'checked_utc': datetime.now(timezone.utc).isoformat(),
                                   'response': response, 'negative_control': negative,
                                   'scope': 'Official lightweight semantic analysis; not full compilation or chart runtime'})
        assert negative_errors, 'Analyzer failed to reject an undefined identifier'
        assert not errors, errors
        print(json.dumps({'pine_semantic_errors': len(errors), 'negative_control_errors': len(negative_errors),
                          'native_chart_runtime': 'NOT_RUN'}))
