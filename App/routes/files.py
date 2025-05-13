from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from ..code.VisaForm import MyPdfFile
from ..code.utils.WordToPdf import WordToPDFConverter
import subprocess
import os

# 创建蓝图
files_process = Blueprint('files_process', __name__)


def is_ajax():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


@files_process.route('/file_processing')
def file_processing():
    return render_template('files/pdf.html')


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

@files_process.route('/files_home')
def files_home():
    """文件处理首页路由"""
    return render_template('files/文件处理首页.html')
