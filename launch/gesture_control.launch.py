"""Run only the two HRI nodes against an already running TurtleBot 4."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory('tb4_simplesimu')
    return LaunchDescription([
        DeclareLaunchArgument('model_path', default_value=str(
            Path.home() / '.cache/tb4_gesture/gesture_recognizer.task')),
        DeclareLaunchArgument('camera_index', default_value='0'),
        DeclareLaunchArgument('cmd_vel_topic', default_value='/cmd_vel'),
        DeclareLaunchArgument('scan_topic', default_value='/scan'),
        DeclareLaunchArgument('start_camera', default_value='true'),
        Node(package='tb4_simplesimu', executable='gesture_recognition_node.py',
             name='gesture_recognition_node', output='screen',
             condition=IfCondition(LaunchConfiguration('start_camera')),
             parameters=[str(Path(share) / 'config/gesture.yaml'), {
                 'use_sim_time': False,
                 'model_path': LaunchConfiguration('model_path'),
                 'camera_index': ParameterValue(LaunchConfiguration('camera_index'),
                                                value_type=int)}]),
        Node(package='tb4_simplesimu', executable='robot_behavior_node.py',
             name='robot_behavior_node', output='screen',
             parameters=[str(Path(share) / 'config/gesture.yaml'), {'use_sim_time': True}],
             remappings=[('/cmd_vel', LaunchConfiguration('cmd_vel_topic')),
                         ('/scan', LaunchConfiguration('scan_topic'))]),
    ])
