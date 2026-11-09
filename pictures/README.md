# Ảnh dùng làm báo cáo bài 7

| Tệp | Nội dung / cách dùng |
|---|---|
| `01_ban_do_slam_goc.png` | Bản đồ SLAM ban đầu, giữ nguyên từ `maps/phase2`. |
| `02_ban_do_tham_chieu_gazebo.png` | Bản đồ raster từ hình học mê cung, dùng cho demo tái lập; không phải bản đồ SLAM mới. |
| `03_phan_vung_A_B_C.png` | Ba khu chức năng, điểm đích và chú giải; nên dùng ở phần segmentation. |
| `04_phan_vung_ban_do_slam_goc.png` | Kết quả áp dụng segmentation lên bản đồ SLAM gốc. |
| `05_so_do_kien_truc.png` | Micro/WAV → Whisper → parser → Nav2 → robot và RViz. |
| `06_quy_trinh_phan_vung.png` | Các bước BFS đa nguồn, chọn đích và chuyển hệ tọa độ. |
| `07_sai_so_dich_do_duoc.png` | Sai số đích cuối từ JSON kiểm thử Gazebo/AMCL thực. |
| `08_demo_dieu_huong_A.png` | Khung hình trích từ video demo trực tiếp, điều hướng tới A. |
| `09_demo_lo_trinh_A_B.png` | Khung hình trích từ video demo trực tiếp, kịch bản A → B. |
| `10_demo_tu_choi_vung_Z.png` | Khung hình cuối demo, từ chối vùng không tồn tại. |
| `11_tong_hop_kiem_thu.png` | Tổng hợp số lượng test từ các tệp kết quả hiện có. |
| `12_RViz_phien_kiem_thu.png` | Ảnh RViz thực được lưu trong phiên tự kiểm thử; Navigation/Localization ACTIVE. Nhãn tên phòng ở ảnh là giao diện trước lần rút gọn còn A/B/C. |

Ảnh sơ đồ được vẽ để giải thích mã nguồn. Các ảnh 08–10 được trích từ video `videos/01_demo_giong_tong_hop_Whisper_Nav2.mp4`; không phải ảnh chụp RViz hay ảnh đo bằng camera ngoài. Số liệu trong biểu đồ lấy từ `docs/bai7/*.json`, không tự đặt.

Gợi ý chọn cho báo cáo 1–2 trang: ảnh 03, 05, 07 và 10. Xem thêm [video và phạm vi thử nghiệm](../videos/README.md).

Tái tạo ảnh/video từ tài nguyên hiện có: `python3 docs/bai7/prepare_media.py` (cần Pillow, OpenCV, Matplotlib, NumPy và các tệp nguồn trong dự án).
