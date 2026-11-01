"""Real service and persisted-readback checks; retains an audit receipt in MongoDB."""
import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

parser = argparse.ArgumentParser()
parser.add_argument('--profile', choices=['dev', 'prod'], default='dev')
profile = parser.parse_args().profile
import QUANTAXIS as QA
from QUANTAXIS.QAUtil import DATABASE

port = 8080 if profile == 'dev' else 8081
with urlopen(f'http://127.0.0.1:{port}/api/readiness', timeout=10) as response:
    readiness = json.load(response)
assert readiness['environment'] == profile, readiness
assert readiness['mongodb_server'] == ['192.168.1.35', 27017], readiness
assert readiness['mongodb_database'] == 'quantaxis', readiness
assert readiness['debug'] == (profile == 'dev'), readiness
assert readiness['autoreload'] == (profile == 'dev'), readiness
assert readiness['scheduler_collection'] == 'jobs_' + profile, readiness
assert DATABASE.client.address == ('192.168.1.35', 27017)
receipt = {
    '_id': str(uuid.uuid4()), 'kind': 'deployment_readback', 'environment': profile,
    'created_at': datetime.now(timezone.utc).isoformat(), 'quantaxis': QA.__version__,
    'source': str(Path(QA.__file__).resolve()), 'python': sys.version.split()[0],
    'readiness': readiness,
}
DATABASE.deployment_checks.insert_one(receipt)
assert DATABASE.deployment_checks.find_one({'_id': receipt['_id']}) == receipt
with urlopen(f'http://127.0.0.1:{port}/api/qifis?action=accountlist', timeout=10) as response:
    receipt['accountlist'] = json.load(response)
with urlopen(f'http://127.0.0.1:{port}/api/scheduler/query', timeout=10) as response:
    receipt['scheduler'] = json.load(response)
receipt['write_readback'] = 'passed'
destination = Path(__file__).resolve().parent / f'verification-{profile}.json'
destination.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(receipt, ensure_ascii=False, indent=2))
