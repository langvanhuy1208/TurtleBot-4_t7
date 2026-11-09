#!/usr/bin/env python3
"""Nonblocking ROS 2 NavigateToPose client with ordered semantic itineraries."""
import json
import math
import time
from collections import deque

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Point
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import String
from visualization_msgs.msg import Marker, MarkerArray
from semantic_map import RegionCatalog


class VoiceNavigation(Node):
    def __init__(self):
        super().__init__('voice_navigation')
        self.declare_parameter('regions_file', '')
        self.declare_parameter('goal_timeout_sec', 300.0)
        self.catalog = RegionCatalog(self.get_parameter('regions_file').value)
        self.timeout = float(self.get_parameter('goal_timeout_sec').value)
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError('goal_timeout_sec must be positive')
        self.client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.status_pub = self.create_publisher(String, '/voice_nav/status', 10)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.marker_pub = self.create_publisher(MarkerArray, '/semantic_regions', qos)
        self.route_pub = self.create_publisher(Marker, '/voice_nav/route', qos)
        self.subscription = self.create_subscription(String, '/voice_command', self.command, 10)
        self.queue = deque()
        self.busy = False
        self.goal_handle = None
        self.cancel_requested = False
        self.cancel_sent = False
        self.deadline = None
        self.current = None
        self.create_timer(0.25, self.tick)
        self.create_timer(2.0, self.publish_regions)
        self.publish_regions()
        self.status('ready', regions=list(self.catalog.regions))

    def status(self, state, **fields):
        payload = json.dumps(dict(state=state, **fields), ensure_ascii=False)
        self.status_pub.publish(String(data=payload))
        self.get_logger().info(payload)

    def command(self, msg):
        try:
            route = self.catalog.parse(msg.data)
        except ValueError as exc:
            self.status('rejected', text=msg.data, reason=str(exc))
            return
        if not route:
            if self.busy:
                self.queue.clear()
                self.cancel_requested = True
                self.status('cancelling')
                self.cancel_active()
            else:
                self.status('idle')
            return
        if self.busy:
            self.status('rejected', reason='Robot đang đi; nói dừng lại trước khi gửi lệnh mới')
            return
        if not self.client.server_is_ready():
            self.status('rejected', reason='Nav2 chưa sẵn sàng; khởi động Nav2 và định vị AMCL')
            return
        self.queue = deque(route)
        self.busy = True
        self.cancel_requested = False
        self.cancel_sent = False
        self.publish_route(route)
        self.status('accepted', text=msg.data, route=route)
        self.send_next()

    def send_next(self):
        if self.cancel_requested or not self.queue:
            self.finish('cancelled' if self.cancel_requested else 'completed')
            return
        self.current = self.queue.popleft()
        region = self.catalog.regions[self.current]
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = self.catalog.data['frame_id']
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(region['goal']['x'])
        goal.pose.pose.position.y = float(region['goal']['y'])
        yaw = float(region['goal']['yaw'])
        goal.pose.pose.orientation.z = math.sin(yaw / 2)
        goal.pose.pose.orientation.w = math.cos(yaw / 2)
        self.deadline = time.monotonic() + self.timeout
        self.status('navigating', region=self.current, remaining=list(self.queue))
        try:
            self.client.send_goal_async(goal).add_done_callback(self.goal_response)
        except Exception as exc:
            self.finish('failed', reason=str(exc))

    def goal_response(self, future):
        try:
            self.goal_handle = future.result()
            if not self.goal_handle.accepted:
                self.finish('failed', reason='Nav2 từ chối mục tiêu')
                return
            self.goal_handle.get_result_async().add_done_callback(self.goal_result)
            if self.cancel_requested:
                self.cancel_active()
        except Exception as exc:
            self.finish('failed', reason=str(exc))

    def goal_result(self, future):
        try:
            code = future.result().status
        except Exception as exc:
            self.finish('failed', reason=str(exc))
            return
        self.goal_handle = None
        if self.cancel_requested:
            self.finish('cancelled')
        elif code == GoalStatus.STATUS_SUCCEEDED:
            self.status('arrived', region=self.current)
            self.send_next()
        else:
            self.finish('failed', reason=f'Nav2 status={code}', region=self.current)

    def cancel_active(self):
        if self.goal_handle is not None and not self.cancel_sent:
            self.cancel_sent = True
            self.goal_handle.cancel_goal_async().add_done_callback(self.cancel_response)

    def cancel_response(self, future):
        try:
            if not future.result().goals_canceling:
                self.status('cancel_pending', reason='Chờ kết quả cuối từ Nav2')
        except Exception as exc:
            self.status('cancel_pending', reason=str(exc))
        # Keep busy until the action result arrives; never overlap robot goals.

    def tick(self):
        if self.busy and not self.cancel_requested and self.deadline and time.monotonic() > self.deadline:
            self.queue.clear()
            self.cancel_requested = True
            self.status('timeout', region=self.current)
            self.cancel_active()

    def finish(self, state, **fields):
        self.busy = False
        self.queue.clear()
        self.goal_handle = None
        self.deadline = None
        self.cancel_requested = False
        self.cancel_sent = False
        self.status(state, **fields)
        self.publish_route([])

    def publish_regions(self):
        array = MarkerArray()
        for index, region in enumerate(self.catalog.regions.values()):
            for text_marker in (False, True):
                m = Marker()
                m.header.frame_id = self.catalog.data['frame_id']
                m.header.stamp = self.get_clock().now().to_msg()
                m.ns = 'semantic_regions'
                m.id = index*2 + int(text_marker)
                m.type = Marker.TEXT_VIEW_FACING if text_marker else Marker.CYLINDER
                m.action = Marker.ADD
                m.pose.position.x = float(region['goal']['x'])
                m.pose.position.y = float(region['goal']['y'])
                m.pose.position.z = 0.8 if text_marker else 0.05
                if text_marker:
                    m.pose.position.y += 0.55
                m.pose.orientation.w = 1.0
                m.scale.x = m.scale.y = 0.45
                m.scale.z = 0.55 if text_marker else 0.1
                palette = [(0.2, 0.5, 0.95), (0.95, 0.6, 0.1), (0.2, 0.75, 0.4)]
                m.color.r, m.color.g, m.color.b = ((0.1, 0.1, 0.1) if text_marker else palette[index % 3])
                m.color.a = 1.0
                # Short IDs remain legible beside walls in the RViz map.
                m.text = region['id']
                array.markers.append(m)
        self.marker_pub.publish(array)

    def publish_route(self, route):
        marker = Marker()
        marker.header.frame_id = self.catalog.data['frame_id']
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns, marker.id = 'semantic_itinerary', 0
        marker.type, marker.action = Marker.LINE_STRIP, Marker.ADD if route else Marker.DELETE
        marker.pose.orientation.w = 1.0
        marker.scale.x = 0.06
        marker.color.r, marker.color.g, marker.color.b, marker.color.a = (1.0, 0.6, 0.1, 1.0)
        for rid in route:
            goal = self.catalog.regions[rid]['goal']
            marker.points.append(Point(x=float(goal['x']), y=float(goal['y']), z=0.15))
        self.route_pub.publish(marker)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = VoiceNavigation()
        rclpy.spin(node)
    except KeyboardInterrupt:
        if node and node.busy:
            node.cancel_requested = True
            node.cancel_active()
            until = time.monotonic() + 3
            while node.busy and time.monotonic() < until:
                rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        if node:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
