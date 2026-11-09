cmake_minimum_required(VERSION 3.8)
project(tb4_simplesimu)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)

install(DIRECTORY
  launch
  maps
  config
  scripts
  urdf
  worlds
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/auto_mapper.py
  scripts/waypoint_navigator.py
  scripts/yolo_detector.py
  scripts/odom_tf_broadcaster.py
  scripts/scan_retimestamp.py
  scripts/gesture_core.py
  scripts/gesture_recognition_node.py
  scripts/robot_behavior_node.py
  scripts/download_gesture_model.py
  scripts/semantic_map.py
  scripts/segment_map.py
  scripts/voice_navigation_node.py
  scripts/voice_input.py
  scripts/map_from_world.py
  scripts/voice_audio.py
  scripts/voice_demo_ready.py
  scripts/run_bai7_live.sh
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
