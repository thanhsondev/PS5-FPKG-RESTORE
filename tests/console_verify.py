"""Explicit utility deployment/test. Does not launch any game or reboot."""
from pathlib import Path
from ftplib import FTP, error_perm
import argparse, urllib.request, urllib.parse, hashlib, io, json, datetime, sys
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--host',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
out=ROOT/'verification';out.mkdir(exist_ok=True)
f=FTP();f.connect(a.host,2121,timeout=20);f.login()
def get(path):
    b=io.BytesIO();f.retrbinary('RETR '+path,b.write);return b.getvalue()
if a.run:
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup=out/('before_'+stamp);backup.mkdir()
    for name in ['app.db','appinfo.db']:
        (backup/name).write_bytes(get('/system_data/priv/mms/'+name))
    remote='/data/ps5_storage_restore'
    try:f.mkd(remote)
    except error_perm:pass
    payload=(ROOT/'PS5_FPKG_RESTORE.elf').read_bytes()
    target=remote+'/PS5_FPKG_RESTORE.elf'
    try:old=get(target)
    except error_perm:old=None
    if old is not None:(backup/'previous_console.elf').write_bytes(old)
    f.storbinary('STOR '+target,io.BytesIO(payload))
    assert get(target)==payload
    f.quit()
    url='http://'+a.host+':8080/hbldr?'+urllib.parse.urlencode({'pipe':1,'daemon':1,'path':target})
    try:
        response=urllib.request.urlopen(url,timeout=45).read()
        (out/'launcher_response.txt').write_bytes(response)
        print(response.decode(errors='replace')[:1000])
    except Exception as e:print('Launcher response:',repr(e))
else:
    for remote,name in [('/data/ps5_storage_restore/restore.log','console.log'),
                        ('/system_data/priv/mms/app.db','after_app.db'),
                        ('/system_data/priv/mms/appinfo.db','after_appinfo.db')]:
        b=get(remote);(out/name).write_bytes(b)
        if name=='console.log':print(b.decode(errors='replace')[-18000:])
    f.quit()
