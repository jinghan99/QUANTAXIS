"""QUANTAXIS interactive data-management CLI with the shared server configuration."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sitecustomize
from QUANTAXIS import QA_cmd

if __name__ == '__main__':
    QA_cmd()
