import math
import sys
import tempfile
import unittest
from pathlib import Path
from dataclasses import replace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'local-terminal'))
from src.vsa_observer.reference import Candle, Observer, Sweep, Zone, classify, phase, setup_mask, closed_context


def fixture(i):
    close = (200000 + (i*7919+31)%997 - 498 + (i%80 if i%160<80 else 160-i%160)*12)/100
    opened = close + ((i*11)%200-100)/100
    high = max(opened,close)+(25+(i*17)%150)/100
    low = min(opened,close)-(25+(i*13)%150)/100
    return Candle(1577836800000+i*300000,1577837100000+i*300000,opened,high,low,close,0 if i%97==0 else 100+(i*37)%250)


def context(bar, minutes):
    end = bar.end//(minutes*60000)*(minutes*60000)
    return Candle(end-minutes*60000,end,2000,2002,1998,2001 if (end//(minutes*60000))%2==0 else 1999,100)


class EngineTests(unittest.TestCase):
    def test_native_ema_seed(self):
        e=Observer(.01)
        for i in range(199):self.assertIsNone(e.on_close(fixture(i))['ema'])
        self.assertAlmostEqual(e.on_close(fixture(199))['ema'],2004.38805,places=8)
        self.assertAlmostEqual(e.on_close(fixture(200))['ema'],2004.4018007462687,places=8)

    def test_classifier_boundaries_and_mutation_controls(self):
        cases=[((True,1.5,1.2,.7,1,False),1),((True,1.5,1.2,.3,-1,False),-1),
               ((True,1.5,.8,.65,0,False),2),((True,1.5,.8,.35,0,False),-2),
               ((True,.7,.8,.5,-1,True),3),((True,.7,.8,.5,1,True),-3)]
        for args, expected in cases:
            self.assertEqual(classify(*args),expected)
            self.assertEqual(classify(False,*args[1:]),99)
        self.assertEqual(classify(True,1.499999,1.2,.7,1,False),0)
        self.assertEqual(classify(True,.7,.8,.5,-1,False),0)

    def test_all_flag_combinations_and_phase_precedence(self):
        for mask in range(512):
            age=-1 if mask&2 else 11 if mask&4 else 10
            if mask&2 and mask&4: continue
            actual=setup_mask(age,bool(mask&8),bool(mask&16),not mask&32,not mask&64,not mask&128,bool(mask&256),not mask&1)
            self.assertEqual(actual,mask)
        for mask, expected in [(0,3),(128,2),(32,1),(2,0),(16,4),(4|32,6),(8|4,5)]:
            self.assertEqual(phase(mask),expected)

    def test_sweep_latches_and_ten_bar_boundary(self):
        s=Sweep();s.update(1,100,99,10,1,100)
        s.update(1,None,None,11,2,99);self.assertFalse(s.invalid)
        s.update(1,None,None,12,3,98.99);self.assertTrue(s.invalid)
        s.update(1,None,None,13,4,101);self.assertTrue(s.invalid)
        s.update(1,100,98,14,5,101);self.assertFalse(s.invalid)
        self.assertFalse(setup_mask(10,False,False,True,True,True,False,True)&4)
        self.assertTrue(setup_mask(11,False,False,True,True,True,False,True)&4)

    def test_closed_context_simultaneous_close_and_future_rejection(self):
        b=fixture(0);ctx=context(b,15)
        self.assertEqual(closed_context([ctx,replace(ctx,end=b.end+1)],b.end),ctx)
        self.assertIsNone(closed_context([ctx],ctx.end-1))
        self.assertEqual(closed_context([ctx],ctx.end),ctx)
        with self.assertRaises(ValueError): Observer(.01).on_close(b,(replace(ctx,end=b.end+1),None))

    def test_zones_touch_tie_and_distance_boundary(self):
        e=Observer(.01);e.atr=2
        e.fvgs=[Zone('FVG',1,1,1,1,99,100,True),Zone('FVG',-1,3,1,1,100,101)]
        e.obs=[Zone('OB',1,2,1,1,99,100)]
        self.assertEqual(e.zone_context(1,101)['code'],2)
        self.assertEqual(e.zone_context(1,101)['zone']['id'],2)
        self.assertEqual(e.zone_context(1,101.0001)['code'],3)
        e.obs[0].terminal=True
        self.assertIn('đã chạm',e.zone_context(1,100)['text'])

    def test_prefix_replay_missing_volume_and_bounds(self):
        a=Observer(.01);snapshots=[]
        for i in range(2500):
            b=fixture(i);snapshots.append(a.on_close(b,(context(b,15),context(b,60))))
            self.assertLessEqual(len(a.pools),1002);self.assertLessEqual(len(a.fvgs),251);self.assertLessEqual(len(a.obs),251)
        b=Observer(.01)
        for i in range(731):
            bar=fixture(i);got=b.on_close(bar,(context(bar,15),context(bar,60)))
            self.assertEqual(got,snapshots[i])
        self.assertFalse(snapshots[598]['dataReady'])
        self.assertEqual(snapshots[679]['vsa'],99)
        with self.assertRaises(ValueError): b.on_close(fixture(730))
        self.assertGreater(len(a.events),0)


if __name__=='__main__':unittest.main()
