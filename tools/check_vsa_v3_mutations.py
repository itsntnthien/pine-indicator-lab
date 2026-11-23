"""Prove behavioral tests reject deliberately broken engines without editing production."""
import hashlib
import json
from pathlib import Path
import sys
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import test_vsa_v3 as suite

source=(ROOT/'src/vsa_observer/reference.py').read_text('utf8')
mutations=[
    ('pool_cap_8','if len(zones)>cap:',"if zones is self.pools: zones[:] = zones[-8:]\n            if len(zones)>cap:",'test_ninth_pool_survives_and_can_be_swept'),
    ('gap_allowed',' and bar.time == prev.end and prev.time == self.history[-2].end','', 'test_gap_is_not_continuous_fvg'),
    ('same_bar_confirmed','True, False, event[\'price\']','False, True, event[\'price\']','test_same_bar_structure_requires_next_bar_hold'),
    ('stale_break_resurrects',"elif fresh and event['time'] > self.stamp:","elif event is not None and age > 0:",'test_failed_next_bar_hold_cannot_resurrect_old_break'),
    ('missing_volume_ready','ready = valid and','ready = True or','test_no_volume_keeps_price_structure_and_reports_quality')]
results=[]
for name,old,new,test in mutations:
    assert source.count(old)==1,(name,source.count(old))
    module=types.ModuleType('mutation_'+name)
    sys.modules[module.__name__]=module
    exec(compile(source.replace(old,new),module.__name__,'exec'),module.__dict__)
    suite.Observer=module.Observer
    result=unittest.TestResult()
    suite.V3RegressionTests(test).run(result)
    assert result.failures and not result.errors,(name,result.failures,result.errors)
    results.append({'mutation':name,'test':test,'status':'REJECTED','failure':result.failures[0][1].splitlines()[-1]})
out=ROOT/'evidence/vsa_observer/v3-mutations.json'
out.write_text(json.dumps({'reference_sha256':hashlib.sha256(source.encode()).hexdigest(),'results':results},indent=2),encoding='utf8')
print(json.dumps(results,indent=2))
