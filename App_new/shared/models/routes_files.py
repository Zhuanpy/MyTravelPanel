from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, send_file
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
    return render_template('shared/own_company/letter_generator.html')


@files_process.route('/test_letter')
def test_letter():
    """信件生成器测试页面"""
    return render_template('shared/company_manager/test_letter.html')


@files_process.route('/letter_demo')
def letter_demo():
    """信件生成器演示页面"""
    return render_template('shared/company_manager/letter_demo.html')


@files_process.route('/generate_letter_pdf', methods=['POST'])
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
        
        # 获取样式
        styles = getSampleStyleSheet()
        
        # 创建自定义样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        company_style = ParagraphStyle(
            'CompanyStyle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=6
        )
        
        normal_style = ParagraphStyle(
            'NormalStyle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            alignment=TA_LEFT
        )
        
        # 添加公司抬头
        story.append(Paragraph("JOYFUL ESCAPE", title_style))
        story.append(Paragraph("Travel & Tourism Services", title_style))
        story.append(Spacer(1, 20))
        
        # 添加公司信息
        company_info = [
            "JOYFUL ESCAPES PTE LTD",
            "Travel & Tourism Services",
            "TA License No.: TA03652",
            "TEL: 9106 8716 / 9627 5316",
            "Email: joyfulescape@hotmail.com"
        ]
        
        for info in company_info:
            story.append(Paragraph(info, company_style))
        
        story.append(Spacer(1, 30))
        
        # 添加收件人信息
        if recipient_name:
            story.append(Paragraph(f"<b>{recipient_name}</b>", normal_style))
        if recipient_title:
            story.append(Paragraph(recipient_title, normal_style))
        if recipient_company:
            story.append(Paragraph(recipient_company, normal_style))
        if recipient_address:
            story.append(Paragraph(recipient_address, normal_style))
        
        story.append(Spacer(1, 20))
        
        # 添加日期
        story.append(Paragraph(formatted_date, normal_style))
        story.append(Spacer(1, 20))
        
        # 添加主题
        if letter_subject:
            story.append(Paragraph(f"<b>Subject: {letter_subject}</b>", normal_style))
            story.append(Spacer(1, 20))
        
        # 添加信件内容
        if letter_body:
            # 将内容按段落分割
            paragraphs = letter_body.split('\n')
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), normal_style))
                    story.append(Spacer(1, 12))
        
        story.append(Spacer(1, 30))
        
        # 添加发件人信息和电子章
        if sender_name:
            story.append(Paragraph(f"<b>{sender_name}</b>", normal_style))
        if sender_title:
            story.append(Paragraph(sender_title, normal_style))
        story.append(Paragraph("JOYFUL ESCAPES PTE LTD", normal_style))
        
        # 添加电子章（使用绝对路径）
        try:
            # 使用绝对路径
            stamp_path = os.path.join(os.getcwd(), 'App_new', 'static', 'JE', 'company digital stamp.png')
            if os.path.exists(stamp_path):
                stamp_image = Image(stamp_path, width=60, height=60)
                story.append(Spacer(1, 10))
                story.append(stamp_image)
        except Exception as e:
            # 如果电子章加载失败，继续生成PDF，不中断流程
            print(f"电子章加载失败: {e}")
            pass
        
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
