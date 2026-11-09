# Kết quả kiểm chứng phần mềm — 24/10/2026

Các kiểm tra được thực hiện trên workspace hiện tại. Không thay thế cho
video webcam và robot trong Gazebo.

| Kiểm tra | Kết quả |
|---|---|
| `colcon build --symlink-install --packages-select tb4_simplesimu` | PASS, 1 package |
| `python3 -m unittest discover -s tests -v` | PASS, 19/19 |
| Nạp launch điều khiển với `--show-args` | PASS |
| Nạp launch mô phỏng với `--show-args` | PASS; sau đó đã mở Gazebo thật |
| Compile Python các node và launch mới | PASS |
| `tests/ros_gesture_smoke.py` | PASS, 6 tình huống trên topic kiểm thử |
| `tests/mediapipe_smoke.py` | PASS, MediaPipe 0.10.21, mô hình chính thức, 3 ảnh trống |
| Tạo PDF | PASS, 4 trang A4, font tiếng Việt nhúng |
| Webcam và cử chỉ thật | Đã mở `/dev/video0` trên máy thật và nhận cử chỉ |
| Robot chạy quỹ đạo trong Gazebo | PASS, đo bằng odometry; xem bảng dưới |
| Video, ảnh thực nghiệm, GitHub Public, Drive | Chưa tạo/upload |

Kiểm thử ROS đã xác nhận:

1. Chọn Pointing Up chưa phát vận tốc di chuyển.
2. Thumb Up sau lựa chọn phát vận tốc tiến.
3. Open Palm đưa vận tốc về 0 và trạng thái IDLE.
4. Ngừng phát cử chỉ: watchdog đưa vận tốc về 0.
5. Ngừng phát scan trong khi vẫn có cử chỉ: đưa vận tốc về 0.
6. Tia LiDAR ở 0,3 m: hủy và đưa vận tốc về 0.

DDS trong sandbox không truy cập được giao diện mạng. Lần chạy đạt dùng
localhost ngoài sandbox, domain 86 để tách khỏi hệ thống robot đang chạy:

```bash
source /opt/ros/humble/setup.bash
ROS_LOG_DIR=/tmp/bai6-ros-logs ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=86 \
  python3 tests/ros_gesture_smoke.py
```

MediaPipe được cài thử riêng trong `/tmp/tb4-gesture-deps`, không sửa
Python hệ thống. Mô hình tải về `/tmp/tb4-gesture-model/gesture_recognizer.task`.
Thư viện dùng CPU/XNNPACK; có cảnh báo EGL không có GPU nhưng suy luận thành công.
Ảnh thử trống chỉ xác nhận API, model và VIDEO mode hoạt động; không chứng
minh nhận diện đúng 6 cử chỉ trên webcam.

```bash
PYTHONPATH=/tmp/tb4-gesture-deps MPLCONFIGDIR=/tmp/bai6-mpl \
XDG_CACHE_HOME=/tmp/bai6-cache \
python3 tests/mediapipe_smoke.py \
  /tmp/tb4-gesture-model/gesture_recognizer.task
```

Khi tái lập bằng venv đã hướng dẫn, dùng Python venv thay cho PYTHONPATH.
Điền kết quả demo thật vào `ket_qua_thuc_nghiem.md` sau khi chạy trên máy có camera.

## Cập nhật sau khi chạy trực tiếp trên máy thật

Webcam có sẵn ngoài sandbox: `/dev/video0`, đọc ảnh 640×480 thành công.
Cửa sổ webcam nhận được Open Palm, Pointing Up, Victory và Closed Fist từ
tay người dùng; không khẳng định đã đánh giá độ chính xác của tất cả nhãn.
Quan sát 12 giây: 240 kết quả webcam, 182 scan và 745 bản tin odometry.
Khoảng cách tường gần nhất khoảng 4,91 m, dữ liệu LiDAR hợp lệ.

Các sửa lỗi từ chạy thật:

- Tăng giới hạn participant Cyclone DDS lên 120, bind loopback để tránh
  lỗi “Failed to find a free participant index”.
- Giữ lựa chọn 5 giây qua các khung hình NONE trước khi xác nhận; đang
  chạy mà NONE vẫn hủy ngay.
- Dùng /clock cho pha chuyển động, đồng hồ đơn điệu thực cho watchdog.
- Bỏ render cảm biến camera/IR/cliff không dùng trong sân trống; giữ IMU
  và LiDAR 15 Hz, physics step 0,004 s. Chỉ áp dụng launch Bài 6.
- Bổ sung hai kiểm thử, tổng 19/19 đạt; chạy lại tích hợp ROS vẫn PASS.

Mở lại bằng `./scripts/run_bai6_live.sh`. Log ở `log/bai6_live/`.

## Kết quả chạy robot trong Gazebo

Kiểm tra này tạm dừng node webcam, phát nhãn thử lên `/detected_gesture`,
quan sát chuyển động thật của mô hình qua `/odom`, rồi tự bật lại webcam.
Đây là kiểm chứng đường điều khiển và động học, không phải video demo cử chỉ tay.

| Hành vi | Kết quả đo |
|---|---|
| Tiến–lùi | Đủ 8 chặng (+/− luân phiên), 4 chu kỳ, quãng đường 1,882 m |
| Vòng tròn | Quãng đường 3,754 m, góc quay 6,273 rad, lệch điểm đầu 0,015 m |
| Chào | Hoàn thành, không tịnh tiến, góc dư khoảng 0,065 rad |
| Open Palm khi đang chạy | Trạng thái IDLE, `/cmd_vel` bằng 0 |

Lưu ý: tiến–lùi kết thúc lệch điểm đầu 0,519 m, cho thấy giới hạn của
điều khiển vận tốc theo thời gian và động học đảo chiều. Chương trình
không có bộ điều khiển odometry để bảo đảm trở về đúng điểm đầu.
Số liệu gốc ở `gazebo_test_results.json`. Webcam đã được bật lại sau test.
