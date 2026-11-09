#!/usr/bin/env python3
"""Isolated real DDS/action test with a fake Nav2 server; never moves a robot."""
from pathlib import Path
import json
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import rclpy
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import String
from voice_navigation_node import VoiceNavigation


def main():
    root = Path(__file__).resolve().parents[1]
    rclpy.init(args=['--ros-args', '-p', f'regions_file:={root}/maps/bai7/regions.yaml',
                     '-r', 'navigate_to_pose:=/bai7_test/navigate_to_pose',
                     '-r', '/voice_command:=/bai7_test/command',
                     '-r', '/voice_nav/status:=/bai7_test/status'])
    controller = VoiceNavigation()
    probe = Node('bai7_probe')
    states, goals = [], []
    mode = {'value': 'success', 'delay_accept': 0.0}
    publisher = probe.create_publisher(String, '/voice_command', 10)
    probe.create_subscription(String, '/voice_nav/status', lambda m: states.append(json.loads(m.data)), 100)

    def accept(_goal):
        time.sleep(mode['delay_accept'])
        return GoalResponse.ACCEPT

    def execute(handle):
        pose = handle.request.pose
        assert pose.header.frame_id == 'map'
        goals.append((pose.pose.position.x, pose.pose.position.y))
        until = time.monotonic() + (3 if mode['value'] == 'slow' else 0.15)
        while time.monotonic() < until:
            if handle.is_cancel_requested:
                handle.canceled()
                return NavigateToPose.Result()
            time.sleep(0.01)
        if mode['value'] == 'abort':
            handle.abort()
        else:
            handle.succeed()
        return NavigateToPose.Result()

    server = ActionServer(probe, NavigateToPose, 'navigate_to_pose', execute,
                          callback_group=ReentrantCallbackGroup(), goal_callback=accept,
                          cancel_callback=lambda _: CancelResponse.ACCEPT)
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(controller)
    executor.add_node(probe)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()

    def wait(predicate, seconds=8):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.02)
        raise AssertionError(f'Timeout; states={states[-10:]} goals={goals}')

    def send(text):
        publisher.publish(String(data=text))

    results = []
    try:
        wait(lambda: publisher.get_subscription_count() > 0 and controller.client.server_is_ready())
        for text, route in [('Đi đến khu vực A', ['A']),
                            ('Đi đến khu A', ['A']),
                            ('Đi đến khu B', ['B']),
                            ('Đi đến khu C', ['C']),
                            ('Di chuyển từ khu vực A đến khu vực B', ['A', 'B']),
                            ('Đi đến phòng thí nghiệm', ['B']),
                            ('Đi từ phòng A qua hành lang rồi đến phòng B', ['A', 'C', 'B'])]:
            states.clear()
            start = len(goals)
            send(text)
            wait(lambda: any(s['state'] == 'completed' for s in states))
            expected = [(controller.catalog.regions[r]['goal']['x'],
                         controller.catalog.regions[r]['goal']['y']) for r in route]
            assert goals[start:] == expected, (goals[start:], expected)
            results.append({'command': text, 'route': route, 'result': 'PASS'})
        states.clear()
        start = len(goals)
        send('Đi từ khu vực Z đến khu vực B')
        wait(lambda: any(s['state'] == 'rejected' for s in states))
        assert len(goals) == start
        results.append({'test': 'unknown source rejects entire route', 'result': 'PASS'})
        mode['value'] = 'abort'
        states.clear()
        start = len(goals)
        send('Đi từ A đến B')
        wait(lambda: any(s['state'] == 'failed' for s in states))
        assert len(goals) == start + 1
        results.append({'test': 'abort A never sends B', 'result': 'PASS'})
        mode['value'] = 'slow'
        mode['delay_accept'] = 0.4
        states.clear()
        send('Đi từ A đến B')
        wait(lambda: any(s['state'] == 'navigating' for s in states))
        send('Đi đến C')
        wait(lambda: any(s['state'] == 'rejected' for s in states))
        send('Dừng lại')
        wait(lambda: any(s['state'] == 'cancelled' for s in states))
        assert not controller.busy
        results.append({'test': 'busy rejection and cancel before goal acceptance', 'result': 'PASS'})
        mode['delay_accept'] = 0
        controller.timeout = 0.3
        states.clear()
        send('Đi từ B đến C')
        wait(lambda: any(s['state'] == 'timeout' for s in states))
        wait(lambda: any(s['state'] == 'cancelled' for s in states))
        results.append({'test': 'timeout cancels action and clears queue', 'result': 'PASS'})
        path = root / 'docs/bai7/ros_test_results.json'
        path.write_text(json.dumps({'type': 'real ROS 2 transport; fake Nav2 server',
                                    'tests': results}, ensure_ascii=False, indent=2) + '\n')
        print(f'PASS: {len(results)} ROS integration scenarios; {path}')
    finally:
        executor.shutdown()
        thread.join(timeout=3)
        server.destroy()
        controller.destroy_node()
        probe.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
