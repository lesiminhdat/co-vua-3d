# Cờ Vua 3D — đóng gói thành ứng dụng

Mã nguồn gốc: `index.html`. Thư mục `app/` chứa phần đóng gói:

| Nền tảng | Công cụ | File tạo ra |
|---|---|---|
| Windows | Electron | `app/dist/Co Vua 3D Setup 1.0.0.exe` (bản cài), `app/dist/CoVua3D-portable-1.0.0.exe` (chạy luôn, không cần cài) |
| macOS | Electron | `.dmg` (build qua GitHub Actions) |
| Android | Capacitor | `CoVua3D.apk` (build qua GitHub Actions) |
| iPhone | Capacitor | `CoVua3D-unsigned.ipa` (build qua GitHub Actions, cần máy Mac nên không build được trên Windows) |

App chạy hoàn toàn offline: thư viện (Tailwind, chess.js, Font Awesome, font Be Vietnam Pro) đã được tải về `app/www/vendor/`.
Các đoạn script do Gemini Canvas tự chèn vào đầu `index.html` (kèm token đăng nhập) bị loại bỏ khi đóng gói.

## Build trên máy này (Windows)

```powershell
cd C:\chess\app
npm install
npm run dist:win
```

Chạy thử không cần đóng gói: `npm start`.

Sau khi sửa `index.html`, chỉ cần build lại — script `scripts/prepare.mjs` tự tạo lại `app/www/`.

## Build APK + IPA bằng GitHub Actions (miễn phí)

1. Tạo một repository mới trên GitHub (nên để Private).
2. Đẩy thư mục `C:\chess` lên:

```powershell
cd C:\chess
git init -b main
git add .
git commit -m "Cờ Vua 3D app"
git remote add origin https://github.com/<tên-bạn>/<tên-repo>.git
git push -u origin main
```

3. Vào tab **Actions** của repo → workflow **Build apps** tự chạy (~10–15 phút).
4. Mở lần chạy đó, kéo xuống phần **Artifacts** để tải: `CoVua3D-android-apk`, `CoVua3D-ios-ipa`, `CoVua3D-desktop-Windows`, `CoVua3D-desktop-macOS`.
5. Muốn có trang tải cố định (Releases): tạo tag `git tag v1.0.0 && git push origin v1.0.0`.

## Web app — cài từ trình duyệt, không cần ESign

Link: **https://lesiminhdat.github.io/co-vua-3d/** (tự cập nhật mỗi khi đẩy code lên nhánh `main`).

- **iPhone:** mở link bằng **Safari** → bấm **Chia sẻ** → **Thêm vào MH chính**. Không cần ký, không hết hạn.
- **Android:** mở bằng Chrome → bấm **Cài đặt** trên thanh hiện ra ở cuối trang.
- Sau lần mở đầu tiên, app chạy được cả khi không có mạng.

Chạy thử bản web trên máy: `node app/scripts/serve.mjs` rồi mở http://localhost:5173.

## Cài trên điện thoại (file APK / IPA)

**Android:** chép file `.apk` vào điện thoại → mở → cho phép "Cài ứng dụng không rõ nguồn gốc". Đây là bản ký debug; nếu cài bản mới build ở lần chạy khác mà báo xung đột chữ ký, hãy gỡ bản cũ trước.

**iPhone:** Apple không cho cài `.ipa` tùy ý. File `.ipa` này **chưa ký**, cần ký khi cài bằng một trong các cách:
- **Sideloadly** hoặc **AltStore** (Windows/Mac) + Apple ID miễn phí → cài được, nhưng phải cài lại sau mỗi 7 ngày.
- Tài khoản Apple Developer (99 USD/năm) → ký 1 năm, hoặc phát hành qua TestFlight/App Store.

**Windows:** chạy `Co Vua 3D Setup 1.0.0.exe`. Vì chưa có chứng chỉ ký số, Windows SmartScreen có thể cảnh báo → bấm "More info" → "Run anyway".
