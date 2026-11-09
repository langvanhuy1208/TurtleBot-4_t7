#!/usr/bin/env python3
"""Rebuild the Vietnamese PDF. Replace metadata and add measured screenshots."""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                               TableStyle, PageBreak)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon


HERE = Path(__file__).resolve().parent
STUDENT = '[Điền họ tên, MSSV, lớp]'
VIDEO_URL = '[Bổ sung link Google Drive công khai sau khi quay]'
GITHUB_URL = '[Bổ sung link repository GitHub Public]'


def main():
    fonts = Path('/usr/share/fonts/truetype/dejavu')
    pdfmetrics.registerFont(TTFont('VN', str(fonts / 'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('VN-Bold', str(fonts / 'DejaVuSans-Bold.ttf')))
    styles = getSampleStyleSheet()
    for name in ('Normal', 'Title', 'Heading1', 'Heading2'):
        styles[name].fontName = 'VN-Bold' if name != 'Normal' else 'VN'
    styles['Normal'].fontSize, styles['Normal'].leading = 10, 16
    styles['Normal'].spaceAfter = 9
    styles['Title'].fontSize, styles['Title'].leading = 17, 25
    styles['Heading1'].fontSize, styles['Heading1'].leading = 13, 20
    cell = ParagraphStyle('CellVN', parent=styles['Normal'], fontSize=8, leading=12)
    story = []

    def p(text, style='Normal'):
        story.append(Paragraph(escape(text), styles[style]))

    def table(rows, widths):
        t = Table([[Paragraph(escape(str(c)), cell) for c in row] for row in rows],
                  colWidths=widths, repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#94a3b8')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7)]))
        story.extend([t, Spacer(1, 12)])

    p('BÀI TẬP 6\nGIAO TIẾP PHI NGÔN NGỮ VỚI TURTLEBOT 4', 'Title')
    p('Nhận diện cử chỉ tay bằng webcam và điều khiển hành vi qua ROS 2')
    p('Sinh viên: ' + STUDENT)
    p('1. Mục tiêu và phạm vi', 'Heading1')
    p('Xây dựng hai node ROS 2 Humble để nhận diện 6 cử chỉ và điều khiển '
      'TurtleBot 4 trong Ignition Gazebo. Hệ thống yêu cầu chọn rồi xác nhận, '
      'có dừng/hủy, lọc nhiễu và watchdog. Không cần Nav2 hoặc bản đồ.')
    p('2. Kiến trúc hệ thống', 'Heading1')
    d = Drawing(470, 215)
    def box(x, y, w, lines):
        d.add(Rect(x, y, w, 48, rx=5, fillColor=colors.HexColor('#eff6ff'),
                   strokeColor=colors.HexColor('#2563eb')))
        for i, line in enumerate(lines):
            d.add(String(x + w / 2, y + 30 - i * 15, line,
                         fontName='VN', fontSize=8, textAnchor='middle'))
    def arrow(x1, y1, x2, y2):
        d.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor('#334155')))
        if y1 == y2:
            d.add(Polygon([x2, y2, x2-6, y2+3, x2-6, y2-3],
                          fillColor=colors.HexColor('#334155')))
        else:
            d.add(Polygon([x2, y2, x2-3, y2+6, x2+3, y2+6],
                          fillColor=colors.HexColor('#334155')))
    box(0, 150, 110, ['Webcam laptop', 'OpenCV / RGB'])
    box(155, 150, 145, ['gesture_recognition_node', 'MediaPipe + lọc thời gian'])
    box(345, 150, 120, ['robot_behavior_node', 'FSM + watchdog'])
    box(345, 30, 120, ['TurtleBot 4 / Gazebo', 'Twist → chuyển động'])
    box(155, 30, 145, ['LiDAR /scan', 'LaserScan → kiểm tra an toàn'])
    arrow(110, 174, 155, 174)
    arrow(300, 174, 345, 174)
    arrow(405, 150, 405, 78)
    d.add(Line(300, 54, 320, 54))
    d.add(Line(320, 54, 320, 160))
    arrow(320, 160, 345, 160)
    d.add(String(302, 202, '/detected_gesture', fontName='VN', fontSize=8))
    d.add(String(412, 110, '/cmd_vel', fontName='VN', fontSize=8))
    d.add(String(0, 0, 'Trạng thái /robot_behavior/status được đưa về cửa sổ webcam.',
                 fontName='VN', fontSize=9))
    story.extend([d, Spacer(1, 10)])
    p('Luồng xử lý: ảnh → AI → nhãn/lọc → chọn/xác nhận → kiểm tra an toàn → '
      'vận tốc. LiDAR tác động vào bộ điều khiển trước khi phát vận tốc.')
    story.append(PageBreak())

    p('3. Node, topic và nhận diện', 'Heading1')
    table([
        ['Topic', 'Kiểu', 'Luồng'],
        ['/detected_gesture', 'std_msgs/msg/String', 'Nhận diện → điều khiển'],
        ['/cmd_vel', 'geometry_msgs/msg/Twist', 'Điều khiển → robot'],
        ['/scan', 'sensor_msgs/msg/LaserScan', 'LiDAR → điều khiển'],
        ['/robot_behavior/status', 'std_msgs/msg/String (JSON)', 'Điều khiển → webcam'],
    ], [5.3*cm, 5.0*cm, 6.2*cm])
    p('Node nhận diện dùng MediaPipe Tasks Gesture Recognizer, VIDEO mode, '
      'timestamp mili giây tăng dần. Mô hình trả về 21 landmark và nhãn/điểm '
      'tin cậy. Năm tư thế tĩnh dùng nhãn có sẵn; Wave là quy tắc chuyển động '
      'của tâm lòng bàn tay: 3 lượt ngang luân phiên, biên độ mỗi lượt ≥10% '
      'chiều rộng ảnh, trong 1,6 giây. Wave không phải lớp AI tự huấn luyện.')
    p('Điểm tin cậy tối thiểu 0,65. Chọn/xác nhận phải giữ ổn định 0,35 giây; '
      'Open Palm và Closed Fist được ưu tiên không chờ bộ lọc. Hai tay hoặc '
      'mất nhận diện phát NONE; khi đang chạy sẽ dừng. Lựa chọn chưa chạy được giữ 5 giây. Chuyển tư thế phát TRANSITION '
      'và không gia hạn watchdog. Nhãn lặp lại không tạo sự kiện mới.')
    p('4. Ánh xạ và máy trạng thái', 'Heading1')
    table([
        ['Cử chỉ', 'Hành vi'],
        ['Wave', 'Chọn chào trái–phải; chờ xác nhận'],
        ['Pointing Up', 'Chọn 4 chu kỳ tiến–lùi, tổng 8 chặng'],
        ['Victory', 'Chọn một vòng tròn'],
        ['Thumbs Up', 'Xác nhận hành vi đã chọn'],
        ['Open Palm', 'Dừng, xóa lựa chọn'],
        ['Closed Fist', 'Hủy hành vi, về IDLE'],
    ], [4.8*cm, 11.7*cm])
    p('Máy trạng thái: IDLE → SELECTED → RUNNING → IDLE. Chào cũng cần '
      'xác nhận để tuân thủ yêu cầu đề. Khi bắt đầu vẫy, Open Palm dừng robot; '
      'sau khi đủ mẫu vẫy, nhãn Wave được giữ đến lúc đổi tư thế. Khi đã '
      'Thumbs Up xác nhận, xòe tay lại sẽ dừng bình thường.')
    story.append(PageBreak())

    p('5. Nguyên lý điều khiển và an toàn', 'Heading1')
    p('Node điều khiển phát Twist ở 20 Hz. Tiến/lùi: linear.x = ±0,15 m/s, '
      'mỗi chặng 2 giây, lặp 4 chu kỳ (khoảng 16 giây). Vòng tròn: v=0,15 m/s, '
      'R=0,60 m, ω=v/R=0,25 rad/s, T=2π/ω≈25,13 giây. Chào: angular.z=±0,5 '
      'rad/s theo các pha 0,8–1,6–0,8 giây, lặp hai lần.')
    p('Chuyển động dựa trên thời gian và vận tốc, không có phản hồi odometry '
      'để sửa sai vị trí. Bán kính và thời lượng là giá trị danh định. '
      'Thời lượng chuyển động dùng /clock; watchdog dùng thời gian thực.')
    p('Open Palm/Closed Fist gửi vận tốc 0 ngay trong callback. NONE hủy '
      'ngay; không có cử chỉ hợp lệ quá 0,8 giây thì watchdog dừng. Timer '
      'dùng đồng hồ đơn điệu thực, hoạt động cả khi /clock bị dừng. Robot '
      'không tự tiếp tục khi tín hiệu quay lại.')
    p('LiDAR toàn hướng: khoảng cách tối thiểu phải lớn hơn 0,45 m, ít nhất '
      '80% tia sử dụng được và scan mới trong 0,8 giây. Thiếu scan hoặc có '
      'vật gần đều hủy. Đây là cơ chế dừng theo khoảng cách; không phải bộ '
      'lập đường tránh vật cản. Nếu tiến trình điều khiển bị tắt cưỡng bức, '
      'cần timeout của bộ điều khiển vận tốc bên dưới.')
    p('6. Cài đặt và tái lập', 'Heading1')
    p('Ubuntu 22.04, ROS 2 Humble, Ignition Fortress, Python 3.10. Tạo venv '
      '--system-site-packages, cài requirements-gesture.txt và tải mô hình '
      'bằng scripts/download_gesture_model.py. Build package với colcon build '
      '--symlink-install --packages-select tb4_simplesimu.')
    p('Chạy gesture_sim.launch.py để mở sân 10×10 m; chờ xóa dock. Chạy '
      'gesture_control.launch.py start_camera:=false và dùng Python của venv '
      'để chạy gesture_recognition_node.py. README có đầy đủ lệnh, tham số '
      'và cách kiểm tra topic. Không chạy đồng thời teleop/Nav2.')
    p('Giữ một tay hợp lệ trong khung hình suốt hành vi. Demo lần lượt: '
      'chọn chưa xác nhận, tiến–lùi, vòng tròn, chào, Open Palm, Closed Fist, '
      'rút tay và giữ Thumb Up sau khi xong. Không dùng phím để lái robot.')
    story.append(PageBreak())

    p('7. Kiểm chứng và kết quả thực nghiệm', 'Heading1')
    p('Đã có 19 kiểm thử tự động cho máy trạng thái và lọc cử chỉ: xác nhận '
      'trước khi chạy, bốn chu kỳ tiến–lùi, vòng tròn kết thúc, chào, dừng/hủy, '
      'timeout, không kích hoạt lặp và phát hiện Wave. Kết quả chạy trên '
      'workspace: 19/19 đạt; colcon build package thành công.')
    p('Kiểm thử tích hợp ROS dùng topic /bai6_test/* đã đạt 6 tình huống: '
      'chọn, xác nhận, dừng, timeout tín hiệu, timeout scan và vật cản. '
      'MediaPipe 0.10.21 đã nạp mô hình chính thức và xử lý 3 ảnh trống '
      'thành công bằng CPU. Kết quả chi tiết ghi trong validation.md; các '
      'kiểm tra này không chứng minh chất lượng nhận diện webcam thật.')
    p('Gazebo đã chạy đủ 4 chu kỳ tiến–lùi, một vòng tròn và chào. Vòng tròn đo được 6,273 rad, lệch điểm đầu 0,015 m. Tiến–lùi lệch điểm đầu 0,519 m do điều khiển theo thời gian. Đã mở webcam thật trên desktop, nhận được cử chỉ tay qua '
      'MediaPipe và kiểm tra LiDAR thực tế 15 Hz. Kiểm tra trước đây trong '
      'sandbox không thấy webcam; thiết bị có trên máy thật. Chưa có video '
      'nộp bài hoặc thống kê độ chính xác nhận diện; không dùng unit test '
      'thay cho đánh giá chất lượng webcam.')
    table([
        ['Ảnh/thử nghiệm cần bổ sung', 'Trạng thái'],
        ['Ảnh webcam: nhãn, điểm tin cậy, landmark', 'Chưa chụp'],
        ['Gazebo: SELECTED, tiến–lùi và vòng tròn', 'Chưa chụp'],
        ['Open Palm dừng robot, log lý do', 'Chưa chụp'],
        ['10 lần/cử chỉ: đúng, nhầm, không nhận', 'Chưa đo'],
    ], [11.4*cm, 5.1*cm])
    p('8. Đường dẫn nộp bài', 'Heading1')
    p('Video: ' + VIDEO_URL)
    p('GitHub: ' + GITHUB_URL)
    p('Cần điền thông tin sinh viên, ảnh và số liệu thật, upload video công '
      'khai rồi cập nhật các link trong build_report.py và tạo lại PDF trước khi nộp.')
    p('9. Tài liệu tham khảo', 'Heading1')
    for url in [
        'https://ai.google.dev/edge/mediapipe/solutions/vision/gesture_recognizer/python',
        'https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html',
        'https://turtlebot.github.io/turtlebot4-user-manual/software/simulation.html',
    ]:
        story.append(Paragraph(f'<link href="{url}">{escape(url)}</link>', cell))

    def footer(canvas, doc):
        canvas.setFont('VN', 8)
        canvas.drawString(2*cm, 1.2*cm, 'Bài 6 — Giao tiếp phi ngôn ngữ với TurtleBot 4')
        canvas.drawRightString(19*cm, 1.2*cm, f'Trang {doc.page}')

    document = SimpleDocTemplate(str(HERE / 'bao_cao.pdf'),
        pagesize=(21*cm, 29.7*cm), rightMargin=2*cm, leftMargin=2*cm,
        topMargin=1.8*cm, bottomMargin=1.8*cm,
        title='Bài 6 — Điều khiển TurtleBot 4 bằng cử chỉ tay', author=STUDENT)
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print(HERE / 'bao_cao.pdf')


if __name__ == '__main__':
    main()
