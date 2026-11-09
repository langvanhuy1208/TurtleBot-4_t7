# Video demo bài 7

| Tệp | Nội dung |
|---|---|
| `01_demo_giong_tong_hop_Whisper_Nav2.mp4` | Robot Gazebo/AMCL và đường Nav2 được ghi trực tiếp. Đầu vào WAV tiếng Việt tổng hợp được Whisper nhận dạng; có track phát lại WAV ghép trước thời điểm chấp nhận lệnh. |
| `02_demo_du_lieu_goc_khong_ghep_tieng.mp4` | Bản video trực tiếp gốc trước khi thêm track âm thanh tổng hợp. |

Video dài khoảng 2 phút 13 giây, gồm: đến A; A → B; đến phòng thí nghiệm B; đến hành lang C; từ chối khu vực Z. Các điểm/vệt đường lấy từ ROS/AMCL/Nav2 của robot trong Gazebo, không phải quỹ đạo dựng giả.

**Hai video này dùng giọng tổng hợp, không phải bản quay người dùng nói qua micro.** Môi trường đã kiểm tra thu micro thật, nhưng video giọng người do người dùng tự quay có thể bổ sung vào thư mục này sau. Không dùng số liệu 5/5 trên WAV tổng hợp làm độ chính xác giọng người trong tiếng ồn.

Bản đồ demo là bản đồ tham chiếu raster hóa từ `worlds/maze_fast.sdf`; bản đồ SLAM gốc và phân vùng tương ứng được giữ riêng tại `maps/phase2` và `maps/bai7/phase2-segmentation`.

Quay bản mới bằng:

```bash
bash scripts/run_bai7_live.sh
```

Đợi SẴN SÀNG QUAY VIDEO, ghi màn hình kèm micro, nhấn Enter để nói từng lệnh và chờ `completed` trước lệnh tiếp theo. Kịch bản: [READY_TO_RECORD.md](../docs/bai7/READY_TO_RECORD.md).
