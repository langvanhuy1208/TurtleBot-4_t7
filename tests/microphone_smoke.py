#!/usr/bin/env python3
"""Brief local microphone transport check; never saves or transcribes samples."""
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from voice_audio import record_audio, pulse_source
source = pulse_source()
audio = record_audio(1.0, backend='pulse', source=source)
assert audio.shape == (16000,) and audio.dtype == np.float32
assert np.isfinite(audio).all()
rms = float(np.sqrt(np.mean(audio**2)))
result = dict(backend='PulseAudio parec', device=source, sample_rate=16000,
              channels=1, samples=len(audio), rms=round(rms,6),
              passed=True, scope='capture transport only; no human speech recognition measured; samples not saved')
path=Path(__file__).resolve().parents[1]/'docs/bai7/microphone_test_results.json'
path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
