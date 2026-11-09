#!/usr/bin/env python3
"""Run Ultralytics YOLO on a TurtleBot RGB image topic."""

import cv2
import rclpy
import threading
import time
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from sensor_msgs.msg import Image
import torch
from ultralytics import YOLO


class YoloDetector(Node):
    def __init__(self):
        super().__init__('yolo_detector')
        self.declare_parameter('image_topic', '/oakd/rgb/preview/image_raw')
        self.declare_parameter('model', 'yolov8n.pt')
        self.declare_parameter('show_window', True)
        self.declare_parameter('publish_topic', '/yolo/detections/image')
        self.declare_parameter('inference_period', 0.5)
        self.declare_parameter('confidence', 0.25)
        self.declare_parameter('image_size', 320)
        torch.set_num_threads(1)
        self.bridge = CvBridge()
        self.model = YOLO(self.get_parameter('model').value)
        self.show_window = bool(self.get_parameter('show_window').value)
        self.inference_period = float(self.get_parameter('inference_period').value)
        self.confidence = float(self.get_parameter('confidence').value)
        self.image_size = int(self.get_parameter('image_size').value)
        self.last_inference = 0.0
        self._condition = threading.Condition()
        self._latest_frame = None
        self._frame_sequence = 0
        self._annotated_frame = None
        self._annotated_sequence = 0
        self._stop_worker = False
        self._displayed_sequence = 0
        self._last_detection_log = 0.0
        self.image_pub = self.create_publisher(Image, self.get_parameter('publish_topic').value, 10)
        self.image_sub = self.create_subscription(
            Image, self.get_parameter('image_topic').value, self.image_callback, 10
        )
        self.display_timer = self.create_timer(0.03, self._display_callback)
        self._worker = threading.Thread(target=self._inference_worker, daemon=True)
        self._worker.start()
        self.get_logger().info(f"YOLO ready; listening on {self.get_parameter('image_topic').value}")

    def image_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            with self._condition:
                self._latest_frame = frame
                self._latest_header = msg.header
                self._frame_sequence += 1
                self._condition.notify()
        except Exception as exc:  # keep the subscription alive on a bad frame
            self.get_logger().error(f'Image conversion failed: {exc}')

    def _inference_worker(self):
        consumed_sequence = 0
        while True:
            with self._condition:
                while not self._stop_worker and self._frame_sequence == consumed_sequence:
                    self._condition.wait()
                if self._stop_worker:
                    return
                delay = self.inference_period - (time.monotonic() - self.last_inference)
                if delay > 0:
                    self._condition.wait_for(lambda: self._stop_worker, timeout=delay)
                    if self._stop_worker:
                        return
                frame = self._latest_frame.copy()
                header = self._latest_header
                consumed_sequence = self._frame_sequence
            self.last_inference = time.monotonic()
            try:
                result = self.model.predict(
                    frame, conf=self.confidence, imgsz=self.image_size,
                    device='cpu', verbose=False
                )[0]
                annotated = result.plot()
                detections = []
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    label = result.names[class_id]
                    detections.append(f'{label} ({confidence:.2f})')
                now = time.monotonic()
                if detections and now - self._last_detection_log >= 1.0:
                    self.get_logger().info('Detected: ' + ', '.join(detections))
                    self._last_detection_log = now
                output = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
                output.header = header
                self.image_pub.publish(output)
                with self._condition:
                    self._annotated_frame = annotated
                    self._annotated_sequence += 1
            except Exception as exc:  # keep processing subsequent camera frames
                self.get_logger().error(f'Image inference failed: {exc}')

    def _display_callback(self):
        if not self.show_window:
            return
        with self._condition:
            if self._annotated_frame is not None and self._annotated_sequence != self._displayed_sequence:
                annotated = self._annotated_frame.copy()
                self._displayed_sequence = self._annotated_sequence
            else:
                annotated = None
        if annotated is not None:
            cv2.imshow('TurtleBot 4 YOLO', annotated)
        cv2.waitKey(1)

    def destroy_node(self):
        with self._condition:
            self._stop_worker = True
            self._condition.notify_all()
        if self._worker.is_alive():
            self._worker.join(timeout=5.0)
        if self.show_window:
            cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = YoloDetector()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            # The ROS signal handler may already have shut down the context.
            pass


if __name__ == '__main__':
    main()
