"""Configure the dedicated Conda interpreter without putting credentials in the repo."""
import json
import os
import shutil
import site
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
if Path(sys.prefix).name != 'quantaxis':
    raise RuntimeError('Run this script using miniconda3/envs/quantaxis/python.exe')
runtime = Path(os.environ['LOCALAPPDATA']) / 'quantaxis-local'
runtime.mkdir(parents=True, exist_ok=True)
result = subprocess.run(['ssh','-o','BatchMode=yes','thousand-stock-server',
    'cat /vol2/1000/docker/mongodb/client.json'], capture_output=True, text=True, check=True)
data = json.loads(result.stdout)
(runtime / 'database.json').write_text(json.dumps(data), encoding='utf-8')
# This .pth belongs to the dedicated quantaxis environment, never stock/base.
packages = next(Path(path) for path in site.getsitepackages() if Path(path).name.lower() == 'site-packages')
(packages / 'quantaxis_local.pth').write_text(str(root / 'local-dev') + '\n', encoding='utf-8')
vendor = Path(r'\\wsl.localhost\Ubuntu-24.04\home\jinghan\.local\share\quantaxis-local\vendor')
if vendor.exists():
    shutil.copytree(vendor, runtime / 'vendor', dirs_exist_ok=True)
print('Windows database bootstrap and local frontend dependencies configured; credentials not printed.')
