from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    package_share = get_package_share_directory('tb4_simplesimu')
    nav_launch = PathJoinSubstitution([package_share, 'launch', 'sim_nav.launch.py'])
    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=PathJoinSubstitution([
            package_share, 'maps', 'phase2', 'map.yaml'])),
        DeclareLaunchArgument('world', default_value='maze'),
        DeclareLaunchArgument('world_name', default_value='maze'),
        DeclareLaunchArgument('headless', default_value='true',
                              choices=['true', 'false']),
        DeclareLaunchArgument('model', default_value='standard'),
        DeclareLaunchArgument('x', default_value='2.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='3.14159'),
        DeclareLaunchArgument('image_topic', default_value='/oakd/rgb/preview/image_raw'),
        DeclareLaunchArgument('yolo_model', default_value='yolov8n.pt'),
        DeclareLaunchArgument('show_window', default_value='true'),
        DeclareLaunchArgument('start_yolo', default_value='true'),
        DeclareLaunchArgument('set_initial_pose', default_value='true'),
        DeclareLaunchArgument('goal_x', default_value='[4.0, 0.0, 0.0]'),
        DeclareLaunchArgument('goal_y', default_value='[3.0, 2.5, -3.0]'),
        DeclareLaunchArgument('goal_yaw', default_value='[1.57, 3.14159, -1.57]'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav_launch),
            launch_arguments={'map': LaunchConfiguration('map'),
                              'world': LaunchConfiguration('world'),
                              'world_name': LaunchConfiguration('world_name'),
                              'headless': LaunchConfiguration('headless'),
                              'model': LaunchConfiguration('model'),
                              'x': LaunchConfiguration('x'),
                              'y': LaunchConfiguration('y'),
                              'yaw': LaunchConfiguration('yaw')}.items()),
        Node(package='tb4_simplesimu', executable='yolo_detector.py', output='screen',
             parameters=[{'image_topic': LaunchConfiguration('image_topic'),
                          'model': LaunchConfiguration('yolo_model'),
                          'show_window': LaunchConfiguration('show_window')}],
             condition=IfCondition(LaunchConfiguration('start_yolo'))),
        Node(package='tb4_simplesimu', executable='waypoint_navigator.py', output='screen',
             parameters=[{'use_sim_time': True,
                          'set_initial_pose': LaunchConfiguration('set_initial_pose'),
                          'initial_x': LaunchConfiguration('x'),
                          'initial_y': LaunchConfiguration('y'),
                          'initial_yaw': LaunchConfiguration('yaw'),
                          'goal_x': LaunchConfiguration('goal_x'),
                          'goal_y': LaunchConfiguration('goal_y'),
                          'goal_yaw': LaunchConfiguration('goal_yaw')}]),
    ])
