"""Check tracked export scope, common secret patterns, links and Pine manifests."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = {'.env', 'runtime', 'node_modules', '.venv', 'archive',
           'chart-workspace', 'local-terminal', '.playwright-cli'}
SECRET_PATTERNS = [
    re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),
    re.compile(r'github_pat_[A-Za-z0-9_]{40,}'),
    re.compile(r'AKIA[0-9A-Z]{16}'),
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----\s+[A-Za-z0-9+/=]{32,}'),
]


def content_findings(relative, content):
    path = PurePosixPath(relative)
    findings = []
    if path.parts[0].lower() == 'data' or any(part.lower() in BLOCKED for part in path.parts):
        findings.append('outside Pine export scope')
    if path.name.lower().startswith('.env') or path.name.lower() in {
            'connection.json', 'api-key.txt', 'private-key.txt'}:
        findings.append('sensitive filename')
    if path.suffix.lower() in {'.pem', '.key', '.db', '.sqlite', '.csv', '.parquet', '.zip', '.pyc'}:
        findings.append('private/generated file type')
    if any(pattern.search(content) for pattern in SECRET_PATTERNS):
        findings.append('possible secret; value withheld')
    return findings


def verify_manifest(root, manifest_path):
    manifest = json.loads((root / manifest_path).read_text('utf-8'))
    artifact = (root / manifest_path).with_suffix('').with_suffix('.pine')
    if hashlib.sha256(artifact.read_bytes()).hexdigest() != manifest['sha256']:
        raise ValueError(f'Artifact hash mismatch: {artifact.name}')
    for relative, expected in manifest['inputs'].items():
        path = root / relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Stale build input: {relative}')


def main():
    top = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT, text=True).strip()
    if Path(top).resolve() != ROOT:
        raise SystemExit('Initialize the curated repository before running this check.')
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
    paths = [p for p in paths if p]
    if not paths:
        raise SystemExit('No tracked files; stage the curated export first.')
    errors = []
    for relative in paths:
        path = ROOT / relative
        data = path.read_bytes()
        content = data.decode('utf-8', errors='replace') if path.suffix not in {'.png', '.jpg'} else ''
        errors.extend(f'{relative}: {finding}' for finding in content_findings(relative, content))
        if len(data) > 5_000_000:
            errors.append(f'{relative}: exceeds 5 MB curated-file limit')
        if path.suffix == '.md':
            targets = re.findall(r'\]\(([^)]+)\)', content)
            targets += re.findall(r'<img[^>]+src="([^"]+)"', content)
            for target in targets:
                if target.startswith(('https:', 'http:', '#', 'mailto:')):
                    continue
                target = unquote(target.split('#', 1)[0])
                if target and not (path.parent / target).exists():
                    errors.append(f'{relative}: missing link target {target}')
    manifests = [
        'dist/intraday/ICT_INTRADAY_EXPERIMENTAL.build.json',
        'dist/lux_custom/SMC_ICT_OBSERVER.build.json',
        'dist/vsa_observer/VSA_OBSERVER_V3.build.json',
    ]
    for relative in manifests:
        try:
            verify_manifest(ROOT, relative)
        except (ValueError, KeyError, OSError) as error:
            errors.append(str(error))
    if errors:
        raise SystemExit('\n'.join(errors))
    print(json.dumps({'status': 'PASS', 'tracked_files': len(paths),
                      'pine_manifests': len(manifests),
                      'scope': 'Pine indicators and directly related tooling only'}))


if __name__ == '__main__':
    main()
