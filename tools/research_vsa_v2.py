"""Frozen chronological excursion study; observations are not trades or returns."""
import hashlib
import json
import statistics
import sys
from collections import defaultdict, Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.vsa_observer.reference import Candle,Observer,HTF,VERSION

def run():
    if not VERSION.startswith('vsa-observer-2'):
        raise RuntimeError('v2 evidence is frozen. Use research_vsa_v3.py with the v3 oracle.')
    folder=ROOT/'research/vsa-observer-v2-20261118'
    manifest=json.loads((folder/'exness/manifest.json').read_text())
    start,end=manifest['targetStart'],manifest['targetEnd']
    data={};sources=[]
    for tf in [*HTF,'D','W']:
        merged={}
        for sub in ['exness-warmup','exness']:
            file=folder/sub/(tf+'.json')
            if not file.exists():continue
            sources.append(dict(file=str(file.relative_to(ROOT)),sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
            for b in json.loads(file.read_text()):merged[b['time']]=b
        rows=sorted(merged.values(),key=lambda b:b['time'])
        # Native D/W ends are unspecified by this REST schema. Do not fabricate them.
        data[tf]=[] if tf in ('D','W') else [Candle(b['time']*1000,(b['time']+int(tf)*60)*1000,b['open'],b['high'],b['low'],b['close'],b.get('volume')) for b in rows if (b['time']+int(tf)*60)*1000<=end]
    summary=[];records=[]
    split=lambda t:'train' if t<start+.6*(end-start) else 'validation' if t<start+.8*(end-start) else 'holdout'
    for tf in HTF:
        engine=Observer(.001,tf);bars=data[tf];contexts=[data[k] for k in HTF[tf]];pos=[0,0];latest=[None,None]
        seen=set();last_independent=-100;groups=defaultdict(list);counts=Counter()
        for i,b in enumerate(bars):
            for j,samples in enumerate(contexts):
                while pos[j]<len(samples) and samples[pos[j]].end<=b.end:
                    latest[j]=samples[pos[j]];pos[j]+=1
            s=engine.on_close(b,latest)
            if b.end<start:continue
            for name in ['long','short']:
                side=s[name];counts[side['text']]+=1
                ident=(side['side'],side['sweep']['stamp'])
                if not side['structureConfirmed'] or side['phase'] not in (2,3) or ident in seen:continue
                seen.add(ident)
                if not s['dataReady'] or i-last_independent<=10:continue
                if i+10>=len(bars) or split(bars[i+10].end)!=split(b.end):continue
                last_independent=i
                record=dict(timeframe=tf,time=b.end,side=side['side'],split=split(b.end),phase=side['phase'],mask=side['mask'],zone=side['zone']['code'],atr=s['atr'])
                for horizon in [3,5,10]:
                    future=bars[i+1:i+horizon+1]
                    hi=max(x.high for x in future);lo=min(x.low for x in future)
                    record[f'mfe{horizon}']=max(0,hi-b.close if side['side']==1 else b.close-lo)/s['atr']
                    record[f'mae{horizon}']=max(0,b.close-lo if side['side']==1 else hi-b.close)/s['atr']
                records.append(record);groups[(record['split'],record['side'],record['phase'])].append(record)
        result=dict(timeframe=tf,bars=len(bars),warmup=sum(b.end<start for b in bars),first=bars[0].time if bars else None,last=bars[-1].end if bars else None,
                    nativeHtfComplete=all(contexts),stateCounts=dict(counts),groups=[])
        for (part,side,phase),items in groups.items():
            result['groups'].append(dict(split=part,side=side,phase=phase,n=len(items),inference='DESCRIPTIVE_ONLY' if len(items)>=60 else 'INSUFFICIENT_SAMPLE',
                medians={k:statistics.median(r[k] for r in items) for k in ['mfe3','mae3','mfe5','mae5','mfe10','mae10']}))
        summary.append(result)
    report=dict(status='DESCRIPTIVE_NOT_PROFITABILITY',source='Exness XAUUSD BID',start=start,end=end,split='chronological 60/20/20',
                selection='first structure confirmation per sweep; valid nonconflicting phase; dataReady; globally >10 bars apart per timeframe; horizon cannot cross split',
                limitations=['D/W native end unverified: H1/H4 HTF gate blocked','OHLC excursions, no fill/spread/fees/P&L','No parameters optimized on holdout','Groups across timeframes share market data; not pooled as independent samples'],
                productionSha256=hashlib.sha256((ROOT/'dist/vsa_observer/XAU_VSA_OBSERVER.pine').read_bytes()).hexdigest(),sources=sources,frames=summary)
    (folder/'study.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    (folder/'observations.json').write_text(json.dumps(records,ensure_ascii=False),encoding='utf8')
    print(json.dumps([{'tf':s['timeframe'],'bars':s['bars'],'warmup':s['warmup'],'independent':sum(g['n'] for g in s['groups']),'htf':s['nativeHtfComplete']} for s in summary]))
if __name__=='__main__':run()
