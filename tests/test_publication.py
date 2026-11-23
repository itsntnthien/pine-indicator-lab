import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from verify_publication import content_findings, verify_manifest


class PublicationTests(unittest.TestCase):
    def test_blocks_apps_and_private_files(self):
        for path in ['chart-workspace/main.py', 'local-terminal/server.py',
                     'runtime/prices.json', 'data/prices.json', '.env.local', 'connection.json', 'bars.csv']:
            self.assertTrue(content_findings(path, ''), path)

    def test_normal_source_and_attribution_allowed(self):
        for path in ['src/intraday/config.pine', 'docs/LUX_CUSTOM_ATTRIBUTION.json',
                     'references/calibration/data/resampler.py']:
            self.assertEqual(content_findings(path, '// Read environment credentials at runtime.'), [])

    def test_secret_detection_does_not_echo_value(self):
        secret = 'gh' + 'p_' + 'X' * 36
        findings = content_findings('config.txt', secret)
        self.assertTrue(findings)
        self.assertNotIn(secret, str(findings))

    def test_manifest_rejects_modified_source_and_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source.pine'
            artifact = root / 'sample.pine'
            source.write_bytes(b'source')
            artifact.write_bytes(b'artifact')
            digest = lambda value: hashlib.sha256(value).hexdigest()
            (root / 'sample.build.json').write_text(json.dumps({
                'sha256': digest(b'artifact'), 'inputs': {'source.pine': digest(b'source')}
            }))
            verify_manifest(root, 'sample.build.json')
            source.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Stale build input'):
                verify_manifest(root, 'sample.build.json')
            source.write_bytes(b'source')
            artifact.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Artifact hash mismatch'):
                verify_manifest(root, 'sample.build.json')
