#!/usr/bin/env python3
"""Create a reviewable source submission without caches, secrets or git history."""
from pathlib import Path
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'release/bai7_submission.zip'
OUT.parent.mkdir(exist_ok=True)
files = []
for name in ['CMakeLists.txt','package.xml','README.md','LICENSE','.gitignore','requirements-voice.txt','requirements-gesture.txt']:
    files.append(ROOT/name)
for directory in ['scripts','launch','config','maps','urdf','worlds','tests','docs','pictures','videos']:
    for path in (ROOT/directory).rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc','.pyo'):
            files.append(path)
files = sorted(set(files))
manifest = ROOT/'docs/bai7/SHA256SUMS.txt'
files = [p for p in files if p != manifest]
manifest.write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT)}\n' for p in files))
files.append(manifest)
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for path in files:
        archive.write(path,Path('bai7_submission')/path.relative_to(ROOT))
with zipfile.ZipFile(OUT) as archive:
    assert archive.testzip() is None
print(f'{OUT}: {len(files)} files, {OUT.stat().st_size/1024/1024:.2f} MiB')
