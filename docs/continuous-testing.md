# Kiểm thử hiệu năng liên tục cho EShop

**Đề xuất cho G4.** Dùng workflow trên runner cố định có cấu hình được ghi lại. Baseline là commit gần nhất đã duyệt, với cùng phiên bản JMeter, fixture, workload và thời gian giữ tải. Nếu đổi cấu hình máy hoặc tập dữ liệu, tạo baseline mới trước khi so sánh.

```text
Commit / pull request
        |
        v
Diff chạm API, DB, deps backend hoặc chuỗi gọi API admin?
        |-- Không --> Ghi lý do bỏ qua hoặc chạy theo lịch
        v Có
Smoke 1 VU, kiểm tra token, giá đọc lại và đơn mẫu
        |-- Lỗi --> Lưu JTL, báo lỗi nghiệp vụ, dừng
        v Đạt
Load ngắn, chụp RSS/CPU, lấy p95 từng label trên đoạn giữ
        |
        v
Đủ mẫu và môi trường tương đương?
        |-- Không --> Đánh dấu thiếu bằng chứng, chạy lại
        v Có
Có label tăng >20% so với baseline?
        |-- Không --> Lưu kết quả; duyệt baseline sau merge
        v Có
Khôi phục fixture, lặp lại trên cùng runner
        |-- Bình thường --> Lưu cả hai lượt để theo dõi nhiễu
        v Lặp lại
Báo regression với commit, label, p95, cỡ mẫu và JTL
```

## Quyết định và chi phí

- Trigger gồm thay đổi backend, schema hoặc script seed và mã nguồn Web Admin thay đổi số lần/thứ tự gọi API. Thay đổi tài liệu thuần có thể bỏ lượt ngắn. Lịch đêm chạy stress hoặc spike theo phiên bản có thay đổi, lịch tuần chạy soak trên runner cố định.
- Mốc tăng 20% là ngưỡng cảnh báo thử nghiệm. Khi baseline chỉ vài mili giây, dao động 1 ms đã đủ vượt 20%. Hiển thị chênh lệch tuyệt đối, tải quan sát, số mẫu và tỷ lệ lỗi; yêu cầu tối thiểu 100 mẫu mỗi label trong phép so sánh. Lỗi assertion xử lý riêng ngay cả khi p95 thấp.
- Lặp lại có chọn lọc giảm cảnh báo giả do CPU dùng chung, GC hoặc DB phình ra; chi phí là thêm thời gian runner và chậm phản hồi. Chỉ cập nhật baseline sau khi người phụ trách xác nhận thay đổi có chủ đích. Lưu JTL và telemetry cho lượt cảnh báo để tái kiểm tra.
