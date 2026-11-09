#!/usr/bin/env python3
"""OpenCV webcam + MediaPipe Tasks Gesture Recognizer, one operator hand."""
import json
import time
from pathlib import Path

import cv2
import mediapipe as mp
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from gesture_core import GestureFilter, GESTURES


class GestureRecognitionNode(Node):
    def __init__(self):
        super().__init__('gesture_recognition_node')
        for key, value in {'model_path': '', 'camera_index': 0,
                           'confidence_threshold': 0.65, 'hold_seconds': 0.35}.items():
            self.declare_parameter(key, value)
        p = lambda name: self.get_parameter(name).value
        model = Path(p('model_path')).expanduser()
        if not model.is_file():
            raise FileNotFoundError('Missing .task model; run scripts/download_gesture_model.py')
        self.threshold = p('confidence_threshold')
        if not 0 < self.threshold <= 1 or not 0 < p('hold_seconds') < 0.7:
            raise ValueError('confidence must be in (0,1]; hold_seconds in (0,0.7)')
        self.filter = GestureFilter(p('hold_seconds'))
        self.publisher = self.create_publisher(String, '/detected_gesture', 1)
        self.robot_status = 'Waiting for robot_behavior_node'
        self.create_subscription(String, '/robot_behavior/status', self.on_status, 1)
        options = mp.tasks.vision.GestureRecognizerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6)
        self.recognizer = mp.tasks.vision.GestureRecognizer.create_from_options(options)
        self.camera = cv2.VideoCapture(p('camera_index'), cv2.CAP_V4L2)
        if not self.camera.isOpened():
            self.recognizer.close()
            self.camera.release()
            raise RuntimeError('Cannot open webcam; check camera_index and /dev/video*')
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.timestamp = -1
        self.create_timer(1.0 / 20.0, self.on_frame)

    def on_status(self, msg):
        try:
            s = json.loads(msg.data)
            self.robot_status = f"{s['state']} | {s['selected'] or '-'} | {s['reason']}"
        except (ValueError, KeyError, TypeError):
            self.robot_status = 'Invalid status'

    def on_frame(self):
        ok, frame = self.camera.read()
        if not ok:
            self.publisher.publish(String(data='NONE'))
            self.filter.update('NONE', 0.0, time.monotonic())
            return
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        now = time.monotonic()
        self.timestamp = max(self.timestamp + 1, int(now * 1000))
        result = self.recognizer.recognize_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), self.timestamp)
        raw, score, center = 'NONE', 0.0, 0.0
        # Two hands are ambiguous: refuse control instead of switching operators.
        if len(result.hand_landmarks) == 1 and result.gestures and result.gestures[0]:
            category = result.gestures[0][0]
            score = float(category.score)
            if category.category_name in GESTURES and score >= self.threshold:
                raw = category.category_name
            landmarks = result.hand_landmarks[0]
            center = sum(landmarks[i].x for i in (0, 5, 9, 13, 17)) / 5
            for point in landmarks:
                cv2.circle(frame, (int(point.x * frame.shape[1]),
                                   int(point.y * frame.shape[0])), 3, (0, 230, 255), -1)
        label = self.filter.update(raw, center, now)
        self.publisher.publish(String(data=label))
        lines = [f'AI: {raw}  confidence: {score:.2f}', f'Published: {label}',
                 self.robot_status, 'Select: wave / 1 finger / V; confirm: thumb up',
                 'STOP: palm | CANCEL: fist | Keep one hand visible']
        for i, line in enumerate(lines):
            cv2.putText(frame, line, (10, 25 + i * 24), cv2.FONT_HERSHEY_SIMPLEX,
                        0.46, (0, 255, 0), 1, cv2.LINE_AA)
        cv2.imshow('Bai 6 - Hand Gesture HRI', frame)
        # Window events only: no keyboard controls.
        cv2.waitKey(1)
        if cv2.getWindowProperty('Bai 6 - Hand Gesture HRI', cv2.WND_PROP_VISIBLE) < 1:
            self.publisher.publish(String(data='NONE'))
            raise SystemExit

    def close(self):
        if rclpy.ok():
            self.publisher.publish(String(data='NONE'))
        self.camera.release()
        self.recognizer.close()
        cv2.destroyAllWindows()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = GestureRecognitionNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.close()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
