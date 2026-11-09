#!/usr/bin/env python3
"""Wait for matching map, odometry/TF and ACTIVE Nav2; optionally initialize spawn.

--initialize-spawn is only for a freshly started default maze simulation.
"""
import argparse
import math
from pathlib import Path
import time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, DurabilityPolicy
from rclpy.time import Time
from geometry_msgs.msg import PoseWithCovarianceStamped
from lifecycle_msgs.srv import GetState
from nav_msgs.msg import OccupancyGrid, Odometry
from tf2_ros import Buffer, TransformListener
from semantic_map import RegionCatalog


def wait_ready(regions_file, initialize_spawn=False, timeout=180):
    node = Node('voice_demo_ready')
    node.set_parameters([Parameter('use_sim_time', value=True)])
    catalog = RegionCatalog(regions_file)
    qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    received = {'map': None, 'odom': False}
    node.create_subscription(OccupancyGrid, '/map', lambda m: received.update(map=m), qos)
    node.create_subscription(Odometry, '/odom', lambda _: received.update(odom=True), 10)
    initial = node.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
    lifecycle = node.create_client(GetState, '/bt_navigator/get_state')
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    future = None
    active = False
    initial_sent = False
    last_initial = 0
    deadline = time.monotonic()+timeout
    try:
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            grid = received['map']
            if grid:
                m = catalog.map
                same = (grid.info.width == m.width and grid.info.height == m.height
                        and abs(grid.info.resolution-m.resolution)<1e-6
                        and abs(grid.info.origin.position.x-m.origin[0])<1e-6
                        and abs(grid.info.origin.position.y-m.origin[1])<1e-6)
                q = grid.info.origin.orientation
                yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
                same = same and abs(math.remainder(yaw-m.origin[2],2*math.pi)) < 1e-6
                if not same:
                    raise RuntimeError('Map Nav2 không khớp catalog vùng; kiểm tra map.yaml')
                if received.get('map_checked') is not grid:
                    # OccupancyGrid indexes bottom-up while PGM indexes top-down.
                    actual = np.asarray(grid.data).reshape(m.height,m.width)[::-1]
                    occupancy = m.image.astype(float)/255
                    if not m.meta.get('negate', 0):
                        occupancy = 1-occupancy
                    expected = np.full(m.image.shape,-1,dtype=np.int16)
                    expected[occupancy < float(m.meta['free_thresh'])] = 0
                    expected[occupancy > float(m.meta['occupied_thresh'])] = 100
                    if not np.array_equal(actual,expected):
                        raise RuntimeError('Nội dung /map khác bản đồ phân vùng')
                    received['map_checked'] = grid
            if (initialize_spawn and grid and received['odom']
                    and node.get_clock().now().nanoseconds > 5_000_000_000
                    and buffer.can_transform('odom','base_link',Time())
                    and (not initial_sent or not buffer.can_transform('map','base_link',Time()))
                    and time.monotonic()-last_initial >= 1):
                msg = PoseWithCovarianceStamped()
                msg.header.frame_id = catalog.data['frame_id']
                msg.pose.pose.position.x, msg.pose.pose.position.y = 2.0, 0.0
                msg.pose.pose.orientation.z = 1.0
                msg.pose.pose.orientation.w = 0.0
                msg.pose.covariance[0] = msg.pose.covariance[7] = msg.pose.covariance[35] = 0.05
                initial.publish(msg)
                initial_sent = True
                last_initial = time.monotonic()
            if future and future.done():
                active = future.result().current_state.id == 3
                future = None
            if lifecycle.service_is_ready() and future is None and not active:
                future = lifecycle.call_async(GetState.Request())
            if (grid and received['odom'] and active
                    and (not initialize_spawn or initial_sent)
                    and buffer.can_transform('map','base_link',Time())):
                node.get_logger().info('SẴN SÀNG: bản đồ khớp, AMCL/TF và Nav2 ACTIVE. Có thể nhận lệnh.')
                return
        raise TimeoutError('Chưa đủ map/odom/TF/AMCL/Nav2 ACTIVE trong thời gian chờ')
    finally:
        node.destroy_node()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--regions', default=str(Path(__file__).resolve().parents[1]/'maps/bai7/regions.yaml'))
    p.add_argument('--initialize-spawn', action='store_true')
    p.add_argument('--timeout',type=float,default=180)
    a = p.parse_args()
    rclpy.init()
    try:
        wait_ready(a.regions, a.initialize_spawn, a.timeout)
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
