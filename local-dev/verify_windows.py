"""Start both Windows entry points on temporary ports, verify them, then stop them."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

root = Path(__file__).resolve().parents[1]
runtime = Path(os.environ['LOCALAPPDATA']) / 'quantaxis-local'
opener = build_opener(ProxyHandler({}))
environment = dict(os.environ, PYTHONUTF8='1', PYTHONUNBUFFERED='1', QUANTAXIS_ENV='dev',
                   QA_SCHEDULER_COLLECTION='jobs_dev', QA_BACKEND_PORT='18010', QA_FRONTEND_PORT='18090')
processes = []
logs = []
try:
    for name, script, arguments in [('backend','run_backend.py',['--address=127.0.0.1','--port=18010']), ('frontend','run_frontend.py',[])]:
        log = (runtime / f'windows-{name}-verification.log').open('w', encoding='utf-8')
        logs.append(log)
        processes.append(subprocess.Popen([sys.executable, str(root/'local-dev'/script)] + arguments,
            cwd=root, env=environment, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW))
    deadline = time.monotonic() + 45
    while True:
        try:
            with opener.open('http://127.0.0.1:18090/api/readiness', timeout=2) as response:
                readiness = json.load(response)
            break
        except Exception:
            if any(process.poll() is not None for process in processes) or time.monotonic() >= deadline:
                raise RuntimeError('Windows verification failed; inspect windows-*-verification.log in the local runtime directory')
            time.sleep(0.25)
    assert readiness['mongodb_server'] == ['192.168.1.35', 27017], readiness
    assert readiness['debug'] and readiness['environment'] == 'dev', readiness
    with opener.open('http://127.0.0.1:18090/', timeout=5) as response:
        assert b'QUANTAXIS' in response.read()
    with opener.open('http://127.0.0.1:18090/api/qifis?action=accountlist', timeout=5) as response:
        accounts = json.load(response)
    receipt = {'status':'passed','interpreter':sys.executable,'python':sys.version.split()[0],
               'readiness':readiness,'accountlist':accounts,'temporary_ports':[18010,18090]}
    (root/'local-dev/verification-windows.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
finally:
    for process in processes:
        if process.poll() is None: process.terminate()
    for process in processes:
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill()
    for log in logs: log.close()
