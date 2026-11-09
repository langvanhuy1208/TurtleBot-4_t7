#!/usr/bin/env python3
"""Build a two-page Vietnamese report using measured result files."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STUDENT = '[Điền họ tên / MSSV / lớp]'
GITHUB = '[Bổ sung URL repository public]'
VIDEO = 'demo_voice_navigation.mp4 (WAV tổng hợp; cần bổ sung demo micro người thật)'


def main():
    fonts = Path('/usr/share/fonts/truetype/dejavu')
    pdfmetrics.registerFont(TTFont('VN', str(fonts/'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('VN-Bold', str(fonts/'DejaVuSans-Bold.ttf')))
    styles = getSampleStyleSheet()
    for key in ('Normal', 'Title', 'Heading2'):
        styles[key].fontName = 'VN' if key == 'Normal' else 'VN-Bold'
    styles['Normal'].fontSize, styles['Normal'].leading = 9, 13
    styles['Normal'].spaceAfter = 7
    styles['Title'].fontSize, styles['Title'].leading = 15, 21
    styles['Heading2'].fontSize, styles['Heading2'].leading = 11, 16
    cell = ParagraphStyle('cell', parent=styles['Normal'], fontSize=8, leading=11)
    story = []

    def p(text, style='Normal'):
        story.append(Paragraph(escape(text), styles[style]))

    def table(rows, widths):
        t = Table([[Paragraph(escape(str(v)), cell) for v in row] for row in rows], colWidths=widths)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dbeafe')),
            ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#94a3b8')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),
            ('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        story.extend([t, Spacer(1,8)])

    p('BÀI THỰC HÀNH 7', 'Title')
    p('Phân vùng bản đồ và điều hướng TurtleBot 4 bằng giọng nói', 'Heading2')
    p('Sinh viên: '+STUDENT)
    p('1. Bản đồ và phương pháp phân vùng', 'Heading2')
    p('Môi trường: Ubuntu 22.04, ROS 2 Humble, TurtleBot 4 / Ignition Gazebo và Nav2. '
      'Giữ nguyên bản đồ SLAM gốc tại maps/phase2 và xuất phân vùng riêng. Demo tái lập dùng '
      'bản đồ tham chiếu raster hóa collision box từ maze_fast.sdf, resolution 0,05 m, '
      'map trùng hệ world; đây không phải bản đồ SLAM mới. Pixel 205 giữ là chưa biết '
      'với free_thresh=0,196, không cho nhãn lan vào ô này.')
    p('Chọn thủ công ba hạt giống A (phòng học), B (phòng thí nghiệm), C (hành lang). '
      'BFS đa nguồn gán nhãn theo khoảng cách đường đi trên ô trống 4 lân cận, không xuyên tường. '
      'Tên là nhãn chức năng do người dùng gán, không phải kết quả tự nhận diện phòng. '
      'Điểm đích chọn gần hạt giống nhất và cách vật cản ít nhất 0,35 m bằng OpenCV distance transform.')
    image = Image(str(ROOT/'maps/bai7/segmented_map.png'), width=7.2*cm, height=8.25*cm, kind='proportional')
    story.append(image)
    p('Chuyển pixel: x=(u+0,5)r; y=(H−v−0,5)r; xoay theo yaw rồi cộng origin. '
      'regions.yaml lưu ID, tên, aliases, nhãn ảnh, tọa độ x/y/yaw, clearance và hash map. '
      'Nạp catalog sẽ kiểm tra đích còn trống, đúng vùng và map chưa thay đổi.')
    story.append(PageBreak())
    p('2. Nhận dạng và điều hướng', 'Heading2')
    p('Luồng: micro/WAV → faster-whisper small (tiếng Việt, CPU int8, VAD) → /voice_command '
      '→ chuẩn hóa Unicode, phân tích câu → NavigateToPose. Thu micro theo nút Enter và lưu WAV; '
      'bỏ âm lượng quá thấp hoặc transcript rỗng. Mô hình chạy cục bộ, không dùng API key. '
      'Bộ phân tích khớp alias đầy đủ, không khớp tên bằng substring; có alias “hành lan” cho C '
      'sau khi đo lỗi phiên âm trên mẫu tổng hợp. Không dùng fuzzy matching không giới hạn.')
    p('“Đi từ A đến B” luôn gửi A trước và chỉ gửi B khi A thành công. Hỗ trợ A qua C rồi đến B. '
      'Vùng không tồn tại làm toàn bộ lệnh bị từ chối. Khi đang đi, từ chối lệnh mới; '
      '“Dừng lại” hủy goal và xóa hàng đợi. Timeout/hủy chờ kết quả cuối trước khi nhận hành trình mới. '
      'Nav2 đảm nhận lập đường, điều khiển và tránh vật cản; RViz có marker nhãn, thứ tự waypoint và /plan.')
    p('3. Kết quả thực nghiệm và giới hạn', 'Heading2')
    asr_path = HERE/'asr_test_results.json'
    asr = json.loads(asr_path.read_text()) if asr_path.exists() else {}
    results = asr.get('results', [])
    if results:
        p('ASR: '+asr['model']+'; nguồn: '+asr['source']+'. '
          f'Khớp lộ trình {sum(bool(r["passed"]) for r in results)}/{len(results)} mẫu. '
          'Không dùng kết quả này làm độ chính xác giọng người trong môi trường nhiễu.')
        table([['Câu mẫu', 'Phiên âm / kết quả']] + [
            [r['text'], r['transcript']+' → '+('đạt' if r['passed'] else 'chưa đạt')]
            for r in results], [7*cm, 10*cm])
    nav_path = HERE/'gazebo_test_results.json'
    nav = json.loads(nav_path.read_text()) if nav_path.exists() else {}
    nav_results = nav.get('results', [])
    p('Kiểm thử phần mềm: 38 trường hợp bản đồ/câu lệnh/đầu vào âm thanh và 8 kịch bản DDS/action với Nav2 giả '
      '(chuỗi điểm, nguồn sai, hủy khi đang chờ chấp nhận, timeout và thất bại chặng đầu). '
      'Nav2 giả chỉ xác minh giao tiếp; số liệu chuyển động được ghi riêng bằng Gazebo/AMCL.')
    if nav_results:
        passed = sum(bool(r['passed']) for r in nav_results)
        p(f'Gazebo: {passed}/{len(nav_results)} kịch bản đạt; đầu vào: '+nav.get('input', '')+'.')
        table([['Lệnh', 'Đã tới', 'Sai số cuối (m)', 'Kết quả']] + [
            [r['text'], ' → '.join(r.get('arrived', [])) or '—',
             r.get('final_error_m') if r.get('final_error_m') is not None else '—',
             'Đạt' if r['passed'] else r['state']] for r in nav_results], [7*cm, 3*cm, 3*cm, 4*cm])
    else:
        p('Chưa có kết quả hoàn tất toàn bộ hành trình Gazebo; xem log/JSON đi kèm trước khi kết luận đạt.')
    p('Đã xác minh thu micro thật 16 kHz mono qua PulseAudio. Cần quay bổ sung người thật nói ít nhất '
      'ba câu lệnh và thử tiếng ồn; chưa đo độ chính xác giọng người có nhãn. Phân vùng phụ thuộc hạt giống và bản đồ; điểm tĩnh hợp lệ vẫn có '
      'thể bị chặn bởi vật cản mới, khi đó Nav2 có quyền báo không tìm được đường.')
    p('Mã nguồn: '+GITHUB+'. Video: '+VIDEO)
    p('Tham khảo: api.nav2.org/actions/humble/navigatetopose.html; github.com/SYSTRAN/faster-whisper.')
    def page(canvas, doc):
        canvas.setFont('VN',8)
        canvas.drawRightString(19*cm,1*cm,f'{doc.page}/2')
    SimpleDocTemplate(str(HERE/'bao_cao.pdf'),pagesize=(21*cm,29.7*cm),
        leftMargin=2*cm,rightMargin=2*cm,topMargin=1.4*cm,bottomMargin=1.4*cm,
        title='Bài 7 — Phân vùng bản đồ và điều hướng giọng nói',author=STUDENT).build(
        story,onFirstPage=page,onLaterPages=page)
    print(HERE/'bao_cao.pdf')


if __name__ == '__main__':
    main()
