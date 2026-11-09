"""Audio validation and privacy boundaries without accessing a real microphone."""
from pathlib import Path
import subprocess
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import voice_audio


@pytest.mark.parametrize('duration', [0, -.1, .49, 31, float('nan')])
def test_duration_must_be_bounded(duration):
    with pytest.raises(ValueError):
        voice_audio.record_audio(duration)


def test_speaker_monitor_is_not_a_microphone(monkeypatch):
    monkeypatch.setattr(voice_audio.subprocess,'run',lambda *a,**k:
        subprocess.CompletedProcess(a,0,stdout='speaker.monitor\n'))
    with pytest.raises(RuntimeError,match='monitor'):
        voice_audio.pulse_source()


@pytest.mark.parametrize('source',['speaker.monitor','@DEFAULT_MONITOR@'])
def test_explicit_monitor_also_rejected(source):
    with pytest.raises(ValueError,match='monitor'):
        voice_audio.record_pulse(1,source)


def test_auto_prefers_pulse_without_importing_portaudio(monkeypatch):
    sentinel=object()
    monkeypatch.setattr(voice_audio.shutil,'which',lambda _: '/usr/bin/parec')
    monkeypatch.setattr(voice_audio,'record_pulse',lambda *a,**k: sentinel)
    assert voice_audio.record_audio(1,backend='auto') is sentinel
