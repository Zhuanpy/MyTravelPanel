from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, send_file
from App_new.exts import csrf
from App_new.utils.VisaForm import MyPdfFile
from App_new.utils.WordToPdf import WordToPDFConverter
import subprocess
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib import colors
from io import BytesIO
import datetime

# 创建蓝图
files_process = Blueprint('files_process', __name__)


def is_ajax():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


@files_process.route('/file_processing')
def file_processing():
    return render_template('shared/utils/pdf.html')


@files_process.route('/pdf_to_pdf', methods=['POST'])
def merge_pdf_to_pdf():
    try:
        path = request.form.get('pdfFolderPath')
        if not path:
            if is_ajax():
                return jsonify({'success': False, 'message': '请提供PDF文件夹路径'}), 400
            flash('请提供PDF文件夹路径')
            return redirect(url_for('files_process.file_processing'))
            
        if not os.path.exists(path) or not os.path.isdir(path):
            if is_ajax():
                return jsonify({'success': False, 'message': '提供的文件夹路径无效或不存在'}), 400
            flash('提供的文件夹路径无效或不存在')
            return redirect(url_for('files_process.file_processing'))
            
        f = MyPdfFile(path)
        f.merge_pdf2pdf()
        
        if is_ajax():
            return jsonify({'success': True, 'message': 'PDF合并成功'})
        flash('PDF合并成功')
        return redirect(url_for('files_process.file_processing'))
    except Exception as e:
        if is_ajax():
            return jsonify({'success': False, 'message': f'处理失败：{str(e)}'}), 500
        flash(f'处理失败：{str(e)}')
        return redirect(url_for('files_process.file_processing'))


@files_process.route('/images_to_pdf', methods=['POST'])
def merge_images_to_pdf():
    try:
        path = request.form.get('imageFolderPath')
        if not path:
            if is_ajax():
                return jsonify({'success': False, 'message': '请提供图片文件夹路径'}), 400
            flash('请提供图片文件夹路径')
            return redirect(url_for('files_process.file_processing'))
            
        if not os.path.exists(path) or not os.path.isdir(path):
            if is_ajax():
                return jsonify({'success': False, 'message': '提供的文件夹路径无效或不存在'}), 400
            flash('提供的文件夹路径无效或不存在')
            return redirect(url_for('files_process.file_processing'))
            
        f = MyPdfFile(path)
        f.merge_images2pdf()
        
        if is_ajax():
            return jsonify({'success': True, 'message': '图片合并为PDF成功'})
        flash('图片合并为PDF成功')
        return redirect(url_for('files_process.file_processing'))
    except Exception as e:
        if is_ajax():
            return jsonify({'success': False, 'message': f'处理失败：{str(e)}'}), 500
        flash(f'处理失败：{str(e)}')
        return redirect(url_for('files_process.file_processing'))


@files_process.route('/word_to_pdf', methods=['POST'])
def word_to_pdf():
    folder_path = request.form.get('worldFolderPath')
    # 检查是否接收到路径
    if not folder_path:
        if is_ajax():
            return jsonify({'success': False, 'message': '请提供Word文件夹路径'}), 400
        flash('请提供Word文件夹路径')
        return redirect(url_for('files_process.file_processing'))

    # 检查路径是否有效
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        if is_ajax():
            return jsonify({'success': False, 'message': '提供的文件夹路径无效或不存在'}), 400
        flash('提供的文件夹路径无效或不存在')
        return redirect(url_for('files_process.file_processing'))

    try:
        # 初始化 WordToPDFConverter
        converter = WordToPDFConverter(folder_path)

        # 启动文件处理
        converter.process_files()

        # 返回成功信息
        if is_ajax():
            return jsonify({'success': True, 'message': 'Word转PDF成功'})
        flash('Word转PDF成功')
        return redirect(url_for('files_process.file_processing'))

    except FileNotFoundError as fnf_error:
        if is_ajax():
            return jsonify({'success': False, 'message': f'浏览器驱动未找到或路径错误: {fnf_error}'}), 500
        flash(f'浏览器驱动未找到或路径错误: {fnf_error}')
        return redirect(url_for('files_process.file_processing'))

    except RuntimeError as runtime_error:
        if is_ajax():
            return jsonify({'success': False, 'message': f'文件处理时发生错误: {runtime_error}'}), 500
        flash(f'文件处理时发生错误: {runtime_error}')
        return redirect(url_for('files_process.file_processing'))

    except Exception as e:
        if is_ajax():
            return jsonify({'success': False, 'message': f'未知错误: {e}'}), 500
        flash(f'未知错误: {e}')
        return redirect(url_for('files_process.file_processing'))

@files_process.route('/open_FuXin_pdf')
def open_FuXin_pdf():
    try:
        software_path = r"E:\SOFT\福昕PDF套件高级编辑器\福昕PDF套件高级编辑器 5.0.4.0920 单文件破解版.exe"
        subprocess.run([software_path], shell=True)
        if is_ajax():
            return jsonify({'success': True, 'message': '福昕PDF编辑器已启动'})
        return redirect(url_for("index.index"))
    except Exception as e:
        if is_ajax():
            return jsonify({'success': False, 'message': f'启动失败：{str(e)}'}), 500
        flash(f'启动失败：{str(e)}')
        return redirect(url_for("index.index"))


@files_process.route('/open_Photoshop')
def open_Photoshop():
    try:
        software_path = r"C:\Program Files\Adobe\Adobe Photoshop CS6 (64 Bit)\Photoshop.exe"
        subprocess.run([software_path], shell=True)
        if is_ajax():
            return jsonify({'success': True, 'message': 'Photoshop已启动'})
        return redirect(url_for("index.index"))
    except Exception as e:
        if is_ajax():
            return jsonify({'success': False, 'message': f'启动失败：{str(e)}'}), 500
        flash(f'启动失败：{str(e)}')
        return redirect(url_for("index.index"))

@files_process.route('/open_Athina')
def open_Athina():
    try:
        software_path = r"C:\Program Files (x86)\Athena Bookings\Athena Bookings ver 2.0.RDP"
        subprocess.run([software_path], shell=True)
        if is_ajax():
            return jsonify({'success': True, 'message': 'Athina已启动'})
        return redirect(url_for("index.index"))
    except Exception as e:
        if is_ajax():
            return jsonify({'success': False, 'message': f'启动失败：{str(e)}'}), 500
        flash(f'启动失败：{str(e)}')
        return redirect(url_for("index.index"))


@files_process.route('/letter_generator')
def letter_generator():
    """信件生成器页面"""
    from App_new.business.tour.models.Packagemodels import CompanyInfo
    company = CompanyInfo.query.first()
    return render_template('shared/own_company/letter_generator.html',
                           today_date=datetime.date.today().isoformat(),
                           company=company)


@files_process.route('/test_letter')
def test_letter():
    """信件生成器测试页面"""
    return render_template('shared/company_manager/test_letter.html')


@files_process.route('/letter_demo')
def letter_demo():
    """信件生成器演示页面"""
    return render_template('shared/company_manager/letter_demo.html')


@files_process.route('/generate_letter_pdf', methods=['POST'])
@csrf.exempt
def generate_letter_pdf():
    """生成信件PDF"""
    try:
        # 获取表单数据
        recipient_name = request.form.get('recipientName', '')
        recipient_title = request.form.get('recipientTitle', '')
        recipient_company = request.form.get('recipientCompany', '')
        recipient_address = request.form.get('recipientAddress', '')
        letter_date = request.form.get('letterDate', '')
        letter_subject = request.form.get('letterSubject', '')
        letter_body = request.form.get('letterBody', '')
        sender_name = request.form.get('senderName', '')
        sender_title = request.form.get('senderTitle', '')
        
        # 格式化日期
        if letter_date:
            try:
                date_obj = datetime.datetime.strptime(letter_date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%B %d, %Y')
            except:
                formatted_date = letter_date
        else:
            formatted_date = datetime.datetime.now().strftime('%B %d, %Y')
        
        # 创建PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # 注册中文字体
        from flask import current_app
        font_path = os.path.join(current_app.static_folder, 'fonts', 'msyh.ttc')
        font_bold_path = os.path.join(current_app.static_folder, 'fonts', 'msyhbd.ttc')
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('MSYH', font_path, subfontIndex=0))
            if os.path.exists(font_bold_path):
                pdfmetrics.registerFont(TTFont('MSYH-Bold', font_bold_path, subfontIndex=0))
                pdfmetrics.registerFontFamily('MSYH', normal='MSYH', bold='MSYH-Bold')
            cn_font = 'MSYH'
        else:
            cn_font = 'Helvetica'

        # 获取样式
        styles = getSampleStyleSheet()

        # 创建自定义样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=cn_font,
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER
        )

        company_style = ParagraphStyle(
            'CompanyStyle',
            parent=styles['Normal'],
            fontName=cn_font,
            fontSize=12,
            spaceAfter=6
        )

        normal_style = ParagraphStyle(
            'NormalStyle',
            parent=styles['Normal'],
            fontName=cn_font,
            fontSize=11,
            spaceAfter=2,
            leading=15,
            alignment=TA_LEFT
        )
        
        from reportlab.platypus import Table, TableStyle, HRFlowable
        from App_new.business.tour.models.Packagemodels import CompanyInfo

        # 从数据库获取公司信息
        company = CompanyInfo.query.first()
        co_name = company.company_name if company else 'JOYFUL ESCAPES PTE LTD'
        co_short = (company.company_short_name or 'JOYFUL ESCAPES').upper() if company else 'JOYFUL ESCAPES'
        co_cn = company.company_name_cn or '' if company else ''
        co_address = company.address or '' if company else ''
        co_ta = company.ta_license or '' if company else ''
        co_phone = company.phone or '' if company else ''
        co_email = company.email or '' if company else ''

        # Logo 路径
        if company and company.logo_path:
            logo_path = os.path.join(current_app.static_folder, company.logo_path)
        else:
            logo_path = os.path.join(current_app.static_folder, 'JE', 'LOGO.jpg')

        # 右侧联系信息（中文名在最顶部）
        contact_lines = []
        if co_cn:
            contact_lines.append(f"<b><font size=11>{co_cn}</font></b>")
        contact_lines.append(f"<b>{co_name}</b>")
        if co_address:
            addr = co_address.replace('\n', '<br/>').replace('SINGAPORE', '<br/>SINGAPORE')
            contact_lines.append(addr)
        if co_ta:
            contact_lines.append(f"TA License No.: {co_ta}")
        if co_email:
            contact_lines.append(f"Email: {co_email}")

        contact_style = ParagraphStyle('ContactStyle', parent=styles['Normal'], fontName=cn_font, fontSize=9, alignment=TA_RIGHT, leading=13)
        header_right = Paragraph('<br/>'.join(contact_lines), contact_style)

        # 左侧：Logo + 英文简写 + 中文名（上下排列）
        logo_center_style = ParagraphStyle('LogoCenter', parent=styles['Normal'], fontName=cn_font, fontSize=12, alignment=TA_CENTER, leading=14)
        left_rows = []
        if os.path.exists(logo_path):
            left_rows.append([Image(logo_path, width=42, height=42)])
        left_rows.append([Paragraph(f"<b>{co_short}</b>", logo_center_style)])

        left_content = Table(left_rows, colWidths=[120])
        left_content.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))

        # 用表格实现左右排列
        header_table = Table(
            [[left_content, header_right]],
            colWidths=[140, 340]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        story.append(header_table)
        story.append(Spacer(1, 12))

        # 日期
        story.append(Paragraph(formatted_date, normal_style))
        story.append(Spacer(1, 6))

        # 收件人信息
        if recipient_name:
            story.append(Paragraph(f"<b>{recipient_name}</b>", normal_style))
        if recipient_title:
            story.append(Paragraph(recipient_title, normal_style))
        if recipient_company:
            story.append(Paragraph(recipient_company, normal_style))
        if recipient_address:
            story.append(Paragraph(recipient_address, normal_style))

        story.append(Spacer(1, 6))

        # 主题
        if letter_subject:
            story.append(Paragraph(f"<b>Subject: {letter_subject}</b>", normal_style))
            story.append(Spacer(1, 6))

        # 信件内容（保持原始换行）
        body_style = ParagraphStyle('BodyStyle', parent=normal_style, spaceAfter=2, leading=16)
        body_gap_style = ParagraphStyle('BodyGap', parent=normal_style, spaceAfter=8, leading=16)
        if letter_body:
            for line in letter_body.split('\n'):
                if line.strip():
                    story.append(Paragraph(line.strip(), body_style))
                else:
                    story.append(Spacer(1, 6))

        story.append(Spacer(1, 10))

        # 签名（电子章覆盖在公司名右上角）
        sender_dept = request.form.get('senderDept', '')
        sender_phone = request.form.get('senderPhone', '')

        story.append(Paragraph("Yours faithfully,", normal_style))
        story.append(Spacer(1, 16))

        # 构建签名文本
        sig_lines = []
        if sender_name:
            sig_lines.append(f"<b>{sender_name}</b>")
        if sender_dept:
            sig_lines.append(sender_dept)
        if sender_title:
            sig_lines.append(sender_title)
        if sender_phone:
            sig_lines.append(f"Contact: {sender_phone}")
        sig_lines.append(co_name)

        sig_style = ParagraphStyle('SigStyle', parent=normal_style, spaceAfter=2)
        sig_paragraph = Paragraph('<br/>'.join(sig_lines), sig_style)

        # 加载电子章
        stamp_cell = ''
        try:
            if company and company.stamp_path:
                stamp_path = os.path.join(current_app.static_folder, company.stamp_path)
            else:
                stamp_path = os.path.join(current_app.static_folder, 'JE', 'company digital stamp.png')
            if os.path.exists(stamp_path):
                stamp_cell = Image(stamp_path, width=80, height=80)
        except Exception as e:
            print(f"电子章加载失败: {e}")

        # 用表格实现签名+电子章，左对齐
        if stamp_cell:
            # 计算可用宽度（A4 宽 595pt - 左右边距各72pt = 451pt）
            available_width = 451
            sig_table = Table(
                [[sig_paragraph, stamp_cell]],
                colWidths=[available_width - 90, 90],
                hAlign='LEFT'
            )
            sig_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (0, 0), 'TOP'),
                ('VALIGN', (1, 0), (1, 0), 'BOTTOM'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(sig_table)
        else:
            story.append(sig_paragraph)
        
        # 生成PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'JOYFUL_ESCAPES_Letter_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"PDF生成错误: {e}")
        return jsonify({'error': str(e)}), 500


@files_process.route('/test_simple_pdf')
def test_simple_pdf():
    """测试简单的PDF生成功能"""
    try:
        # 创建PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # 获取样式
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']
        
        # 添加简单内容
        story.append(Paragraph("JOYFUL ESCAPE", normal_style))
        story.append(Paragraph("Travel & Tourism Services", normal_style))
        story.append(Paragraph("Test PDF Generation", normal_style))
        story.append(Paragraph("This is a test PDF to verify the generation works correctly.", normal_style))
        
        # 生成PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name='test_letter.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"测试PDF生成错误: {e}")
        return jsonify({'error': str(e)}), 500
