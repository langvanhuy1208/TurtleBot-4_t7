#!/usr/bin/env python3
"""Add clearly synthetic command playback before logged acceptance in live video.

This is a presentation audio track, not a recording of a microphone. The
original live-data video is retained as demo_navigation.mp4.
"""
from fractions import Fraction
import json
from pathlib import Path
import wave
import av
import numpy as np

here = Path(__file__).resolve().parent
results = json.loads((here/'gazebo_test_results.json').read_text())
assert 'Whisper' in results['input'], 'Only speech-pipeline recordings are supported'
source = av.open(str(here/'demo_navigation.mp4'))
video_in = source.streams.video[0]
duration = float(video_in.duration * video_in.time_base)
end = results['events'][-1]['seconds']
ratio = duration/end
mix = np.zeros(int((duration+0.1)*16000), dtype=np.float32)
commands = [e for e in results['events'] if e['state'] in ('accepted', 'rejected') and 'text' in e]
assert len(commands) == len(results['results'])
cues = []
for event, case in zip(commands, results['results']):
    with wave.open(str(here/'audio'/case['wav'])) as wav:
        assert wav.getframerate() == 16000 and wav.getnchannels() == 1
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').astype(np.float32)/32768
    start = max(0, int((event['seconds']*ratio-len(samples)/16000-0.3)*16000))
    count = min(len(samples),len(mix)-start)
    mix[start:start+count] += samples[:count]
    cues.append(dict(wav=case['wav'], at_video_seconds=round(start/16000,3)))
output = av.open(str(here/'demo_voice_navigation.mp4'), mode='w')
video_out = output.add_stream_from_template(video_in)
audio_out = output.add_stream('aac', rate=16000)
audio_out.layout = 'mono'
audio_out.bit_rate = 64000
packets = []
for packet in source.demux(video_in):
    if packet.dts is not None:
        packet.stream = video_out
        packets.append(packet)
for start in range(0,len(mix),1024):
    frame = av.AudioFrame.from_ndarray(mix[start:start+1024].reshape(1,-1), format='fltp', layout='mono')
    frame.sample_rate, frame.time_base, frame.pts = 16000, Fraction(1,16000), start
    packets.extend(audio_out.encode(frame))
packets.extend(audio_out.encode(None))
packets.sort(key=lambda packet: float(packet.dts*packet.time_base))
for packet in packets:
    output.mux(packet)
output.close()
source.close()
(here/'demo_audio_cues.json').write_text(json.dumps(dict(
    source='Synthetic WAV replay aligned before logged command acceptance; not microphone audio',
    video='demo_voice_navigation.mp4', cues=cues),ensure_ascii=False,indent=2)+'\n')
print(here/'demo_voice_navigation.mp4')
