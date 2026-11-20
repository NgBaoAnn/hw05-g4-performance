# HW05 G4 · Hiệu năng quản trị EShop

Bộ JMeter chạy trên EShop local cho luồng admin đăng nhập → mở Dashboard → tạo coupon → sửa giá sản phẩm → đọc lại giá → xem đơn hàng.

| Plan | Cấu hình |
|---|---|
| Load | 10 VU, ramp 60 giây, giữ 5 phút |
| Stress | 10 → 20 → 40 → 80 VU, mỗi bậc giữ 2 phút |
| Spike | 5 → 50 → 5 VU, tăng trong 5 giây, giữ đỉnh 60 giây |
| Soak | Dùng plan Load, chọn VU theo kết quả Stress, giữ 12 phút |

[Hướng dẫn dựng SUT, tái lập dữ liệu và chạy](REPRODUCE.md) · [Test plans](plans/) · [Dữ liệu demo](data/) · [Agent Skill phân tích JTL](skills/jmeter-workflow/SKILL.md).
