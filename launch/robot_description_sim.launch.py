from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import (
    Command,
    LaunchConfiguration,
    PathJoinSubstitution,
    PythonExpression,
)
from launch_ros.actions import Node
from launch.conditions import IfCondition, UnlessCondition


def generate_launch_description():
    package_share = get_package_share_directory('tb4_simplesimu')
    standard_xacro = PathJoinSubstitution([
        package_share, 'urdf', 'standard', 'turtlebot4.urdf.xacro'
    ])
    lite_xacro = PathJoinSubstitution([
        get_package_share_directory('turtlebot4_description'),
        'urdf', 'lite', 'turtlebot4.urdf.xacro',
    ])
    xacro_file = PythonExpression([
        "'", standard_xacro, "' if '", LaunchConfiguration('model'),
        "' == 'standard' else '", lite_xacro, "'",
    ])

    return LaunchDescription([
        DeclareLaunchArgument('model', default_value='standard', choices=['standard', 'lite']),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('namespace', default_value=''),
        DeclareLaunchArgument('gesture_sensors', default_value='false'),
        DeclareLaunchArgument('sensor_render_engine', default_value='ogre'),
        Node(
            package='robot_state_publisher', executable='robot_state_publisher',
            name='robot_state_publisher', namespace=LaunchConfiguration('namespace'),
            condition=IfCondition(LaunchConfiguration('gesture_sensors')),
            parameters=[{
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'robot_description': Command([
                    'python3 ', PathJoinSubstitution([
                        package_share, 'scripts', 'gesture_robot_description.py']),
                    ' ', xacro_file, ' --namespace=', LaunchConfiguration('namespace'),
                    ' --render-engine=', LaunchConfiguration('sensor_render_engine')]),
            }],
            remappings=[('robot_description', '/robot_description'),
                        ('/tf', '/tf'), ('/tf_static', '/tf_static')],
            output='screen'),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            condition=UnlessCondition(LaunchConfiguration('gesture_sensors')),
            namespace=LaunchConfiguration('namespace'),
            output='screen',
            parameters=[{
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'robot_description': Command([
                    'xacro ', xacro_file,
                    ' gazebo:=ignition namespace:=',
                    LaunchConfiguration('namespace'),
                ]),
            }],
            remappings=[
                ('robot_description', '/robot_description'),
                ('/tf', '/tf'),
                ('/tf_static', '/tf_static'),
            ],
        ),
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
            output='screen',
            parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}],
            remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
        ),
    ])
