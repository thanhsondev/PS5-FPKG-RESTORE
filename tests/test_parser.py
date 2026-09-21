"""Exercise the actual C parser, including malformed untrusted metadata tables."""
from pathlib import Path
import json, struct, subprocess, shutil, tempfile, argparse
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--recovered', type=Path)
args = parser.parse_args()
exe = ROOT / 'build/pkg_probe.exe'
subprocess.run([shutil.which('clang'), '-O2', '-Wall', '-Wextra', '-Werror',
               str(ROOT / 'tests/pkg_probe.c'), '-o', str(exe)], check=True)
results = []
def make_pkg(items):
    base = 256
    names = bytearray(b'\0')
    positions = []
    for name, data, flags in items:
        positions.append(len(names)); names += name.encode() + b'\0'
    count = len(items)+1
    table_off = 128
    data_off = table_off + count*32
    table = bytearray(struct.pack('>8I', 0x200, 0, 0x40000000, 0, data_off, len(names), 0, 0))
    body = bytearray(names)
    for i, (name, data, flags) in enumerate(items):
        table += struct.pack('>8I', 0x1000+i, positions[i], flags, 0, data_off+len(body), len(data), 0, 0)
        body += data
    h = bytearray(base+table_off)
    h[:4] = b'\x7fFIH';struct.pack_into('<Q', h, 0x58, base)
    h[base:base+4] = b'\x7fCNT'
    struct.pack_into('>I', h, base+0x10, count)
    struct.pack_into('>I', h, base+0x18, table_off)
    return h+table+body
with tempfile.TemporaryDirectory() as tmp:
    sample = Path(tmp)/'fixture.pkg'
    def check(label, blob, expected, expected_names=None):
        sample.write_bytes(blob)
        p = subprocess.run([str(exe), str(sample)], capture_output=True, text=True)
        assert (p.returncode == 0) == expected, (label, p.returncode, p.stdout, p.stderr)
        if expected_names is not None:
            assert sorted(line.split()[0] for line in p.stdout.splitlines()) == sorted(expected_names), label
        results.append(label)
    param = b'{"titleId":"PPSA12345"}\n'
    good = make_pkg([('param.json',param,0),('icon0.png',b'png-data',0x08000000)])
    check('valid plaintext metadata',good,True,['param.json','icon0.png'])
    check('truncated header',good[:120],False)
    b=good.copy();b[0]=0;check('wrong FIH',b,False)
    b=good.copy();struct.pack_into('<Q',b,0x58,2**64-1);check('overflow CNT offset',b,False)
    b=good.copy();struct.pack_into('>I',b,256+0x10,65536);check('excessive entry count',b,False)
    b=good.copy();struct.pack_into('>I',b,384+32+16,0xffffffff);check('entry outside package',b,False)
    b=good.copy();struct.pack_into('>I',b,384+32+4,0xffffffff);check('invalid name offset',b,False)
    check('encrypted param rejected',make_pkg([('param.json',param,0x80000000)]),False)
    check('unknown metadata flags rejected',make_pkg([('param.json',param,0x100)]),False)
    check('duplicate param rejected',make_pkg([('param.json',param,0),('param.json',param,0)]),False)
    check('no param rejected',make_pkg([('icon0.png',b'png',0)]),False)
    check('path traversal ignored',make_pkg([('param.json',param,0),('../icon.png',b'x',0)]),True,['param.json'])
    check('encrypted optional image ignored',make_pkg([('param.json',param,0),('icon0.png',b'x',0x80000000)]),True,['param.json'])
    if args.recovered:
        rows=json.loads((args.recovered/'PACKAGES.json').read_text(encoding='utf-8'))
        for row in rows:
            folder=args.recovered/'metadata'/row['title_id'];items=[]
            for e in row['entries']:
                name=e['name'];path=folder/name
                if name and path.is_file() and path.suffix in ('.json','.dds','.png','.at9'):
                    items.append((name,path.read_bytes(),e['flags1']))
            check('recovered metadata '+row['title_id'],make_pkg(items),True,[x[0] for x in items])
(ROOT/'TEST_RESULTS.json').write_text(json.dumps({'passed':len(results),'cases':results,
    'scope':'Host execution of exact C PKG parser; fixtures use repacked metadata, not full game packages.'},indent=2),encoding='utf-8')
print(f'PASS: {len(results)} parser cases')
