"""Migrate this deployment to the server's established Compose/bind-volume layout."""
import json
import subprocess
from pathlib import Path

files = {name: (Path(__file__).parent / "mongodb" / name).read_text() for name in ("docker-compose.yml", "init-user.js", ".env.example")}
remote = r'''
import datetime, json, os, pathlib, shutil, subprocess
from urllib.parse import urlparse
root=pathlib.Path('/vol2/1000/docker/mongodb')
old=pathlib.Path('/home/jinghan/services/mongodb')
if root.exists(): raise SystemExit('Target exists; inspect before migrating.')
root.mkdir(mode=0o700)
os.chown(root,1000,1001)
files=FILES
for name,content in files.items():
    target=root/name
    target.write_text(content)
    os.chown(target,1000,1001)
    target.chmod(0o644)
env=(old/'mongo.env').read_text()
client=json.loads((old/'client.json').read_text())
env+='MONGO_APP_PASSWORD='+urlparse(client['uri']).password+'\n'
for name,content in [('.env',env),('client.json',json.dumps(client))]:
    target=root/name
    target.write_text(content)
    os.chown(target,1000,1001)
    target.chmod(0o600)
compose=['docker','compose','-f',str(root/'docker-compose.yml')]
subprocess.run(compose+['config','--quiet'],check=True)
source=pathlib.Path(subprocess.check_output(['docker','volume','inspect','--format','{{.Mountpoint}}','common-mongodb-data'],text=True).strip())
if source!=pathlib.Path('/vol1/docker/volumes/common-mongodb-data/_data'):
    raise SystemExit('Unexpected data source; refusing migration.')
archive='common-mongodb-before-compose-'+datetime.datetime.now().strftime('%Y%m%d%H%M%S')
subprocess.run(['docker','stop','common-mongodb'],check=True)
subprocess.run(['docker','update','--restart=no','common-mongodb'],check=True)
subprocess.run(['docker','rename','common-mongodb',archive],check=True)
data=root/'data'
data.mkdir()
subprocess.run(['cp','-a',str(source)+'/.',str(data)+'/'],check=True)
subprocess.run(compose+['up','-d','--wait','--wait-timeout','90'],check=True)
(root/'migration-receipt.json').write_text(json.dumps({'preserved_container':archive,'preserved_volume':'common-mongodb-data','active_data':str(data)},indent=2))
print('Compose deployment ready: '+str(root))
print('Original container and volume preserved: '+archive)
'''.replace("FILES", repr(files))
subprocess.run(["ssh", "-o", "BatchMode=yes", "thousand-stock-server", "sudo python3 -"], input=remote, text=True, check=True)
