#!/usr/bin/env python3
"""Optional fixture generation using Google TTS. Sends only listed sample text.
Requires gTTS and PyAV in a separate tools environment; not needed at runtime.
"""
import io
import json
from pathlib import Path
import wave
import av
from gtts import gTTS

root = Path(__file__).resolve().parents[1]
folder = root/'docs/bai7/audio'
data = json.loads((folder/'commands.json').read_text())
for case in data['cases']:
    audio = io.BytesIO()
    gTTS(case['text'], lang='vi', timeout=20).write_to_fp(audio)
    audio.seek(0)
    container = av.open(audio)
    resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
    pcm = bytearray(b'\0'*16000)
    for frame in container.decode(audio=0):
        for out in resampler.resample(frame):
            pcm.extend(out.to_ndarray().astype('<i2').tobytes())
    for out in resampler.resample(None):
        pcm.extend(out.to_ndarray().astype('<i2').tobytes())
    pcm.extend(b'\0'*16000)
    with wave.open(str(folder/case['wav']), 'wb') as wav:
        wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        wav.writeframes(pcm)
    print(case['text'], flush=True)
data['source'] = 'Synthetic Vietnamese speech generated with Google TTS (gTTS); NOT human microphone recordings'
(folder/'commands.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
