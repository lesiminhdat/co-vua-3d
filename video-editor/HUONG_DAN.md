# Edit video sản phẩm 40 giây – tự động

## Cách dùng (3 bước)

1. **Bỏ video/ảnh vào thư mục dự án**, ví dụ `du_an_mau\`
   - Nhận: `.mp4 .mov .m4v .avi .mkv .webm .jpg .png .webp`
   - Thứ tự xuất hiện theo tên file → đặt tên `01_...`, `02_...` để sắp xếp.
   - File có tên chứa `end` hoặc `cta` (vd `end_sanpham.mp4`) sẽ được dùng làm cảnh cuối (cảnh kêu gọi mua).
   - Clip quá ngắn sẽ tự chuyển slow-motion cho đủ thời lượng.

2. **Chạy lần đầu** → script tự tạo file `project.json`. Mở file đó sửa chữ:

```json
{
  "title": "SERUM VITAMIN C",
  "subtitle": "Da sáng mịn sau 7 ngày",
  "features": ["Chiết xuất thiên nhiên", "Thấm nhanh", "Phù hợp mọi loại da"],
  "cta": "MUA NGAY - GIẢM 30%",
  "price": "Chỉ 199.000đ",
  "style": "energetic",
  "format": "9:16",
  "fit": "crop",
  "duration": 40,
  "accent": "#FF3B5C",
  "music": "",
  "music_seed": 0
}
```

3. **Chạy lại** → kết quả ở `du_an_mau\output\video_final.mp4`

```powershell
cd C:\chess\video-editor; python edit_video.py du_an_mau
```

## Các tuỳ chọn

| Mục | Giá trị | Ý nghĩa |
|---|---|---|
| `style` | `energetic` | Nhạc sôi động 124 BPM, cắt nhanh theo nhịp, chuyển cảnh trượt/zoom — hợp mỹ phẩm, thời trang, đồ công nghệ, flash sale |
| | `chill` | Nhạc nhẹ nhàng 92 BPM, chuyển cảnh mềm, màu ấm — hợp đồ ăn, đồ gia dụng, đồ handmade |
| | `luxury` | Nhạc sang trọng 100 BPM, màu trầm có viền tối — hợp trang sức, nước hoa, hàng cao cấp |
| `format` | `9:16` / `16:9` / `1:1` / `4:5` | TikTok/Reels/Shorts / YouTube / Facebook vuông / Facebook dọc |
| `fit` | `crop` | Cắt cho đầy khung (có thể mất 2 bên nếu quay ngang) |
| | `blur` | Giữ nguyên toàn bộ khung hình, nền mờ phía sau — dùng khi quay video ngang mà xuất dọc |
| `music_seed` | `0` hoặc số bất kỳ | `0` = tự chọn theo tên sản phẩm. Không thích nhạc → đổi sang số khác (1, 2, 3…) để có giai điệu mới |
| `music` | đường dẫn file | Dùng nhạc riêng của bạn thay nhạc tự tạo (chỉ dùng nhạc bạn có quyền) |
| `accent` | mã màu | Màu chủ đạo của chữ (viền tiêu đề, khung slogan, nút kêu gọi). Mặc định hồng `#FF6FA5` |
| `font` | tên file phông | Mặc định `Mali-Bold.ttf` (tròn, dễ thương). Có sẵn trong thư mục `fonts\`: `Mali-Bold.ttf`, `Itim-Regular.ttf`, `Pacifico-Regular.ttf` (viết tay bay bướm), `Sriracha-Regular.ttf`, `PatrickHand-Regular.ttf`. Tất cả miễn phí (Google Fonts, giấy phép OFL), hỗ trợ tiếng Việt |
| `beauty` | `0`–`3` | Làm đẹp: mịn da, da trắng hồng, sáng trong, ánh sáng mềm. `0` = tắt, `1` = nhẹ tự nhiên, `2` = vừa (mặc định), `3` = mạnh |

## Về bản quyền

- **Nhạc nền được tạo hoàn toàn bằng code** (tổng hợp từ sóng âm + nhiễu, giai điệu sinh ngẫu nhiên theo seed), không dùng đoạn nhạc hay sample nào có sẵn → hệ thống nhận diện bản quyền (Content ID của TikTok/Facebook/YouTube) không có gì để so khớp.
- **Font chữ** dùng Arial Bold có sẵn của Windows.
- **Video/ảnh đầu vào** phải là của bạn (tự quay, hoặc được nhà cung cấp cho phép). Script không xử lý được vấn đề bản quyền của hình ảnh bạn đưa vào.
- Nếu dùng `"music"` với nhạc bên ngoài thì bạn tự chịu trách nhiệm về bản quyền của file đó.

## Yêu cầu

FFmpeg (đã cài qua `winget install Gyan.FFmpeg`), Python + numpy. Render 40 giây mất khoảng 2–3 phút.
