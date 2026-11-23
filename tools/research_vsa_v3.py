"""Development-only ablations on already inspected archives; never select a winner."""
import hashlib
import json
import statistics
import sys
import types
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.vsa_observer.reference import Candle, Observer, HTF, classify


def fvg_variant(threshold):
    """Research-only engine clone: filter at birth so dependent OB creation also changes."""
    source=(ROOT/'src/vsa_observer/reference.py').read_text('utf8')
    bull='if lo > self.ticks(b2.high) and self.ticks(prev.high) > self.ticks(b2.high):'
    bear='elif hi < self.ticks(b2.low) and self.ticks(prev.low) < self.ticks(b2.low):'
    assert source.count(bull)==source.count(bear)==1
    source=source.replace(bull,bull[:-1]+f' and self.ticks(prev.close) > self.ticks(b2.high) and self.atr is not None and (lo-self.ticks(b2.high))*self.tick >= {threshold}*self.atr:')
    source=source.replace(bear,bear[:-1]+f' and self.ticks(prev.close) < self.ticks(b2.low) and self.atr is not None and (self.ticks(b2.low)-hi)*self.tick >= {threshold}*self.atr:')
    module=types.ModuleType('vsa_fvg_research_'+str(threshold).replace('.','_'))
    sys.modules[module.__name__]=module
    exec(compile(source,module.__name__,'exec'),module.__dict__)
    return module.Observer


class SessionVolume:
    """Same local minute in the prior 20 traded sessions, NY 17:00 boundary."""
    def __init__(self):
        self.sessions = deque(maxlen=21)

    def observe(self, candle):
        local = datetime.fromtimestamp(candle.time / 1000, timezone.utc).astimezone(ZoneInfo('America/New_York'))
        day = (local - timedelta(hours=17)).date()
        slot = (local.hour * 60 + local.minute - 17 * 60) % 1440
        if not self.sessions or self.sessions[-1][0] != day:
            self.sessions.append((day, {}))
        prior = [slots[slot] for _, slots in list(self.sessions)[:-1]
                 if slot in slots and slots[slot] is not None and slots[slot] > 0]
        ratio = candle.volume / statistics.mean(prior) if len(prior) >= 10 and candle.volume is not None and candle.volume > 0 else None
        self.sessions[-1][1][slot] = candle.volume
        return ratio


def load_data():
    folder = ROOT / 'research/vsa-observer-v2-20261118'
    manifest = json.loads((folder / 'exness/manifest.json').read_text())
    data, sources = {}, []
    for tf in [*HTF, 'D', 'W']:
        merged = {}
        for sub in ['exness-warmup', 'exness']:
            path = folder / sub / (tf + '.json')
            if path.exists():
                sources.append({'path':path.relative_to(ROOT).as_posix(), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
                for b in json.loads(path.read_text()): merged[b['time']] = b
        # D/W close times are absent in this archive. No guessed daily/week boundaries.
        data[tf] = [] if tf in ('D','W') else [Candle(b['time']*1000,(b['time']+int(tf)*60)*1000,b['open'],b['high'],b['low'],b['close'],b.get('volume'))
            for b in sorted(merged.values(),key=lambda x:x['time']) if (b['time']+int(tf)*60)*1000 <= manifest['targetEnd']]
    return data, sources, manifest


def run():
    data, sources, manifest = load_data()
    # Independent HTF engines consume only bars whose native/declared close has passed.
    htf_trends = {}
    for tf, bars in data.items():
        e = Observer(.001, tf)
        htf_trends[tf] = [e.on_close(b)['trend'] for b in bars]
    variants={f'fvg_middle_close_atr_{n:.2f}':fvg_variant(n) for n in [.05,.10]}
    frames, records = [], []
    for tf in HTF:
        e, volume = Observer(.001, tf), SessionVolume()
        fvg_engines={name:engine(.001,tf) for name,engine in variants.items()}
        bars = data[tf]
        pos, latest, trends = [0,0], [None,None], [0,0]
        seen = defaultdict(set)
        last_independent = defaultdict(lambda:-100)
        samples = defaultdict(list)
        counts = Counter()
        vsa_memory = {1:None,-1:None}
        sweep_stamp = {1:None,-1:None}
        peaks = [0,0,0]
        for i, b in enumerate(bars):
            for j, ctx_tf in enumerate(HTF[tf]):
                ctx_bars = data[ctx_tf]
                while pos[j] < len(ctx_bars) and ctx_bars[pos[j]].end <= b.end:
                    latest[j] = ctx_bars[pos[j]]
                    trends[j] = htf_trends[ctx_tf][pos[j]]
                    pos[j] += 1
            s = e.on_close(b, latest)
            fvg_snapshots={name:engine.on_close(b,latest) for name,engine in fvg_engines.items()}
            for name, candidate in fvg_snapshots.items():
                assert (candidate['long']['mask'],candidate['short']['mask'])==(s['long']['mask'],s['short']['mask']), 'FVG must not alter independent setup gates'
                if b.end>=manifest['targetStart']:
                    candidate_engine=fvg_engines[name]
                    counts[name+'_new_ob']+=sum(z.born==candidate_engine.index for z in candidate_engine.obs)
                    for side_name in ['long','short']:
                        counts[name+'_zone_context_changed']+=candidate[side_name]['zone']['code']!=s[side_name]['zone']['code']
            peaks = [max(n,len(z)) for n,z in zip(peaks,[e.pools,e.fvgs,e.obs])]
            session_rv = volume.observe(b)
            prior = bars[max(0,i-20):i]
            seasonal = classify(session_rv is not None and s['rr'] is not None, session_rv, s['rr'],
                (b.close-b.low)/(b.high-b.low) if b.high>b.low else None,
                b.close-prior[-1].close if prior else 0,
                len(prior)>=2 and b.volume is not None and prior[-1].volume is not None and prior[-2].volume is not None and b.volume < prior[-1].volume and b.volume < prior[-2].volume)
            if b.end >= manifest['targetStart']:
                counts['bars'] += 1
                counts['seasonal_ready'] += session_rv is not None
                for z in e.fvgs:
                    if z.born == e.index:
                        counts['fvg_baseline'] += 1
                        middle = prior[-1].close
                        displacement = middle > z.low if z.side == 1 else middle < z.high
                        for threshold in [.05,.10]:
                            counts[f'fvg_middle_close_atr_{threshold:.2f}'] += bool(displacement and s['atr'] and z.high-z.low >= threshold*s['atr'])
            for name in ['long','short']:
                state = s[name]
                side, stamp = state['side'], state['sweep']['stamp']
                if stamp != sweep_stamp[side]:
                    vsa_memory[side] = None
                    sweep_stamp[side] = stamp
                if s['vsa'] != 99 and s['vsa'] * side < 0: vsa_memory[side] = None
                elif stamp is not None and s['vsa'] != 99 and s['vsa'] * side > 0: vsa_memory[side] = i
                remembered = vsa_memory[side] is not None and i-vsa_memory[side] < 3
                mask = state['mask']
                gates = {'baseline':mask==0,
                    'htf_structure_5_5':(mask & ~64)==0 and all(t==side for t in trends),
                    'session_volume_20_min10':(mask & ~128)==0 and seasonal!=99 and seasonal*side>0,
                    'vsa_lifetime_3':(mask & ~128)==0 and remembered}
                for variant,candidate_snapshot in fvg_snapshots.items():
                    gates[variant]=candidate_snapshot[name]['mask']==0
                for candidate, eligible in gates.items():
                    if not eligible or b.end < manifest['targetStart']: continue
                    counts[candidate+'_bars'] += 1
                    key = (side,stamp)
                    if key in seen[candidate]: continue
                    seen[candidate].add(key)
                    if i-last_independent[candidate] <= 10 or i+10 >= len(bars): continue
                    future = bars[i+1:i+11]
                    if any(x.time != y.end for y,x in zip([b]+future[:-1],future)): continue
                    last_independent[candidate] = i
                    hi,lo = max(x.high for x in future), min(x.low for x in future)
                    mfe = max(0,hi-b.close if side==1 else b.close-lo)/s['atr']
                    mae = max(0,b.close-lo if side==1 else hi-b.close)/s['atr']
                    chosen=fvg_snapshots.get(candidate,s)
                    row = {'tf':tf,'candidate':candidate,'time':b.end,'side':side,'mfe10':mfe,'mae10':mae,'score':mfe-mae,'zone':chosen[name]['zone']['code'],'partition':'DEVELOPMENT_ALREADY_SEEN'}
                    samples[candidate].append(row)
                    records.append(row)
        summaries = {candidate:{'independent_n':len(samples[candidate]),
            'median_mfe10_minus_mae10':statistics.median(r['score'] for r in samples[candidate]) if samples[candidate] else None,
            'holdout_n':0,'promote':False} for candidate in ['baseline','htf_structure_5_5','session_volume_20_min10','vsa_lifetime_3',*variants]}
        frames.append({'symbol':'EXNESS:XAUUSD','tf':tf,'bars_total':len(bars),'counts':dict(counts),'peak_active_pool_fvg_ob':peaks,'native_htf_complete':all(data[k] for k in HTF[tf]),'candidates':summaries})
        print(tf, len(bars), {k:v['independent_n'] for k,v in summaries.items()}, flush=True)
    report = {'status':'DEVELOPMENT_ONLY_NO_PROMOTION','production_sha256':hashlib.sha256((ROOT/'dist/vsa_observer/VSA_OBSERVER_V3.pine').read_bytes()).hexdigest(),
        'sources':sources,'frames':frames,'untouched_holdout':False,'nas100':'NO_ARCHIVED_MATCHED_FEED_DATA',
        'promotion_gate':'Per symbol/frame: >=100 development + >=50 untouched holdout independent observations; retain >=50%; paired session-block 95% CI of MFE10-MAE10 improvement >0. Not evaluated without untouched holdout.',
        'fvg_variant_scope':'Full causal engine clone with birth filter, downstream OB and zone selection. Asserted every bar that independent setup masks remain equal; FVG is descriptive context, not an eligibility gate.',
        'limitations':['Observed prices, no fills/costs/P&L','All archive partitions previously inspected; relabelled development','D/W timestamps unavailable; H1/H4 HTF candidates blocked','Intraday ends derived from archive interval, shortened sessions unverified','FVG filtering changes context, not existing confluence gates; identical excursion outcomes cannot establish improvement','Session normalization is a NY 17:00 research convention, not a verified Exness volume-session calendar','Timeframes overlap and are not pooled as independent samples']}
    out = ROOT/'research/vsa-v3-20261119'
    (out/'study.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    (out/'observations.json').write_text(json.dumps(records,ensure_ascii=False),encoding='utf8')


if __name__ == '__main__': run()
