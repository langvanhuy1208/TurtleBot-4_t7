#!/usr/bin/env python3
"""Export report images and demo videos from existing measured artifacts."""
from pathlib import Path
import json
import os
import re
import shutil
import textwrap

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
PIC=ROOT/'pictures'; VID=ROOT/'videos'; DOC=ROOT/'docs/bai7'
PIC.mkdir(exist_ok=True); VID.mkdir(exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def font(size=24,bold=False):return ImageFont.truetype(BOLD if bold else FONT,size)
def canvas(title,subtitle='',size=(1500,1000)):
 image=Image.new('RGB',size,'#f8fafc');draw=ImageDraw.Draw(image)
 draw.text((45,25),title,font=font(32,True),fill='#0f172a')
 if subtitle:draw.text((45,78),subtitle,font=font(20),fill='#475569')
 return image,draw
def save_map(source,target,title,subtitle):
 original=Image.open(source).convert('RGB')
 image,draw=canvas(title,subtitle,(1200,1150))
 original.thumbnail((1090,970),getattr(Image, 'Resampling', Image).NEAREST)
 image.paste(original,((1200-original.width)//2,135))
 image.save(PIC/target)

save_map(ROOT/'maps/phase2/map.pgm','01_ban_do_slam_goc.png',
         'Bản đồ SLAM gốc được cung cấp','Nguồn: maps/phase2/map.pgm — giữ nguyên dữ liệu gốc')
save_map(ROOT/'maps/bai7/map.pgm','02_ban_do_tham_chieu_gazebo.png',
         'Bản đồ tham chiếu khớp Gazebo','Raster hóa collision box maze_fast.sdf; 0,05 m/ô; không phải kết quả SLAM mới')
shutil.copy2(ROOT/'maps/bai7/segmented_map.png',PIC/'03_phan_vung_A_B_C.png')
shutil.copy2(ROOT/'maps/bai7/phase2-segmentation/segmented_map.png',PIC/'04_phan_vung_ban_do_slam_goc.png')

image,draw=canvas('Kiến trúc điều hướng bằng giọng nói',
                 'Mã triển khai: PulseAudio → Whisper small → parser → Nav2 → TurtleBot 4',(1500,930))
boxes=[(55,175,455,315,['Micro / WAV','16 kHz, mono; nhấn Enter để thu']),
       (550,175,950,315,['Whisper small','Tiếng Việt • CPU int8 • VAD']),
       (1045,175,1445,315,['Bộ phân tích lệnh','Tên vùng / danh sách đích']),
       (1045,520,1445,660,['Nav2 NavigateToPose','Gửi từng chặng theo thứ tự']),
       (550,520,950,660,['Robot Gazebo','LiDAR / odometry / AMCL']),
       (55,520,455,660,['RViz + terminal','Nhãn A/B/C, /plan, trạng thái'])]
for x1,y1,x2,y2,lines in boxes:
 draw.rounded_rectangle((x1,y1,x2,y2),radius=14,fill='#e0f2fe',outline='#0284c7',width=3)
 for k,line in enumerate(lines):
  draw.text(((x1+x2)/2,y1+32+k*40),line,font=font(23,k==0),fill='#0f172a',anchor='mt')
def arrow(a,b,label=None):
 draw.line([a,b],fill='#334155',width=5)
 direction=np.asarray(b,dtype=float)-a;direction/=np.linalg.norm(direction)
 normal=np.array([-direction[1],direction[0]]);end=np.array(b)
 points=[tuple(end),tuple(end-18*direction+9*normal),tuple(end-18*direction-9*normal)]
 draw.polygon(points,fill='#334155')
 if label:draw.text(((a[0]+b[0])/2,(a[1]+b[1])/2-30),label,font=font(19),fill='#334155',anchor='mm')
arrow((455,245),(550,245));arrow((950,245),(1045,245));arrow((1245,315),(1245,520))
arrow((1045,590),(950,590));arrow((550,590),(455,590))
draw.rounded_rectangle((650,365,1020,460),radius=10,fill='#fef3c7',outline='#d97706',width=2)
draw.text((835,380),'regions.yaml',font=font(24,True),fill='#78350f',anchor='mt')
draw.text((835,417),'ID • aliases • x/y/yaw • clearance',font=font(19),fill='#78350f',anchor='mt')
arrow((1020,413),(1140,315))
draw.text((70,755),'Vùng không tồn tại → rejected, không gửi mục tiêu.',font=font(25),fill='#991b1b')
draw.text((70,805),'Dừng lại → hủy chặng hiện tại, xóa các điểm còn lại.',font=font(25),fill='#0f172a')
image.save(PIC/'05_so_do_kien_truc.png')

image,draw=canvas('Phân vùng bán tự động trên Occupancy Grid',
                 'Không suy ra tên phòng từ ảnh; tên chức năng do người dùng gán',(1500,820))
steps=[('1. Đọc map.yaml','Resolution, origin, threshold'),('2. Chọn hạt giống','A: phòng học; B: phòng thí nghiệm; C: hành lang'),
       ('3. BFS đa nguồn','Lan nhãn trên ô trống 4 lân cận; không xuyên tường'),('4. Chọn đích hợp lệ','OpenCV distance transform; clearance ≥ 0,35 m'),
       ('5. Đổi hệ tọa độ','Tâm pixel → xoay theo yaw → cộng origin'),('6. Xuất dữ liệu','labels.png + regions.yaml + ảnh màu')]
for index,(heading,body) in enumerate(steps):
 y=145+index*95
 draw.rounded_rectangle((65,y,1435,y+75),radius=9,fill='#e0f2fe' if index%2==0 else '#e2e8f0')
 draw.text((90,y+12),heading,font=font(24,True),fill='#0f172a')
 draw.text((485,y+15),body,font=font(22),fill='#334155')
image.save(PIC/'06_quy_trinh_phan_vung.png')

os.environ.setdefault('MPLCONFIGDIR','/tmp/bai7-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family']='DejaVu Sans'
nav=json.loads((DOC/'gazebo_test_results.json').read_text())
extended=json.loads((DOC/'gazebo_extended_results.json').read_text())
valid=[r for r in nav['results'] if r['expected_route']]
fig,ax=plt.subplots(figsize=(11,6.2),layout='constrained')
labels=['Đến A','A → B','Đến phòng thí nghiệm','Đến hành lang C']
values=[r['final_error_m'] for r in valid]
bars=ax.bar(labels,values,color=['#3b82f6','#f59e0b','#f59e0b','#22c55e'])
ax.bar_label(bars,fmt='%.3f m',padding=5)
ax.set_ylim(0,.55);ax.axhline(.5,color='#ef4444',linestyle='--',label='Ngưỡng kiểm thử 0,50 m')
ax.set_ylabel('Khoảng cách AMCL tới đích yêu cầu (m)')
ax.set_title('Sai số đích cuối — Nav2 / Gazebo thực')
ax.legend();ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
fig.text(.02,.005,'Nguồn: docs/bai7/gazebo_test_results.json. Đầu vào: WAV giọng Việt tổng hợp → Whisper small.',fontsize=9)
fig.savefig(PIC/'07_sai_so_dich_do_duoc.png',dpi=170);plt.close(fig)

video=DOC/'demo_voice_navigation.mp4'
cap=cv2.VideoCapture(str(video));duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/cap.get(cv2.CAP_PROP_FPS)
for name,seconds in [('08_demo_dieu_huong_A.png',45),('09_demo_lo_trinh_A_B.png',78),('10_demo_tu_choi_vung_Z.png',duration-.5)]:
 cap.set(cv2.CAP_PROP_POS_MSEC,seconds*1000);ok,frame=cap.read()
 if not ok:raise RuntimeError('Cannot export video frame: '+name)
 cv2.imwrite(str(PIC/name),frame)
cap.release()

ros=json.loads((DOC/'ros_test_results.json').read_text())
asr=json.loads((DOC/'asr_test_results.json').read_text())
unit=re.search(r'(\d+) passed',(DOC/'unit_test_results.txt').read_text()).group(1)
image,draw=canvas('Kết quả kiểm thử đã lưu',
                 'Mỗi nhóm có nguồn chứng minh riêng; Nav2 giả không đo chuyển động robot',(1500,850))
rows=[('Bản đồ / parser / audio',unit+'/'+unit,'unit_test_results.txt'),
      ('ROS DDS + Nav2 giả',f'{len(ros["tests"])}/{len(ros["tests"])}','ros_test_results.json'),
      ('Whisper small / WAV tổng hợp',f'{sum(r["passed"] for r in asr["results"])}/{len(asr["results"])}','asr_test_results.json'),
      ('Whisper → Nav2 → Gazebo',f'{sum(r["passed"] for r in nav["results"])}/{len(nav["results"])}','gazebo_test_results.json'),
      ('Gazebo nhiều điểm + hủy',f'{len(extended["results"])}/{len(extended["results"])}','gazebo_extended_results.json')]
for index,(title,result,source) in enumerate(rows):
 y=160+index*105
 draw.rounded_rectangle((55,y,1445,y+85),radius=10,fill='#e2e8f0')
 draw.text((80,y+15),title,font=font(25,True),fill='#0f172a')
 draw.text((690,y+15),result,font=font(28,True),fill='#15803d')
 draw.text((850,y+20),source,font=font(19),fill='#475569')
draw.text((65,735),'Micro thật đã thu được; chưa đo độ chính xác trên tập giọng người có nhãn.',font=font(23),fill='#475569')
image.save(PIC/'11_tong_hop_kiem_thu.png')

# The supplied speech demo is synthetic, as declared in its manifest.
shutil.copy2(DOC/'demo_voice_navigation.mp4',VID/'01_demo_giong_tong_hop_Whisper_Nav2.mp4')
shutil.copy2(DOC/'demo_navigation.mp4',VID/'02_demo_du_lieu_goc_khong_ghep_tieng.mp4')
manifest={'source':'Existing project maps, measured JSON results and actual live-data demo frames.',
          'videos':{'01_demo_giong_tong_hop_Whisper_Nav2.mp4':'Live Gazebo/AMCL data with synthetic WAV replay; NOT a human microphone recording.',
                    '02_demo_du_lieu_goc_khong_ghep_tieng.mp4':'Original live-map recording, no added audio.'},
          'pictures':sorted(p.name for p in PIC.glob('*.png'))}
(DOC/'media_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(f'Exported {len(manifest["pictures"])} images and {len(manifest["videos"])} videos')
