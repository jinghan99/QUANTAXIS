"""Make an explicit, fixed production source snapshot; never overwrite one."""
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = {'created_at': datetime.now(timezone.utc).isoformat(), 'sources': {}}
for name in ('QUANTAXIS', 'qamazing_community'):
    source = root.parent / name
    target = root.parent / (name + '-prod')
    if target.exists():
        raise SystemExit(f'Production snapshot already exists: {target}')
    tracked = subprocess.check_output(['git', '-C', str(source), 'ls-files', '-z']).decode().split('\0')
    files = {source / path for path in tracked if path and (source / path).is_file()}
    if name == 'QUANTAXIS':
        for extra in ('local-dev', 'strategies'):
            files.update(path for path in (source / extra).rglob('*') if path.is_file() and '__pycache__' not in path.parts)
    hashes = {}
    for path in sorted(files):
        relative = path.relative_to(source)
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        hashes[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest['sources'][name] = {'commit': subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD']).decode().strip(), 'files': hashes}
    print(f'Fixed source snapshot: {target} ({len(files)} files)')
(root.parent / 'QUANTAXIS-prod' / 'deployment-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
