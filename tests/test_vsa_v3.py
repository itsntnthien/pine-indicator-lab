"""Behavioral regressions: these must fail on the frozen v2 oracle."""
import unittest
from src.vsa_observer.reference import Candle, Observer, Zone, Sweep


def bar(i, o=100, h=101, l=99, c=100, v=100):
    return Candle(i*60000,(i+1)*60000,o,h,l,c,v)


class V3RegressionTests(unittest.TestCase):
    def test_ninth_pool_survives_and_can_be_swept(self):
        e=Observer(.01)
        e.pools=[Zone('POOL',-1,i,0,0,110+i,110+i) for i in range(9)]
        e.on_close(bar(0))
        self.assertEqual(len(e.pools),9)
        s=e.on_close(bar(1,h=110.5,c=100))
        self.assertEqual(s['sweepCode'],-1)
        self.assertEqual(s['short']['sweep']['level'],110)

    def test_gap_is_not_continuous_fvg(self):
        e=Observer(.01)
        e.on_close(bar(0,h=101))
        e.on_close(bar(1,h=102,c=101))
        e.on_close(bar(10,o=104,h=106,l=103,c=105))
        self.assertEqual(e.fvgs,[])

    def test_same_bar_structure_requires_next_bar_hold(self):
        e=Observer(.01)
        e.pools=[Zone('POOL',1,1,0,0,99,99)]
        e.high_swing=(10100,0,0)
        s=e.on_close(bar(0,o=100,h=103,l=98,c=102))
        self.assertFalse(s['long']['structureConfirmed'])
        self.assertTrue(s['long']['pendingStructure'])
        s=e.on_close(bar(1,o=102,h=104,l=101,c=103))
        self.assertTrue(s['long']['structureConfirmed'])

    def test_failed_next_bar_hold_cannot_resurrect_old_break(self):
        e=Observer(.01)
        e.pools=[Zone('POOL',1,1,0,0,99,99)]
        e.high_swing=(10100,0,0)
        e.on_close(bar(0,o=100,h=103,l=98,c=102))
        s=e.on_close(bar(1,o=102,h=103,l=99,c=100))
        self.assertFalse(s['long']['structureConfirmed'])
        s=e.on_close(bar(2,o=100,h=104,l=99,c=103))
        self.assertFalse(s['long']['structureConfirmed'])

    def test_no_volume_keeps_price_structure_and_reports_quality(self):
        e=Observer(.01)
        e.pools=[Zone('POOL',1,1,0,0,99,99)]
        e.high_swing=(10100,0,0)
        e.on_close(bar(0,o=100,h=103,l=98,c=102,v=None))
        s=e.on_close(bar(1,o=102,h=104,l=101,c=103,v=None))
        self.assertTrue(s['long']['structureConfirmed'])
        self.assertEqual(s['dataIssue'],'VOLUME_MISSING')
        self.assertNotEqual(s['long']['mask'],0)
        self.assertTrue(s['long']['mask'] & 1)

    def test_pool_and_zone_inclusive_lifetime(self):
        for kind, ttl in [('POOL',500),('FVG',250),('OB',250)]:
            e=Observer(.01)
            z=Zone(kind,-1,1,0,0,110,111)
            zones={'POOL':e.pools,'FVG':e.fvgs,'OB':e.obs}[kind]
            zones.append(z)
            e.index=ttl-1
            e.on_close(bar(0))
            self.assertIn(z,zones)
            e.on_close(bar(1))
            self.assertNotIn(z,zones)
            self.assertEqual(z.end_reason,'EXPIRED')

    def test_ob_touch_starts_after_confirmation(self):
        e=Observer(.01)
        e.on_close(bar(0,o=99.8,h=100,l=98,c=99.5))
        e.on_close(bar(1,o=104,h=105,l=99.5,c=101))
        e.high_swing=(10200,0,0)
        e.on_close(bar(2,o=101,h=106,l=100.5,c=105))
        self.assertEqual(len(e.obs),1)
        ob=e.obs[0]
        self.assertEqual(ob.source_time,60000)
        self.assertEqual(ob.anchor,120000)
        self.assertFalse(ob.touched)
        e.on_close(bar(3,o=105,h=106,l=104,c=105))
        self.assertTrue(ob.touched)
        self.assertEqual(ob.first_touch,4)

    def test_all_fvgs_retained_independent_of_display(self):
        e=Observer(.01)
        e.fvgs=[Zone('FVG',-1,i,0,0,110+i,111+i) for i in range(20)]
        e.on_close(bar(0))
        self.assertEqual(len(e.fvgs),20)

    def test_reset_and_expiry_clear_structure_both_directions(self):
        for side in [-1,1]:
            s=Sweep()
            s.update(side,100,98 if side==1 else 102,1,10,100)
            event={'type':side,'time':20,'price':100}
            self.assertTrue(s.confirm(side,2,20,side,event,100+side))
            self.assertTrue(s.confirm(side,11,110,side,event,100+side))
            self.assertFalse(s.confirm(side,12,120,side,event,100+side))
            s.update(side,100,98 if side==1 else 102,13,130,100)
            self.assertFalse(s.confirm(side,13,130,side,event,100+side))

    def test_volume_recovers_only_after_21_positive_bars(self):
        e=Observer(.01)
        for i in range(600):e.on_close(bar(i))
        self.assertTrue(e.snapshot['dataReady'])
        e.on_close(bar(600,v=0))
        for i in range(601,621):
            self.assertFalse(e.on_close(bar(i))['dataReady'])
        self.assertTrue(e.on_close(bar(621))['dataReady'])

    def test_tick_equality_does_not_invalidate(self):
        e=Observer(.1)
        e.low_sweep.update(1,100,99,0,0,100)
        self.assertFalse(e.on_close(bar(0,o=99,h=100,l=98,c=98.99))['long']['sweep']['invalid'])


if __name__=='__main__':unittest.main()
