#!/usr/bin/env python3
"""Check the real MediaPipe Tasks API/model on blank frames; no webcam needed."""
import argparse
import numpy as np
import mediapipe as mp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model_path')
    args = parser.parse_args()
    options = mp.tasks.vision.GestureRecognizerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=args.model_path),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.6)
    with mp.tasks.vision.GestureRecognizer.create_from_options(options) as recognizer:
        image = mp.Image(image_format=mp.ImageFormat.SRGB,
                         data=np.zeros((480, 640, 3), dtype=np.uint8))
        for timestamp in (0, 50, 100):
            result = recognizer.recognize_for_video(image, timestamp)
            assert not result.hand_landmarks
    print(f'PASS: MediaPipe {mp.__version__}, VIDEO mode, model loaded, three no-hand frames')


if __name__ == '__main__':
    main()
