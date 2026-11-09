#!/usr/bin/env python3
"""Record measured AMCL/Nav2 motion. Use only with the matching Gazebo maze."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Path as NavPath
from std_msgs.msg import String
from lifecycle_msgs.srv import GetState

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from semantic_map import RegionCatalog


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--speech', action='store_true', help='Real Whisper decoding of synthetic WAV fixtures')
    p.add_argument('--model', default='base')
    a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root/'docs/bai7'
    catalog = RegionCatalog(root/'maps/bai7/regions.yaml')
    rclpy.init()
    node = Node('bai7_gazebo_demo')
    node.set_parameters([Parameter('use_sim_time', value=True)])
    pub = node.create_publisher(String, '/voice_command', 10)
    initial = node.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
    lifecycle = node.create_client(GetState, '/bt_navigator/get_state')
    data = {'pose': None, 'path': [], 'statuses': [], 'text': '', 'transcript': '', 'trail': [], 'events': []}
    started = time.monotonic()

    def amcl(msg):
        pose = msg.pose.pose
        data['pose'] = (pose.position.x, pose.position.y)
        data['trail'].append(data['pose'])

    def status(msg):
        item = json.loads(msg.data)
        data['statuses'].append(item)
        data['events'].append(dict(seconds=round(time.monotonic()-started, 2), **item))
        print(msg.data, flush=True)

    node.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', amcl, 10)
    node.create_subscription(String, '/voice_nav/status', status, 100)
    node.create_subscription(String, '/voice_nav/transcript', lambda m: data.update(transcript=m.data), 10)
    node.create_subscription(NavPath, '/plan', lambda m: data.update(
        path=[(p.pose.position.x, p.pose.position.y) for p in m.poses]), 10)
    base = Image.open(output.parent.parent/'maps/bai7/segmented_map.png').convert('RGB')
    size = (1000, 1160)
    writer = cv2.VideoWriter(str(output/'demo_navigation.mp4'), cv2.VideoWriter_fourcc(*'mp4v'), 5, size)
    if not writer.isOpened():
        raise RuntimeError('MP4 video codec unavailable')
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
    next_frame = 0
    frames = 0

    def pixel(point):
        u, v = catalog.map.world_to_pixel(*point)
        return u*2+10, v*2+150

    def spin(seconds):
        nonlocal next_frame, frames
        until = time.monotonic()+seconds
        while time.monotonic() < until:
            rclpy.spin_once(node, timeout_sec=0.02)
            now = time.monotonic()
            if now >= next_frame:
                canvas = Image.new('RGB', size, 'white')
                canvas.paste(base, (10, 150))
                draw = ImageDraw.Draw(canvas)
                mode = 'Whisper từ WAV giọng Việt tổng hợp' if a.speech else 'Lệnh văn bản kiểm thử, không phải giọng nói'
                draw.text((15, 10), 'Bài 7 — Robot Gazebo / vị trí AMCL / đường Nav2 thực tế', fill='black', font=font)
                draw.text((15, 38), mode, fill='darkblue', font=font)
                draw.text((15, 66), data['text'], fill='black', font=font)
                draw.text((15, 94), 'ASR: '+data['transcript'], fill='black', font=font)
                draw.text((15, 122), f'Thời gian đo: {now-started:.1f}s | ' + str(data['statuses'][-1:] or 'Đang định vị')[:90], fill='black', font=font)
                if len(data['path']) > 1:
                    draw.line([pixel(pt) for pt in data['path']], fill='orange', width=3)
                if len(data['trail']) > 1:
                    draw.line([pixel(pt) for pt in data['trail']], fill='purple', width=3)
                if data['pose']:
                    x, y = pixel(data['pose'])
                    draw.ellipse((x-9, y-9, x+9, y+9), fill='red', outline='black')
                draw.text((15, 1120), 'Đỏ: robot | Tím: vệt AMCL | Cam: kế hoạch Nav2', fill='black', font=font)
                writer.write(cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR))
                frames += 1
                next_frame = now + 0.2

    results = []
    process = None
    try:
        deadline = time.monotonic()+100
        while data['pose'] is None and time.monotonic() < deadline:
            # Matches the default simulator spawn: (2, 0, pi).
            msg = PoseWithCovarianceStamped()
            msg.header.frame_id = 'map'
            msg.pose.pose.position.x, msg.pose.pose.position.y = 2.0, 0.0
            msg.pose.pose.orientation.z, msg.pose.pose.orientation.w = 1.0, 0.0
            msg.pose.covariance[0] = msg.pose.covariance[7] = 0.05
            msg.pose.covariance[35] = 0.05
            initial.publish(msg)
            spin(1)
        assert data['pose'] is not None, 'AMCL never localized'
        # Action discovery alone does not imply the lifecycle server is active.
        deadline = time.monotonic()+90
        while time.monotonic() < deadline:
            if lifecycle.service_is_ready():
                future = lifecycle.call_async(GetState.Request())
                while not future.done() and time.monotonic() < deadline:
                    spin(0.1)
                if future.done() and future.result().current_state.id == 3:
                    break
            spin(0.5)
        else:
            raise RuntimeError('Nav2 lifecycle never became ACTIVE')
        cases = json.loads((output/'audio/commands.json').read_text())['cases']
        for case in cases:
            data['text'] = case['text']
            data['transcript'] = ''
            data['statuses'].clear()
            start = time.monotonic()
            if a.speech:
                process = subprocess.Popen([str(root/'.venv-voice/bin/python'), str(root/'scripts/voice_input.py'),
                    '--wav', str(output/'audio'/case['wav']), '--model', a.model])
            else:
                pub.publish(String(data=case['text']))
            deadline = time.monotonic()+320
            terminal = {'completed', 'rejected', 'failed', 'cancelled'}
            while time.monotonic() < deadline:
                spin(0.2)
                if data['statuses'] and data['statuses'][-1]['state'] in terminal:
                    break
                if process and process.poll() not in (None, 0):
                    raise RuntimeError(f'Voice input failed: {process.returncode}')
            else:
                raise RuntimeError('No terminal navigation status within 320 seconds')
            if process:
                process.wait(timeout=10)
                process = None
            expected = case['expected_route']
            arrived = [s['region'] for s in data['statuses'] if s['state'] == 'arrived']
            state = data['statuses'][-1]['state']
            error = None
            if expected and data['pose']:
                goal = catalog.regions[expected[-1]]['goal']
                error = math.hypot(data['pose'][0]-goal['x'], data['pose'][1]-goal['y'])
            passed = (state == 'rejected' and not arrived) if expected is None else (
                state == 'completed' and arrived == expected and error is not None and error <= 0.5)
            results.append(dict(**case, transcript=data['transcript'], arrived=arrived, state=state,
                                final_error_m=round(error, 3) if error is not None else None,
                                seconds=round(time.monotonic()-start, 2), passed=passed))
            spin(2)
        assert all(item['passed'] for item in results), 'Some scenarios failed; inspect measured results'
    finally:
        if process and process.poll() is None:
            process.terminate()
        pub.publish(String(data='Dừng lại'))
        writer.release()
        (output/'gazebo_test_results.json').write_text(json.dumps(dict(
            source='Gazebo TurtleBot4, real Nav2 and AMCL; geometry reference map, not SLAM',
            input='Whisper decoding synthetic Vietnamese WAVs' if a.speech else 'text commands',
            video=dict(file='demo_navigation.mp4', frames=frames, fps=5),
            results=results, events=data['events']), ensure_ascii=False, indent=2)+'\n')
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
