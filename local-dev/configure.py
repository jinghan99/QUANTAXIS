"""Configure isolated user services. Run this with the local WSL venv Python."""
import json
import argparse
import secrets
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--profile', choices=['dev', 'prod'], default='dev')
PROFILE = parser.parse_args().profile
DEV_ROOT = Path(__file__).resolve().parents[1]
ROOT = DEV_ROOT if PROFILE == 'dev' else DEV_ROOT.parent / 'QUANTAXIS-prod'
RUNTIME = Path.home() / ".local/share/quantaxis-local"
VENV = RUNTIME / 'venv' if PROFILE == 'dev' else RUNTIME / 'prod/venv'
LOGS = RUNTIME / PROFILE / 'logs'
LOGS.mkdir(parents=True, exist_ok=True)
BACKEND_PORT = 18089
FRONTEND_PORT = 8080 if PROFILE == 'dev' else 8081
FRONTEND_SOURCE = ROOT.parent / ('qamazing_community' if PROFILE == 'dev' else 'qamazing_community-prod')
UNITS = Path.home() / ".config/systemd/user"
RUNTIME.mkdir(parents=True, exist_ok=True)
UNITS.mkdir(parents=True, exist_ok=True)
for name in ("mongodb-data", "logs", "notebooks", "jupyter-runtime"):
    (RUNTIME / name).mkdir(exist_ok=True)

# Only this private venv loads the deployment bootstrap (including Jupyter kernels).
(VENV / "lib/python3.11/site-packages/quantaxis_local.pth").write_text(str(ROOT / "local-dev") + "\n")

jupyter_config = RUNTIME / "jupyter_config.py"
if not jupyter_config.exists():
    token = secrets.token_urlsafe(32)
    jupyter_config.write_text(
        "c = get_config()\n"
        "c.ServerApp.ip = '127.0.0.1'\n"
        "c.ServerApp.port = 8888\n"
        "c.ServerApp.port_retries = 0\n"
        "c.ServerApp.open_browser = False\n"
        f"c.ServerApp.root_dir = {str(ROOT)!r}\n"
        f"c.IdentityProvider.token = {token!r}\n"
        f"c.ServerApp.runtime_dir = {str(RUNTIME / 'jupyter-runtime')!r}\n",
        encoding="utf-8",
    )
    jupyter_config.chmod(0o600)
    access = RUNTIME / "jupyter-url.txt"
    access.write_text(f"http://localhost:8888/lab?token={token}\n")
    access.chmod(0o600)

services = {
    "backend": (f"{VENV}/bin/qawebserver --address=127.0.0.1 --port={BACKEND_PORT}", ""),
    "frontend": (f"{VENV}/bin/python {ROOT}/local-dev/frontend.py", "backend"),
}
if PROFILE == 'dev':
    services['jupyter'] = (f"{VENV}/bin/jupyter lab --config={jupyter_config}", '')

for name, (command, dependency) in services.items():
    depends = f"Requires=quantaxis-{PROFILE}-{dependency}.service\nAfter=quantaxis-{PROFILE}-{dependency}.service\n" if dependency else ""
    (UNITS / f"quantaxis-{PROFILE}-{name}.service").write_text(
        f"[Unit]\nDescription=QUANTAXIS {PROFILE} {name}\n{depends}\n"
        f"[Service]\nType=simple\nWorkingDirectory={ROOT}\nExecStart={command}\n"
        "Environment=PYTHONUNBUFFERED=1\n"
        f"Environment=QUANTAXIS_ENV={PROFILE}\nEnvironment=QA_SCHEDULER_COLLECTION=jobs_{PROFILE}\n"
        f"Environment=QA_FRONTEND_PORT={FRONTEND_PORT}\nEnvironment=QA_BACKEND_PORT={BACKEND_PORT}\n"
        f"Environment=QA_FRONTEND_SOURCE={FRONTEND_SOURCE}\n"
        "Environment=TZ=Asia/Shanghai\nRestart=on-failure\nRestartSec=5\n"
        f"StandardOutput=append:{LOGS}/{name}.service.log\n"
        f"StandardError=append:{LOGS}/{name}.service.log\nTimeoutStopSec=30\n"
        "\n[Install]\nWantedBy=default.target\n", encoding="utf-8"
    )
subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
print(f"{PROFILE} user services configured; source: {ROOT}")
