"""Run with Windows Python; uses the configured SSH alias and never prints credentials."""
import json
import subprocess

REMOTE = r'''
import json, os, secrets, subprocess
from pathlib import Path
root = Path.home() / 'services/mongodb'
if root.exists():
    raise SystemExit('Deployment directory already exists; inspect it before continuing.')
root.mkdir(parents=True, mode=0o700)
admin_password = secrets.token_urlsafe(36)
app_password = secrets.token_urlsafe(36)
env = root / 'mongo.env'
env.write_text('MONGO_INITDB_ROOT_USERNAME=mongo_admin\nMONGO_INITDB_ROOT_PASSWORD=' + admin_password + '\n')
env.chmod(0o600)
init = root / 'init.js'
init.write_text('db = db.getSiblingDB("admin"); db.createUser(' + json.dumps({
    'user': 'quantaxis', 'pwd': app_password,
    'roles': [{'role':'readWrite','db':name} for name in ['quantaxis','qascheduler','QAREALTIME']]
}) + ');\n')
init.chmod(0o644)  # Readable by the container UID; host parent directory remains 0700.
client = root / 'client.json'
client.write_text(json.dumps({'uri':'mongodb://quantaxis:' + app_password + '@192.168.1.35:27017/?authSource=admin&serverSelectionTimeoutMS=5000&connectTimeoutMS=5000', 'server':'192.168.1.35', 'database':'quantaxis'}))
client.chmod(0o600)
subprocess.run(['sudo','docker','volume','create','common-mongodb-data'], check=True)
subprocess.run(['sudo','docker','run','-d','--name','common-mongodb','--restart','unless-stopped',
    '--publish','192.168.1.35:27017:27017','--memory','2g','--cpus','2',
    '--log-driver','json-file','--log-opt','max-size=20m','--log-opt','max-file=3',
    '--env-file',str(env),'-v','common-mongodb-data:/data/db',
    '-v',str(init)+':/docker-entrypoint-initdb.d/10-user.js:ro',
    'mongo:7.0.45','--auth','--bind_ip_all'], check=True)
print('MongoDB deployed on 192.168.1.35:27017; credentials are in protected configuration files.')
'''
subprocess.run(["ssh", "-o", "BatchMode=yes", "thousand-stock-server", "python3 -"], input=REMOTE, text=True, check=True)
result = subprocess.run(["ssh", "-o", "BatchMode=yes", "thousand-stock-server", "cat /home/jinghan/services/mongodb/client.json"], capture_output=True, text=True, check=True)
json.loads(result.stdout)
INSTALL = r'''
import configparser, json, pathlib, sys
runtime=pathlib.Path.home()/'.local/share/quantaxis-local'
data=json.loads(sys.stdin.read())
target=runtime/'database.json'
target.write_text(json.dumps(data))
target.chmod(0o600)
settings=pathlib.Path.home()/'.quantaxis/setting/config.ini'
if settings.exists() and not (runtime/'config.before-remote.ini').exists():
    (runtime/'config.before-remote.ini').write_bytes(settings.read_bytes())
cfg=configparser.ConfigParser()
if settings.exists(): cfg.read(settings)
if not cfg.has_section('MONGODB'): cfg.add_section('MONGODB')
cfg.set('MONGODB','uri',data['uri'])
settings.parent.mkdir(parents=True,exist_ok=True)
with settings.open('w') as f: cfg.write(f)
settings.chmod(0o600)
print('Authenticated MongoDB client configured in WSL; credentials were not printed.')
'''
subprocess.run(["wsl", "-d", "Ubuntu-24.04", "--", "python3", "-c", INSTALL], input=result.stdout, text=True, check=True)
