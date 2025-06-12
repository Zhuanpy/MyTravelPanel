from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from ..code.VisaForm import MyPdfFile
from ..code.utils.WordToPdf import WordToPDFConverter
import subprocess
import os
import traceback
from flask import current_app

# 创建蓝图
utils_process = Blueprint('utils_process', __name__)


def is_ajax():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


@utils_process.route('/file_processing')
def file_processing():
    return render_template('utils/pdf.html')


@utils_process.route('/pdf_to_pdf', methods=['POST'])
def merge_pdf_to_pdf():
    try:
        path = request.form.get('pdfFolderPath')
        if not path:
            if is_ajax():
                return jsonify({'success': False, 'message': '请提供PDF文件夹路径'}), 400
            flash('请提供PDF文件夹路径')
            return redirect(url_for('utils_process.file_processing'))
            
        if not os.path.exists(path) or not os.path.isdir(path):
            if is_ajax():
                return jsonify({'success': False, 'message': '提供的文件夹路径无效或不存在'}), 400
            flash('提供的文件夹路径无效或不存在')
            return redirect(url_for('utils_process.file_processing'))
            
        f = MyPdfFile(path)
        f.merge_pdf2pdf()
        
        if is_ajax():
            return jsonify({'success': True, 'message': 'PDF合并成功'})
        flash('PDF合并成功')
        return redirect(url_for('utils_process.file_processing'))
    except Exception as e:
        if is_ajax():
            return jsonify({'success': False, 'message': f'处理失败：{str(e)}'}), 500
        flash(f'处理失败：{str(e)}')
        return redirect(url_for('utils_process.file_processing'))


@utils_process.route('/images_to_pdf', methods=['POST'])
def merge_images_to_pdf():
    try:
        path = request.form.get('imageFolderPath')
        if not path:
            if is_ajax():
                return jsonify({'success': False, 'message': '请提供图片文件夹路径'}), 400
            flash('请提供图片文件夹路径')
            return redirect(url_for('utils_process.file_processing'))
            
        if not os.path.exists(path) or not os.path.isdir(path):
            if is_ajax():
                return jsonify({'success': False, 'message': '提供的文件夹路径无效或不存在'}), 400
            flash('提供的文件夹路径无效或不存在')
            return redirect(url_for('utils_process.file_processing'))
            
        f = MyPdfFile(path)
        f.merge_images2pdf()
        
        if is_ajax():
            return jsonify({'success': True, 'message': '图片合并为PDF成功'})
        flash('图片合并为PDF成功')
        return redirect(url_for('utils_process.file_processing'))
    except Exception as e:
        if is_ajax():
            return jsonify({'success': False, 'message': f'处理失败：{str(e)}'}), 500
        flash(f'处理失败：{str(e)}')
        return redirect(url_for('utils_process.file_processing'))


@utils_process.route('/word_to_pdf', methods=['POST'])
def word_to_pdf():
    try:
        # 获取并验证表单数据
        folder_path = request.form.get('wordFolderPath')  # 修正字段名
        if not folder_path:
            error_msg = '请提供Word文件夹路径'
            if is_ajax():
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg)
            return redirect(url_for('utils_process.file_processing'))

        # 规范化路径
        folder_path = os.path.normpath(folder_path)
        
        # 检查路径是否有效
        if not os.path.exists(folder_path):
            error_msg = f'提供的文件夹路径不存在: {folder_path}'
            if is_ajax():
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg)
            return redirect(url_for('utils_process.file_processing'))
            
        if not os.path.isdir(folder_path):
            error_msg = f'提供的路径不是文件夹: {folder_path}'
            if is_ajax():
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg)
            return redirect(url_for('utils_process.file_processing'))

        # 检查文件夹是否为空
        if not os.listdir(folder_path):
            error_msg = f'文件夹为空: {folder_path}'
            if is_ajax():
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg)
            return redirect(url_for('utils_process.file_processing'))

        # 检查文件夹中是否有Word文件
        word_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.doc', '.docx'))]
        if not word_files:
            error_msg = f'文件夹中没有Word文件: {folder_path}'
            if is_ajax():
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg)
            return redirect(url_for('utils_process.file_processing'))

        # 初始化转换器并处理文件
        converter = WordToPDFConverter(folder_path)
        converter.process_files()

        # 返回成功信息
        success_msg = f'成功转换 {len(word_files)} 个Word文件为PDF'
        if is_ajax():
            return jsonify({
                'success': True, 
                'message': success_msg,
                'files_processed': len(word_files)
            })
        flash(success_msg)
        return redirect(url_for('utils_process.file_processing'))

    except FileNotFoundError as fnf_error:
        error_msg = f'浏览器驱动未找到或路径错误: {str(fnf_error)}'
        current_app.logger.error(error_msg)
        if is_ajax():
            return jsonify({'success': False, 'message': error_msg}), 500
        flash(error_msg)
        return redirect(url_for('utils_process.file_processing'))

    except RuntimeError as runtime_error:
        error_msg = f'文件处理时发生错误: {str(runtime_error)}'
        current_app.logger.error(error_msg)
        if is_ajax():
            return jsonify({'success': False, 'message': error_msg}), 500
        flash(error_msg)
        return redirect(url_for('utils_process.file_processing'))

    except Exception as e:
        error_msg = f'未知错误: {str(e)}'
        current_app.logger.error(f'Word转PDF错误: {error_msg}\n{traceback.format_exc()}')
        if is_ajax():
            return jsonify({'success': False, 'message': error_msg}), 500
        flash(error_msg)
        return redirect(url_for('utils_process.file_processing'))

@utils_process.route('/open_FuXin_pdf')
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

@utils_process.route('/open_Photoshop')
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

@utils_process.route('/open_Athina')
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

@utils_process.route('/files_home')
def files_home():
    """文件处理首页路由"""
    return render_template('utils/文件处理首页.html')
