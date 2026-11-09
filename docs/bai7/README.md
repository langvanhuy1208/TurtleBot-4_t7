# Bài thực hành 7 — Phân vùng bản đồ và điều hướng bằng giọng nói

Hệ thống ROS 2 Humble cho TurtleBot 4: âm thanh tiếng Việt → Whisper chạy cục bộ → danh sách khu vực → từng action `NavigateToPose`. Mã chạy chính không sử dụng API trả phí hay API key.

## Chạy để quay video — một lệnh

```bash
cd /home/huy/tb4_simplesimu
bash scripts/run_bai7_live.sh
```

Script mở RViz và Gazebo headless, kiểm tra bản đồ, tự đặt pose AMCL, chờ Nav2 ACTIVE rồi báo **SẴN SÀNG QUAY VIDEO**. Nhấn Enter, nói lệnh trong 6 giây rồi chờ robot tới nơi. Terminal hiển thị transcript và trạng thái điều hướng trong lúc robot chạy. Ctrl+C dừng cả đầu vào và mô phỏng. WAV micro và log được lưu trong `log/bai7_live/`, không đưa vào gói public tự động. Script dành cho một phiên mô phỏng mới, không chạy hai phiên cùng lúc.

Đầu vào tự chọn PulseAudio qua `parec` trên máy này; không cần PortAudio. Đã kiểm tra micro thật 16 kHz mono trong `microphone_test_results.json` (chỉ xác minh thu âm, chưa đo nhận dạng giọng người có nhãn). Có thể dùng `--audio-backend sounddevice --device 0` khi đã cài PortAudio; hoặc `--pulse-source TEN_SOURCE` để chọn nguồn PulseAudio khác.

## Những tệp cần nộp

- Mã nguồn: `scripts/semantic_map.py`, `segment_map.py`, `voice_input.py`, `voice_navigation_node.py`, `map_from_world.py`; launch `launch/voice_navigation.launch.py`.
- Bản đồ SLAM được cung cấp ban đầu: `maps/phase2/map.pgm`, `map.yaml`, được giữ nguyên.
- Phân vùng bản đồ SLAM cũ: `maps/bai7/phase2-segmentation/` (PGM, YAML, ảnh màu, labels 16-bit và vùng/đích).
- Bản đồ chạy demo: `maps/bai7/`, kèm `provenance.txt`. Đây là bản đồ tham chiếu tạo từ collision box của `worlds/maze_fast.sdf`, **không phải kết quả đo SLAM mới**. Trục map trùng world, giúp tái lập vị trí ban đầu và kết quả mô phỏng. Không dùng pose map của bản đồ SLAM cũ làm pose world.
- Báo cáo: `docs/bai7/bao_cao.pdf`; số liệu kiểm thử JSON cùng thư mục.
- Video có âm thanh `demo_voice_navigation.mp4` và bản gốc không ghép tiếng `demo_navigation.mp4`: xem trường `input` trong `gazebo_test_results.json` để biết bản ghi dùng văn bản hay Whisper trên âm thanh tổng hợp. Không coi bản tổng hợp là bản thu giọng người qua micro.

## 1. Cài đặt và build

Chạy ở thư mục gốc repository trên Ubuntu 22.04 có ROS 2 Humble và TurtleBot 4 Simulation:

```bash
sudo apt update
sudo apt install python3-venv python3-pip python3-opencv python3-numpy \
  python3-yaml python3-pil python3-pytest python3-reportlab pulseaudio-utils libportaudio2 \
  ros-humble-nav2-msgs ros-humble-visualization-msgs
source /opt/ros/humble/setup.bash
colcon build --packages-select tb4_simplesimu --symlink-install
source install/setup.bash
/usr/bin/python3 -m venv --system-site-packages .venv-voice
.venv-voice/bin/python -m pip install -r requirements-voice.txt
```

Dùng venv có system site packages để đọc được `rclpy`/OpenCV từ apt. NumPy được giới hạn dưới 2 để tương thích các extension ROS Humble. Không chạy `pip install` vào Python hệ thống. Tải mô hình `small` cần mạng lần đầu; lần sau có thể chỉ định thư mục mô hình cục bộ. Kiểm thử ngoài sandbox đã xác minh thu âm micro thật qua PulseAudio; độ chính xác giọng người có nhãn vẫn cần đo khi quay video.

## 2. Phân vùng và gắn nhãn

```bash
python3 scripts/map_from_world.py --world worlds/maze_fast.sdf --output maps/bai7
python3 scripts/segment_map.py --map maps/bai7/map.yaml \
  --seeds config/regions_seed.yaml --output maps/bai7
```

Phương pháp bán tự động: chọn ba hạt giống trong không gian trống, sau đó lan nhãn BFS đa nguồn trên đồ thị ô trống 4 lân cận. Khoảng cách là khoảng cách đường đi trên bản đồ, nên nhãn không xuyên tường. Đây là các **khu chức năng gán thủ công**, không phải mô hình tự suy ra ý nghĩa phòng học/phòng thí nghiệm từ ảnh. Ô có vật cản, ô chưa biết và vùng rời không tiếp cận từ hạt giống giữ nhãn 0. Điểm đích gần hạt giống nhất phải cách vật cản ít nhất 0,35 m, tính bằng distance transform OpenCV; không lấy tâm hình học có thể nằm trong tường.

| ID | Nhãn | Hạt giống map (m) |
|---|---|---|
| A | Phòng học | (-2, 0) |
| B | Phòng thí nghiệm | (2, 3) |
| C | Hành lang | (2, -3) |

Đích thực dùng tâm ô và được lưu chính xác trong `regions.yaml`. Với pixel `(u,v)`, chiều cao ảnh `H`, resolution `r`: `x_local=(u+0.5)r`, `y_local=(H-v-0.5)r`. Sau đó xoay theo yaw origin rồi cộng origin XY. Mã hỗ trợ origin có góc quay. `labels.png` là ảnh nhãn uint16; ảnh màu chỉ dùng trình bày, **không thay PGM của Nav2**.

Đối với map SLAM khác, đặt hạt giống đúng trong hệ `map` của map đó, dùng cùng file map cho Nav2 và segmentation:

```bash
python3 scripts/segment_map.py --map /duong/dan/map.yaml \
  --seeds /duong/dan/seeds.yaml --output /duong/dan/semantic
ros2 launch tb4_simplesimu voice_navigation.launch.py \
  regions_file:=/duong/dan/semantic/regions.yaml
```

Catalog kiểm tra SHA-256 map, vị trí đích, ô trống, clearance và membership vùng lúc khởi động. Nếu sửa map, phải chạy lại segmentation. Bản sao SLAM cũ dùng `free_thresh: 0.196` để pixel 205 được giữ là chưa biết; YAML cũ có 0.25 có thể phân loại pixel 205 thành trống. Mã segmentation tuân thủ threshold YAML, không tự sửa pixel của bản đồ gốc.

## 3. Chạy mô phỏng và điều hướng

Terminal 1:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch tb4_simplesimu voice_navigation.launch.py simulation:=true
```

Launch bài 7 dùng Ogre2 cho cảm biến mô phỏng nhẹ và giữ timestamp đo LiDAR gốc. Mặc định giữ LiDAR/IMU và giảm cảm biến hiển thị để tiết kiệm CPU; dùng `lightweight_sensors:=false` nếu cần toàn bộ cảm biến mô phỏng.

Trong RViz dùng **2D Pose Estimate**: robot mặc định spawn `(2, 0)` hướng `π` trong world và bản đồ tham chiếu. Chờ AMCL định vị và lifecycle Nav2 ACTIVE. Có thể kiểm tra `ros2 lifecycle get /bt_navigator`. Khởi động đầu vào ở terminal 2 cùng ROS_DOMAIN_ID/RMW với terminal 1:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
.venv-voice/bin/python scripts/voice_input.py --model small \
  --seconds 6 --save-audio docs/bai7/microphone_recordings
```

Nhấn Enter, nói trong 6 giây, chờ transcript và trạng thái. Cơ chế nhấn để thu giúp tránh nhận lệnh từ hội thoại nền. Nếu cần chọn micro:

```bash
.venv-voice/bin/python -m sounddevice
.venv-voice/bin/python scripts/voice_input.py --device 0 --seconds 7
```

Whisper dùng tiếng Việt, CPU int8, VAD loại khoảng im lặng và lọc đoạn có xác suất không có lời nói cao. Từ chối âm lượng quá nhỏ; không gửi lệnh nếu transcript rỗng. Không sử dụng prompt chứa sẵn tên đích để ép nhận dạng. Mô hình `small` được chọn cho vận hành; `base` được giữ làm đối chứng trong kết quả thử nghiệm.

Các câu lệnh:

- “Đi đến khu vực A.”
- “Di chuyển từ khu vực A đến khu vực B.” — luôn đi A thành công rồi mới đến B.
- “Đi đến phòng thí nghiệm.”
- “Đi đến hành lang.”
- “Đi từ phòng A qua hành lang rồi đến phòng B.”
- “Đi đến khu vực Z.” — từ chối toàn bộ, không gửi action.
- “Dừng lại.” hoặc “Hủy điều hướng.” — hủy chặng hiện tại và xóa phần còn lại.

Alias “hành lan” được thêm có chủ đích cho C sau khi quan sát lỗi phiên âm của Whisper; các vùng khác vẫn cần khớp alias đầy đủ. Bộ phân tích chuẩn hóa chữ hoa/thường, dấu tiếng Việt và dấu câu; tên vùng phải khớp alias đầy đủ. Không tìm nhãn A/B/C bằng substring. Tên không có trong catalog, nguồn không tồn tại, phủ định và cấu trúc không hỗ trợ đều bị từ chối. Không chấp nhận lệnh mới khi robot đang đi; cần dừng trước. Nếu Nav2 báo thất bại/timeout, không đi tiếp vùng sau. Bộ điều hướng giữ trạng thái bận trong lúc chờ phản hồi hủy, tránh gửi mục tiêu chồng lên nhau.

Để kiểm tra độc lập với ASR:

```bash
.venv-voice/bin/python scripts/voice_input.py --text 'Đi từ phòng A qua hành lang rồi đến phòng B'
.venv-voice/bin/python scripts/voice_input.py --wav docs/bai7/audio/01.wav --model small
ros2 topic echo /voice_nav/status
```

`--text` chỉ kiểm tra parsing/Nav2, không được tính là thử nghiệm giọng nói.

## 4. Topic và RViz

| Giao diện | Kiểu | Nội dung |
|---|---|---|
| `/voice_command` | `std_msgs/String` | Lệnh sau nhận dạng hoặc lệnh test |
| `/voice_nav/transcript` | `std_msgs/String` | Văn bản ASR |
| `/voice_nav/status` | `std_msgs/String` JSON | accepted, navigating, arrived, completed, rejected, timeout, cancelling, cancelled, failed |
| `/semantic_regions` | `visualization_msgs/MarkerArray` | Nhãn và điểm đích A/B/C |
| `/voice_nav/route` | `visualization_msgs/Marker` | Thứ tự waypoint nối thẳng |
| `/navigate_to_pose` | `nav2_msgs/action/NavigateToPose` | Action gửi từng chặng |
| `/plan` | `nav_msgs/Path` | Đường thực do Nav2 lập |

Cấu hình RViz bài 7 đã bật hai marker. Nếu dùng RViz khác, thêm MarkerArray `/semantic_regions` và Marker `/voice_nav/route`, durability Transient Local. Đường nối waypoint biểu diễn thứ tự đi; đường tránh tường phải xem `/plan`, không dùng đoạn thẳng giữa các tâm vùng làm quỹ đạo robot.

## 5. Kiểm thử và quay demo

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_semantic_navigation.py tests/test_voice_audio.py
python3 tests/ros_voice_smoke.py
# Với một mô phỏng mới đang chạy: python3 tests/gazebo_voice_extended.py
.venv-voice/bin/python tests/whisper_voice_smoke.py --model small
```

`ros_voice_smoke.py` remap action và topic sang `/bai7_test/*`, sử dụng Nav2 giả, kiểm tra DDS/action thực nhưng **không đo chuyển động robot**. Các tests bản đồ xác nhận cùng thành phần liên thông sau khi chừa bán kính 0,25 m. Bảo đảm không có node điều hướng khác khi chạy demo chuyển động. Nếu DDS báo lỗi multicast trên máy, dùng `export CYCLONEDDS_URI=file://$PWD/config/cyclonedds_local.xml` và cùng `ROS_DOMAIN_ID` ở các terminal; cấu hình này dùng loopback cho mô phỏng trên một máy.

Chạy video tự động khi Gazebo/Nav2 bài 7 vừa khởi động, robot ở pose spawn, dùng đầu vào WAV tổng hợp đã đính kèm:

```bash
export HF_HOME="$PWD/.cache-voice/huggingface"  # chỉ khi dùng cache trong workspace này
python3 tests/gazebo_voice_demo.py --speech --model small
```

Script đợi AMCL và lifecycle ACTIVE, gọi Whisper trên WAV, lưu MP4 từ dữ liệu live AMCL và đường `/plan`, lưu kết quả từng lệnh vào `gazebo_test_results.json`. Đây là video bản đồ trực tiếp, không phải video dựng quỹ đạo giả. Nhãn nguồn âm thanh tổng hợp hiển thị trên video. Không khởi động lại script giữa hành trình rồi coi vị trí hiện tại là pose spawn. Sau khi quay, chạy `.venv-voice/bin/python docs/bai7/add_demo_audio.py` để thêm track phát lại WAV tổng hợp trước thời điểm chấp nhận lệnh; thời điểm ghép được lưu trong `demo_audio_cues.json`. Track này là phần trình bày, không phải âm thanh micro.

Để có video đúng yêu cầu **giọng nói của sinh viên**: dùng OBS hoặc trình ghi màn hình Ubuntu, ghi cả âm thanh micro, RViz, terminal transcript/status; nói ba lệnh đầu, lệnh nhiều điểm và lệnh Z. Lưu WAV qua `--save-audio`, đo số lệnh nhận đúng/tổng số, thời gian, sai số vị trí từ AMCL. Không thay các số liệu mẫu thành kết quả micro chưa đo.

Có thể tái tạo fixture offline bằng `python3 scripts/make_voice_fixtures.py` nếu có libespeak-ng; giọng eSpeak không được Whisper base nhận tốt trong lần thử và số liệu thất bại được giữ riêng. Fixture WAV hiện hành ghi rõ nguồn trong `audio/commands.json`. Tạo lại giọng Google TTS là bước tùy chọn, cần gTTS/PyAV và mạng; không cần gTTS khi vận hành robot.

## 6. GitHub và hoàn thiện nộp bài

Bản làm việc chứa cả bài cũ và thay đổi chưa commit của người dùng. Theo yêu cầu hiện tại, hoàn tất tự kiểm thử và quay video trước; GitHub thực hiện sau khi người dùng yêu cầu. Gói `release/bai7_submission.zip` chứa nguồn package và tài liệu cần thiết; loại trừ cache mô hình, venv, build/install/log và `.git`.

Tạo repository GitHub public dành cho bài 7, giải nén gói và chạy trong thư mục vừa giải nén:

```bash
git init
git add .
git commit -m 'Bai 7: semantic mapping and Vietnamese voice navigation'
git branch -M main
git remote add origin https://github.com/TAI_KHOAN/TEN_REPO.git
git push -u origin main
```

Theo yêu cầu mới nhất, người dùng tự làm báo cáo; file PDF/script mẫu cũ vẫn được giữ để tham khảo. GitHub thực hiện sau khi người dùng test/quay xong và yêu cầu. Báo cáo chỉ được ghi “đạt yêu cầu” đối với các mục đã có dữ liệu thực; thử nghiệm tiếng nói qua micro vẫn cần người thực hiện.

## Tài liệu kỹ thuật

- [Nav2 Humble NavigateToPose](https://api.nav2.org/actions/humble/navigatetopose.html): mục tiêu pose trong frame map và phản hồi action.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper): mô hình đa ngôn ngữ, CPU int8 và VAD.
