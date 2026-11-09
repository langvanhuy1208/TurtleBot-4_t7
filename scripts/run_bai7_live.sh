#!/usr/bin/env bash
# Fresh maze + RViz + AMCL/Nav2 + Vietnamese microphone input. Ctrl+C stops all.
set -eo pipefail
task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_root"
source /opt/ros/humble/setup.bash
if [[ ! -f "$task_root/install/setup.bash" ]]; then
    echo 'Chưa build: chạy colcon build --packages-select tb4_simplesimu --symlink-install' >&2
    exit 1
fi
source "$task_root/install/setup.bash"
unset ROS_LOCALHOST_ONLY
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-87}"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://$task_root/config/cyclonedds_local.xml"
export IGN_PARTITION="bai7_live_${ROS_DOMAIN_ID}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export LP_NUM_THREADS=2
export ROS_LOG_DIR="$task_root/log/bai7_live/ros"
if [[ -d "$task_root/.cache-voice/huggingface" ]]; then
    export HF_HOME="$task_root/.cache-voice/huggingface"
fi
mkdir -p "$task_root/log/bai7_live"
voice_python="$task_root/.venv-voice/bin/python"
PYTHONPATH="$task_root/scripts:${PYTHONPATH:-}" "$voice_python" -c \
    'import rclpy, faster_whisper, numpy; from voice_audio import pulse_source; print("Micro:", pulse_source())'

task_sim_pid=''
cleanup() {
    trap - EXIT INT TERM
    if [[ -n "$task_sim_pid" ]]; then
        # Let Nav2 process cancellation before terminating this simulator group.
        timeout 3 "$voice_python" scripts/voice_input.py --text 'Dừng lại' >/dev/null 2>&1 || true
        kill -INT -- "-$task_sim_pid" 2>/dev/null || true
        for task_attempt in {1..30}; do
            kill -0 "$task_sim_pid" 2>/dev/null || break
            sleep 0.1
        done
        kill -TERM -- "-$task_sim_pid" 2>/dev/null || true
        wait "$task_sim_pid" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM
setsid ros2 launch tb4_simplesimu voice_navigation.launch.py simulation:=true \
    start_rviz:="${BAI7_RVIZ:-true}" headless:=true \
    > "$task_root/log/bai7_live/simulation.log" 2>&1 &
task_sim_pid="$!"
echo 'Đang khởi động Gazebo/RViz, đặt pose AMCL và đợi Nav2...'
/usr/bin/python3 scripts/voice_demo_ready.py --initialize-spawn
if ! kill -0 "$task_sim_pid" 2>/dev/null; then
    echo 'Mô phỏng đã dừng. Xem log/bai7_live/simulation.log' >&2
    exit 1
fi
echo 'SẴN SÀNG QUAY VIDEO. Nhấn Enter rồi nói, chờ robot đến đích trước lệnh tiếp theo.'
echo 'Ví dụ: Đi đến khu vực A | Đi từ khu vực A đến khu vực B | Đi đến phòng thí nghiệm'
echo 'Thử lỗi: Đi đến khu vực Z. Hủy bằng: Dừng lại. Ctrl+C kết thúc toàn bộ.'
"$voice_python" scripts/voice_input.py --model "${BAI7_MODEL:-small}" \
    --save-audio "$task_root/log/bai7_live/microphone_recordings" "$@" \
    2>&1 | tee "$task_root/log/bai7_live/voice.log"
