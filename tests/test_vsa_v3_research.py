import unittest
from datetime import datetime, timezone
from tools.research_vsa_v3 import SessionVolume, fvg_variant
from src.vsa_observer.reference import Candle, Observer


class ResearchTests(unittest.TestCase):
    def test_fvg_filter_also_blocks_dependent_ob(self):
        for middle_close,third_low,accepted in [(99.9,100.5,False),(101,100.01,False),(101,100.5,True)]:
            engines=[Observer(.01),fvg_variant(.10)(.01)]
            for e in engines:
                e.atr=2
                e.on_close(Candle(0,60000,99.8,100,98,99.5,100))
                e.on_close(Candle(60000,120000,104,105,99.5,middle_close,100))
                e.high_swing=(10200,0,0)
                e.on_close(Candle(120000,180000,101,106,third_low,105,100))
            self.assertEqual(len(engines[0].obs),1)
            self.assertEqual(len(engines[1].obs),int(accepted))
            self.assertEqual(len(engines[1].fvgs),int(accepted))
            self.assertEqual(engines[0].snapshot['long']['mask'],engines[1].snapshot['long']['mask'])

    def test_seasonal_volume_excludes_current_and_requires_ten_sessions(self):
        normalizer=SessionVolume()
        first=int(datetime(2026,1,1,15,tzinfo=timezone.utc).timestamp()*1000)
        for day in range(10):
            t=first+day*86400000
            self.assertIsNone(normalizer.observe(Candle(t,t+60000,100,101,99,100,100)))
        t=first+10*86400000
        self.assertEqual(normalizer.observe(Candle(t,t+60000,100,101,99,100,200)),2)
        # Current session never enters its own baseline, including repeat inspection.
        self.assertEqual(normalizer.observe(Candle(t,t+60000,100,101,99,100,300)),3)
        self.assertIsNone(normalizer.observe(Candle(t+60000,t+120000,100,101,99,100,100)))

    def test_seasonal_window_never_exceeds_twenty_prior_sessions(self):
        n=SessionVolume()
        first=1767279600000
        for day in range(30):
            t=first+day*86400000
            ratio=n.observe(Candle(t,t+60000,100,101,99,100,100 if day else 10000))
        self.assertEqual(len(n.sessions),21)
        self.assertEqual(ratio,1)


if __name__=='__main__':unittest.main()
