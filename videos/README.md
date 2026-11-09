# Video demo bài 7 — bản đã sửa định dạng

## Cách mở

- **Trên máy:** mở `index.html` trong thư mục này bằng Firefox rồi nhấn ▶. Trang xem ưu tiên WebM và có MP4 dự phòng.
- Hoặc mở trực tiếp **`03_demo_mo_bang_Firefox.webm` bằng Firefox**.
- Hai tệp `.mp4` đã đổi sang H.264/yuv420p; bản có tiếng dùng AAC, moov atom đặt đầu tệp (faststart). Không còn dùng codec MPEG-4 Part 2 trong thư mục `videos/`.
- **Trên GitHub:** nếu trang tệp không hiện trình phát, bấm **Download raw file** để tải. Muốn dùng `index.html`, tải/clone cả thư mục để các tệp video nằm cùng chỗ.

[Tải MP4 có tiếng](https://github.com/langvanhuy1208/TurtleBot-4_t7/raw/refs/heads/main/videos/01_demo_giong_tong_hop_Whisper_Nav2.mp4) · [Tải WebM dự phòng](https://github.com/langvanhuy1208/TurtleBot-4_t7/raw/refs/heads/main/videos/03_demo_mo_bang_Firefox.webm)

| Tệp | Nội dung |
|---|---|
| `01_demo_giong_tong_hop_Whisper_Nav2.mp4` | Robot Gazebo/AMCL và đường Nav2 được ghi trực tiếp. Đầu vào WAV tiếng Việt tổng hợp được Whisper nhận dạng; có track phát lại WAV ghép trước thời điểm chấp nhận lệnh. |
| `02_demo_du_lieu_goc_khong_ghep_tieng.mp4` | Bản video trực tiếp gốc trước khi thêm track âm thanh tổng hợp. |

| `03_demo_mo_bang_Firefox.webm` | Cùng demo có tiếng, mã hóa VP9/Opus để mở bằng Firefox khi MP4 thiếu codec hệ thống. |
| `index.html` | Trang xem cục bộ, nhấn ▶ để phát. |

Video dài khoảng 2 phút 13 giây, gồm: đến A; A → B; đến phòng thí nghiệm B; đến hành lang C; từ chối khu vực Z. Các điểm/vệt đường lấy từ ROS/AMCL/Nav2 của robot trong Gazebo, không phải quỹ đạo dựng giả.

**Nguồn câu lệnh của demo có tiếng là giọng tổng hợp, không phải bản quay người dùng nói qua micro.** Môi trường đã kiểm tra thu micro thật, nhưng video giọng người do người dùng tự quay có thể bổ sung vào thư mục này sau. Không dùng số liệu 5/5 trên WAV tổng hợp làm độ chính xác giọng người trong tiếng ồn.

Bản đồ demo là bản đồ tham chiếu raster hóa từ `worlds/maze_fast.sdf`; bản đồ SLAM gốc và phân vùng tương ứng được giữ riêng tại `maps/phase2` và `maps/bai7/phase2-segmentation`.

Quay bản mới bằng:

```bash
bash scripts/run_bai7_live.sh
```

Đợi SẴN SÀNG QUAY VIDEO, ghi màn hình kèm micro, nhấn Enter để nói từng lệnh và chờ `completed` trước lệnh tiếp theo. Kịch bản: [READY_TO_RECORD.md](../docs/bai7/READY_TO_RECORD.md).

## Xác minh định dạng

Cả ba tệp được giải mã kiểm tra đầy đủ 667 khung hình; hai bản có tiếng đều có audio giải mã được. Kết quả codec, thời lượng, checksum và faststart nằm trong [`video_compatibility_results.json`](../docs/bai7/video_compatibility_results.json). Kiểm tra này xác minh tệp dữ liệu, không bảo đảm mọi ứng dụng trên mọi máy đều có codec cài sẵn.

Tái mã hóa: `.venv-voice/bin/python docs/bai7/encode_compatible_videos.py`. Tệp đo gốc tại `docs/bai7/demo_*.mp4` vẫn được giữ để đối chiếu; nên mở các bản tương thích trong `videos/`.

Tham khảo khả năng tương thích: [MDN video codecs](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Formats/Video_codecs), [Firefox video/audio support](https://support.mozilla.org/en-US/kb/audio-and-video-firefox).
