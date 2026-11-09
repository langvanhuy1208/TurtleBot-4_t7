#!/usr/bin/env python3
"""Download the official versioned model; never fetch models at node startup."""
import argparse
from pathlib import Path
import urllib.request

URL = ('https://storage.googleapis.com/mediapipe-models/gesture_recognizer/'
       'gesture_recognizer/float16/1/gesture_recognizer.task')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=Path('models/gesture_recognizer.task'))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix('.download')
    try:
        with urllib.request.urlopen(URL, timeout=60) as response:
            temporary.write_bytes(response.read())
        if temporary.stat().st_size < 100000:
            raise RuntimeError('Unexpected model size; download rejected')
        temporary.replace(args.output)
    finally:
        temporary.unlink(missing_ok=True)
    print(args.output.resolve())


if __name__ == '__main__':
    main()
