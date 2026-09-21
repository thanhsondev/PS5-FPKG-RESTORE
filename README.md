# PS5 FPKG Restore

> A PS5 payload ELF that brings back every FPKG game installed on your external drive / M.2 SSD after a console restore — send the payload and your games reappear, **no reinstall needed**.

**English** · [Tiếng Việt](README.vi.md)

![Version](https://img.shields.io/badge/version-1.1-blue)
![Payload](https://img.shields.io/badge/PS5-payload%20ELF-black)
![Tested](https://img.shields.io/badge/tested-PS5%20Pro%20FW%2010.01-success)
![UI](https://img.shields.io/badge/notifications-EN%20%2F%20VI-orange)

**Authors:** Nguyễn Thanh Sơn & Ngô Phi Phương — [PSVIETHOA.COM](https://psviethoa.com)

## The problem

You installed a lot of FPKG games on an external drive or M.2 SSD. Then you restored the console, reset it,
or lost the system database: **the game data is still on the drive, but the home screen and Game Library are empty.**
Reinstalling every game one by one takes hours, plus the extra disk space and bandwidth.

## The solution

Send `PS5_FPKG_RESTORE.elf` to the console. The payload:

1. Scans internal storage `/user/app` and external drives `/mnt/ext0` … `/mnt/ext15`.
2. Finds every installed `PPSAxxxxx/app.pkg`, with no hardcoded game list.
3. Reads the public metadata inside the package (`param.json`, icons, backgrounds, sounds) and restores any missing files.
4. For games on an external drive, creates a **read-only** mount at `/user/app/<TITLEID>`. Internal games are used in place.
5. Calls the system's own installer service (AppInst) to **register each game again**.
6. Shows a *"Registered X/Y games/apps"* notification and exits.

Your games are back on the home screen and in the Game Library, and the data stays on the external drive.

<p align="center">
  <img src="docs/images/home-restored.jpg" width="49%" alt="Games back on the home screen">
  <img src="docs/images/notification.jpg" width="49%" alt="Registration notification">
</p>

## Highlights

- **No game list**: detects every PPSA title on the drives.
- **Data-safe**: never writes to `app.pkg`, never edits the SQLite databases directly, never deletes or overwrites folders that already hold data.
- **Idempotent**: run it as often as you like; a second run creates nothing new.
- **Automatic language**: Vietnamese notifications on a Vietnamese console, English otherwise.
- **Hardened PKG parser**: bounds checks, rejects encrypted/unknown entries, blocks path traversal; 22 test cases.

## Requirements

- A PS5 with a working payload/jailbreak environment and an ELF loader (tested with *Homebrew web launcher v0.30.1*).
- Games that were **already installed** on the drive, with their `PPSAxxxxx/app.pkg` folder still present.
- FTP access to copy the ELF to the console.

## Usage

1. Download `PS5_FPKG_RESTORE.elf` from [Releases](https://github.com/thanhsondev/PS5-FPKG-RESTORE/releases).
2. Start your payload environment and wait until the external drive / M.2 is mounted. Close any game and any install/update task.
3. Copy the ELF over FTP to `/data/ps5_storage_restore/PS5_FPKG_RESTORE.elf` (create the folder first if needed).
4. Run the ELF once with your ELF loader.
5. Wait for the **"Registered X/Y games/apps"** notification, then open the Game Library.

The log is written to `/data/ps5_storage_restore/restore.log`. Each run is delimited by `START` … `END`; check the last one.

> The on-screen notification title still reads **PS5 STORAGE RESTORE** and the log folder is `ps5_storage_restore`,
> because both are compiled into the 1.1 ELF.

### Run automatically on every boot

Mounts for external drives only last for the current session, so the payload must run again after every reboot.
With `ps5_autoloader`:

1. Back up `/data/ps5_autoloader/autoload.txt`.
2. Copy the ELF to `/data/ps5_autoloader/PS5_FPKG_RESTORE.elf`.
3. Add a `PS5_FPKG_RESTORE.elf` line **after** your base payloads and **before** `shadowmountplus.elf`.
   See [`examples/autoload.example.txt`](examples/autoload.example.txt). Merge it into your existing config; don't overwrite the whole file.
4. If you used the old `M2_RESTORE_PS5.elf` (hardcoded to 9 games), replace that line. Keep only one restore tool.

If the last run in the log shows `found=0`, the autoloader ran before the drive was mounted. Wait for the drive, then run the ELF again.

## Reading the log

| Log line | Meaning |
|---|---|
| `REGISTER … rc=0x00000000` | Registered successfully |
| `mode=internal-direct` | Internal storage game, registered in place |
| `mode=external-readonly` | External/M.2 game, registered through a read-only mount |
| `SKIP invalid/unsupported PKG table` | Unsupported package format or unreadable metadata table |
| `SKIP invalid param.json/titleId` | Broken `param.json`, or `titleId` does not match the folder name |
| `SKIP metadata conflict/write failed` | Existing `param.json` differs from the package, or a write error; data left untouched |
| `SKIP occupied/unowned destination` | `/user/app/<TITLEID>` already holds other data or a mount; never deleted |
| `MOUNT_FAILED` | Check payload privileges, drive status and current mounts |

No new `START` line means the payload never reached `main` or could not open the log folder.

## Scope & limitations

**Not supported:** downloaded PKGs that were never installed, PS4 `CUSA` titles, standalone DLC/updates, `app0` dumps,
or wiped/formatted drives. The payload does not launch games or reboot the console.

**Tested on PS5 Pro, FW 10.01:** 9 M.2 games + 2 internal apps (Netflix, YouTube), 11/11 registered with `rc=0`.
A second run created 0 files, both databases passed `PRAGMA integrity_check`, and the icons were visible for both users.

**Not yet verified:** launching games after registration, a clean reboot flow, a console set to English, other firmware versions.
Successful registration does not guarantee a game will start; that still depends on your runtime environment and the game itself.

## Uninstall / revert

Remove only the `PS5_FPKG_RESTORE.elf` line from `autoload.txt`, close any game, and reboot. Registered games stay in the library.

> ⚠️ **Never recursively delete `/user/app/PPSAxxxxx` while it is a mount pointing to the external drive** — that deletes the real game on the drive.

The payload has no uninstall or database rollback feature.

## Building from source

See [docs/BUILD.md](docs/BUILD.md). Detailed technical notes (Vietnamese): [docs/TECHNICAL.vi.md](docs/TECHNICAL.vi.md).

```
src/        storage_restore.c (scan, metadata, mount, AppInst, notifications) · pkg_reader.h (PKG parser)
tests/      parser tests and console deployment/verification scripts
examples/   autoload.txt fragment
licenses/   third-party licenses (json-c, PS5 payload SDK)
build.py    standalone build script
```

## Authors & credits

Developed by **Nguyễn Thanh Sơn** & **Ngô Phi Phương** — [PSVIETHOA.COM](https://psviethoa.com)

Technical references: [ShadowMountPlus](https://github.com/drakmor/ShadowMountPlus) ·
[LibProsperoPKG](https://github.com/SvenGDK/LibProsperoPKG) ·
[PS5 payload SDK](https://github.com/ps5-payload-dev/sdk) ·
[json-c](https://github.com/json-c/json-c) ·
[ps5-syslang](https://github.com/owendswang/ps5-syslang#languages)

This repository contains no game packages, extracted game artwork, or console databases. Use it only with content you legally own.
