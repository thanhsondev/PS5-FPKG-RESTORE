# Build & Test

## Requirements / Yêu cầu

- Python 3
- LLVM `clang`, `ld.lld`, `llvm-strip` on `PATH` (tested with LLVM-MinGW on Windows, clang 22.1.8)
- PS5 payload SDK — tested with `pacbrew-repo v0.40.2` (`ps5-payload-dev.tar.gz`,
  sha256 `a85f65de418a8e6a898c6c3e3c870d50fff7618a200e4dd59ea9692af6ecec4d`), containing:
  - `target/include`, `target/lib/crt1.o`, `libkernel_sys*` and system `Sce*` libraries
  - `target/user/homebrew/include/json-c`, `target/user/homebrew/lib/libjson-c.a`
  - `ldscripts/elf_x86_64.x`

`build.py` does not download the SDK or install a compiler.

## Build

```powershell
# Windows PowerShell
$env:PS5_SDK = 'D:\path\to\sdk'
python .\build.py
```

```sh
# macOS / Linux
PS5_SDK=/path/to/sdk python3 build.py
```

Output:

| File | Description |
|---|---|
| `PS5_FPKG_RESTORE.elf` | Stripped payload |
| `BUILD.json` | ELF layout, hashes, compiler and SDK info |
| `build/PS5_FPKG_RESTORE.debug.elf` | Unstripped ELF with debug info |
| `build/payload.map` | Linker map |

An existing ELF is kept as `build/previous-<sha256>.elf`. After a new build `console_runtime_verified`
is reset to `false` — the new ELF must be tested on a console again.

## Parser tests (host)

```sh
python tests/test_parser.py                      # 13 generic cases
python tests/test_parser.py --recovered <dir>    # + fixtures from real metadata (22 cases in the release)
```

Results are written to `TEST_RESULTS.json`. Fixtures are repacked metadata, not full game packages.

## Console verification (development only)

Requires FTP on port 2121 and the web ELF launcher on port 8080.

```sh
python tests/console_verify.py --host <PS5_IP> --run   # back up app.db/appinfo.db, upload and RUN the payload
python tests/console_verify.py --host <PS5_IP>         # fetch restore.log and the databases after the run
python tests/check_console_results.py                  # regression check for the 11-title test console
```

`--run` never launches a game. FTP database copies are diagnostic snapshots, not a consistent backup.
`check_console_results.py` is specific to the test console (11 titles) — it is not a list of supported games.

## Packaging a release

```sh
python package_release.py
```

Checks that the ELF hash matches `BUILD.json` and the runtime evidence, regenerates `SHA256SUMS.txt`
and writes `dist/PS5_FPKG_RESTORE_1.1.zip` (refuses to include `.db` or `.pkg` files).
