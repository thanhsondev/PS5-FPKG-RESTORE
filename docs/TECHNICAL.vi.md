# PS5 FPKG Restore 1.1 — Báo cáo kỹ thuật

Bản quyền: **NGÔ PHI PHƯƠNG - NGUYỄN THANH SƠN - PSVIETHOA.COM**

## Bài toán và kết quả

Sau reset, các gói PS5 trên M.2 còn nguyên nhưng chín title không còn trong
database đăng ký. Khôi phục metadata rồi gọi AppInst trực tiếp trên đường dẫn
`/mnt/ext1/user/app/` trả `0x80020002`. Cách đã chạy được là tạo mount nullfs
chỉ đọc vào `/user/app/<TITLEID>`, chuẩn bị metadata và đăng ký bằng AppInst.

Bản 1.1 tự quét bộ nhớ trong và ext0–ext15, không chứa danh sách title hay
kích thước PKG cố định. Trên PS5 Pro FW 10.01, ELF cuối đăng ký thành công
11/11 title: chín game M.2 và hai ứng dụng bộ nhớ trong (Netflix, YouTube).
Tất cả trả `0x00000000`. Lượt chạy lại ghi `created=0`.

Hai database tải về đều qua `PRAGMA integrity_check`. Mỗi title có
`visible=1, installStatus=2` trong bảng icon của cả hai tài khoản trên máy thử.
Đây là xác nhận đăng ký trên console và đối chiếu database; chưa xác nhận
ảnh giao diện, mở game, reboot hoặc firmware khác. Nhánh bộ nhớ trong đã
được chạy thực tế với hai ứng dụng PS5, chưa có game PS5 nội bộ để thử riêng.
Thông báo tiếng Việt đã được biên dịch UTF-8 và gọi trên console; việc dấu
tiếng Việt/dòng dài hiển thị đầy đủ vẫn cần xem trực tiếp trên TV.
ELF 1.1 đọc ngôn ngữ thực tế thành công: `system=28, rc=0, selected=vi`.
Nhánh chọn English chưa thử bằng cách đổi ngôn ngữ console.

## Luồng xử lý

1. Đọc `sceSystemServiceParamGetInt(1, &language)`: ID 28 chọn tiếng Việt;
   English US/UK, ngôn ngữ khác hoặc API lỗi chọn English. Không ghi thiết lập
   ngôn ngữ máy. Sau đó khóa phiên bằng `flock`, mở log trong `/data/ps5_storage_restore`.
2. Lưu authid hiện tại, đặt authid phục vụ AppInst; nạp thư viện AppInst động
   sau khi vào main. Hoàn trả authid trước khi thoát bình thường.
3. Quét `/user/app` trước, sau đó `/mnt/ext0/user/app` đến `ext15`.
   Chỉ nhận thư mục `PPSA` + năm chữ số có `app.pkg` là file thường.
   Bỏ qua nullfs khi quét bộ nhớ trong để không đếm lại alias M.2.
4. Đọc FIH, lấy CNT offset uint64 little-endian tại 0x58. Đọc bảng CNT:
   count BE32 tại 0x10, table offset BE32 tại 0x18, entry 32 byte.
5. Kiểm tra giới hạn file, offset, count, bảng tên ID 0x200 và tên metadata.
   Bảng tên thực tế có flag 0x40000000; đây là flag đã quan sát trong gói
   thử nghiệm. Metadata chấp nhận flags 0 hoặc 0x08000000, flags2=0.
   Bỏ qua nội dung mã hóa; không giải mã hay trích dữ liệu thực thi.
6. Dùng json-c đọc param.json, yêu cầu titleId khớp tên thư mục. Chọn
   param.json, playgo-scenario.json và ảnh/âm thanh .png/.dds/.at9 có tên phẳng.
7. Bổ sung file còn thiếu vào `<source>/sce_sys` và `/user/appmeta/<TITLEID>`.
   Giữ nguyên ảnh hiện có; param.json hiện có phải khớp byte với gói.
   Ghi file tạm exclusive, fsync, đọc lại đối chiếu, kiểm tra đích rồi rename.
   Khóa phiên ngăn hai bản tiện ích cùng chạy; không đồng bộ với trình cài game
   khác, vì vậy chạy khi không có tác vụ cài đặt/cập nhật đồng thời.
8. Bộ nhớ trong: đăng ký trực tiếp. M.2/ổ ext: tạo nullfs MNT_RDONLY vào
   `/user/app/<TITLEID>` rồi đăng ký. Không thay đích đang chứa dữ liệu khác.
9. Gọi `sceAppInstUtilAppInstallTitleDir(titleId, "/user/app/", NULL)`.
   Chấp nhận rc=0 hoặc 0x80990002 theo hành vi API; bài thử thực tế toàn bộ rc=0.
   Khi đăng ký lỗi, bỏ mount vừa tạo nếu có thể và chỉ rmdir thư mục rỗng vừa tạo.
10. Ghi tổng số, gửi thông báo EN/VI đã chọn có dòng bản quyền, thoát.

## Dữ liệu thay đổi

- Có thể tạo metadata còn thiếu cạnh app.pkg và trong `/user/appmeta`.
- Có thể tạo thư mục alias `/user/app/<TITLEID>` và mount chỉ đọc.
- Tạo log, file khóa và marker nguồn trong `/data/ps5_storage_restore`.
- AppInst cập nhật database theo API của hệ thống. ELF không tự sửa SQLite.
- Không ghi nội dung app.pkg, không sao chép toàn bộ game, không sửa ELF
  ShadowMount gốc, không chạy game hay reboot.
- Metadata đã tạo được ghi từng đường dẫn và kích thước trong log. Nếu một
  title thất bại giữa chừng, file metadata đã thêm có thể vẫn còn để chạy lại.

Đối với M.2, đường đăng ký là alias `/user/app`; dữ liệu PKG vẫn nằm ở ổ gốc.
Chưa thử luồng di chuyển/cập nhật/gỡ game trong Settings sau cách đăng ký này.
Không cung cấp thao tác xóa mount đệ quy hoặc ghi trả database khi Shell đang chạy.

## Kiểm tra

- Build `-Wall -Wextra -Werror`, target x86_64-sie-ps5.
- ELF64 little-endian, ET_DYN, x86-64, entry nằm trong LOAD executable;
  các program header và segment nằm trong file, filesz không vượt memsz.
- Không import AppInst/UserService sớm trong DT_NEEDED; AppInst dùng dlopen/dlsym.
- 22 ca chạy bằng bộ đọc C thực tế trên host: header cắt cụt, offset tràn,
  entry ngoài file, tên sai, param mã hóa, flag lạ, param trùng/thiếu, path traversal,
  và fixture đóng lại từ metadata của chín game. Fixture không phải toàn bộ PKG.
- ELF cuối đã chạy trên console, đọc các PKG thật, đăng ký 11 title và chạy lại
  không tạo thêm metadata. Log và bản sao database trước/sau giữ ở `verification`
  của thư mục làm việc; các database không đưa vào ZIP chia sẻ.
- Quá trình tạo nullfs mới trước đó đã xác nhận với bản khôi phục chín title.
  Các lượt thử bản tổng quát dùng lại mount M.2 đang tồn tại; chưa thử lại từ boot sạch.

## Giới hạn hiện tại

Tối đa 65.535 entry bảng PKG, 512 file metadata được chọn, 32 MiB mỗi file,
256 MiB tổng metadata/title, 1 MiB param.json. Quá giới hạn sẽ bỏ qua.
Chỉ xử lý PKG đã cài theo cấu trúc PPSA chuẩn. Không phục hồi game đã xóa,
không hỗ trợ CUSA, DLC/update riêng hay app0 dump. Không tự chờ ổ đến muộn.
Nếu cùng title tồn tại trên nhiều ổ, giữ đường đích đã dùng và bỏ qua nguồn xung đột.

## Source và build

`src/pkg_reader.h`: bộ đọc metadata có kiểm tra giới hạn.
`src/storage_restore.c`: quét ổ, chuẩn bị metadata, mount, AppInst, thông báo.
`build.py`: build độc lập với script ngoài dự án; cần Python 3, LLVM/LLD và
PS5 payload SDK có sysroot + json-c static. Xem BUILD_SOURCE.txt.
`tests`: kiểm tra parser và các script triển khai/đối chiếu dùng khi phát triển.

SDK dùng để thử: pacbrew-repo v0.40.2; hash asset được lưu trong BUILD.json.
Giữ debug ELF và linker map trong thư mục build của bản làm việc.

Nguồn tham khảo kỹ thuật:
- ShadowMountPlus/AppInst: https://github.com/drakmor/ShadowMountPlus
- Cấu trúc gói: https://github.com/SvenGDK/LibProsperoPKG
- PS5 payload SDK: https://github.com/ps5-payload-dev/sdk
- json-c và giấy phép: https://github.com/json-c/json-c
- Mã ngôn ngữ PS5: https://github.com/owendswang/ps5-syslang#languages
- Ngôn ngữ giao diện: https://www.playstation.com/en-vn/legal/language-support/

Đây là tiện ích riêng cho đăng ký lại gói đã cài, không phải bản thay thế toàn bộ
ShadowMountPlus. Thông tin bản quyền của thư viện bên thứ ba giữ trong thư mục licenses.
