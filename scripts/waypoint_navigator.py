#!/usr/bin/env python3
"""Visit a sequence of map-frame poses using Nav2 Simple Commander."""

import math
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.parameter import Parameter
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener


class WaypointNavigator(BasicNavigator):
    def __init__(self):
        super().__init__('waypoint_navigator')
        # Nav2 and Gazebo use simulation time; goal stamps must use the same clock.
        self.set_parameters([Parameter('use_sim_time', value=True)])
        self.odom_received = False
        self.create_subscription(Odometry, '/odom', self._odom_callback, 10)
        self.tf_buffer = Buffer(node=self)
        self.tf_listener = TransformListener(
            self.tf_buffer, self, spin_thread=False
        )
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('set_initial_pose', False)
        self.declare_parameter('initial_x', 2.0)
        self.declare_parameter('initial_y', 0.0)
        self.declare_parameter('initial_yaw', 3.14159)
        self.declare_parameter('goal_x', [4.0, 0.0, 0.0])
        self.declare_parameter('goal_y', [3.0, 2.5, -3.0])
        self.declare_parameter('goal_yaw', [1.57, 3.14159, -1.57])

    def _odom_callback(self, _msg):
        self.odom_received = True

    def make_pose(self, x, y, yaw):
        pose = PoseStamped()
        pose.header.frame_id = self.get_parameter('frame_id').value
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(x)
        pose.pose.position.y = float(y)
        pose.pose.orientation.z = math.sin(float(yaw) / 2.0)
        pose.pose.orientation.w = math.cos(float(yaw) / 2.0)
        return pose

    def run_waypoints(self):
        xs = list(self.get_parameter('goal_x').value)
        ys = list(self.get_parameter('goal_y').value)
        yaws = list(self.get_parameter('goal_yaw').value)
        if not xs or len(xs) != len(ys) or len(xs) != len(yaws):
            self.get_logger().error('goal_x, goal_y and goal_yaw must have equal non-zero lengths')
            return

        if self.get_parameter('set_initial_pose').value:
            deadline = time.monotonic() + 180.0
            while (
                (
                    not self.odom_received
                    or self.get_clock().now().nanoseconds < 10_000_000_000
                    or not self.tf_buffer.can_transform(
                        'odom', 'base_link', Time()
                    )
                )
                and time.monotonic() < deadline
            ):
                rclpy.spin_once(self, timeout_sec=0.1)
            if (
                not self.odom_received
                or self.get_clock().now().nanoseconds < 10_000_000_000
                or not self.tf_buffer.can_transform('odom', 'base_link', Time())
            ):
                raise RuntimeError(
                    'No synchronized /clock, /odom, and odom-to-base_link TF; '
                    'cannot initialize AMCL'
                )
            initial_pose = self.make_pose(
                self.get_parameter('initial_x').value,
                self.get_parameter('initial_y').value,
                self.get_parameter('initial_yaw').value,
            )
            # Use TF's latest transform for AMCL initialization. Gazebo can
            # publish odometry a little ahead of /clock during startup.
            initial_pose.header.stamp.sec = 0
            initial_pose.header.stamp.nanosec = 0
            self.setInitialPose(initial_pose)
            self.get_logger().info(
                'Published initial pose using the latest odometry transform.'
            )
        else:
            self.get_logger().info(
                'Set the robot pose with RViz 2D Pose Estimate; waiting for AMCL.'
            )

        self.get_logger().info('Waiting for Nav2 lifecycle nodes and AMCL pose...')
        self.waitUntilNav2Active()
        for index, (x, y, yaw) in enumerate(zip(xs, ys, yaws), start=1):
            goal = self.make_pose(x, y, yaw)
            self.get_logger().info(f'Navigating to goal {index}: x={x:.2f}, y={y:.2f}, yaw={yaw:.2f}')
            self.goToPose(goal)
            while not self.isTaskComplete():
                feedback = self.getFeedback()
                elapsed = 0.0
                if feedback:
                    elapsed = (
                        feedback.navigation_time.sec
                        + feedback.navigation_time.nanosec * 1e-9
                    )
                if feedback and elapsed > 600.0:
                    self.get_logger().error(f'Goal {index} timed out; cancelling')
                    self.cancelTask()
                    break
                rclpy.spin_once(self, timeout_sec=0.1)
            result = self.getResult()
            if result == TaskResult.SUCCEEDED:
                self.get_logger().info(f'Goal {index} reached')
            else:
                self.get_logger().error(f'Goal {index} failed (result={result}); stopping waypoint sequence')
                break


def main(args=None):
    rclpy.init(args=args)
    navigator = WaypointNavigator()
    try:
        navigator.run_waypoints()
    except KeyboardInterrupt:
        navigator.cancelTask()
    except Exception as exc:
        navigator.get_logger().error(f'Navigation node failed: {exc}; cancelling active task')
        navigator.cancelTask()
    finally:
        navigator.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
