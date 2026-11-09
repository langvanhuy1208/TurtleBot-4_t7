#!/usr/bin/env python3
"""Throttle simulator scans; optionally restamp for legacy simulator setups."""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from sensor_msgs.msg import LaserScan


class ScanRetimestamp(Node):
    def __init__(self):
        super().__init__('scan_retimestamp')
        qos = QoSProfile(depth=1)
        self.publisher = self.create_publisher(LaserScan, '/scan_nav', qos)
        self.subscription = self.create_subscription(
            LaserScan, '/scan', self.on_scan, qos
        )
        self.declare_parameter('publish_period', 0.2)
        self.declare_parameter('restamp', True)
        self.restamp = bool(self.get_parameter('restamp').value)
        publish_period = float(self.get_parameter('publish_period').value)
        if publish_period <= 0.0:
            raise ValueError('publish_period must be greater than zero')
        self.publish_period_ns = int(publish_period * 1_000_000_000)
        self.last_published_ns: int | None = None

    def on_scan(self, msg):
        now = self.get_clock().now()
        now_ns = (now.nanoseconds if self.restamp else
                  msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec)
        if self.last_published_ns is not None and now_ns < self.last_published_ns:
            self.last_published_ns = None
        if (
            self.last_published_ns is not None
            and now_ns - self.last_published_ns < self.publish_period_ns
        ):
            return
        if self.restamp:
            msg.header.stamp = now.to_msg()
        self.publisher.publish(msg)
        self.last_published_ns = now_ns


def main(args=None):
    rclpy.init(args=args)
    node = ScanRetimestamp()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
