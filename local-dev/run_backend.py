"""PyCharm / Windows dev backend entry point."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import sitecustomize  # Loads only the protected deployment configuration.

if not os.getenv('MONGODB_URI'):
    raise RuntimeError('Database configuration missing. Run local-dev/configure_windows.py first.')
os.environ.setdefault('QUANTAXIS_ENV', 'dev')
os.environ.setdefault('QA_SCHEDULER_COLLECTION', 'jobs_dev')

from QUANTAXIS.QAWebServer.server import main

if __name__ == '__main__':
    main()
