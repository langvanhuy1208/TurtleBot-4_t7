#!/usr/bin/env python3
"""Encode the original measured demos as browser-friendly MP4 and WebM.

No trajectory, subtitles, speech or timing is invented. The synthetic audio
track already in the source is retained, with its provenance unchanged.
"""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct
import av

ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'docs/bai7';OUT=ROOT/'videos'
OUT.mkdir(exist_ok=True)


def encode(source_path,destination,webm=False):
    source=av.open(str(source_path))
    original=source.streams.video[0]
    rate=original.average_rate or Fraction(5,1)
    output=av.open(str(destination),mode='w',options={} if webm else {'movflags':'+faststart'})
    video=output.add_stream('libvpx-vp9' if webm else 'libx264',rate=rate)
    video.width,video.height=original.width,original.height
    video.pix_fmt='yuv420p'
    video.codec_context.thread_count=4
    video.options=({'crf':'32','b':'0','deadline':'realtime','cpu-used':'5'} if webm else
                   {'crf':'20','preset':'fast','profile':'baseline'})
    audio=None
    resampler=None
    if source.streams.audio:
        if webm:
            audio=output.add_stream('libopus',rate=48000)
            audio.layout='mono';audio.bit_rate=64000
            resampler=av.AudioResampler(format='flt',layout='mono',rate=48000)
        else:
            audio=output.add_stream_from_template(source.streams.audio[0])
    packets=[];frames=0
    for packet in source.demux():
        if packet.stream.type=='video':
            for frame in packet.decode():
                frame=frame.reformat(format='yuv420p')
                frame.pts=frames;frame.time_base=Fraction(rate.denominator,rate.numerator)
                frames+=1
                packets.extend(video.encode(frame))
        elif packet.stream.type=='audio' and audio is not None:
            if webm:
                for frame in packet.decode():
                    for converted in resampler.resample(frame):packets.extend(audio.encode(converted))
            elif packet.dts is not None:
                packet.stream=audio;packets.append(packet)
    packets.extend(video.encode(None))
    if webm and audio is not None:
        for converted in resampler.resample(None):packets.extend(audio.encode(converted))
        packets.extend(audio.encode(None))
    packets.sort(key=lambda p:float(p.dts*p.time_base))
    for packet in packets:output.mux(packet)
    output.close();source.close()
    return frames


def inspect(path):
    with av.open(str(path)) as container:
        codec=container.streams.video[0].codec_context
        result=dict(file=path.name,video_codec=codec.name,pixel_format=codec.format.name,
                    profile=codec.profile,duration_seconds=round(container.duration/av.time_base,3),
                    audio_codecs=[s.codec_context.name for s in container.streams.audio])
        count=0;audio_frames=0
        for frame in container.decode():
            if isinstance(frame,av.VideoFrame):count+=1
            else:audio_frames+=1
        result.update(decoded_video_frames=count,decoded_audio_frames=audio_frames,
                      bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    if path.suffix=='.mp4':
        raw=path.read_bytes();atoms=[];offset=0
        while offset+8<=len(raw):
            size,kind=struct.unpack('>I4s',raw[offset:offset+8])
            if size==1:size=struct.unpack('>Q',raw[offset+8:offset+16])[0]
            if size==0:size=len(raw)-offset
            if size<8:raise AssertionError('Invalid MP4 atom')
            atoms.append(kind.decode('ascii',errors='replace'));offset+=size
        result['faststart']=atoms.index('moov')<atoms.index('mdat')
        assert result['faststart']
        assert result['video_codec']=='h264'
    else:assert result['video_codec']=='vp9'
    assert count==667,(path,count)
    if result['audio_codecs']:assert audio_frames>0
    return result


def main():
    jobs=[(DOC/'demo_voice_navigation.mp4',OUT/'01_demo_giong_tong_hop_Whisper_Nav2.mp4',False),
          (DOC/'demo_navigation.mp4',OUT/'02_demo_du_lieu_goc_khong_ghep_tieng.mp4',False),
          (DOC/'demo_voice_navigation.mp4',OUT/'03_demo_mo_bang_Firefox.webm',True)]
    results=[]
    for source,destination,webm in jobs:
        temporary=destination.with_name(destination.stem+'.converting'+destination.suffix)
        print('Encoding '+destination.name,flush=True)
        encode(source,temporary,webm)
        result=inspect(temporary)
        temporary.replace(destination);result['file']=destination.name
        results.append(result)
        print(json.dumps(result,ensure_ascii=False),flush=True)
    (DOC/'video_compatibility_results.json').write_text(json.dumps(dict(
        source='Original measured Gazebo demo; synthetic speech track, not human microphone audio',
        verification='All video/audio frames decoded; H.264/yuv420p + AAC/faststart MP4, VP9/Opus WebM',
        results=results),ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
