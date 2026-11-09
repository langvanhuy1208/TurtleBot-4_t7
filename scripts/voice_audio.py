#!/usr/bin/env python3
"""Bounded mono 16 kHz recording with PulseAudio or PortAudio."""
import os
import selectors
import shutil
import subprocess
import tempfile
import time

import numpy as np

SAMPLE_RATE = 16000


def pulse_source():
    """Read the real default input; never silently capture a speaker monitor."""
    result = subprocess.run(['pactl', 'get-default-source'], capture_output=True,
                            text=True, timeout=4, check=True)
    source = result.stdout.strip()
    if not source or source.endswith('.monitor'):
        raise RuntimeError('Đầu vào mặc định là loa monitor. Chọn micro trong Sound Settings.')
    return source


def record_pulse(seconds, source=None):
    source = source or pulse_source()
    if source.endswith('.monitor') or source == '@DEFAULT_MONITOR@':
        raise ValueError('Cần chọn micro, không dùng monitor của loa')
    count = int(seconds*SAMPLE_RATE)*2
    chunks = bytearray()
    command = ['parec', '--raw', '--format=s16le', '--rate=16000', '--channels=1',
               '--latency-msec=80', '--client-name=Bai7Voice', '--device='+source]
    # Stderr goes to a file so an error cannot deadlock a full pipe.
    with tempfile.TemporaryFile() as error:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=error)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                deadline = time.monotonic()+seconds+5
                while len(chunks) < count:
                    remaining = deadline-time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError('Micro không trả đủ dữ liệu âm thanh')
                    if not selector.select(timeout=min(remaining, 0.25)):
                        continue
                    block = os.read(process.stdout.fileno(), min(32768, count-len(chunks)))
                    if not block:
                        error.seek(0)
                        raise RuntimeError('Lỗi thu micro: '+error.read().decode(errors='replace'))
                    chunks.extend(block)
        finally:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
            process.stdout.close()
    return np.frombuffer(chunks, dtype='<i2').astype(np.float32)/32768


def record_audio(seconds, backend='auto', device=None, source=None):
    if not 0.5 <= seconds <= 30:
        raise ValueError('Thời gian thu phải từ 0,5 đến 30 giây')
    if backend == 'pulse' or (backend == 'auto' and device is None and shutil.which('parec')):
        return record_pulse(seconds, source=source)
    if backend not in ('auto', 'sounddevice'):
        raise ValueError('Backend không hợp lệ')
    import sounddevice as sd
    data = sd.rec(int(seconds*SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1,
                  dtype='float32', device=device)
    try:
        sd.wait()
    except BaseException:
        sd.stop()
        raise
    return data[:, 0]
