#!/usr/bin/env bash
# Run the live simulator + webcam on this Ubuntu desktop. Ctrl+C stops all nodes.
set -eo pipefail
task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_root"
source /opt/ros/humble/setup.bash
source "$task_root/install/setup.bash"
# Loopback is selected explicitly in the Cyclone config. ROS_LOCALHOST_ONLY
# would append a second interface configuration on this Humble installation.
unset ROS_LOCALHOST_ONLY
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-86}"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://$task_root/config/cyclonedds_gesture.xml"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export LP_NUM_THREADS=2
export ROS_LOG_DIR="$task_root/log/bai6_live/ros"
mkdir -p "$task_root/log/bai6_live"

gesture_python=/usr/bin/python3
if [[ -x "$task_root/.venv-gesture/bin/python" ]]; then
    gesture_python="$task_root/.venv-gesture/bin/python"
elif [[ -d /tmp/tb4-gesture-deps/mediapipe ]]; then
    export PYTHONPATH="/tmp/tb4-gesture-deps:${PYTHONPATH:-}"
    export MPLCONFIGDIR=/tmp/bai6-mpl
fi
"$gesture_python" -c 'import mediapipe, cv2' > /dev/null

gesture_model="$task_root/models/gesture_recognizer.task"
if [[ -f "$HOME/.cache/tb4_gesture/gesture_recognizer.task" ]]; then
    gesture_model="$HOME/.cache/tb4_gesture/gesture_recognizer.task"
elif [[ -f /tmp/tb4-gesture-model/gesture_recognizer.task ]]; then
    gesture_model=/tmp/tb4-gesture-model/gesture_recognizer.task
elif [[ ! -f "$gesture_model" ]]; then
    /usr/bin/python3 scripts/download_gesture_model.py --output "$gesture_model"
fi

task_children=()
cleanup() {
    trap - EXIT INT TERM
    for task_child in "${task_children[@]}"; do
        kill -TERM -- "-$task_child" 2>/dev/null || true
    done
    wait || true
}
trap cleanup EXIT INT TERM

setsid ros2 launch tb4_simplesimu gesture_sim.launch.py \
    > "$task_root/log/bai6_live/simulation.log" 2>&1 &
task_children+=("$!")
setsid ros2 launch tb4_simplesimu gesture_control.launch.py start_camera:=false \
    > "$task_root/log/bai6_live/behavior.log" 2>&1 &
task_children+=("$!")
setsid "$gesture_python" scripts/gesture_recognition_node.py --ros-args \
    --params-file config/gesture.yaml -p model_path:="$gesture_model" \
    -p camera_index:="${1:-0}" \
    > "$task_root/log/bai6_live/camera.log" 2>&1 &
task_children+=("$!")

echo 'Đã mở Gazebo + webcam. Chờ robot và LiDAR sẵn sàng, dock xóa sau khoảng 20 giây.'
echo 'Một ngón/V/vẫy → chọn; ngón cái → chạy; xòe tay → dừng; nắm tay → hủy.'
echo "Log: $task_root/log/bai6_live/ | Ctrl+C dừng cả ba tiến trình."
wait -n "${task_children[@]}"
