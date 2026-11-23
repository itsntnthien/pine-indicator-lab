"""Assemble the observation derivative of the user-supplied XAU-VSA indicator."""
import json
from workspace import ROOT, sha

FRAGMENTS = ('config', 'core', 'setup', 'ui', 'render')
OUTPUT = ROOT / 'dist/vsa_observer/VSA_OBSERVER_V3.pine'


def build():
    paths = [ROOT / f'src/vsa_observer/{name}.pine' for name in FRAGMENTS]
    source = '\n\n'.join(p.read_text('utf-8').rstrip() for p in paths) + '\n'
    assert source.count('//@version=') == 1
    for forbidden in ('strategy(', 'MainCandidate', 'ScalpEntrySetup', 'mainBuyEvent', 'mainSellEvent', '"BUY"', '"SELL"', 'varip '):
        assert forbidden not in source, forbidden
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(source, encoding='utf-8', newline='\n')
    manifest = {'sha256': sha(OUTPUT), 'lines': len(source.splitlines()),
                'inputs': {p.relative_to(ROOT).as_posix(): sha(p) for p in paths},
                'provenance': 'research/vsa-observer-20261117/provenance.json',
                'mode': 'OBSERVATION_ONLY', 'ui_attribution': 'docs/VSA_OBSERVER_LUX_UI_SOURCES.json',
                'validation': 'evidence/vsa_observer/v3-lux-system-acceptance.json'}
    OUTPUT.with_suffix('.build.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
