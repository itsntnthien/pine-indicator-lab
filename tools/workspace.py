"""Shared path and hashing helpers for the curated repository.

Preserved from the original workspace tooling; migration/archive commands are
intentionally outside this export. Use the individual build_*.py entry points.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def local(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('Catalog path leaves workspace')
    return path


def load(name):
    return json.loads((ROOT / "catalog" / name).read_text(encoding="utf-8"))
