import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_vsa_observer import build, OUTPUT


class ObserverBuildTests(unittest.TestCase):
    def test_reproducible_observation_build(self):
        first = build()
        self.assertEqual(first, build())
        source = OUTPUT.read_text('utf-8')
        self.assertNotIn('strategy(', source)
        self.assertNotIn('MainCandidate', source)
        self.assertNotIn('varip ', source)
        self.assertNotIn('"BUY"', source)
        self.assertNotIn('"SELL"', source)
        self.assertEqual(source.count('alertcondition('), 3)

    def test_original_archive_unchanged(self):
        archive = ROOT / 'research/vsa-observer-20261117'
        provenance = json.loads((archive / 'provenance.json').read_text('utf-8'))
        self.assertEqual(hashlib.sha256((archive / 'original.pine').read_bytes()).hexdigest(), provenance['original_sha256'])

    def test_frozen_v2_unchanged_and_drawing_limits_not_state_limits(self):
        baseline=ROOT/'research/vsa-v3-20261119/baseline'
        for relative,digest in json.loads((baseline/'manifest.json').read_text()).items():
            self.assertEqual(hashlib.sha256((baseline/relative).read_bytes()).hexdigest(),digest)
        self.assertEqual(hashlib.sha256((ROOT/'dist/vsa_observer/XAU_VSA_OBSERVER.pine').read_bytes()).hexdigest(),
                         '78b389c46aba4164437605c5f8230c460062ebff76eb6f8ea98455203555a316')
        core=(ROOT/'src/vsa_observer/core.pine').read_text('utf8')
        for name in ['smcLiquidityDisplayLimit','smcFvgDisplayLimit','smcObDisplayLimit','showOnlyActiveZones']:
            self.assertNotIn(name,core)
        render=(ROOT/'src/vsa_observer/render.pine').read_text('utf8')
        self.assertNotIn('line.delete',render)
        self.assertNotIn('box.delete',render)
        self.assertIn('f_ticks_to_price(event.price_ticks, syminfo.mintick)',render)
        self.assertIn('c16c02SwingHighSourceTime[1]',render)
        self.assertIn('c16c02SwingLowSourceTime[1]',render)

    def test_v2_tools_refuse_v3_oracle(self):
        from tools.build_vsa_v2_parity import build as v2_parity
        from tools.research_vsa_v2 import run as v2_study
        for action in [v2_parity,v2_study]:
            with self.assertRaisesRegex(RuntimeError,'v2 .*frozen'):
                action()

    def test_native_regressions_bound_to_production_helpers(self):
        source = OUTPUT.read_text('utf-8')
        harness = (ROOT / 'tests/vsa_observer_native.pine').read_text('utf-8')
        for name in ('f_obs_vsa', 'f_obs_expired', 'f_obs_candle_direction'):
            self.assertGreater(source.count(name+'('), 1)
            self.assertIn(name+'(', harness)
        self.assertIn('runtime.error(', harness)
        self.assertEqual(source.count('runtime.error("V3 invariant:'), 3)

    def test_setup_harness_uses_shipped_logic(self):
        source = OUTPUT.read_text('utf-8')
        harness = (ROOT / 'tests/vsa_observer_setup_native.pine').read_text('utf-8')
        for name in ('f_setup_mask', 'f_setup_structure', 'f_setup_has'):
            self.assertGreater(source.count(name + '('), 1)
            self.assertIn(name + '(', harness)
        self.assertIn('record.update(', harness)
        self.assertIn('for bits = 0 to 127', harness)
        self.assertIn('for ageIndex = 0 to 3', harness)
        self.assertNotIn('SETUP_E2E_PASS', source)


if __name__ == '__main__':
    unittest.main()
