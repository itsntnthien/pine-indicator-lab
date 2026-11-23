"""Behavioral witnesses for both feeds/pairs; synthetic data is not trading evidence."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict, replace
import json
import math
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
from src.intraday import reference as r
from indicator_readiness import wilder_atr
from build_intraday import build, FRAGMENTS

BASE = 1640995200000


def bar(i, minutes=5, o=100, h=101, lo=99, c=100):
    return r.Bar(BASE + i * minutes * 60000, BASE + (i + 1) * minutes * 60000, o, h, lo, c)


def warm(feed='OANDA:XAUUSD', htf=60, side=1, tick=.01):
    ctx = r.Context(feed, htf, tick)
    ctx.bias = side
    engine = r.EntryEngine(ctx, 5 if htf == 60 else 15)
    for i in range(14):
        engine.on_close(bar(i, engine.minutes))
    return engine


def zone(engine, kind='SSL', side=1, lo=100, hi=100, available=None):
    return engine.context.add_zone(kind, side, lo, hi, BASE, available or engine.series.bars[-1].end, 0)


class SignalBehavior(unittest.TestCase):
    def test_buy_sell_each_zone_both_feeds_and_pairs(self):
        for feed in sorted(r.FEEDS):
            for htf in (60, 240):
                for side in (1, -1):
                    for kind in ('LIQ', 'OB', 'FVG', 'SD', 'SR'):
                        with self.subTest(feed=feed, htf=htf, side=side, kind=kind):
                            engine = warm(feed, htf, side)
                            liquidity = kind == 'LIQ'
                            kind = ('SSL' if side == 1 else 'BSL') if liquidity else kind
                            source = zone(engine, kind, side, 100 if liquidity else 99.5, 100 if liquidity else 100.5)
                            zone(engine, 'BSL' if side == 1 else 'SSL', -side, 110 if side == 1 else 90, 110 if side == 1 else 90)
                            sample = bar(14, engine.minutes, 101, 102, 99, 101) if side == 1 else bar(14, engine.minutes, 99, 101, 98, 99)
                            signal = engine.on_close(sample)
                            self.assertIsNotNone(signal)
                            self.assertEqual(signal.side, side)
                            self.assertEqual(signal.target, 110 if side == 1 else 90)
                            self.assertEqual(signal.confirmed_at, sample.end)
                            self.assertAlmostEqual(signal.stop, 98.79 if side == 1 else 101.21)
                            self.assertTrue(source.used)
                            self.assertEqual(signal.sources, (source.id,))
                            self.assertIsNone(engine.on_close(replace(sample, time=sample.end, end=sample.end + engine.minutes*60000)))
                            self.assertEqual(len(engine.setups), 1)
                            self.assertEqual(len(engine.observations), 1)

    def test_no_future_zone_or_intrabar_htf_close_used(self):
        engine = warm()
        source = zone(engine, available=bar(14).end)
        self.assertIsNone(engine.on_close(bar(14, o=101, h=102, lo=99, c=101)))
        self.assertFalse(source.used)
        self.assertIsNotNone(engine.on_close(bar(15, o=101, h=102, lo=99, c=101)))
        with self.assertRaises(ValueError):
            engine.context.on_close(bar(100, 60))
            engine.on_close(bar(16))

    def test_sweep_threshold_requires_tick_and_reclaim(self):
        engine = warm(tick=.1)
        zone(engine)
        self.assertIsNone(engine.on_close(bar(14, o=101, h=102, lo=99.95, c=101)))
        self.assertIsNone(engine.on_close(bar(15, o=100, h=101, lo=99.9, c=100.05)))
        self.assertIsNotNone(engine.on_close(bar(16, o=100, h=101, lo=99.9, c=100.1)))

    def test_confirmation_at_third_following_bar_uses_attempt_extreme(self):
        engine = warm()
        zone(engine)
        for i, low in [(14, 99), (15, 98), (16, 98.5)]:
            self.assertIsNone(engine.on_close(bar(i, o=100, h=100.5, lo=low, c=99.8)))
        signal = engine.on_close(bar(17, o=99.8, h=101, lo=99.5, c=100.5))
        self.assertEqual(signal.extreme, 98)
        self.assertLess(signal.stop, 98)

    def test_timeout_cannot_slide_and_rearms_only_after_exit(self):
        engine = warm()
        source = zone(engine)
        for i in range(14, 18):
            self.assertIsNone(engine.on_close(bar(i, o=100, h=100.5, lo=99, c=99.8)))
        self.assertIsNone(engine.on_close(bar(18, o=100, h=101, lo=99, c=100.5)))
        self.assertTrue(source.blocked)
        self.assertIsNone(engine.on_close(bar(19, o=101, h=102, lo=100.5, c=101)))
        self.assertFalse(source.blocked)
        self.assertIsNotNone(engine.on_close(bar(20, o=101, h=102, lo=99, c=101)))

    def test_direction_flip_cancels_pending_attempt(self):
        engine = warm()
        source = zone(engine)
        engine.on_close(bar(14, o=100, h=100.5, lo=99, c=99.8))
        engine.context.bias = -1
        self.assertIsNone(engine.on_close(bar(15, o=100, h=101, lo=99, c=100.5)))
        self.assertIsNone(source.attempt)
        self.assertFalse(source.used)

    def test_multiple_sources_one_immutable_snapshot(self):
        engine = warm()
        a = zone(engine)
        b = zone(engine, 'FVG', lo=99.5, hi=100.5)
        target = zone(engine, 'OB', -1, 109, 112)
        signal = engine.on_close(bar(14, o=101, h=102, lo=98, c=101))
        self.assertEqual(signal.sources, (a.id, b.id))
        self.assertEqual(signal.target, 109)
        before = asdict(signal)
        target.lo = 105
        engine.on_close(bar(15, o=111, h=112, lo=110, c=111))
        self.assertEqual(asdict(signal), before)
        self.assertTrue(engine.observations[-1].adverse)
        with self.assertRaises(FrozenInstanceError):
            signal.stop = 0

    def test_missing_target_and_low_rr_do_not_block(self):
        engine = warm()
        zone(engine)
        signal = engine.on_close(bar(14, o=101, h=102, lo=99, c=101))
        self.assertIsNone(signal.target)
        self.assertIsNone(r.reward_risk(1, 101, signal.stop, None))
        engine = warm()
        zone(engine)
        zone(engine, 'FVG', -1, 101.1, 101.2)
        signal = engine.on_close(bar(14, o=101, h=102, lo=99, c=101))
        self.assertIsNotNone(signal)
        self.assertLess(r.reward_risk(1, 101, signal.stop, signal.target), 1.5)

    def test_next_open_at_stop_is_adverse_not_a_fill(self):
        engine = warm()
        zone(engine)
        signal = engine.on_close(bar(14, o=101, h=102, lo=99, c=101))
        engine.on_close(bar(15, o=signal.stop, h=101, lo=signal.stop-1, c=100))
        observed = engine.observations[-1]
        self.assertTrue(observed.adverse)
        self.assertIsNone(observed.rr)
        self.assertEqual(engine.setups[0], signal)
        self.assertNotIn('fill', asdict(observed))

    def test_visual_union_does_not_change_reclaim_boundary(self):
        engine = warm()
        first = zone(engine, 'OB', lo=99, hi=100)
        second = zone(engine, 'FVG', lo=99.5, hi=102)
        before = deepcopy(engine.context.zones)
        groups = r.visual_groups(engine.context.zones)
        self.assertEqual((groups[0]['lo'], groups[0]['hi']), (99, 102))
        self.assertEqual(engine.context.zones, before)
        signal = engine.on_close(bar(14, o=100, h=102, lo=99, c=101))
        self.assertEqual(signal.sources, (first.id,))
        self.assertFalse(second.used)

    def test_prefix_reload_invariance(self):
        samples = [bar(i, o=100, h=100.5, lo=99, c=99.8) for i in range(14, 17)]
        samples += [bar(17, o=100, h=102, lo=99, c=101), bar(18, o=101, h=103, lo=100, c=102)]
        full = warm()
        zone(full)
        zone(full, 'BSL', -1, 110, 110)
        for sample in samples:
            full.on_close(sample)
        for end in range(1, len(samples)+1):
            prefix = warm()
            zone(prefix)
            zone(prefix, 'BSL', -1, 110, 110)
            for sample in samples[:end]:
                prefix.on_close(sample)
            self.assertEqual(prefix.setups, [s for s in full.setups if s.confirmed_at <= samples[end-1].end])
            self.assertEqual(prefix.observations, [o for o in full.observations if o.at <= samples[end-1].time])


class ContextBehavior(unittest.TestCase):
    def context(self):
        ctx = r.Context('OANDA:XAUUSD', 60, .01)
        for i in range(14):
            ctx.on_close(bar(i, 60))
        return ctx

    def test_pivot_confirmation_tie_keeps_earliest(self):
        ctx = self.context()
        ctx.on_close(bar(14, 60, 100, 105, 99, 101))
        ctx.on_close(bar(15, 60, 101, 105, 99, 100))
        self.assertFalse(any(z.kind == 'BSL' for z in ctx.zones))
        ctx.on_close(bar(16, 60, 100, 102, 99, 100))
        pools = [z for z in ctx.zones if z.kind == 'BSL']
        self.assertEqual(len(pools), 1)
        self.assertEqual(pools[0].anchor, bar(14, 60).time)
        self.assertEqual(pools[0].available, bar(16, 60).end)
        ctx.on_close(bar(17, 60))
        self.assertEqual(ctx.high_pivot[0], bar(14, 60).time)

    def test_ob_uses_last_opposing_full_wick_not_fallback(self):
        ctx = self.context()
        ctx.high_pivot = (BASE, 103)
        ctx.on_close(bar(14, 60, 101, 102, 98, 100))
        ctx.on_close(bar(15, 60, 100, 105, 99, 104))
        obs = [z for z in ctx.zones if z.kind == 'OB']
        self.assertEqual([(z.lo, z.hi, z.side) for z in obs], [(98, 102, 1)])
        self.assertEqual(ctx.bias, 1)
        ctx.on_close(bar(16, 60, 104, 106, 103, 105))
        self.assertEqual(len([z for z in ctx.zones if z.kind == 'OB']), 1)
        ctx = self.context()
        ctx.high_pivot = (BASE, 103)
        ctx.on_close(bar(14, 60, 100, 105, 99, 104))
        self.assertFalse(any(z.kind == 'OB' for z in ctx.zones))

    def test_fvg_third_close_and_minimum_size(self):
        ctx = self.context()
        ctx.on_close(bar(14, 60, 102, 104, 102, 103))
        gaps = [z for z in ctx.zones if z.kind == 'FVG']
        self.assertEqual([(z.lo, z.hi, z.side) for z in gaps], [(101, 102, 1)])
        self.assertEqual(gaps[0].available, bar(14, 60).end)
        ctx = self.context()
        ctx.on_close(bar(14, 60, 101.1, 102, 101.1, 101.5))
        self.assertFalse(any(z.kind == 'FVG' for z in ctx.zones))

    def test_no_zones_during_atr_warmup(self):
        ctx = r.Context('OANDA:XAUUSD', 60, .01)
        for i in range(13):
            ctx.on_close(bar(i, 60, 100+i*4, 102+i*4, 99+i*4, 101+i*4))
        self.assertEqual(ctx.zones, [])

    def test_supply_demand_uses_longest_base_and_prior_atr(self):
        ctx = self.context()
        for i in range(14, 17):
            ctx.on_close(bar(i, 60, 100, 100.4 + (16-i)*.1, 99.6 - (16-i)*.1, 100.1))
        ctx.on_close(bar(17, 60, 100, 105, 100, 104))
        regions = [z for z in ctx.zones if z.kind == 'SD']
        self.assertEqual(len(regions), 1)
        self.assertAlmostEqual(regions[0].lo, 99.4)
        self.assertAlmostEqual(regions[0].hi, 100.6)

    def test_zone_invalidation_close_only_and_age_boundary(self):
        ctx = self.context()
        created = ctx.add_zone('OB', 1, 99, 101, BASE, BASE, 13)
        ctx.on_close(bar(14, 60, 100, 102, 95, 100))
        self.assertIn(created, ctx.zones)
        ctx.on_close(bar(15, 60, 100, 101, 97, 98))
        self.assertNotIn(created, ctx.zones)
        created = ctx.add_zone('OB', 1, 95, 96, BASE, BASE, 15)
        for i in range(16, 115):
            ctx.on_close(bar(i, 60))
        self.assertIn(created, ctx.zones)
        ctx.on_close(bar(115, 60))
        self.assertNotIn(created, ctx.zones)

    def test_three_swings_and_fixed_sr_width(self):
        ctx = self.context()
        for i in range(4):
            ctx.add_zone('BSL', -1, 105+i, 105+i, BASE+i, BASE+i, i)
        self.assertEqual([z.lo for z in ctx.zones], [106, 107, 108])
        ctx = self.context()
        ctx.on_close(bar(14, 60, 100, 105, 99, 101))
        ctx.on_close(bar(15, 60, 101, 104, 99, 100))
        ctx.on_close(bar(16, 60, 100, 102, 99, 100))
        sr = next(z for z in ctx.zones if z.kind == 'SR')
        bounds = (sr.lo, sr.hi)
        self.assertAlmostEqual((sr.hi-sr.lo)/2, .2*ctx.series.atr)
        ctx.on_close(bar(17, 60, 100, 104, 90, 100))
        self.assertEqual((sr.lo, sr.hi), bounds)

    def test_sell_htf_geometry_is_explicitly_checked(self):
        def mirror(b):
            return replace(b, open=200-b.open, high=200-b.low, low=200-b.high, close=200-b.close)
        ctx = self.context()
        ctx.low_pivot = (BASE, 97)
        ctx.on_close(mirror(bar(14, 60, 101, 102, 98, 100)))
        ctx.on_close(mirror(bar(15, 60, 100, 105, 99, 104)))
        ob = next(z for z in ctx.zones if z.kind == 'OB')
        self.assertEqual((ob.side, ob.lo, ob.hi), (-1, 98, 102))
        self.assertEqual(ctx.bias, -1)
        ctx = self.context()
        ctx.on_close(mirror(bar(14, 60, 102, 104, 102, 103)))
        fvg = next(z for z in ctx.zones if z.kind == 'FVG')
        self.assertEqual((fvg.side, fvg.lo, fvg.hi), (-1, 98, 99))
        ctx = self.context()
        for i in range(14, 17):
            ctx.on_close(mirror(bar(i, 60, 100, 100.4+(16-i)*.1, 99.6-(16-i)*.1, 100.1)))
        ctx.on_close(mirror(bar(17, 60, 100, 105, 100, 104)))
        sd = next(z for z in ctx.zones if z.kind == 'SD')
        self.assertEqual(sd.side, -1)
        self.assertAlmostEqual(sd.lo, 99.4)
        self.assertAlmostEqual(sd.hi, 100.6)

    def test_future_context_failure_does_not_mutate_ltf_history(self):
        engine = warm()
        before = len(engine.series.bars)
        engine.context.on_close(bar(10, 60))
        with self.assertRaisesRegex(ValueError, 'Future HTF'):
            engine.on_close(bar(14))
        self.assertEqual(len(engine.series.bars), before)

    def test_atr_matches_independent_batch_helper(self):
        series = r.Series()
        random.seed(731)
        for i in range(200):
            o = 100 + random.random()*10
            series.append(bar(i, o=o, h=o+3, lo=o-2, c=o+1))
            expected = wilder_atr(series.ranges)[-1]
            if expected is None:
                self.assertIsNone(series.atr)
            else:
                self.assertAlmostEqual(series.atr, expected, places=12)

    def test_bad_input_and_observation_only_timeframes(self):
        series = r.Series()
        for invalid in [replace(bar(0), high=math.nan), replace(bar(0), low=110), replace(bar(0), end=BASE)]:
            with self.assertRaises(ValueError):
                series.append(invalid)
        self.assertEqual(series.bars, [])
        series.append(bar(0))
        with self.assertRaises(ValueError):
            series.append(bar(0))
        ctx = self.context()
        for minutes in (1, 15, 60, 240):
            with self.assertRaises(ValueError):
                r.EntryEngine(ctx, minutes)

    def test_replay_does_not_consume_future_htf(self):
        htf = [bar(i, 60) for i in range(20)]
        ltf = [bar(i) for i in range(25)]
        ctx = r.Context('OANDA:XAUUSD', 60, .01)
        r.replay(ctx, 5, htf, ltf)
        self.assertEqual(len(ctx.series.bars), 2)


class PineArtifactChecks(unittest.TestCase):
    def test_bundle_is_reproducible_and_does_not_claim_native_compile(self):
        a, b = build(), build()
        self.assertEqual(a['sha256'], b['sha256'])
        self.assertEqual(a['native_compile'], 'NOT_RUN')
        self.assertEqual(len(a['inputs']), len(FRAGMENTS))
        code = (ROOT / a['output']).read_text(encoding='utf-8')
        self.assertEqual(code.count('//@version=6'), 1)
        self.assertNotIn('strategy.entry', code)
        self.assertIn('varip string lastConfirmedAlert', code)
        self.assertIn('if canSignal and barstate.isconfirmed', code)
        self.assertNotIn('string text =', code)  # Native Pine reserves the text namespace.

    def test_every_security_packet_field_has_same_one_bar_offset(self):
        code = (ROOT / 'src/intraday/context.pine').read_text(encoding='utf-8')
        returned = next(line.strip() for line in code.splitlines() if line.strip().startswith('[time[1]'))
        fields = returned[1:-1].split(', ')
        self.assertEqual(len(fields), 18)
        self.assertTrue(all(field.endswith('[1]') or field == 'time[3]' for field in fields))
        self.assertEqual(code.count('lookahead = barmerge.lookahead_on'), 4)
        self.assertNotIn('barstate.isconfirmed', code)


if __name__ == '__main__':
    unittest.main()
