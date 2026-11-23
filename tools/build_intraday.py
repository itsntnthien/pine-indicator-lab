"""Assemble the reviewed intraday fragments; never claim native Pine compilation."""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from workspace import ROOT, sha

FRAGMENTS = ('config.pine', 'context.pine', 'zones.pine', 'setup.pine', 'ui.pine')


def build():
    folder = ROOT / 'src/intraday'
    parts = [(name, (folder / name).read_text(encoding='utf-8')) for name in FRAGMENTS]
    inputs = {str((folder / name).relative_to(ROOT)).replace('\\', '/'): sha(folder / name) for name in FRAGMENTS}
    fingerprint = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    token = int(fingerprint[:12], 16)
    content = '\n\n'.join(text.rstrip() for _, text in parts) + '\n'
    lines = content.splitlines()
    lines.insert(2, f'int BUILD_TOKEN = {token}')
    content = '\n'.join(lines) + '\n'
    if content.count('//@version=6') != 1 or not content.startswith('//@version=6'):
        raise ValueError('Expected exactly one Pine v6 header')
    if 'strategy(' in content or 'strategy.entry' in content:
        raise ValueError('This artifact is an indicator, not an execution strategy')
    output = ROOT / 'dist/intraday/ICT_INTRADAY_EXPERIMENTAL.pine'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding='utf-8', newline='\n')
    manifest = {
        'status': 'EXPERIMENTAL_NOT_TRADING_CERTIFIED',
        'built_utc': datetime.now(timezone.utc).isoformat(),
        'inputs': inputs, 'build_token': token, 'source_fingerprint': fingerprint,
        'output': output.relative_to(ROOT).as_posix(), 'sha256': sha(output),
        'native_compile': 'NOT_RUN', 'native_runtime': 'NOT_RUN', 'native_parity': 'NOT_RUN',
        'feeds': ['OANDA:XAUUSD', 'FOREXCOM:NAS100'], 'entry_pairs': {'5': '60', '15': '240'},
    }
    output.with_suffix('.build.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(output), 'sha256': manifest['sha256'], 'lines': len(content.splitlines())}, ensure_ascii=False))
    return manifest


if __name__ == '__main__':
    build()
