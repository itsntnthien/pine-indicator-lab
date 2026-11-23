from dataclasses import replace
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
from src.intraday.reference import Bar, Context
from src.lux_custom.reference import Observer, Pool, Region, Structure, assessment, pivots
from build_lux_custom import build, OUTPUT
from check_lux_custom import diagnostics


def bar(i, o=100, h=102, lo=98, c=100):
    return Bar(i*300000+1800000000000, (i+1)*300000+1800000000000, o, h, lo, c)


class ObservationTests(unittest.TestCase):
    def test_structure_initial_bos_choch_and_single_use(self):
        s = Structure(high=(1, 103), low=(2, 97))
        self.assertEqual(s.advance(bar(0, h=105, c=104), None, None)[:2], (1, 1))
        self.assertEqual(s.advance(bar(1, h=106, c=105), None, None)[0], 0)
        s.advance(bar(2), (3, 104), None)
        self.assertEqual(s.advance(bar(3, h=106, c=105), None, None)[:2], (1, 2))
        self.assertEqual(s.advance(bar(4, lo=95, c=96), None, None)[:2], (-1, 3))

    def test_new_pivot_cannot_create_same_bar_break(self):
        s = Structure()
        self.assertEqual(s.advance(bar(0, h=105, c=104), (1, 103), None)[0], 0)
        self.assertEqual(s.advance(bar(1, h=105, c=104), None, None)[0], 1)

    def test_pivot_delay_and_first_equal_anchor(self):
        bars = [bar(i, h=h) for i, h in enumerate([101, 102, 105, 105, 103, 102])]
        self.assertIsNone(pivots(bars[:4], 2)[0])
        self.assertEqual(pivots(bars[:5], 2)[0], (bars[2].time, 105))
        self.assertIsNone(pivots(bars, 2)[0])

    def test_two_sided_sweep_is_explicit_and_not_repeated(self):
        o = Observer(.01)
        o.pools = [Pool(99, 1, 1, -1), Pool(101, -1, 2, -1)]
        self.assertEqual(o.on_close(bar(0))['sweep_mask'], 3)
        self.assertEqual(o.on_close(bar(1))['sweep_mask'], 0)
        self.assertEqual(o.pools, [])

    def test_exact_touch_is_not_sweep_and_break_consumes_pool(self):
        o = Observer(.01)
        o.pools = [Pool(99, 1, 1, -1)]
        self.assertEqual(o.on_close(bar(0, lo=99))['sweep_mask'], 0)
        self.assertEqual(len(o.pools), 1)
        self.assertEqual(o.on_close(bar(1, lo=98, c=98.5))['sweep_mask'], 0)
        self.assertEqual(o.pools, [])

    def test_region_no_creation_bar_fill_then_inverts_once(self):
        z = Region('FVG', 1, 99, 101, 1, 0, 0)
        self.assertEqual(z.advance(bar(0, lo=95, c=96), 0), (True, False))
        self.assertEqual(z.stage, 0)
        self.assertEqual(z.advance(bar(1), 1), (True, False))
        self.assertEqual(z.stage, 2)
        self.assertEqual(z.advance(bar(2, lo=95, c=96), 2), (True, True))
        self.assertEqual((z.kind, z.side, z.available, z.stage), ('IFVG', -1, 2, 0))
        self.assertEqual(z.advance(bar(3, h=104, c=103), 3), (False, False))

    def test_bearish_ob_breaker_and_absolute_expiry(self):
        z = Region('OB', -1, 99, 101, 1, 0, 0)
        self.assertEqual(z.advance(bar(1, h=104, c=103), 1), (True, True))
        self.assertEqual((z.kind, z.side), ('BRK', 1))
        self.assertEqual(z.advance(bar(200), 200), (False, False))

    def test_empty_arrays_and_atr_warmup(self):
        o = Observer(.01)
        for i in range(13):
            o.on_close(bar(i, o=100+i*5, h=104+i*5, lo=99+i*5, c=103+i*5))
            self.assertEqual(o.regions, [])
        o.on_close(bar(13, o=165, h=169, lo=164, c=168))
        self.assertTrue(o.regions)
        self.assertTrue(all(z.stage == 0 for z in o.regions))

    def test_future_htf_rejected_without_mutation(self):
        o = Observer(.01)
        ctx = Context('OANDA:XAUUSD', 60, .01)
        ctx.on_close(bar(0))
        with self.assertRaisesRegex(ValueError, 'not available'):
            o.on_close(bar(0), ctx)
        self.assertEqual(o.series.bars, [])
        o.on_close(bar(1), ctx)

    def test_assessment_conflicts_override_alignment(self):
        self.assertIn('trái hướng', assessment(1, -1, 1, 1))
        self.assertIn('nhiễu', assessment(1, 1, 1, 1, 3))
        self.assertIn('chưa xác lập', assessment(0, 0, 1, 1))
        self.assertIn('không diễn giải', assessment(1, 1, 1, 1, available=False))
        self.assertIn('ngược', assessment(1, 1, -1, 1))
        self.assertIn('cùng hướng', assessment(1, 0, 1, 1))

    def test_prefix_replay_and_bounded_storage(self):
        rng = random.Random(114)
        bars = []
        price = 2000
        for i in range(600):
            previous, price = price, price+rng.uniform(-8, 8)
            bars.append(bar(i, previous, max(previous, price)+rng.random()*3, min(previous, price)-rng.random()*3, price))
        full = Observer(.01)
        for b in bars:
            full.on_close(b)
            self.assertLessEqual(len(full.pools), 40)
            self.assertLessEqual(len(full.regions), 64)
        for cutoff in (50, 173, 599):
            partial = Observer(.01)
            for b in bars[:cutoff]:
                partial.on_close(b)
            self.assertEqual(partial.observations, full.observations[:cutoff])
        self.assertTrue(any(x['swing_break'] == 1 for x in full.observations))
        self.assertTrue(any(x['swing_break'] == -1 for x in full.observations))

    def test_invalid_inputs_fail_before_history_changes(self):
        with self.assertRaises(ValueError):
            Observer(float('nan'))
        o = Observer(.01)
        with self.assertRaises(ValueError):
            o.on_close(replace(bar(0), low=110))
        self.assertEqual(o.series.bars, [])


class ArtifactTests(unittest.TestCase):
    def test_pine_analyzer_checks_nested_errors_not_only_success_flag(self):
        errors = [{'message': 'Undeclared identifier'}]
        self.assertEqual(diagnostics({'success': True, 'result': {'errors2': errors}}), errors)
        self.assertEqual(diagnostics({'success': True, 'result': {'types': []}}), [])
        with self.assertRaises(ValueError):
            diagnostics({'success': False})

    def test_reproducible_observation_only_build(self):
        a, b = build(), build()
        self.assertEqual(a['sha256'], b['sha256'])
        self.assertFalse(a['entry_engine_included'])
        source = OUTPUT.read_text(encoding='utf-8')
        for forbidden in ('BUY', 'SELL', 'f_target(', 'f_evaluate(', 'strategy.', 'Setup.new', 'f_rr('):
            self.assertNotIn(forbidden, source)
        self.assertEqual(source.count('//@version=6'), 1)

    def test_new_algorithms_do_not_depend_on_visual_toggles(self):
        for name in ('structure', 'regions', 'assessment'):
            source = (ROOT / f'src/lux_custom/{name}.pine').read_text(encoding='utf-8')
            self.assertNotIn('lxShow', source)
        source = (ROOT / 'src/lux_custom/assessment.pine').read_text(encoding='utf-8')
        self.assertIn('[high[1], low[1]]', source)
        self.assertIn('America/New_York', source)
        self.assertNotIn('"UTC-5"', source)
        self.assertIn('h1Request == "60" and h4Request == "240" and contextConflict', source)


if __name__ == '__main__':
    unittest.main()
