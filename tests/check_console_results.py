from pathlib import Path
import sqlite3, json, re, hashlib, sys
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
ROOT=Path(__file__).resolve().parents[1]
v=ROOT/'verification'
log=(v/'console.log').read_text(encoding='utf-8')
last='START'+log.rsplit('START',1)[1]
assert 'END registered=11 found=11 skipped=0' in last,last
rows=re.findall(r'REGISTER (PPSA\d{5}) rc=0x00000000 mode=(\S+)',last)
assert len(rows)==11 and len(dict(rows))==11
db=sqlite3.connect(v/'after_app.db')
assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
info=sqlite3.connect(v/'after_appinfo.db')
assert info.execute('pragma integrity_check').fetchone()[0]=='ok'
tables=[r[0] for r in db.execute("select name from sqlite_master where name like 'tbl_iconinfo_%'")]
titles=[]
for title,mode in rows:
    row=db.execute('select * from tbl_contentinfo where titleId=?',(title,)).fetchone()
    assert row
    col=[d[0] for d in db.execute('select * from tbl_contentinfo limit 0').description]
    data=dict(zip(col,row))
    titles.append({'titleId':title,'titleName':data.get('titleName'),'mode':mode})
    for table in tables:
        icon=db.execute(f'SELECT visible,installStatus FROM "{table}" WHERE titleId=?',(title,)).fetchone()
        assert icon==(1,2),(title,table,icon)
report={'elf_sha256':hashlib.sha256((ROOT/'PS5_FPKG_RESTORE.elf').read_bytes()).hexdigest(),
        'console':'PS5 Pro','firmware':'10.01','native_registration_verified':True,
        'database_integrity':'ok','all_titles_visible_in_user_tables':tables,'titles':titles,
        'final_log':last,'game_launch_verified':False,'reboot_verified':False,
        'ui_screenshot_verified':False}
(ROOT/'CONSOLE_VERIFIED.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
manifest=json.loads((ROOT/'BUILD.json').read_text())
assert manifest['sha256']==report['elf_sha256']
manifest.update(console_runtime_verified=True,native_registration_verified=True,
                console_test_firmware='10.01',console_test_model='PS5 Pro')
(ROOT/'BUILD.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(titles,ensure_ascii=False,indent=2))
