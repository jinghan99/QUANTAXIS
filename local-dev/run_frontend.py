"""PyCharm / Windows entry point for the upstream compiled community frontend."""
import os
import runpy
from pathlib import Path

os.environ.setdefault('QUANTAXIS_ENV', 'dev')
os.environ.setdefault('QA_FRONTEND_PORT', '8080')
os.environ.setdefault('QA_BACKEND_PORT', '18089')
runpy.run_path(str(Path(__file__).with_name('frontend.py')), run_name='__main__')
