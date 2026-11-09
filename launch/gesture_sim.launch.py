"""Wide empty arena, TurtleBot 4 and dock removal; no navigation stack."""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
    share = get_package_share_directory('tb4_simplesimu')
    def local(name):
        return PythonLaunchDescriptionSource(PathJoinSubstitution([share, 'launch', name]))
    return LaunchDescription([
        IncludeLaunchDescription(local('ignition_fast.launch.py'), launch_arguments={
            'world': 'gesture_arena', 'headless': 'false',
            'world_file': PathJoinSubstitution([share, 'worlds', 'gesture_arena.sdf'])
        }.items()),
        IncludeLaunchDescription(local('turtlebot4_spawn_sim.launch.py'),
                                 launch_arguments={
                                     'world': 'gesture_arena', 'model': 'standard',
                                     'gesture_sensors': 'true',
                                     'x': '0.0', 'y': '0.0', 'z': '0.02'
                                 }.items()),
        TimerAction(period=20.0, actions=[ExecuteProcess(cmd=[
            'ign', 'service', '-s', '/world/gesture_arena/remove',
            '--reqtype', 'ignition.msgs.Entity', '--reptype', 'ignition.msgs.Boolean',
            '--timeout', '5000', '--req', 'name: "standard_dock" type: MODEL'
        ], output='screen')]),
    ])
