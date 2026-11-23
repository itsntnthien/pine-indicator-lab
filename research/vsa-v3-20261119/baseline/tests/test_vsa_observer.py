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

    def test_native_regressions_bound_to_production_helpers(self):
        source = OUTPUT.read_text('utf-8')
        harness = (ROOT / 'tests/vsa_observer_native.pine').read_text('utf-8')
        for name in ('f_obs_vsa', 'f_obs_expired', 'f_obs_candle_direction'):
            self.assertGreater(source.count(name+'('), 1)
            self.assertIn(name+'(', harness)
        self.assertIn('runtime.error(', harness)
        self.assertNotIn('runtime.error(', source)

    def test_setup_harness_uses_shipped_logic(self):
        source = OUTPUT.read_text('utf-8')
        harness = (ROOT / 'tests/vsa_observer_setup_native.pine').read_text('utf-8')
        for name in ('f_setup_mask', 'f_setup_structure', 'f_setup_status'):
            self.assertGreater(source.count(name + '('), 1)
            self.assertIn(name + '(', harness)
        self.assertIn('record.update(', harness)
        self.assertIn('for bits = 0 to 127', harness)
        self.assertIn('for ageIndex = 0 to 3', harness)
        self.assertNotIn('SETUP_E2E_PASS', source)


if __name__ == '__main__':
    unittest.main()
