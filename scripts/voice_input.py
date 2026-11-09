#!/usr/bin/env python3
"""Vietnamese Whisper speech input; push-to-talk prevents background commands."""
import argparse
import json
import threading
import time
from pathlib import Path

import rclpy
from rclpy.executors import SingleThreadedExecutor, ExternalShutdownException
from std_msgs.msg import String


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--wav', type=Path, help='Transcribe one existing audio recording')
    source.add_argument('--text', help='Explicit keyboard test mode (not speech evidence)')
    parser.add_argument('--model', default='small', help='Multilingual faster-whisper model or local directory')
    parser.add_argument('--seconds', type=float, default=6)
    parser.add_argument('--device', type=int, help='sounddevice microphone index')
    parser.add_argument('--audio-backend', choices=['auto', 'pulse', 'sounddevice'], default='auto')
    parser.add_argument('--pulse-source', help='PulseAudio input source name; default is the system microphone')
    parser.add_argument('--save-audio', type=Path, help='Directory for microphone evidence WAVs')
    args = parser.parse_args()
    if not 0.5 <= args.seconds <= 30:
        parser.error('--seconds must be 0.5..30')
    rclpy.init()
    node = rclpy.create_node('voice_input')
    publisher = node.create_publisher(String, '/voice_command', 10)
    transcript_pub = node.create_publisher(String, '/voice_nav/transcript', 10)
    node.create_subscription(String, '/voice_nav/status',
        lambda msg: print('Điều hướng: '+msg.data, flush=True), 20)
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    def spin():
        try:
            executor.spin()
        except ExternalShutdownException:
            pass
    spin_thread = threading.Thread(target=spin, daemon=True)
    spin_thread.start()
    try:
        model = None
        if args.text is None:
            from faster_whisper import WhisperModel
            import numpy as np
            model = WhisperModel(args.model, device='cpu', compute_type='int8', cpu_threads=4)
        # Wait briefly for discovery, especially for one-shot file/text modes.
        deadline = time.monotonic() + 5
        while publisher.get_subscription_count() == 0 and time.monotonic() < deadline:
            time.sleep(0.1)
        if publisher.get_subscription_count() == 0:
            raise RuntimeError('Không thấy voice_navigation; khởi động launch/voice_navigation.launch.py trước')
        while rclpy.ok():
            if args.text is not None:
                text = args.text
            else:
                if args.wav:
                    if not args.wav.is_file():
                        raise FileNotFoundError(args.wav)
                    audio = str(args.wav)
                else:
                    from voice_audio import record_audio
                    input('Nhấn Enter rồi nói trong %.1f giây (Ctrl+C để thoát): ' % args.seconds)
                    print('Đang thu âm... ', flush=True)
                    audio = record_audio(args.seconds, backend=args.audio_backend,
                                         device=args.device, source=args.pulse_source)
                    if args.save_audio:
                        import wave
                        args.save_audio.mkdir(parents=True, exist_ok=True)
                        path = args.save_audio / f'command_{time.time_ns()}.wav'
                        with wave.open(str(path), 'wb') as wav:
                            wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                            wav.writeframes((np.clip(audio, -1, 1)*32767).astype('<i2').tobytes())
                    if float(np.sqrt(np.mean(audio**2))) < 0.003:
                        print('Âm thanh quá nhỏ; không gửi lệnh.')
                        continue
                segments, _info = model.transcribe(audio, language='vi', task='transcribe',
                    vad_filter=True, beam_size=5, condition_on_previous_text=False)
                # Do not bias the recognizer with destination prompts on silence.
                text = ' '.join(s.text.strip() for s in segments
                                if s.no_speech_prob < 0.6 and s.avg_logprob > -1.0).strip()
            print(json.dumps({'transcript': text}, ensure_ascii=False), flush=True)
            transcript_pub.publish(String(data=text))
            if text:
                publisher.publish(String(data=text))
                time.sleep(0.2)
            if args.text is not None or args.wav:
                break
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        executor.shutdown()
        spin_thread.join(timeout=3)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
