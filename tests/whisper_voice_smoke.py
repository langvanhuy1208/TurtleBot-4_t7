#!/usr/bin/env python3
"""Measure actual local ASR over labelled synthetic WAV fixtures, without ROS."""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from semantic_map import RegionCatalog
from faster_whisper import WhisperModel

p = argparse.ArgumentParser()
p.add_argument('--model', default='base')
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
fixtures = root/'docs/bai7/audio'
catalog = RegionCatalog(root/'maps/bai7/regions.yaml')
model = WhisperModel(a.model, device='cpu', compute_type='int8', cpu_threads=4)
results = []
manifest = json.loads((fixtures/'commands.json').read_text())
for case in manifest['cases']:
    start = time.monotonic()
    segments, _ = model.transcribe(str(fixtures/case['wav']), language='vi', task='transcribe',
                                  vad_filter=True, beam_size=5, condition_on_previous_text=False)
    text = ' '.join(s.text.strip() for s in segments if s.no_speech_prob < 0.6 and s.avg_logprob > -1.0)
    try:
        route = catalog.parse(text)
    except ValueError:
        route = None
    results.append(dict(**case, transcript=text, route=route,
                        passed=bool(text) and route == case['expected_route'], seconds=round(time.monotonic()-start, 2)))
    print(json.dumps(results[-1], ensure_ascii=False), flush=True)
(root/'docs/bai7/asr_test_results.json').write_text(json.dumps(dict(
    model=a.model, source=manifest['source'],
    results=results), ensure_ascii=False, indent=2)+'\n')
assert all(r['passed'] for r in results), 'See asr_test_results.json for measured failures'
