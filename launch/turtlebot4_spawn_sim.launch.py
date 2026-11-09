from ament_index_python.packages import get_package_share_directory
from irobot_create_common_bringup.namespace import GetNamespacedName
from irobot_create_common_bringup.offset import OffsetParser, RotationalOffsetX, RotationalOffsetY

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, PushRosNamespace


ARGUMENTS = [
    DeclareLaunchArgument('rviz', default_value='false', choices=['true', 'false']),
    DeclareLaunchArgument('use_sim_time', default_value='true', choices=['true', 'false']),
    DeclareLaunchArgument('model', default_value='standard', choices=['standard', 'lite']),
    DeclareLaunchArgument('namespace', default_value=''),
    DeclareLaunchArgument('world', default_value='warehouse'),
    DeclareLaunchArgument('gesture_sensors', default_value='false'),
]
for pose_element in ['x', 'y', 'z', 'yaw']:
    ARGUMENTS.append(DeclareLaunchArgument(pose_element, default_value='0.0'))


def generate_launch_description():
    bringup_share = get_package_share_directory('turtlebot4_ignition_bringup')
    description_share = get_package_share_directory('turtlebot4_description')
    common_bringup_share = get_package_share_directory('irobot_create_common_bringup')
    create_ignition_share = get_package_share_directory('irobot_create_ignition_bringup')
    package_share = get_package_share_directory('tb4_simplesimu')

    robot_name = GetNamespacedName(LaunchConfiguration('namespace'), 'turtlebot4')
    dock_name = GetNamespacedName(LaunchConfiguration('namespace'), 'standard_dock')
    dock_offset_x = RotationalOffsetX(0.157, LaunchConfiguration('yaw'))
    dock_offset_y = RotationalOffsetY(0.157, LaunchConfiguration('yaw'))
    x_dock = OffsetParser(LaunchConfiguration('x'), dock_offset_x)
    y_dock = OffsetParser(LaunchConfiguration('y'), dock_offset_y)
    z_robot = OffsetParser(LaunchConfiguration('z'), -0.0025)
    yaw_dock = OffsetParser(LaunchConfiguration('yaw'), 3.1416)

    description_launch = PathJoinSubstitution([
        package_share, 'launch', 'robot_description_sim.launch.py'
    ])
    dock_description_launch = PathJoinSubstitution([
        common_bringup_share, 'launch', 'dock_description.launch.py'
    ])
    bridge_launch = PathJoinSubstitution([
        bringup_share, 'launch', 'ros_ign_bridge.launch.py'
    ])
    nodes_launch = PathJoinSubstitution([
        bringup_share, 'launch', 'turtlebot4_nodes.launch.py'
    ])
    create_nodes_launch = PathJoinSubstitution([
        common_bringup_share, 'launch', 'create3_nodes.launch.py'
    ])
    create_ignition_nodes_launch = PathJoinSubstitution([
        create_ignition_share, 'launch', 'create3_ignition_nodes.launch.py'
    ])
    default_node_params = PathJoinSubstitution([
        bringup_share, 'config', 'turtlebot4_node.yaml'
    ])
    node_params = LaunchConfiguration('param_file')

    spawn_group = GroupAction([
        PushRosNamespace(LaunchConfiguration('namespace')),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(description_launch),
            launch_arguments={
                'model': LaunchConfiguration('model'),
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'namespace': LaunchConfiguration('namespace'),
                'gesture_sensors': LaunchConfiguration('gesture_sensors'),
            }.items(),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(dock_description_launch),
            launch_arguments={'gazebo': 'ignition'}.items(),
        ),
        Node(
            package='ros_ign_gazebo',
            executable='create',
            arguments=[
                '-name', robot_name,
                '-x', LaunchConfiguration('x'),
                '-y', LaunchConfiguration('y'),
                '-z', z_robot,
                '-Y', LaunchConfiguration('yaw'),
                '-topic', 'robot_description',
            ],
            output='screen',
        ),
        Node(
            package='ros_ign_gazebo',
            executable='create',
            arguments=[
                '-name', dock_name,
                '-x', x_dock,
                '-y', y_dock,
                '-z', LaunchConfiguration('z'),
                '-Y', yaw_dock,
                '-topic', 'standard_dock_description',
            ],
            output='screen',
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(bridge_launch),
            launch_arguments={
                'model': LaunchConfiguration('model'),
                'robot_name': robot_name,
                'dock_name': dock_name,
                'namespace': LaunchConfiguration('namespace'),
                'world': LaunchConfiguration('world'),
            }.items(),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nodes_launch),
            launch_arguments={
                'model': LaunchConfiguration('model'),
                'param_file': node_params,
            }.items(),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(create_nodes_launch),
            launch_arguments={'namespace': LaunchConfiguration('namespace')}.items(),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(create_ignition_nodes_launch),
            launch_arguments={
                'robot_name': robot_name,
                'dock_name': dock_name,
            }.items(),
        ),
        Node(
            name='rplidar_stf',
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments=[
                '0', '0', '0', '0', '0', '0',
                'rplidar_link', [robot_name, '/rplidar_link/rplidar'],
            ],
            remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
            output='screen',
        ),
        Node(
            name='camera_stf',
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments=[
                '0', '0', '0', '1.5707', '-1.5707', '0',
                'oakd_rgb_camera_optical_frame',
                [robot_name, '/oakd_rgb_camera_frame/rgbd_camera'],
            ],
            remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
            output='screen',
        ),
    ])

    return LaunchDescription(ARGUMENTS + [
        DeclareLaunchArgument('param_file', default_value=default_node_params),
        spawn_group,
    ])
