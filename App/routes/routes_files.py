from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from ..code.Visa.utils_visa import MyPdfFile
from ..code.utils.WordToPdf import WordToPDFConverter
import subprocess
import os

# 创建蓝图
files_process = Blueprint('files_process', __name__)


@files_process.route('/file_processing')
def file_processing():
    return render_template('files/pdf.html')


@files_process.route('/pdf_to_pdf', methods=['POST'])
def merge_pdf_to_pdf():
    path = request.form.get('pdfFolderPath')
    f = MyPdfFile(path)
    f.merge_pdf2pdf()
    return render_template('files/result.html', folder_path=path)


@files_process.route('/images_to_pdf', methods=['POST'])
def merge_images_to_pdf():
    path = request.form.get('imageFolderPath')
    f = MyPdfFile(path)
    f.merge_images2pdf()
    return render_template('files/result.html', folder_path=path)


@files_process.route('/word_to_pdf', methods=['POST'])
def word_to_pdf():
    folder_path = request.form.get('worldFolderPath')
    # 检查是否接收到路径
    if not folder_path:
        return jsonify({'error': 'worldFolderPath 参数未提供！'}), 400

    # 检查路径是否有效
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return jsonify({'error': '提供的文件夹路径无效或不存在！'}), 400

    try:
        # 初始化 WordToPDFConverter
        converter = WordToPDFConverter(folder_path)

        # 启动文件处理
        converter.process_files()

        # 返回成功信息
        return jsonify({'success': True, 'message': '文件处理完成！'})

    except FileNotFoundError as fnf_error:
        # 针对驱动路径问题的错误处理
        return jsonify({'error': f'浏览器驱动未找到或路径错误: {fnf_error}'}), 500

    except RuntimeError as runtime_error:
        # 针对运行时错误的处理
        return jsonify({'error': f'文件处理时发生错误: {runtime_error}'}), 500

    except Exception as e:
        # 捕获所有其他异常
        return jsonify({'error': f'未知错误: {e}'}), 500

@files_process.route('/open_FuXin_pdf')
def open_FuXin_pdf():
    # 设置软件路径（假设你已经知道软件的完整路径）
    software_path = r"E:\SOFT\福昕PDF套件高级编辑器\福昕PDF套件高级编辑器 5.0.4.0920 单文件破解版.exe"
    subprocess.run([software_path], shell=True)  # 启动软件
    return redirect(url_for("index.index"))


@files_process.route('/open_Photoshop')
def open_Photoshop():
    # 设置软件路径（假设你已经知道软件的完整路径）
    software_path = r"C:\Program Files\Adobe\Adobe Photoshop CS6 (64 Bit)\Photoshop.exe"
    subprocess.run([software_path], shell=True)  # 启动软件
    return redirect(url_for("index.index"))

@files_process.route('/open_Athina')
def open_Athina():
    # 设置软件路径（假设你已经知道软件的完整路径）
    software_path = r"C:\Program Files (x86)\Athena Bookings\Athena Bookings ver 2.0.RDP"
    subprocess.run([software_path], shell=True)  # 启动软件
    return redirect(url_for("index.index"))
