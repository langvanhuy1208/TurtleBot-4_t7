#!/usr/bin/env python3
"""Gesture-controlled TurtleBot 4, with a wall-clock watchdog and scan interlock."""
import json
import math
import time

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String

from gesture_core import BehaviorController


class RobotBehaviorNode(Node):
    def __init__(self):
        super().__init__('robot_behavior_node')
        defaults = {'signal_timeout': 0.8, 'linear_speed': 0.15,
                    'angular_speed': 0.5, 'leg_seconds': 2.0,
                    'circle_radius': 0.6, 'scan_timeout': 0.8,
                    'obstacle_distance': 0.45}
        for key, value in defaults.items():
            self.declare_parameter(key, value)
        p = lambda name: self.get_parameter(name).value
        self.controller = BehaviorController(p('signal_timeout'), p('linear_speed'),
                                             p('angular_speed'), p('leg_seconds'),
                                             p('circle_radius'))
        self.scan_timeout = p('scan_timeout')
        self.obstacle_distance = p('obstacle_distance')
        if not all(math.isfinite(x) and x > 0 for x in
                   (self.scan_timeout, self.obstacle_distance)):
            raise ValueError('Safety parameters must be finite and positive')
        self.scan_time = None
        self.scan_clear = False
        self.last_status = None
        self.velocity = self.create_publisher(Twist, '/cmd_vel', 1)
        self.status = self.create_publisher(String, '/robot_behavior/status', 1)
        self.create_subscription(String, '/detected_gesture', self.on_gesture, 1)
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.wall_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(0.05, self.on_timer, clock=self.wall_clock)

    def on_gesture(self, msg):
        self.controller.receive(msg.data, time.monotonic(),
                                self.get_clock().now().nanoseconds / 1e9)
        # Publish zero directly in the stop callback, without waiting for timer.
        if self.controller.state != 'RUNNING':
            self.velocity.publish(Twist())

    def on_scan(self, msg):
        self.scan_time = time.monotonic()
        valid = [r for r in msg.ranges if
                 math.isfinite(r) and msg.range_min <= r <= msg.range_max]
        # Positive infinity means no return within sensor range. NaN/zero/-inf
        # are invalid; require >= 80% usable rays rather than ignoring failures.
        usable = len(valid) + sum(r == math.inf for r in msg.ranges)
        self.scan_clear = (bool(msg.ranges) and usable / len(msg.ranges) >= 0.8
                           and msg.range_max > self.obstacle_distance
                           and (not valid or min(valid) > self.obstacle_distance))
        if not self.scan_clear:
            self.controller.stop('LiDAR obstacle or invalid scan')
            self.velocity.publish(Twist())

    def on_timer(self):
        now = time.monotonic()
        safe = (self.scan_time is not None and self.scan_clear
                and now - self.scan_time <= self.scan_timeout)
        v, w = self.controller.tick(now, safe, self.get_clock().now().nanoseconds / 1e9)
        msg = Twist()
        msg.linear.x, msg.angular.z = v, w
        self.velocity.publish(msg)
        state = json.dumps({'state': self.controller.state,
                            'selected': self.controller.selected,
                            'reason': self.controller.reason})
        self.status.publish(String(data=state))
        if state != self.last_status:
            self.get_logger().info(state)
            self.last_status = state


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = RobotBehaviorNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            if rclpy.ok():
                node.velocity.publish(Twist())
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
