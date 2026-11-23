"""Build the observation-only derivative; reuse HTF modules without the entry engine."""
import hashlib
import json
from workspace import ROOT, sha

FRAGMENTS = ('src/lux_custom/config.pine', 'src/intraday/context.pine',
             'src/intraday/zones.pine', 'src/lux_custom/structure.pine',
             'src/lux_custom/regions.pine', 'src/lux_custom/assessment.pine',
             'src/lux_custom/ui.pine')
OUTPUT = ROOT / 'dist/lux_custom/SMC_ICT_OBSERVER.pine'


def build():
    inputs = {name: sha(ROOT / name) for name in FRAGMENTS}
    fingerprint = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    token = int(fingerprint[:12], 16)
    parts = []
    for name in FRAGMENTS:
        part = (ROOT / name).read_text(encoding='utf-8')
        if name == 'src/intraday/zones.pine':
            assert '\nf_contact(' in part
            part = part.split('\nf_contact(', 1)[0]  # Reuse ingestion only, exclude entry/target helpers.
        parts.append(part.rstrip())
    code = '\n\n'.join(parts) + '\n'
    assert code.startswith('//@version=6') and code.count('//@version=') == 1
    assert all(value not in code for value in ['strategy(', 'strategy.entry', 'f_evaluate(', 'f_target(', 'reward_risk', 'Setup.new', 'BUY', 'SELL'])
    lines = code.splitlines()
    lines.insert(2, f'int BUILD_TOKEN = {token}')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    result = {'status': 'OBSERVATION_ONLY_EXPERIMENTAL', 'inputs': inputs, 'build_token': token,
              'source_fingerprint': fingerprint, 'output': OUTPUT.relative_to(ROOT).as_posix(),
              'sha256': sha(OUTPUT), 'lines': len(lines), 'license': 'CC-BY-NC-SA-4.0',
              'native_compile': 'SEE_HASH_PINNED_VALIDATION', 'native_runtime': 'SEE_HASH_PINNED_VALIDATION',
              'validation_evidence': 'evidence/lux_custom/native-20261116.json',
              'fragment_slices': {'src/intraday/zones.pine': 'Before f_contact; zone ingestion only'},
              'chart_timeframes': ['5', '15', '60', '240'], 'entry_engine_included': False}
    OUTPUT.with_suffix('.build.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
