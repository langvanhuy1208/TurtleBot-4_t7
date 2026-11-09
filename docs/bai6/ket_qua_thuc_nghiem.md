# Phiếu ghi kết quả thực nghiệm

Trạng thái: **đã mở webcam và chạy robot trong Gazebo, chưa quay video nộp bài**.
Kiểm tra chuyển động tự động đã đạt 4 chu kỳ tiến–lùi, vòng tròn, chào và
dừng Open Palm qua nhãn thử. Số liệu ở `validation.md` và
`gazebo_test_results.json`. Bảng dưới dành cho đánh giá lại bằng tay thật.
Không sử dụng các giá trị mong đợi dưới đây như số liệu đã đo.

- Họ tên / MSSV / lớp: [điền]
- Ngày chạy / CPU / RAM / webcam: [điền]
- Ubuntu / ROS / MediaPipe: [điền phiên bản thực tế]
- GitHub Public: [điền URL]
- Video Google Drive công khai: [điền URL]

| Kịch bản | Mong đợi | Đo/quan sát thực tế | Đạt? |
|---|---|---|---|
| Pointing Up, chưa xác nhận | Robot đứng yên, SELECTED | Chưa đo | — |
| Pointing Up → Thumb Up | 4 chu kỳ tiến–lùi | Chưa đo | — |
| Victory → Thumb Up | Một vòng bán kính danh định 0,6 m | Chưa đo | — |
| Wave → Thumb Up | Chào trái–phải hai lần | Chưa đo | — |
| Open Palm giữa hành vi | Lệnh 0 ngay khi callback nhận nhãn | Chưa đo | — |
| Closed Fist giữa hành vi | IDLE, xóa lựa chọn | Chưa đo | — |
| Giữ Thumb Up sau khi xong | Không lặp lại | Chưa đo | — |
| Rút tay khỏi webcam | NONE, hủy và dừng | Chưa đo | — |
| Ngừng node nhận diện | Watchdog dừng sau khoảng 0,8–0,85 s | Chưa đo | — |
| Thiếu scan hoặc vật gần | Hủy và dừng | Chưa đo | — |

Ảnh cần chụp và chèn vào báo cáo trước khi nộp:

1. Webcam hiển thị nhãn, điểm tin cậy và landmark.
2. Gazebo và trạng thái SELECTED khi robot chưa di chuyển.
3. Hành vi tiến–lùi và vòng tròn đang chạy.
4. Open Palm dừng robot và log lý do.

Đánh giá nhận diện: mỗi cử chỉ làm 10 lần dưới cùng điều kiện ánh sáng,
ghi số lần nhận đúng, số nhầm và số không nhận. Độ tin cậy AI hiển thị
trên ảnh không thay thế cho tỉ lệ chính xác đo bằng thực nghiệm.
