from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node


def generate_launch_description():
    simulator_pkg = get_package_share_directory('turtlebot4_ignition_bringup')
    navigation_pkg = get_package_share_directory('turtlebot4_navigation')
    package_share = get_package_share_directory('tb4_simplesimu')

    simulator_launch = PathJoinSubstitution([
        simulator_pkg, 'launch', 'turtlebot4_ignition.launch.py'
    ])
    slam_launch = PathJoinSubstitution([
        navigation_pkg, 'launch', 'slam.launch.py'
    ])
    slam_params = PathJoinSubstitution([
        package_share, 'config', 'slam.yaml'
    ])
    remove_spawned_dock = TimerAction(
        period=30.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    'ign', 'service',
                    '-s',
                    PathJoinSubstitution([
                        '/world', LaunchConfiguration('world'), 'remove'
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
        DeclareLaunchArgument('model', default_value='standard'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('x', default_value='2.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('z', default_value='0.01'),
        DeclareLaunchArgument('yaw', default_value='3.14159'),
    ]

    odom_tf_node = Node(
        package='tb4_simplesimu',
        executable='odom_tf_broadcaster.py',
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    return LaunchDescription(arguments + [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(simulator_launch),
            launch_arguments={
                'world': LaunchConfiguration('world'),
                'model': LaunchConfiguration('model'),
                'rviz': LaunchConfiguration('rviz'),
                'x': LaunchConfiguration('x'),
                'y': LaunchConfiguration('y'),
                'z': LaunchConfiguration('z'),
                'yaw': LaunchConfiguration('yaw'),
            }.items(),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(slam_launch),
            launch_arguments={
                'use_sim_time': 'true',
                'params': slam_params,
            }.items(),
        ),
        odom_tf_node,
        remove_spawned_dock,
    ])
