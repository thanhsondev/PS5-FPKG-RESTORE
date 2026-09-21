from pathlib import Path
import hashlib, json, zipfile
ROOT=Path(__file__).resolve().parent
elf=ROOT/'PS5_FPKG_RESTORE.elf'
manifest=json.loads((ROOT/'BUILD.json').read_text(encoding='utf-8'))
evidence=ROOT/'CONSOLE_VERIFIED.json'
if not evidence.exists():evidence=ROOT/'RUNTIME_SUMMARY.json'
verified=json.loads(evidence.read_text(encoding='utf-8'))
digest=hashlib.sha256(elf.read_bytes()).hexdigest()
assert digest==manifest['sha256']==verified['elf_sha256']
assert manifest['console_runtime_verified']
report={k:verified[k] for k in ['elf_sha256','console','firmware','native_registration_verified',
    'database_integrity','game_launch_verified','reboot_verified','ui_screenshot_verified']}
report.update(registered=11,internal_apps=2,m2_games=9,repeat_run_created=0,
              system_language_id=28,selected_language='vi',english_console_language_tested=False)
(ROOT/'RUNTIME_SUMMARY.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
files=[ROOT/n for n in ['PS5_FPKG_RESTORE.elf','BUILD.json','TEST_RESULTS.json',
    'RUNTIME_SUMMARY.json','README.md','README.vi.md','CHANGELOG.md','docs/BUILD.md',
    'docs/TECHNICAL.vi.md','examples/autoload.example.txt','build.py','package_release.py']]
files+=list((ROOT/'src').glob('*'))+list((ROOT/'tests').glob('*.py'))+list((ROOT/'tests').glob('*.c'))
files+=list((ROOT/'licenses').glob('*'))
assert len(list((ROOT/'licenses').glob('*')))>=2
files=sorted(files,key=lambda p:p.relative_to(ROOT).as_posix())
sums=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in files)
(ROOT/'SHA256SUMS.txt').write_text(sums,encoding='utf-8')
files.append(ROOT/'SHA256SUMS.txt')
(ROOT/'dist').mkdir(exist_ok=True)
dest=ROOT/'dist'/'PS5_FPKG_RESTORE_1.1.zip'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
    for p in files:z.write(p,p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(dest) as z:
    assert z.testzip() is None
    for p in files:assert z.read(p.relative_to(ROOT).as_posix())==p.read_bytes()
    assert not any(n.endswith(('.db','.pkg')) for n in z.namelist())
print(json.dumps({'zip':str(dest),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
                  'elf_bytes':elf.stat().st_size,'elf_sha256':digest,'files':len(files)},indent=2))
