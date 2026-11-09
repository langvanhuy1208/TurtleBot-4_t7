# Kịch bản quay video nộp bài

1. Mở ảnh `maps/bai7/segmented_map.png`, chỉ rõ A/B/C và tọa độ đích.
2. Chạy `bash scripts/run_bai7_live.sh`, đợi báo SẴN SÀNG QUAY VIDEO; script tự mở RViz, đặt pose AMCL và chờ Nav2 ACTIVE.
3. Bắt đầu ghi màn hình kèm âm thanh micro. Terminal đã mở đầu vào giọng nói; nhấn Enter để thu từng câu. WAV tự lưu tại `log/bai7_live/microphone_recordings/`.
4. Nói “Đi đến khu vực A”, chỉ ra transcript, trạng thái và robot tới A.
5. Nói “Di chuyển từ khu vực A đến khu vực B”, quay đủ hai lần `arrived`: A rồi B.
6. Nói “Đi đến phòng thí nghiệm”, đối chiếu B.
7. Nói “Đi đến khu vực Z”, chỉ ra `rejected` và không có goal mới.
8. Mở rộng: “Đi từ phòng A qua hành lang rồi đến phòng B”; thử “Dừng lại” khi đang đi.
9. Ghi tên sinh viên, link repo public và link video vào báo cáo; tạo lại PDF.

Video tự động đi kèm dùng WAV giọng tổng hợp (nguồn trong `audio/commands.json`), không chứng minh khả năng thu micro. Video thể hiện dữ liệu robot/đường đi thực từ Gazebo qua AMCL/Nav2; đường màu cam là `/plan`, vệt tím là vị trí AMCL đã nhận.
