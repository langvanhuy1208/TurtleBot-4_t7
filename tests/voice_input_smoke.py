#!/usr/bin/env python3
"""Exercise the actual CLI with text, WAV, silence and real microphone capture.

Commands go only to this observer on an isolated ROS domain, never a robot.
Microphone samples remain in a temporary directory and are deleted on exit.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import wave
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String

root=Path(__file__).resolve().parents[1]
rclpy.init();node=Node('bai7_input_observer')
messages=[]
status=node.create_publisher(String,'/voice_nav/status',10)
def command(msg):
 messages.append(msg.data)
 status.publish(String(data=json.dumps({'state':'observed_by_test','text':msg.data},ensure_ascii=False)))
node.create_subscription(String,'/voice_command',command,10)
e=SingleThreadedExecutor();e.add_node(node)
thread=threading.Thread(target=e.spin,daemon=True);thread.start()
results=[]
def run(args,stdin=None):
 result=subprocess.run([str(root/'.venv-voice/bin/python'),str(root/'scripts/voice_input.py'),*args],
                       input=stdin,text=True,capture_output=True,timeout=60)
 if result.returncode!=0:raise AssertionError(result.stdout+result.stderr)
 return result.stdout
try:
 text='Đi đến khu vực Z'
 output=run(['--text',text]);assert messages[-1]==text
 assert 'observed_by_test' in output,output
 results.append(dict(test='CLI text publish and background status display',passed=True))
 output=run(['--wav',str(root/'docs/bai7/audio/01.wav'),'--model','small'])
 assert messages[-1]=='Đi đến khu vực A.',messages
 results.append(dict(test='CLI real Whisper WAV decoding and publish',passed=True))
 with tempfile.TemporaryDirectory(prefix='bai7-input-') as folder:
  silence=Path(folder)/'silence.wav'
  with wave.open(str(silence),'wb') as wav:
   wav.setparams((1,2,16000,0,'NONE','not compressed'));wav.writeframes(b'\0'*32000)
  before=len(messages)
  output=run(['--wav',str(silence),'--model','small'])
  assert len(messages)==before,(messages,output)
  results.append(dict(test='silent WAV never publishes a robot command',passed=True))
  # A one-second physical capture, then EOF exits the interactive loop.
  output=run(['--model','small','--seconds','1','--audio-backend','pulse',
              '--save-audio',folder],stdin='\n')
  recordings=list(Path(folder).glob('command_*.wav'))
  assert len(recordings)==1,output
  with wave.open(str(recordings[0])) as wav:
   assert (wav.getframerate(),wav.getnchannels(),wav.getnframes())==(16000,1,16000)
  results.append(dict(test='CLI real microphone capture and local Whisper processing',passed=True,
                      scope='transport/decode only; no labelled human sentence accuracy; temporary samples deleted'))
 path=root/'docs/bai7/voice_input_test_results.json'
 path.write_text(json.dumps(dict(source='actual voice_input CLI; isolated ROS observer, no robot',results=results),
                            ensure_ascii=False,indent=2)+'\n')
 print('PASS: all 4 voice input CLI scenarios')
finally:
 e.shutdown();thread.join(timeout=3);node.destroy_node();rclpy.shutdown()
