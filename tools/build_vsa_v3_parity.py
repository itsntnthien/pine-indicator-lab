"""Run shipped Pine engine with deterministic OHLCV and compare each bar to Python."""
import hashlib
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_vsa_v2 import fixture, context
from src.vsa_observer.reference import Observer

def build():
    source=(ROOT/'dist/vsa_observer/VSA_OBSERVER_V3.pine').read_text(encoding='utf8')
    source=re.sub(r'f_native_htf\(string tf\) =>.*?(?=\nstring confTf)', '''f_native_htf(string tf) =>
    int step = int(str.tonumber(tf)) * 60000
    int ending = int(math.floor(time_close / step)) * step
    float closing = int(ending / step) % 2 == 0 ? 2001.0 : 1999.0
    [2000.0, 2002.0, 1998.0, closing, 100.0, ending-step, ending]''',source,flags=re.S)
    source=source.replace('ta.atr(14)','ta.rma(na(close[1]) ? high-low : math.max(high-low, math.max(math.abs(high-close[1]),math.abs(low-close[1]))), 14)')
    source=source.replace('syminfo.mintick','0.01')
    # Preserve strings/comments; rename source and record fields consistently.
    tokens=re.compile(r'"(?:[^"\\]|\\.)*"|//[^\n]*|\b(?:open|high|low|close|volume|time_close|time)\b')
    source=tokens.sub(lambda m:m[0] if m[0].startswith(('"','//')) else 'fx_'+m[0],source)
    # Session labels alone use the platform time() function; they are not parity inputs.
    source=source.replace('fx_time(', 'time(')
    pre='''
int n = bar_index
float fx_close = (200000 + (n*7919+31)%997 - 498 + (n%160<80 ? n%80 : 160-n%160)*12)/100.0
float fx_open = fx_close + ((n*11)%200-100)/100.0
float fx_high = math.max(fx_open,fx_close)+(25+(n*17)%150)/100.0
float fx_low = math.min(fx_open,fx_close)-(25+(n*13)%150)/100.0
float fx_volume = n%97==0 ? 0 : 100+(n*37)%250
int fx_time = 1577836800000+n*300000
int fx_time_close = fx_time+300000
'''
    lines=source.splitlines();idx=next(i for i,l in enumerate(lines) if l.startswith('indicator('))
    lines.insert(idx+1,pre);source='\n'.join(lines)
    engine=Observer(.01);expected=[]
    for i in range(1500):
        bar=fixture(i);expected.append(engine.on_close(bar,(context(bar,15),context(bar,60))))
    metrics={'obsVsa':lambda s:s['vsa'],'obsLongMask':lambda s:s['long']['mask'],
             'obsShortMask':lambda s:s['short']['mask'],'obsLongZoneCode':lambda s:s['long']['zone']['code'],
             'obsShortZoneCode':lambda s:s['short']['zone']['code'],'obsSweep':lambda s:s['sweepCode'],
             'smcTrend':lambda s:s['trend'],'obsEma':lambda s:s['ema'],'obsAtr':lambda s:s['atr'],
             'obsLongZoneId':lambda s:(s['long']['zone']['zone'] or {}).get('id'),
             'obsShortZoneId':lambda s:(s['short']['zone']['zone'] or {}).get('id'),
             'fxLongStructure':lambda s:int(s['long']['structureConfirmed']),
             'fxShortStructure':lambda s:int(s['short']['structureConfirmed']),
             'fxLongPending':lambda s:int(s['long']['pendingStructure']),
             'fxShortPending':lambda s:int(s['short']['pendingStructure'])}
    hashes=[]
    for snap in expected:
        h=0
        for name,fn in metrics.items():
            v=fn(snap)
            if v is None: v=-987654321
            elif name in ('obsEma','obsAtr'): v=int(v*100000+.5)
            h=(h*131+int(v)+10000000000)%1000000007
        hashes.append(h)
    csv=','.join(map(str,hashes))
    harness='\n// All 15 fields hashed per bar; EMA/ATR quantized to 1e-5.\nint fxLongStructure = obsLongStructure ? 1 : 0\nint fxShortStructure = obsShortStructure ? 1 : 0\nint fxLongPending = obsLowSweep.pending ? 1 : 0\nint fxShortPending = obsHighSweep.pending ? 1 : 0\n'
    harness+='f_parity_check() =>\n    var expected = str.split("'+csv+'", ",")\n    int actual = 0\n'
    for name in metrics:
        term=f'int(math.round({name}*100000))' if name in ('obsEma','obsAtr') else name
        harness+=f'    actual := (actual*131+(na({name}) ? -987654321 : {term})+10000000000)%1000000007\n'
    harness+='    if bar_index < 1500 and actual != int(str.tonumber(array.get(expected,bar_index)))\n'
    harness+='        runtime.error("PARITY bar="+str.tostring(bar_index)+" got="+str.tostring(actual)+" want="+array.get(expected,bar_index)+" masks="+str.tostring(obsLongMask)+"/"+str.tostring(obsShortMask)+" zones="+str.tostring(obsLongZoneId)+"/"+str.tostring(obsShortZoneId)+" vsa="+str.tostring(obsVsa)+" ema="+str.tostring(obsEma,"#.########")+" atr="+str.tostring(obsAtr,"#.########"))\n    true\nif barstate.isconfirmed\n    f_parity_check()\n'
    harness+='if barstate.isconfirmed and bar_index == 1499\n    log.info("VSA_V3_PARITY_PASS|bars=1500|fields=15|tick=0.01|fixture=v1")\n'
    out=ROOT/'output/playwright/vsa-v3';out.mkdir(parents=True,exist_ok=True)
    (out/'parity.pine').write_text(source+harness,encoding='utf8')
    (out/'fixture-expected.json').write_text(json.dumps(expected,ensure_ascii=False),encoding='utf8')
    manifest={'production_sha256':hashlib.sha256((ROOT/'dist/vsa_observer/VSA_OBSERVER_V3.pine').read_bytes()).hexdigest(),
              'fixture_bars':1500,'fields':list(metrics),'input_overrides':['OHLCV','time','tick','HTF fixture'],
              'native_htf_request_test':'separate production harness required','status':'GENERATED_NOT_RUN'}
    (out/'parity-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print(json.dumps(manifest))
if __name__=='__main__':build()
