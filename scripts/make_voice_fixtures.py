#!/usr/bin/env python3
"""Generate explicitly synthetic Vietnamese WAV fixtures using system eSpeak NG."""
import ctypes as ct
import json
from pathlib import Path
import wave


def main():
    root = Path(__file__).resolve().parents[1]
    output = root/'docs/bai7/audio'
    output.mkdir(parents=True, exist_ok=True)
    lib = ct.CDLL('libespeak-ng.so.1')
    lib.espeak_Initialize.argtypes = [ct.c_int, ct.c_int, ct.c_char_p, ct.c_int]
    rate = lib.espeak_Initialize(2, 0, None, 0)  # synchronous retrieval, no speaker needed
    assert rate > 0
    lib.espeak_SetVoiceByName.argtypes = [ct.c_char_p]
    assert lib.espeak_SetVoiceByName(b'vi') == 0
    lib.espeak_SetParameter(1, 135, 0)  # words per minute
    callback_type = ct.CFUNCTYPE(ct.c_int, ct.POINTER(ct.c_short), ct.c_int, ct.c_void_p)
    chunks = []

    @callback_type
    def callback(samples, count, _events):
        if samples and count:
            chunks.append(ct.string_at(samples, count*2))
        return 0

    lib.espeak_SetSynthCallback(callback)
    lib.espeak_Synth.argtypes = [ct.c_void_p, ct.c_size_t, ct.c_uint, ct.c_int,
                                ct.c_uint, ct.c_uint, ct.c_void_p, ct.c_void_p]
    commands = [
        ('01', 'Đi đến khu vực A.', ['A']),
        ('02', 'Di chuyển từ khu vực A đến khu vực B.', ['A', 'B']),
        ('03', 'Đi đến phòng thí nghiệm.', ['B']),
        ('04', 'Đi đến hành lang.', ['C']),
        ('05', 'Đi đến khu vực Z.', None),
    ]
    cases = []
    for name, text, route in commands:
        chunks.clear()
        encoded = text.encode('utf-8') + b'\0'
        assert lib.espeak_Synth(encoded, len(encoded), 0, 1, 0, 1, None, None) == 0
        lib.espeak_Synchronize()
        path = output/f'{name}.wav'
        with wave.open(str(path), 'wb') as wav:
            wav.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
            wav.writeframes(b'\0'*rate + b''.join(chunks) + b'\0'*rate)
        cases.append(dict(wav=path.name, text=text, expected_route=route))
    (output/'commands.json').write_text(json.dumps(dict(
        source='synthetic speech: eSpeak NG vi, 135 words/minute; not human recordings',
        cases=cases), ensure_ascii=False, indent=2) + '\n')
    lib.espeak_Terminate()
    print(output)


if __name__ == '__main__':
    main()
