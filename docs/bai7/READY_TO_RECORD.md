# Chạy và quay video bài 7

```bash
cd /home/huy/tb4_simplesimu
bash scripts/run_bai7_live.sh
```

Không cần đặt pose bằng tay. Script tự mở RViz, đặt pose AMCL đúng vị trí spawn và chờ Nav2 ACTIVE. Khi hiện **SẴN SÀNG QUAY VIDEO**, bắt đầu quay màn hình và âm thanh micro.

Nhấn Enter rồi nói trong 6 giây. Chờ dòng `completed` trước lệnh tiếp theo:

1. “Đi đến khu vực A.”
2. “Di chuyển từ khu vực A đến khu vực B.”
3. “Đi đến phòng thí nghiệm.”
4. “Đi đến khu vực Z.” → phải báo `rejected`.
5. Tùy chọn: “Đi từ phòng A qua hành lang rồi đến phòng B.”
6. Thử khi đang chạy: nhấn Enter, nói “Dừng lại.” → `cancelling` rồi `cancelled`.

Terminal hiển thị phiên âm và trạng thái trong lúc robot chạy. RViz hiển thị nhãn A/B/C, điểm đích và đường Nav2. Ctrl+C dừng phiên chạy. WAV micro và log tự lưu dưới `log/bai7_live/`.

Micro mặc định: đầu vào USB C-Media của máy, thu qua PulseAudio. Nếu muốn đổi, dùng Sound Settings của Ubuntu hoặc `--pulse-source TEN_SOURCE`. Không chọn nguồn `.monitor` (âm thanh loa).

Giọng người thật có thể khác các mẫu tổng hợp đã test. Nếu phiên âm sai, nói lại rõ ràng; lệnh sai tên vùng sẽ bị từ chối. Không gửi lệnh mới khi robot đang chạy; nói dừng trước.

Báo cáo do người dùng tự làm. GitHub chỉ thực hiện sau khi người dùng test/quay xong và yêu cầu đẩy mã.
