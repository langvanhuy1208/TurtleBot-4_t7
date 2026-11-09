# Báo cáo thực hành: TurtleBot 4 Navigation và nhận diện vật thể

**Sinh viên:** [Điền họ tên]  
**Lớp:** [Điền lớp]  
**Môi trường mô phỏng:** TurtleBot 4, Gazebo Ignition Fortress, world `maze`  
**Bản đồ:** `maps/phase2/map.yaml` và `maps/phase2/map.pgm`

## 1. Mục tiêu và cấu trúc chương trình

Chương trình nạp bản đồ đã lưu, định vị robot bằng AMCL, dùng Nav2 lập kế
hoạch và điều khiển robot qua các pose trong hệ tọa độ `map`. Node camera
nhận ảnh RGB, chuyển `sensor_msgs/Image` sang OpenCV qua `cv_bridge`, chạy
Ultralytics YOLO và xuất ảnh đã vẽ bounding box cùng thông tin class/confidence.

Luồng xử lý:

1. `sim_nav.launch.py` khởi chạy Gazebo, TurtleBot 4, map server, AMCL,
   Nav2 và RViz2 với simulation time.
2. `robot_description_sim.launch.py` dùng xacro mô phỏng riêng trong
   `urdf/standard/`; phần visual/collision của housing RPLIDAR được bỏ khỏi
   mô hình mô phỏng để tránh GPU LiDAR tự nhìn thấy chính housing. Hình dạng
   robot vật lý, pose LiDAR và thông số quét vẫn được giữ.
3. Initial pose được lấy từ pose spawn hoặc đặt bằng **2D Pose Estimate**;
   `/scan` được đồng bộ thời gian và giảm xuống 5 Hz trên `/scan_nav` để tránh
   xử lý scan trễ. AMCL và hai costmap dùng cùng topic tuyệt đối `/scan_nav`;
   AMCL so khớp dữ liệu này với `/map` rồi phát TF `map → odom`.
4. `waypoint_navigator.py` chờ AMCL/Nav2 active, gửi lần lượt các
   `NavigateToPose` goal và ghi kết quả từng goal.
5. `yolo_detector.py` subscribe ảnh RGB, chạy model YOLO, in detections và
   publish ảnh annotated lên `/yolo/detections/image`.

## 2. Node, topic và action

| Thành phần | Vai trò | Giao tiếp chính |
| --- | --- | --- |
| `map_server` | Nạp occupancy map | `/map` |
| `amcl` | Localization Monte Carlo | `/scan_nav`, `/map`, `/amcl_pose`, TF `map → odom`, `/initialpose` |
| Nav2 planner/controller/BT navigator | Lập đường và điều khiển, tránh vật cản | `/scan_nav`; action `/navigate_to_pose`; `/cmd_vel`, `/tf` |
| `waypoint_navigator.py` | Gửi chuỗi pose tự động | Nav2 Simple Commander / `NavigateToPose` |
| `robot_description_sim.launch.py` | Mô tả robot riêng cho Gazebo simulation, không sửa package hệ thống | URDF/Xacro → Gazebo và TF |
| `scan_retimestamp.py` | Đồng bộ timestamp LiDAR | `/scan` → `/scan_nav` |
| `yolo_detector.py` | Phát hiện vật thể RGB | `/oakd/rgb/preview/image_raw` → `/yolo/detections/image` |

## 3. Localization và navigation

Map YAML chỉ tới ảnh PGM và mô tả resolution, origin cùng ngưỡng occupancy.
Map server cung cấp `/map`; AMCL nhận initial pose, odometry và LiDAR để ước
lượng pose. Khi TF `map → odom → base_link` hợp lệ, Nav2 biến mỗi goal trong
hệ `map` thành đường đi toàn cục, bộ điều khiển cục bộ tránh vật cản bằng
LiDAR và phát vận tốc tới robot.

Ba goal demo mặc định cho map maze hiện tại:

| Goal | x (m) | y (m) | yaw (rad) |
| --- | ---: | ---: | ---: |
| 1 | 0.0 | 0.0 | 3.14159 |
| 2 | 4.0 | 0.0 | 0.0 |
| 3 | 4.0 | -1.5 | -1.57 |

Các goal trên nằm trong phần free đã quan sát của map đính kèm. Nếu đổi world
hoặc map, cần khảo sát lại pose và cập nhật tham số launch.

## 4. Kết quả chạy thử và hình minh họa

Đã chạy `autonomous_demo.launch.py` với map `maps/phase2/map.yaml`, world
`maze`, simulation time, RViz2 và YOLO bật. Log Nav2 lần lượt báo:

- Goal 1 `(4.0, 3.0, 1.57)`: cần xác nhận bằng lượt chạy mới.
- Goal 2 `(0.0, 2.5, 3.14159)`: cần xác nhận bằng lượt chạy mới.
- Goal 3 `(0.0, -3.0, -1.57)`: cần xác nhận bằng lượt chạy mới.
- YOLO nhận ảnh từ `/oakd/rgb/preview/image_raw` và ghi nhận class
  `dining table` (confidence quan sát được 0.27–0.36); ảnh annotate được
  publish lên `/yolo/detections/image`.

Chụp ảnh màn hình từ lượt chạy của bạn để bổ sung vào bản PDF cuối:

- **RViz2, map và initial pose:** [Chèn ảnh]
- **Nav2 plan tới các goal:** [Chèn ảnh]
- **Cửa sổ YOLO có bounding box:** [Chèn ảnh]
- **Kết quả navigation:** [Ghi từng goal reached/failed]

## 5. Link nộp bài

- Video demo Google Drive (public): [Dán link]
- GitHub repository (public): [Dán link]
