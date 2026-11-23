"""Compare native Pine Logs with the independent sequential observation oracle."""
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
import sys
from workspace import ROOT, sha
sys.path.insert(0, str(ROOT))
from src.intraday.reference import Bar
from src.lux_custom.reference import Observer, assessment

FIELDS = ('tag token feed tf tick index time end open high low close atr internal_break internal_type '
          'swing_break swing_type sweep_mask equal_mask inversions internal_bias swing_bias h1_bias h4_bias '
          'h1_time h1_end h4_time h4_end standard assessment regions pools h1_open h1_high h1_low h1_close '
          'h4_open h4_high h4_low h4_close region_count pool_count snapshot').split()


def number(value):
    return None if value in ('NaN', 'na', 'Na', '') else float(value)


def read(path, collapse_exact=False):
    with Path(path).open(encoding='utf-8-sig', newline='') as file:
        raw = list(csv.DictReader(file))
    records = []
    for row in raw:
        values = row['Message'].split('|')
        if len(values) != len(FIELDS) or values[0] != 'O1':
            raise ValueError('Unexpected native log (possibly runtime error or truncated message)')
        records.append(dict(zip(FIELDS, values)))
    records.sort(key=lambda r: int(r['index']))
    if collapse_exact:
        unique=[]
        for row in records:
            if unique and row['time']==unique[-1]['time']:
                if row!=unique[-1]:
                    raise ValueError('Conflicting duplicate native history')
            else:
                unique.append(row)
        records=unique
    if not records or len({r['time'] for r in records}) != len(records):
        raise ValueError('Empty or duplicate native history')
    if [int(r['index']) for r in records] != list(range(len(records))):
        raise ValueError('Need complete history from native bar_index zero, without missing rows')
    for key in ('tag', 'token', 'feed', 'tf', 'tick', 'standard'):
        if len({r[key] for r in records}) != 1:
            raise ValueError('Mixed execution contexts: '+key)
    return records


def check(path, expected_token, collapse_exact=False):
    records = read(path, collapse_exact)
    with Path(path).open(encoding='utf-8-sig',newline='') as handle:
        duplicate_logs=sum(1 for _ in csv.DictReader(handle))-len(records)
    if records[0]['token'] != str(expected_token):
        raise ValueError('Unexpected build token')
    tick = float(records[0]['tick'])
    observer = Observer(tick)
    differences = []
    checked = Counter()
    def compare(index, field, actual, expected):
        checked[field] += 1
        if isinstance(expected, float):
            same = actual is not None and math.isclose(float(actual), expected, rel_tol=0, abs_tol=1e-8)
        else:
            same = actual == expected
        if not same:
            differences.append({'index': index, 'field': field, 'native': actual, 'python': expected})
    for row in records:
        i = int(row['index'])
        bar = Bar(int(row['time']), int(row['end']), *(float(row[k]) for k in ('open','high','low','close')))
        if row['standard'] != 'true':
            for k in ('internal_break','swing_break','sweep_mask','equal_mask','inversions'):
                compare(i,k,int(row[k]),0)
            compare(i,'regions',row['regions'],'')
            compare(i,'pools',row['pools'],'')
            continue
        result = observer.on_close(bar)
        for key in ('internal_break','internal_type','swing_break','swing_type','sweep_mask','equal_mask','inversions'):
            compare(i,key,int(row[key]),result[key])
        compare(i,'atr',number(row['atr']),result['atr'])
        compare(i,'internal_bias',int(row['internal_bias']),observer.internal.bias)
        compare(i,'swing_bias',int(row['swing_bias']),observer.swing.bias)
        native_regions = [z.split(',') for z in row['regions'].split(';') if z]
        native_pools = [p.split(',') for p in row['pools'].split(';') if p]
        if any(len(z) != 8 for z in native_regions) or any(len(p) != 5 for p in native_pools):
            raise ValueError('Truncated native state snapshot')
        compare(i,'region_count',int(row['region_count']),len(observer.regions))
        compare(i,'pool_count',int(row['pool_count']),len(observer.pools))
        if row['snapshot']=='true':
            compare(i,'region_snapshot_count',len(native_regions),len(observer.regions))
            compare(i,'pool_snapshot_count',len(native_pools),len(observer.pools))
        for n,z in zip(native_regions,observer.regions):
            expected = [z.kind,z.side,z.low,z.high,z.anchor,z.born,z.available,z.stage]
            for k,(actual,value) in enumerate(zip(n,expected)):
                compare(i,f'region[{k}]',actual if k==0 else float(actual) if k in (2,3) else int(actual),value)
        for n,p in zip(native_pools,observer.pools):
            expected = [p.level,p.side,p.anchor,p.born,p.equal]
            for k,(actual,value) in enumerate(zip(n,expected)):
                compare(i,f'pool[{k}]',float(actual) if k==0 else actual=='true' if k==4 else int(actual),value)
        minutes = int(row['tf']) if row['tf'].isdigit() else 1440 if row['tf'] in ('D','1D') else 10080
        active = int(number(row['h1_bias' if minutes<=5 else 'h4_bias']) or 0)
        other = int(number(row['h4_bias' if minutes<=5 else 'h1_bias']) or 0) if minutes<=60 else 0
        recent = observer.last_sweep if observer.last_sweep_index is not None and i-observer.last_sweep_index<=5 else 0
        compare(i,'assessment',row['assessment'],assessment(active,other,observer.internal.bias,observer.swing.bias,recent,minutes<=240))
        for prefix,tf in (('h1',60),('h4',240)):
            stamp = number(row[prefix+'_end'])
            if minutes<=tf and stamp is not None:
                compare(i,prefix+'_available',stamp<=bar.time,True)
    return {'status':'PASS_NATIVE_PARITY' if not differences else 'FAIL_NATIVE_PARITY',
            'file':str(path),'sha256':sha(Path(path)), 'feed':records[0]['feed'],'tf':records[0]['tf'],
            'token':records[0]['token'],'rows':len(records),'first_time':records[0]['time'],'last_time':records[-1]['time'],
            'exact_duplicate_logs':duplicate_logs,'log_uniqueness':'FAIL' if duplicate_logs else 'PASS',
            'checks':sum(checked.values()),'checked_fields':dict(checked),
            'events':{key:dict(Counter(r[key] for r in records)) for key in ('internal_break','swing_break','sweep_mask','inversions')},
            'difference_count':len(differences),'differences_first_30':differences[:30],
            'scope':'Exact logged chart OHLC -> oracle events, region/pool counts each bar and full state every 50 bars, ATR, narrative and HTF availability; not profitability'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths',nargs='+',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--token',type=int,required=True)
    parser.add_argument('--collapse-exact-duplicates',action='store_true',help='Report identical duplicate log records separately; conflicting duplicates still fail')
    args=parser.parse_args()
    results=[check(path,args.token,args.collapse_exact_duplicates) for path in args.paths]
    args.output.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{k:v for k,v in r.items() if k not in ('checked_fields','events','differences_first_30')} for r in results]))
    raise SystemExit(any(r['difference_count'] for r in results))
