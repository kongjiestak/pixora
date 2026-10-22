"""Generate a private NVS image; never place upstream or administrator credentials here."""
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.config.stat().st_mode&0o077:parser.error('configuration must have private permissions (chmod 600)')
    try:
        data=json.loads(args.config.read_text())
        if not isinstance(data,dict) or set(data)-{'server','token','ssid','password'}:raise ValueError()
        server=data['server'].rstrip('/');token=data['token'];ssid=data.get('ssid','');password=data.get('password','')
        u=urlsplit(server)
        if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment or any(c.isspace() for c in server) or len(server)>240:raise ValueError()
        if not re.fullmatch(r'[A-Za-z0-9_-]{32,128}',token):raise ValueError()
        if not isinstance(ssid,str) or len(ssid.encode())>32 or not isinstance(password,str) or len(password.encode())>64:raise ValueError()
    except (ValueError,KeyError,TypeError,AttributeError):parser.error('invalid configuration (values suppressed)')
    root=Path(__file__).resolve().parents[3]
    if args.output.resolve().is_relative_to(root):parser.error('write private images outside the source repository')
    idf=Path(os.environ.get('IDF_PATH',''))
    generator=idf/'components/nvs_flash/nvs_partition_generator/nvs_partition_gen.py'
    if not generator.is_file():parser.error('activate ESP-IDF v5.5.5 first')
    os.umask(0o077);args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pixora-nvs-',dir=args.output.parent) as temp:
        csv_path=Path(temp)/'settings.csv'
        with csv_path.open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(['key','type','encoding','value']);writer.writerow(['pixora','namespace','',''])
            for k,v in [('server',server),('token',token),('ssid',ssid),('password',password)]:writer.writerow([k,'data','string',v])
        result=subprocess.run([sys.executable,str(generator),'generate',str(csv_path),str(args.output),'0x6000'],capture_output=True)
        if result.returncode:parser.error('NVS generation failed; private diagnostic output suppressed')
    args.output.chmod(0o600)
    print(json.dumps(dict(bytes=args.output.stat().st_size,sha256=hashlib.sha256(args.output.read_bytes()).hexdigest())))

if __name__=='__main__':main()
