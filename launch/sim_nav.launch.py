from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    navigation_pkg = get_package_share_directory('turtlebot4_navigation')
    package_share = get_package_share_directory('tb4_simplesimu')
    rviz_config = PathJoinSubstitution([
        package_share, 'config', 'nav.rviz'
    ])

    simulator_launch = PathJoinSubstitution([
        package_share, 'launch', 'turtlebot4_ignition_fast.launch.py'
    ])
    localization_launch = PathJoinSubstitution([
        navigation_pkg, 'launch', 'localization.launch.py'
    ])
    nav2_launch = PathJoinSubstitution([
        navigation_pkg, 'launch', 'nav2.launch.py'
    ])
    remove_spawned_dock = TimerAction(
        period=30.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    'ign', 'service',
                    '-s',
                    PathJoinSubstitution([
                        '/world', LaunchConfiguration('world_name'), 'remove'
                    ]),
                    '--reqtype', 'ignition.msgs.Entity',
                    '--reptype', 'ignition.msgs.Boolean',
                    '--timeout', '3000',
                    '--req', 'name: "standard_dock" type: MODEL',
                ],
                output='screen',
            )
        ],
    )

    arguments = [
        DeclareLaunchArgument('world', default_value='maze'),
        DeclareLaunchArgument('world_name', default_value='maze'),
        DeclareLaunchArgument('headless', default_value='true',
                              choices=['true', 'false']),
        DeclareLaunchArgument('model', default_value='standard'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('start_rviz', default_value='true'),
        DeclareLaunchArgument('restamp_scans', default_value='true'),
        DeclareLaunchArgument('x', default_value='2.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('z', default_value='0.01'),
        DeclareLaunchArgument('yaw', default_value='3.14159'),
        DeclareLaunchArgument(
            'map',
            default_value=PathJoinSubstitution([
                package_share, 'maps', 'phase2', 'map.yaml'
            ]),
            description='Full path to the map YAML file',
        ),
    ]

    simulator = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(simulator_launch),
        launch_arguments={
            'world': LaunchConfiguration('world'),
            'headless': LaunchConfiguration('headless'),
            'model': LaunchConfiguration('model'),
            'rviz': 'false',
            'x': LaunchConfiguration('x'),
            'y': LaunchConfiguration('y'),
            'z': LaunchConfiguration('z'),
            'yaw': LaunchConfiguration('yaw'),
        }.items(),
    )
    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(localization_launch),
        launch_arguments={
            'use_sim_time': 'true',
            'map': LaunchConfiguration('map'),
            'params': PathJoinSubstitution([package_share, 'config', 'localization.yaml']),
        }.items(),
    )
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(nav2_launch),
        launch_arguments={
            'use_sim_time': 'true',
            'params_file': PathJoinSubstitution([package_share, 'config', 'nav2.yaml']),
        }.items(),
    )
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(LaunchConfiguration('start_rviz')),
        output='screen',
    )
    odom_tf_node = Node(
        package='tb4_simplesimu',
        executable='odom_tf_broadcaster.py',
        parameters=[{'use_sim_time': True}],
        output='screen',
    )
    scan_retimestamp_node = Node(
        package='tb4_simplesimu',
        executable='scan_retimestamp.py',
        parameters=[{'use_sim_time': True,
                     'restamp': ParameterValue(LaunchConfiguration('restamp_scans'), value_type=bool)}],
        output='screen',
    )

    return LaunchDescription(arguments + [
        simulator,
        localization,
        navigation,
        odom_tf_node,
        scan_retimestamp_node,
        remove_spawned_dock,
        rviz_node,
    ])
