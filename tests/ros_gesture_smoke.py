#!/usr/bin/env python3
"""ROS integration check with isolated topic names; never drives /cmd_vel."""
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from robot_behavior_node import RobotBehaviorNode


def main():
    rclpy.init(args=['--ros-args',
                     '-r', '/cmd_vel:=/bai6_test/cmd_vel',
                     '-r', '/scan:=/bai6_test/scan',
                     '-r', '/detected_gesture:=/bai6_test/gesture',
                     '-r', '/robot_behavior/status:=/bai6_test/status'])
    controller = RobotBehaviorNode()
    assert controller.velocity.topic_name == '/bai6_test/cmd_vel'
    probe = Node('bai6_test_probe')
    gestures = probe.create_publisher(String, '/detected_gesture', 1)
    scans = probe.create_publisher(LaserScan, '/scan', 1)
    velocities = []
    probe.create_subscription(Twist, '/cmd_vel',
                              lambda m: velocities.append((m.linear.x, m.angular.z)), 10)
    executor = SingleThreadedExecutor()
    executor.add_node(controller)
    executor.add_node(probe)
    scan = LaserScan()
    scan.range_min, scan.range_max = 0.12, 10.0
    scan.ranges = [5.0] * 360

    def phase(label, seconds=0.4, send_scan=True):
        velocities.clear()
        end = time.monotonic() + seconds
        next_publish = 0.0
        while time.monotonic() < end:
            now = time.monotonic()
            if now >= next_publish:
                if send_scan:
                    scans.publish(scan)
                if label is not None:
                    gestures.publish(String(data=label))
                next_publish = now + 0.05
            executor.spin_once(timeout_sec=0.005)
        return list(velocities)

    def start():
        phase('Closed_Fist')
        before = phase('Pointing_Up')
        assert before and all(v == (0.0, 0.0) for v in before), before
        after = phase('Thumb_Up')
        assert any(v[0] > 0 for v in after), after

    try:
        # Allow DDS discovery before making assertions.
        phase('Closed_Fist', 1.0)
        start()
        stopped = phase('Open_Palm')
        assert stopped[-1] == (0.0, 0.0)
        assert controller.controller.state == 'IDLE'
        start()
        stopped = phase(None, 1.1)
        assert stopped[-1] == (0.0, 0.0)
        assert controller.controller.reason == 'Control signal timeout'
        start()
        stopped = phase('Thumb_Up', 1.1, send_scan=False)
        assert stopped[-1] == (0.0, 0.0)
        assert controller.controller.state == 'IDLE'
        start()
        scan.ranges = [0.3] * 360
        stopped = phase('Thumb_Up')
        assert stopped[-1] == (0.0, 0.0)
        assert controller.controller.state == 'IDLE'
        print('PASS: selection, confirmation, stop, signal timeout, scan timeout, obstacle')
    finally:
        executor.shutdown()
        controller.destroy_node()
        probe.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
