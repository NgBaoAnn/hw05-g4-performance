# Chạy lại bài đo G4

Luồng quản trị EShop gồm login → năm GET Dashboard → tạo coupon → đổi giá → đọc lại → xem đơn. Mỗi vòng có 10 HTTP sample, bốn khoảng nghĩ ngẫu nhiên 1–3 giây. Một VU dùng một dòng CSV suốt vòng đời thread. Mã coupon duy nhất theo run, slot và vòng. CSV fixture demo có schema cố định, các giá trị không chứa dấu phẩy hoặc xuống dòng. Với dữ liệu có dấu phân cách bên trong trường, đổi sang bộ đọc CSV có hỗ trợ quoting trước khi chạy.

## Chuẩn bị

Cần Python 3.10+, Node và npm, JDK 21, Apache JMeter 5.6.3, Git và lệnh ps. Đã chạy trên macOS. Lệnh bên dưới thực hiện ở thư mục repo. Dùng một bản clone riêng vì backend gốc tạo lại bảng SQLite mỗi khi khởi động. Giữ cổng 3000 trống. Chương trình chỉ lắng nghe trên loopback.

```sh
mkdir -p .work
git clone https://github.com/ttbhanh/eshop-sut .work/eshop
git -C .work/eshop checkout 85af3ba875c88283615e22cb108f13e2fccaf0e9
npm ci --prefix .work/eshop/backend
export JMETER_HOME=/absolute/path/to/apache-jmeter-5.6.3
export JAVA=/absolute/path/to/jdk-21/bin/java
```

Nếu đã giải nén JMeter vào `.work/apache-jmeter-5.6.3` và Java 21 có trên PATH, hai biến bên trên có thể bỏ qua. Các JMX trong `plans/` là plan hoàn chỉnh. Mặc định script chọn tệp theo loại scenario. Nếu tái tạo plan bằng generator vào ngày khác, dùng thư mục mới hoặc giữ đúng một tệp cho mỗi loại.

## Đo

```sh
python3 scripts/run.py Smoke --out evidence/Smoke
python3 scripts/run.py Pilot --out evidence/Pilot
python3 scripts/run.py Load --out evidence/Load
python3 scripts/run.py Stress --out evidence/Stress
python3 scripts/run.py Spike --out evidence/Spike
python3 scripts/analyze.py --choose-soak
```

Dùng số VU do lệnh cuối in ra thay cho N dưới đây. Soak dùng luồng Load trong 721 giây, gồm 1 giây ramp và 720 giây giữ tải. Nếu hết các bậc Stress mà chưa đạt tiêu chí, script đề xuất thăm dò 5 VU. Nếu soak thất bại, hạ về nửa số VU (tối thiểu 1) và tạo thư mục kết quả mới. Sau mỗi lần ghi lại nguyên nhân, gồm p95 theo sampler, lỗi và RPS ba phút cuối.

```sh
python3 scripts/run.py Soak --vu N --out evidence/Soak
python3 scripts/analyze.py evidence/Soak
python3 skills/jmeter-workflow/scripts/metrics.py evidence/Load/samples.jtl
```

Mỗi lệnh khởi động backend mới, chờ seed, nạp 80 admin và sản phẩm thử, thêm đơn 9001, chạy CLI rồi dừng backend. Trạng thái ban đầu là 82 users, 85 products, 3 categories, 4 coupons, 1 order. Lượt sau dùng lại đúng trạng thái này. Mỗi thư mục đầu ra phải mới. `resources.csv` ghi PID, %CPU và RSS (KiB) của Node và Java khoảng mỗi giây. `samples.jtl` là CSV gốc. Mở `html/index.html` sau các lượt chính.

Khi chạy GUI, đặt thuộc tính `-Jfixture=/đường/dẫn/tuyệt/đối/admin-fixtures.csv` và `-JrunId=...`, chạy với backend thử đã seed. Để xem lại kết quả, mở listener của plan và chọn tệp JTL ở ô Filename. Dùng Summary Report cho Load, Aggregate Report cho Stress, Response Time Graph cho Spike. Listener để tắt trong phép đo CLI.

## Smoke toàn miền Admin

Cần Google Chrome và gói Playwright Node cho smoke giao diện. Các bước này chỉ thực hiện sau khi dừng các bài đo.

```sh
npm ci --prefix .work/eshop/frontend-admin
npm install --prefix .work/browser-tools playwright
export NODE_PATH="$PWD/.work/browser-tools/node_modules"
python3 scripts/smoke-ui.py evidence/AdminSmoke
```

Smoke kiểm tra Dashboard, Category/Product CRUD, Coupon create/read/delete, đọc đơn/admin users và import qua giao diện với hai sản phẩm. Ảnh thật và bảng kết quả nằm trong thư mục đầu ra. SUT tham chiếu chưa có endpoint sửa coupon. Mỗi lần dùng thư mục đầu ra mới để giữ lại bằng chứng cũ.
