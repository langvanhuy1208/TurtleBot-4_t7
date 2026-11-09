#!/usr/bin/env python3
import math

import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan


class AutoMapper(Node):
    def __init__(self):
        super().__init__('auto_mapper')
        
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_callback, 10)

        self.state = 'FORWARD'
        self.front_clear = False
        self.scan_received = False
        self.left_clearance = 0.0
        self.right_clearance = 0.0
        self.odom_x = 0.0
        self.odom_y = 0.0
        self.yaw = None
        self.turn_target = None
        self.turn_direction = -1.0
        self.branch_latched = False
        self.branch_position = None

        self.timer = self.create_timer(0.05, self.control_loop)

        self.get_logger().info('====================================================')
        self.get_logger().info('>>> AUTO MAPPER: obstacle and side-branch exploration <<<')
        self.get_logger().info('====================================================')

    @staticmethod
    def angle_error(angle, reference):
        return math.atan2(
            math.sin(angle - reference),
            math.cos(angle - reference),
        )

    @staticmethod
    def yaw_from_quaternion(orientation):
        return math.atan2(
            2.0 * (orientation.w * orientation.z + orientation.x * orientation.y),
            1.0 - 2.0 * (orientation.y**2 + orientation.z**2),
        )

    def sector_min(self, msg, center, half_width):
        distances = []
        for index, distance in enumerate(msg.ranges):
            scan_angle = msg.angle_min + index * msg.angle_increment
            if (
                abs(self.angle_error(scan_angle, center)) <= half_width
                and math.isfinite(distance)
                and msg.range_min <= distance <= msg.range_max
            ):
                distances.append(distance)
        return min(distances, default=0.0)

    def scan_callback(self, msg):
        if not msg.ranges:
            self.front_clear = False
            return

        front_angle = -math.pi / 2
        self.front_clear = self.sector_min(
            msg, front_angle, math.radians(20)
        ) > 0.60
        self.left_clearance = self.sector_min(
            msg, 0.0, math.radians(15)
        )
        self.right_clearance = self.sector_min(
            msg, math.pi, math.radians(15)
        )
        self.scan_received = True

    def odom_callback(self, msg):
        position = msg.pose.pose.position
        self.odom_x = position.x
        self.odom_y = position.y
        self.yaw = self.yaw_from_quaternion(msg.pose.pose.orientation)

    def start_turn(self, direction, angle):
        self.turn_direction = direction
        self.turn_target = math.atan2(
            math.sin(self.yaw + direction * angle),
            math.cos(self.yaw + direction * angle),
        )
        self.state = 'TURNING'
        self.branch_latched = True
        self.branch_position = (self.odom_x, self.odom_y)

    def release_branch_latch_if_clear(self):
        if not self.branch_latched or self.branch_position is None:
            return

        dx = self.odom_x - self.branch_position[0]
        dy = self.odom_y - self.branch_position[1]
        if math.hypot(dx, dy) >= 1.5:
            self.branch_latched = False
            self.branch_position = None
            self.get_logger().info('Ready to explore the next side branch.')

    def publish_cmd(self, cmd):
        self.cmd_pub.publish(cmd)

    def control_loop(self):
        cmd = Twist()

        if not self.scan_received or self.yaw is None:
            self.publish_cmd(cmd)
            return

        self.release_branch_latch_if_clear()

        if self.state == 'TURNING':
            error = self.angle_error(self.turn_target, self.yaw)
            if abs(error) <= 0.12:
                self.state = 'FORWARD'
                self.turn_target = None
                self.get_logger().info('Turn complete; resuming exploration.')
            else:
                cmd.angular.z = 0.6 if error > 0.0 else -0.6

        elif self.state == 'FORWARD':
            if not self.front_clear:
                if self.left_clearance > self.right_clearance and self.left_clearance > 1.0:
                    direction = 1.0
                    angle = math.pi / 2
                elif self.right_clearance > 1.0:
                    direction = -1.0
                    angle = math.pi / 2
                else:
                    direction = -self.turn_direction
                    angle = math.pi
                self.start_turn(direction, angle)
                self.get_logger().info('Obstacle ahead; turning toward the clearest route.')
            elif not self.branch_latched and max(
                self.left_clearance, self.right_clearance
            ) > 1.3:
                left_open = self.left_clearance > 1.3
                right_open = self.right_clearance > 1.3
                if left_open and right_open:
                    direction = -self.turn_direction
                else:
                    direction = 1.0 if left_open else -1.0
                self.start_turn(direction, math.pi / 2)
                side = 'left' if direction > 0.0 else 'right'
                self.get_logger().info(
                    f'Side opening detected; exploring the {side} branch.'
                )
            else:
                cmd.linear.x = 0.25

        self.publish_cmd(cmd)

    def stop_robot(self):
        cmd = Twist()
        for _ in range(5):
            self.publish_cmd(cmd)

def main(args=None):
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = AutoMapper()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.stop_robot()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
