"""Semantic command node; optionally start the existing maze/Nav2 simulation."""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetLaunchConfiguration
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory('tb4_simplesimu')
    return LaunchDescription([
        DeclareLaunchArgument('simulation', default_value='false'),
        DeclareLaunchArgument('headless', default_value='true'),
        DeclareLaunchArgument('start_rviz', default_value='true'),
        SetLaunchConfiguration('voice_start_rviz', LaunchConfiguration('start_rviz')),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('lightweight_sensors', default_value='true'),
        SetLaunchConfiguration('gesture_sensors', LaunchConfiguration('lightweight_sensors')),
        SetLaunchConfiguration('sensor_render_engine', 'ogre2'),
        DeclareLaunchArgument('map', default_value=PathJoinSubstitution(
            [share, 'maps', 'bai7', 'map.yaml'])),
        DeclareLaunchArgument('regions_file', default_value=PathJoinSubstitution(
            [share, 'maps', 'bai7', 'regions.yaml'])),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            PathJoinSubstitution([share, 'launch', 'sim_nav.launch.py'])),
            launch_arguments={'headless': LaunchConfiguration('headless'),
                              'restamp_scans': 'false',
                              'map': LaunchConfiguration('map'),
                              'start_rviz': 'false'}.items(),
            condition=IfCondition(LaunchConfiguration('simulation'))),
        Node(package='tb4_simplesimu', executable='voice_navigation_node.py', output='screen',
             parameters=[{'regions_file': LaunchConfiguration('regions_file'),
                          'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)}]),
        Node(package='rviz2', executable='rviz2', output='screen',
             arguments=['-d', PathJoinSubstitution([share, 'config', 'nav_voice.rviz'])],
             parameters=[{'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)}],
             condition=IfCondition(LaunchConfiguration('voice_start_rviz'))),
    ])
