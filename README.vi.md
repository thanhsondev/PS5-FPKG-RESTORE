# PS5 FPKG Restore

> Payload ELF khôi phục toàn bộ game FPKG đã cài trên ổ ngoài / SSD M.2 sau khi restore máy PS5 — gửi payload là game hiện lại, **không cần cài lại**.

[English](README.md) · **Tiếng Việt**

![Version](https://img.shields.io/badge/version-1.1-blue)
![Payload](https://img.shields.io/badge/PS5-payload%20ELF-black)
![Tested](https://img.shields.io/badge/tested-PS5%20Pro%20FW%2010.01-success)
![UI](https://img.shields.io/badge/th%C3%B4ng%20b%C3%A1o-VI%20%2F%20EN-orange)

**Tác giả:** Nguyễn Thanh Sơn & Ngô Phi Phương — [PSVIETHOA.COM](https://psviethoa.com)

## Vấn đề

Bạn cài hàng loạt game FPKG lên ổ ngoài / SSD M.2. Sau đó restore máy, reset hoặc mất database hệ thống:
**dữ liệu game vẫn nằm nguyên trên ổ, nhưng màn hình chính và Thư viện trò chơi trống trơn.**
Cài lại từng game thì mất hàng giờ, lại tốn chỗ và băng thông.

## Giải pháp

Gửi `PS5_FPKG_RESTORE.elf` vào máy. Payload sẽ:

1. Tự quét bộ nhớ trong `/user/app` và các ổ ngoài `/mnt/ext0` … `/mnt/ext15`.
2. Tìm mọi game đã cài dạng `PPSAxxxxx/app.pkg`, không cần danh sách game có sẵn.
3. Đọc metadata công khai trong gói (`param.json`, icon, ảnh nền, âm thanh), bổ sung file nào còn thiếu.
4. Với game trên ổ ngoài: tạo mount **chỉ đọc** vào `/user/app/<TITLEID>`. Với game ở bộ nhớ trong: dùng trực tiếp.
5. Gọi dịch vụ cài đặt của chính hệ thống (AppInst) để **đăng ký lại từng game**.
6. Gửi thông báo *"Đã đăng ký X/Y game/ứng dụng"* rồi thoát.

Game hiện lại ở màn hình chính và Thư viện, dữ liệu vẫn nằm trên ổ ngoài như cũ.

<p align="center">
  <img src="docs/images/home-restored.jpg" width="49%" alt="Game hiện lại ở màn hình chính">
  <img src="docs/images/notification.jpg" width="49%" alt="Thông báo đăng ký thành công">
</p>

## Điểm nổi bật

- **Không khóa danh sách game**: tự nhận mọi mã PPSA có trên ổ.
- **An toàn dữ liệu**: không ghi vào `app.pkg`, không sửa trực tiếp database SQLite, không xóa hay ghi đè thư mục đã có dữ liệu.
- **Chạy lại bao nhiêu lần cũng được**: lượt sau không tạo thêm file.
- **Tự chọn ngôn ngữ**: máy đặt tiếng Việt thì thông báo tiếng Việt, ngôn ngữ khác thì dùng English.
- **Bộ đọc PKG an toàn**: kiểm tra giới hạn, từ chối mục mã hóa/lạ, chặn path traversal; có 22 ca kiểm thử.

## Yêu cầu

- PS5 đã có môi trường payload/jailbreak và trình chạy ELF (máy thử dùng *Homebrew web launcher v0.30.1*).
- Game **đã từng được cài** trên ổ, còn thư mục `PPSAxxxxx/app.pkg`.
- FTP để chép file ELF vào máy.

## Cách dùng

1. Tải `PS5_FPKG_RESTORE.elf` ở mục [Releases](https://github.com/thanhsondev/PS5-FPKG-RESTORE/releases).
2. Bật môi trường payload, đợi ổ ngoài / M.2 được nhận. Đóng game và mọi tác vụ cài đặt/cập nhật.
3. Chép ELF qua FTP vào `/data/ps5_storage_restore/PS5_FPKG_RESTORE.elf` (tạo thư mục trước nếu chưa có).
4. Chạy ELF một lần bằng trình chạy ELF.
5. Đợi thông báo **"Đã đăng ký X/Y game/ứng dụng"**, rồi mở Thư viện trò chơi.

Log nằm ở `/data/ps5_storage_restore/restore.log`. Mỗi lượt chạy có `START` và `END`, xem lượt cuối cùng.

> Tiêu đề thông báo trên máy vẫn hiện **PS5 STORAGE RESTORE** và thư mục log là `ps5_storage_restore`,
> vì hai giá trị này đã biên dịch sẵn trong ELF 1.1.

### Tự chạy mỗi lần khởi động

Mount ổ ngoài chỉ tồn tại trong phiên hiện tại, nên sau mỗi lần khởi động lại phải chạy lại payload.
Với `ps5_autoloader`:

1. Sao lưu `/data/ps5_autoloader/autoload.txt`.
2. Chép ELF vào `/data/ps5_autoloader/PS5_FPKG_RESTORE.elf`.
3. Thêm dòng `PS5_FPKG_RESTORE.elf` **sau** các payload nền tảng và **trước** `shadowmountplus.elf`.
   Xem [`examples/autoload.example.txt`](examples/autoload.example.txt). Ghép vào cấu hình đang có, đừng chép đè cả file.
4. Nếu đang dùng `M2_RESTORE_PS5.elf` (bản cũ khóa 9 game), thay dòng đó bằng ELF mới. Chỉ giữ một bản.

Nếu lượt cuối trong log ghi `found=0` là autoloader chạy trước khi ổ được nhận. Đợi ổ xuất hiện rồi chạy lại ELF.

## Đọc log

| Dòng log | Ý nghĩa |
|---|---|
| `REGISTER … rc=0x00000000` | Đăng ký thành công |
| `mode=internal-direct` | Game ở bộ nhớ trong, đăng ký trực tiếp |
| `mode=external-readonly` | Game ở ổ ngoài/M.2, đăng ký qua mount chỉ đọc |
| `SKIP invalid/unsupported PKG table` | Gói không đúng định dạng hỗ trợ hoặc không đọc được bảng metadata |
| `SKIP invalid param.json/titleId` | `param.json` lỗi hoặc mã game không khớp tên thư mục |
| `SKIP metadata conflict/write failed` | `param.json` hiện có khác gói hoặc lỗi ghi; giữ nguyên dữ liệu |
| `SKIP occupied/unowned destination` | `/user/app/<mã>` đã có dữ liệu/mount khác; ELF không tự xóa |
| `MOUNT_FAILED` | Kiểm tra quyền payload, tình trạng ổ và mount hiện tại |

Không thấy dòng `START` mới nghĩa là payload chưa chạy tới `main` hoặc không mở được thư mục log.

## Phạm vi & giới hạn

**Không** xử lý: file PKG tải về nhưng chưa cài, game PS4 `CUSA`, DLC/update rời, `app0` dump, ổ đã bị xóa/format.
Payload không tự mở game và không khởi động lại máy.

**Đã thử trên PS5 Pro FW 10.01:** 9 game trên M.2 + 2 ứng dụng bộ nhớ trong (Netflix, YouTube) đều đăng ký 11/11 `rc=0`.
Chạy lại lần hai tạo 0 file; hai database qua `PRAGMA integrity_check`; icon hiển thị ở cả hai tài khoản.

**Chưa kiểm chứng:** mở game sau khi đăng ký, khởi động lại từ đầu, máy đặt English, các firmware khác.
Đăng ký thành công chưa đảm bảo game mở được; việc đó còn phụ thuộc môi trường chạy và bản game.

## Gỡ bỏ / hoàn tác

Xóa riêng dòng `PS5_FPKG_RESTORE.elf` khỏi `autoload.txt`, đóng game rồi khởi động lại. Game đã đăng ký vẫn còn trong thư viện.

> ⚠️ **Tuyệt đối không xóa đệ quy `/user/app/PPSAxxxxx` khi đó còn là mount trỏ tới ổ ngoài**, vì sẽ xóa luôn game thật trên ổ.

Payload không có chức năng gỡ game hay phục hồi database cũ.

## Build từ source

Xem [docs/BUILD.md](docs/BUILD.md). Báo cáo kỹ thuật chi tiết: [docs/TECHNICAL.vi.md](docs/TECHNICAL.vi.md).

```
src/        storage_restore.c (quét ổ, metadata, mount, AppInst, thông báo) · pkg_reader.h (bộ đọc PKG)
tests/      kiểm thử parser và script triển khai/đối chiếu trên máy
examples/   đoạn mẫu autoload.txt
licenses/   giấy phép thư viện bên thứ ba (json-c, PS5 payload SDK)
build.py    script build độc lập
```

## Tác giả & ghi công

Phát triển bởi **Nguyễn Thanh Sơn** & **Ngô Phi Phương** — [PSVIETHOA.COM](https://psviethoa.com)

Tham khảo kỹ thuật: [ShadowMountPlus](https://github.com/drakmor/ShadowMountPlus) ·
[LibProsperoPKG](https://github.com/SvenGDK/LibProsperoPKG) ·
[PS5 payload SDK](https://github.com/ps5-payload-dev/sdk) ·
[json-c](https://github.com/json-c/json-c) ·
[ps5-syslang](https://github.com/owendswang/ps5-syslang#languages)

Kho mã không chứa gói game, ảnh trích từ game hay database của máy. Chỉ dùng với nội dung bạn sở hữu hợp pháp.
