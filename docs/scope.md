# HW05 — G4 Quản trị
Nguyễn Bảo An · 23120207. SUT ttbhanh/eshop-sut, commit 85af3ba875c88283615e22cb108f13e2fccaf0e9. JMeter CLI, backend local trên macOS. Một giao dịch là một phiên nghiệp vụ có đăng nhập.
 
Mỗi vòng gồm login, năm GET của Dashboard theo thứ tự users/orders/products/categories/coupons, tạo coupon, PUT đủ năm trường sản phẩm, GET kiểm tra giá, GET đơn. FR-12/13/15/17/18 là phần đo chính. FR-14/16/19 có phần smoke. CSV import nghiệp vụ và CSV fixture cho JMeter là hai tệp riêng.

Tiêu chí đăng ký trước phép đo: lỗi dưới 1%, p95 elapsed theo từng sampler tối đa hai lần baseline Load trên đoạn giữ tải, successful HTTP RPS không giảm liên tiếp trong ba cửa sổ phút cuối soak. Định nghĩa thử nghiệm trên máy này, chưa phải SLO sản xuất. Đo bộ nhớ RSS và %CPU của Node và Java cùng máy. So sánh bậc Stress với baseline trước khi chọn VU cho soak.
