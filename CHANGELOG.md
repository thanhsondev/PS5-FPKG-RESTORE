# Changelog — PS5 FPKG Restore

## 1.1 — EN/VI

- Generic scan of `/user/app` and `/mnt/ext0` … `/mnt/ext15`; no hardcoded title list or package sizes
  (replaces the 9-title `M2_RESTORE_PS5.elf`).
- Internal storage titles registered directly; M.2/ext titles through read-only nullfs aliases.
- Bounded PKG metadata parser with 22 host test cases.
- Automatic Vietnamese/English notifications from the system language (ID 28 → Vietnamese).
- Verified on PS5 Pro FW 10.01: 11/11 titles registered (9 M.2 games + 2 internal apps), repeat run created 0 files.
