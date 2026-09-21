from pathlib import Path
import json, hashlib, subprocess, shutil, os, struct
ROOT = Path(__file__).resolve().parent
SDK = Path(os.environ.get('PS5_SDK', r'D:\FDM\ShadowMount-build\sdk'))
class sdk:
    SYS = SDK / 'target'
    HB = SYS / 'user/homebrew'
    @staticmethod
    def tool(name):
        path=shutil.which(name)
        if not path: raise RuntimeError(f'Missing LLVM tool on PATH: {name}')
        return path
    @staticmethod
    def run(args):
        args=list(map(str,args));print(subprocess.list2cmdline(args),flush=True)
        subprocess.run(args,check=True)
    @staticmethod
    def compile_flags():
        return ['--no-default-config','--target=x86_64-sie-ps5',
                '-fvisibility-nodllstorageclass=default','-isystem',sdk.SYS/'include',
                '-fno-stack-protector','-fno-plt','-femulated-tls','-fPIC']
    @staticmethod
    def link_flags():
        return ['-m','elf_x86_64','-pie','-e','_start','-T',SDK/'ldscripts/elf_x86_64.x',
                '--eh-frame-hdr','-z','max-page-size=0x4000','-mllvm','-emulated-tls',
                '--hash-style=gnu','-L',sdk.SYS/'lib','-L',sdk.HB/'lib']
    @staticmethod
    def verify_elf(path):
        b=path.read_bytes()
        assert b[:6]==b'\x7fELF\x02\x01'
        assert struct.unpack_from('<HH',b,16)==(3,62)
        entry,phoff=struct.unpack_from('<QQ',b,24)
        stride,count=struct.unpack_from('<HH',b,54)
        assert stride>=56 and phoff+stride*count<=len(b)
        loads=[]
        for i in range(count):
            typ,flags,off,va,pa,fsz,msz,align=struct.unpack_from('<IIQQQQQQ',b,phoff+i*stride)
            assert off+fsz<=len(b)
            if typ==1:
                assert fsz<=msz
                loads.append(dict(offset=off,address=va,filesz=fsz,memsz=msz,flags=flags,alignment=align))
        assert any(x['address']<=entry<x['address']+x['memsz'] and x['flags']&1 for x in loads)
        result=dict(file=path.name,size=len(b),sha256=hashlib.sha256(b).hexdigest(),
                    entry=entry,program_headers=count,load_segments=loads)
        print(json.dumps(result,indent=2));return result
OUT = ROOT / 'build'
OUT.mkdir(exist_ok=True)
obj = OUT / 'storage_restore.o'
debug = OUT / 'PS5_FPKG_RESTORE.debug.elf'
elf = ROOT / 'PS5_FPKG_RESTORE.elf'
if elf.exists():
    old = hashlib.sha256(elf.read_bytes()).hexdigest()
    backup = OUT / f'previous-{old}.elf'
    if not backup.exists(): shutil.copyfile(elf, backup)
sdk.run([sdk.tool('clang'), *sdk.compile_flags(), '-isystem', sdk.HB / 'include',
         '-O2', '-g', '-Wall', '-Wextra', '-Werror', '-c', ROOT / 'src/storage_restore.c', '-o', obj])
sdk.run([sdk.tool('ld.lld'), *sdk.link_flags(), '-Map=' + str(OUT / 'payload.map'),
         '-o', debug, sdk.SYS / 'lib/crt1.o', obj, sdk.HB / 'lib/libjson-c.a',
         '-lc', '-lkernel_sys', '-lSceLibcInternal', '-lSceSystemService', '-lSceSysCore', '-lm'])
sdk.verify_elf(debug)
sdk.run([sdk.tool('llvm-strip'), '--strip-all', '-o', elf, debug])
manifest = sdk.verify_elf(elf)
manifest.update(version='1.1-EN-VI', compiler=subprocess.check_output([sdk.tool('clang'), '--version'], text=True).strip(),
    sdk_asset='pacbrew-repo/v0.40.2/ps5-payload-dev.tar.gz',
    sdk_sha256='a85f65de418a8e6a898c6c3e3c870d50fff7618a200e4dd59ea9692af6ecec4d',
    source_hashes={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [ROOT / 'build.py', *sorted((ROOT / 'src').glob('*'))]},
    console_runtime_verified=False, game_launch_verified=False, reboot_verified=False)
(ROOT / 'BUILD.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
