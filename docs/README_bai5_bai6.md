# TurtleBot 4 — Bài 6: điều khiển bằng cử chỉ tay

Bài làm mới: **[Hướng dẫn cài đặt, chạy và giải thích Bài 6](bai6/README.md)**.
Gồm `gesture_recognition_node`, `robot_behavior_node`, launch sân rộng,
lọc nhiễu, xác nhận bằng Thumbs Up, dừng khi mất tín hiệu và kiểm tra LiDAR.
Báo cáo: [PDF](bai6/bao_cao.pdf). Kết quả demo thực tế và các link nộp
bài cần bổ sung theo [phiếu thực nghiệm](bai6/ket_qua_thuc_nghiem.md).

---

# Tài liệu mô phỏng, SLAM và Navigation trước đây (ROS 2 Humble)

Package này khởi chạy TurtleBot 4 trong Ignition Gazebo, lập bản đồ bằng
SLAM Toolbox, sau đó dùng bản đồ để localization và autonomous navigation
với Nav2. Các launch wrapper trong `launch/` mặc định dùng world `maze`.

## 1. Yêu cầu và cài đặt

Môi trường mục tiêu: Ubuntu 22.04, ROS 2 Humble Desktop và TurtleBot 4
Simulator bản Humble (Ignition Fortress).

```bash
sudo apt update
sudo apt install \
  ros-humble-desktop \
  ros-humble-turtlebot4-simulator \
  ros-humble-turtlebot4-navigation \
  ros-humble-slam-toolbox \
  ros-humble-nav2-map-server \
  ros-humble-nav2-simple-commander \
  ros-humble-cv-bridge \
  python3-opencv \
  ros-humble-teleop-twist-keyboard \
  python3-colcon-common-extensions
# Install CPU-only PyTorch first to avoid pulling CUDA libraries on CPU-only machines.
python3 -m pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision
python3 -m pip install 'numpy<2' 'opencv-python<5' ultralytics
```

Build package từ thư mục này:

```bash
source /opt/ros/humble/setup.bash
cd ~/tb4_simplesimu
colcon build --symlink-install
source install/setup.bash
```

Nếu repository được clone vào đường dẫn khác, thay `~/tb4_simplesimu` bằng
đường dẫn thực tế. Mỗi terminal mới cần nạp lại môi trường:

```bash
source /opt/ros/humble/setup.bash
source ~/tb4_simplesimu/install/setup.bash
```

## 2. Chạy mô phỏng và kiểm tra topic

Wrapper dưới đây bật Gazebo, robot và RViz2. Nó dùng robot description mô
phỏng trong `urdf/standard/` để phần vỏ của RPLIDAR không tự che các tia
GPU LiDAR; xacro gốc của TurtleBot 4 được giữ nguyên trong hệ thống:

```bash
ros2 launch tb4_simplesimu turtlebot4_ignition_fast.launch.py \
  world:=maze model:=standard rviz:=true
```

Kiểm tra `/scan` có các khoảng cách thay đổi và lớn hơn `range_min` ở nhiều
góc trước khi bật Nav2. Nếu mọi tia đều bằng `0.164`, không gửi goal; kiểm
tra lại robot description và Gazebo trước. Sau đó kiểm tra odometry và
publisher/subscriber của velocity:

```bash
ros2 topic echo /scan --once
ros2 topic echo /odom --once
ros2 topic info /cmd_vel
```

Thử điều khiển bằng bàn phím trong một terminal khác:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args -r cmd_vel:=/cmd_vel
```

Nếu robot không nhận lệnh, kiểm tra tên topic thực tế bằng `ros2 topic list`
và `ros2 topic info /cmd_vel`. Dừng teleop bằng `Ctrl+C`.

## 3. Tạo bản đồ bằng SLAM Toolbox

Đóng simulator ở bước trước, rồi chạy wrapper SLAM (wrapper tự khởi động
Gazebo, robot, RViz2 và SLAM Toolbox):

```bash
ros2 launch tb4_simplesimu sim_slam.launch.py
```

Simulator Humble tạo robot cùng dock ở vị trí xuất phát. Launch này tự xóa
model `standard_dock` sau 10 giây để robot có thể di chuyển và khảo sát map.

Có thể đổi world hoặc model:

```bash
ros2 launch tb4_simplesimu sim_slam.launch.py \
  world:=maze model:=lite
```

Trong terminal khác, điều khiển robot bằng teleop:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args -r cmd_vel:=/cmd_vel
```

Di chuyển chậm, khảo sát các khu vực có thể đi qua và tạo các vòng đi có
phần chồng lặp để SLAM khép vòng tốt hơn. Trong RViz2, đặt **Fixed Frame**
thành `map`; hiển thị **Map** (`/map`) và **LaserScan** (`/scan`) nếu chúng
chưa có trong layout.

Có thể chạy bộ khảo sát tự động thay cho teleop:

```bash
ros2 run tb4_simplesimu auto_mapper.py
```

Dừng nó bằng `Ctrl+C`; node sẽ phát lệnh dừng trước khi thoát.

Khi bản đồ hoàn chỉnh, mở terminal mới (giữ SLAM/Gazebo đang chạy), rồi lưu
map vào thư mục `maps/` của package:

```bash
cd ~/tb4_simplesimu
ros2 run nav2_map_server map_saver_cli -f "$(pwd)/maps/map"
```

Map saver sẽ tạo/cập nhật `maps/map.yaml` và `maps/map.pgm`. Dừng teleop và
SLAM bằng `Ctrl+C` sau khi đã lưu. Nếu cần giữ lại bản đồ đi kèm repository,
hãy sao lưu hai file hiện tại trước khi ghi đè.

Snapshot mới từ lần chạy mô phỏng này được lưu riêng tại
`maps/phase2/map.yaml` và `maps/phase2/map.pgm`, không ghi đè `maps/map.*`.
Tại thời điểm lưu, khoảng 51.4% ô trong lưới occupancy đã được quan sát; đây
chưa phải bản đồ hoàn chỉnh của toàn bộ maze, nên cần khảo sát tiếp trước khi
dùng cho navigation toàn khu vực.
Để dùng snapshot đó cho localization/Nav2, truyền đường dẫn:

```bash
ros2 launch tb4_simplesimu sim_nav.launch.py \
  map:="$(pwd)/maps/phase2/map.yaml"
```

## 4. Localization và Nav2 trên bản đồ đã lưu

Sau khi dừng SLAM, chạy wrapper navigation. Wrapper khởi động lại mô phỏng,
nạp map, chạy localization (AMCL) và Nav2:

```bash
cd ~/tb4_simplesimu
ros2 launch tb4_simplesimu sim_nav.launch.py \
  map:="$(pwd)/maps/phase2/map.yaml"
```

Đặt pose ban đầu bằng công cụ **2D Pose Estimate** trong RViz2, đúng với vị
trí và hướng robot trong Gazebo. Chờ pose trên map hội tụ trước khi gửi goal.
Nếu cần thay đổi world, spawn pose hoặc model:

```bash
ros2 launch tb4_simplesimu sim_nav.launch.py \
  world:=maze model:=standard x:=2.0 y:=0.0 yaw:=3.14159 \
  map:="$HOME/tb4_simplesimu/maps/phase2/map.yaml"
```

Wrapper dùng `config/nav.rviz` với góc nhìn top-down, map, robot, LiDAR và
đường đi. Có thể dùng **Publish Point** hoặc `/amcl_pose` để khảo sát pose;
trong lần demo tự động, các mục tiêu được gửi từ node Python bên dưới, không
đặt goal bằng chuột trên RViz2.

## 5. Autonomous Navigation và YOLO

Chạy demo tích hợp sau khi build package và cài Ultralytics. Launch khởi chạy
Gazebo, map server, AMCL/Nav2, RViz2, node waypoint và node YOLO:

```bash
ros2 launch tb4_simplesimu autonomous_demo.launch.py \
  map:="$(pwd)/maps/phase2/map.yaml" \
  world:=maze model:=standard
```

Launch mặc định khởi tạo AMCL ở pose spawn `(2, 0, π)` sau khi simulation clock
và TF đã sẵn sàng, rồi chạy ba goal demo xa nhau trên các vùng map đã biết:
`(4, 3, 1.57) → (0, 2.5, π) → (0, -3, -1.57)`. Ước lượng đường tự do trên
map lần lượt dài khoảng 4.1 m, 4.7 m và 5.5 m. Các điểm này chỉ áp dụng cho
`maze` và map `phase2` hiện tại.
World đi kèm giữ nguyên hình học maze và dùng physics 1 kHz để tương thích
chu kỳ cập nhật 1 ms của ros2_control; Gazebo chạy
headless mặc định để Nav2 có đủ tài nguyên, còn RViz2 và cửa sổ YOLO vẫn hiển thị.
Truyền `headless:=false` nếu muốn mở thêm cửa sổ Gazebo để quay video.
Khi thay map/world hoặc spawn pose, hãy đo lại ít nhất ba pose trên RViz2 rồi
truyền chúng qua `goal_x`, `goal_y`, `goal_yaw` (các dãy phải cùng độ dài):

```bash
ros2 launch tb4_simplesimu autonomous_demo.launch.py \
  map:="$(pwd)/maps/phase2/map.yaml" \
  goal_x:='[1.0, 2.0, 2.5]' goal_y:='[0.5, 1.0, -0.5]' \
  goal_yaw:='[3.14159, 0.0, -1.57]'
```

Để khảo sát tọa độ, dùng **Publish Point** để đọc `(x,y)` trên `/clicked_point`
và ghi yaw mong muốn. Launch demo chỉ gửi initial pose sau khi simulation
clock, `/odom` và TF `odom → base_link` đã sẵn sàng; sau đó đợi AMCL trước khi
gửi goal. Nếu chạy `sim_nav.launch.py` riêng, đặt **2D Pose Estimate** trước
khi gửi mục tiêu. Navigator gửi các goal theo thứ tự, log kết quả và dừng
chuỗi khi có goal thất bại. Không chạy teleop hoặc đặt Nav2 Goal thủ công
trong lúc node điều khiển đang chạy.

YOLO mặc định nghe `/oakd/rgb/preview/image_raw`, dùng model `yolov8n.pt`,
hiển thị cửa sổ OpenCV và publish ảnh có bounding box lên
`/yolo/detections/image`. Lần đầu chạy Ultralytics có thể tải model pretrained
từ internet. Nếu topic camera khác trong mô phỏng, kiểm tra bằng
`ros2 topic list` rồi truyền tên phù hợp:

```bash
ros2 launch tb4_simplesimu autonomous_demo.launch.py \
  image_topic:=/oakd/rgb/preview/image_raw yolo_model:=yolov8n.pt
```

Các node cũng chạy riêng được:

```bash
ros2 run tb4_simplesimu waypoint_navigator.py --ros-args \
  -p set_initial_pose:=true -p initial_x:=2.0 -p initial_y:=0.0 \
  -p initial_yaw:=3.14159 -p goal_x:='[4.0, 0.0, 0.0]' \
  -p goal_y:='[3.0, 2.5, -3.0]' -p goal_yaw:='[1.57, 3.14159, -1.57]'
ros2 run tb4_simplesimu yolo_detector.py --ros-args \
  -p image_topic:=/oakd/rgb/preview/image_raw
```

Lệnh chạy tự động tích hợp bên trên là cách đơn giản nhất để quay demo. Nếu
chỉ kiểm tra phần 3, dùng `start_yolo:=false` để không mở camera/inference.
Node sẽ tự publish initial pose theo `x`, `y`, `yaw` của spawn khi simulation
clock, `/odom` và TF `odom → base_link` sẵn sàng. Scan đầu vào được đồng bộ
timestamp và giảm xuống 5 Hz trên `/scan_nav` để AMCL/costmap không bị nghẽn
với dữ liệu cũ. Cấu hình costmap dùng topic tuyệt đối `/scan_nav` để tránh
ROS tự thêm namespace `/local_costmap` hoặc `/global_costmap`, làm mất scan
tránh vật cản. TF odometry giữ nguyên timestamp từ `/odom`. Đặt
`set_initial_pose:=false` nếu muốn tự đặt pose bằng RViz2.

Node điều hướng dùng `nav2_simple_commander` (`BasicNavigator`) và action
Nav2 NavigateToPose. Node nhận diện subscribe `sensor_msgs/Image`, chuyển ảnh
qua `cv_bridge`, chạy Ultralytics YOLO rồi log class/confidence và publish
ảnh đã vẽ. Các thành phần chính khác gồm AMCL, map server, `/map`, `/scan`,
`/tf` và RViz2.

Lưu ý: snapshot `maps/phase2` đi kèm repo hiện chỉ quan sát được khoảng
51.4% ô occupancy khi lưu theo ghi chú ở trên. Các goal demo nằm trong phần
đã biết của map; hãy khảo sát/lưu map đầy đủ nếu cần điều hướng toàn maze.

## 6. Launch files và dữ liệu

- `launch/sim_slam.launch.py`: mô phỏng TurtleBot 4 và SLAM Toolbox, dùng
  simulation time.
- `launch/sim_nav.launch.py`: mô phỏng, localization và Nav2 trên map được
  truyền qua tham số `map`.
- `launch/autonomous_demo.launch.py`: chạy Nav2, điều hướng waypoint và YOLO.
- `launch/ignition_fast.launch.py`, `worlds/maze_fast.sdf`: chạy world maze ở
  100 Hz, giảm tải physics; có thể bật GUI bằng `headless:=false`.
- `scripts/waypoint_navigator.py`: gửi tuần tự các pose map-frame bằng Nav2.
- `scripts/scan_retimestamp.py`: đồng bộ timestamp `/scan` sang `/scan_nav`.
- `scripts/yolo_detector.py`: nhận ảnh camera, phát hiện vật thể và publish ảnh kết quả.
- `docs/bao_cao.md`: mẫu báo cáo ngắn để chèn ảnh/video/repository sau khi demo.
- `config/slam.yaml`: đặt minimum laser range khớp với LiDAR của simulator.
- `config/nav.rviz`: bố cục RViz2 gọn cho map, LiDAR và đường đi Nav2.
- `maps/phase2/map.yaml`, `maps/phase2/map.pgm`: map mặc định navigation,
  snapshot khảo sát được lưu riêng (có thể đổi bằng tham số `map`).
- Topic chính: `/scan`, `/odom`, `/cmd_vel`, `/map`, `/tf`.

Nếu thay đổi launch hoặc map, build lại package khi cần và source lại
`install/setup.bash` trong terminal mới. Mọi launch sử dụng Gazebo phải dùng
simulation time để dữ liệu TF, SLAM và Nav2 đồng bộ.

## Bài thực hành 7: phân vùng bản đồ và điều hướng giọng nói

Mã chạy, bản đồ phân vùng A/B/C, Whisper tiếng Việt, Nav2 nhiều điểm, kiểm thử và báo cáo nằm trong [hướng dẫn bài 7](docs/bai7/README.md). Launch: `ros2 launch tb4_simplesimu voice_navigation.launch.py simulation:=true`. Đọc hướng dẫn để chọn đúng bản đồ và đặt pose AMCL trước khi điều hướng.
