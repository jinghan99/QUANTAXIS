"""Private venv bootstrap for the authenticated shared MongoDB instance."""
import json
import os
import sys
from pathlib import Path

_runtime = Path(os.environ['LOCALAPPDATA']) / 'quantaxis-local' if os.name == 'nt' else Path.home() / '.local/share/quantaxis-local'
if os.name == 'nt':
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, 'reconfigure'):
            _stream.reconfigure(encoding='utf-8')
_config = _runtime / 'database.json'
if _config.exists():
    _uri = json.loads(_config.read_text())["uri"]
    os.environ["MONGODB"] = _uri
    os.environ["MONGODB_URI"] = _uri
    # qaenv 0.0.4 otherwise prepends mongodb:// to an already complete URI.
    import qaenv
    qaenv.mongo_ip = _uri
    qaenv.mongo_uri = _uri
    qaenv.mongo_port = 27017
