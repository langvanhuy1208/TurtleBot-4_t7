# Trạng thái tự kiểm thử trước khi quay video

Các kiểm tra đã đạt trên máy hiện tại:

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| Build ROS package | Đạt | `colcon build --packages-select tb4_simplesimu --symlink-install` |
| Bản đồ, parser và đầu vào âm thanh | 48/48 | `unit_test_results.txt` |
| DDS/action với Nav2 giả | 11/11 | `ros_test_results.json` |
| Whisper small trên WAV tiếng Việt tổng hợp | 5/5 | `asr_test_results.json` |
| Pipeline WAV → Whisper → Nav2/Gazebo cơ bản | 5/5 | `gazebo_test_results.json` (lần thử ban đầu) |
| Gazebo thực, chuỗi A → C → B, hủy/chạy lại | 5/5 | `gazebo_extended_results.json` (bản sửa hiện hành) |
| CLI văn bản, WAV, im lặng, micro thực | 4/4 | `voice_input_test_results.json` |
| Micro PulseAudio 16 kHz mono | Đạt | `microphone_test_results.json` |
| Giữ timestamp scan, throttle, reset clock | Đạt | `scan_test_results.txt` |

Trong thử nghiệm mở rộng: robot hoàn thành hành trình A → C → B dài khoảng 18,688 m theo AMCL, sai số đích cuối 0,216 m, clearance nhỏ nhất theo AMCL 0,400 m. Khi hủy lúc đang di chuyển, odometry về 0 m/s và 0 rad/s; B trong hàng đợi không được thực hiện. Robot nhận và hoàn thành được lệnh mới sau hủy.

## Các lỗi đã tìm và sửa trong lần kiểm thử bổ sung

- Thu âm: máy có micro/PulseAudio, nhưng Python sounddevice thiếu PortAudio. Thêm backend `parec` thu 16 kHz mono trực tiếp; mặc định không lấy âm thanh monitor loa.
- Khởi tạo: script tự xác minh nội dung `/map`, odometry/TF và lifecycle Nav2 ACTIVE; quaternion pose spawn chuẩn hóa đúng.
- LiDAR: riêng launch bài 7 giữ timestamp đo gốc, thay vì đóng dấu thời điểm nhận dữ liệu; vẫn giảm tần số và phục hồi khi reset clock. Mặc định cũ của các launch bài khác được giữ nguyên.
- Renderer: riêng chế độ cảm biến nhẹ bài 7 dùng Ogre2 cho LiDAR; bài 6 giữ mặc định Ogre cũ. Hành trình nhiều chặng được chạy lại và đạt sau thay đổi này.
- RViz: giữ riêng cờ mở RViz của bài 7 để include Nav2 không ghi đè; tăng kích thước cửa sổ và kích thước chữ. Nhãn RViz dùng ID A/B/C, đặt lệch khỏi chấm đích để luôn đọc được cạnh tường; tên và lệnh trong terminal vẫn dùng tiếng Việt có dấu.
- CLI: tiếp tục hiển thị trạng thái ROS trong lúc đang chờ người dùng nhấn Enter.

Lệnh một bước `bash scripts/run_bai7_live.sh` đã được chạy đến màn hình chờ nói; đã kiểm tra cửa sổ RViz 1280×850, AMCL/TF, Nav2 ACTIVE và đóng bằng Ctrl+C thành công.

## Chạy quay

`bash scripts/run_bai7_live.sh`

Chờ dòng SẴN SÀNG QUAY VIDEO rồi nhấn Enter để nói. Log và bản thu nằm tại `log/bai7_live/`. Ctrl+C đóng toàn bộ phiên chạy. Xem `READY_TO_RECORD.md`.

Micro đã được thu thực và xử lý bằng Whisper cục bộ trong bài test; mẫu thu tạm đã xóa, không đưa giọng người dùng vào gói public. Chưa đo độ chính xác trên tập câu do người thật đọc có nhãn. Các số liệu ASR 5/5 ở trên chỉ dành cho mẫu tổng hợp đã đính kèm.

Bản đồ mặc định demo được raster hóa từ hình học SDF; bản đồ SLAM gốc được giữ và phân vùng riêng. Các số liệu trước khi sửa được giữ riêng để đối chiếu, không dùng để kết luận bản hiện hành đạt.

Báo cáo do người dùng tự làm. Người dùng đã yêu cầu đăng source, README và bộ ảnh/video lên GitHub langvanhuy1208 trong lượt chuẩn bị nộp bài.

## Cập nhật ảnh/video để mở trên máy và trình duyệt

Bộ ảnh `pictures/` đã đổi sang trắng đen, nền trắng, không dùng màu trang trí; bản đồ dùng mức xám và nhãn, biểu đồ dùng nét gạch. Không thay các số liệu đo hay quỹ đạo.

Các video trong `videos/` đã được mã hóa lại từ bản đo gốc: hai MP4 H.264 Constrained Baseline/yuv420p với faststart (bản có tiếng giữ AAC), thêm WebM VP9/Opus. Cả ba tệp đã giải mã đủ 667 khung hình; audio của hai bản có tiếng cũng giải mã được. Chi tiết tại `video_compatibility_results.json`. Mở `videos/index.html` bằng Firefox hoặc tải WebM trực tiếp nếu ứng dụng trên máy thiếu codec MP4.
