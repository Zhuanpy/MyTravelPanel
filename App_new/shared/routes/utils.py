from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, send_file
from flask_login import login_required, current_user
from App_new.utils.VisaForm import MyPdfFile
from App_new.utils.WordToPdf import WordToPDFConverter
from App_new.utils.decorators import staff_only
import subprocess
import os
import tempfile
import traceback
from io import BytesIO
from flask import current_app
from App_new.exts import csrf

# 创建蓝图
utils_process = Blueprint('utils_process', __name__)


def is_ajax():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


@utils_process.route('/file_processing')
@login_required
@staff_only
def file_processing():
    return render_template('shared/utils/pdf.html')


@csrf.exempt
@utils_process.route('/pdf_to_pdf', methods=['POST'])
@login_required
@staff_only
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
            
        # 检查文件夹中是否有PDF文件
        pdf_files = [f for f in os.listdir(path) if f.lower().endswith('.pdf')]
        if not pdf_files:
            if is_ajax():
                return jsonify({'success': False, 'message': '文件夹中没有找到PDF文件'}), 400
            flash('文件夹中没有找到PDF文件')
            return redirect(url_for('utils_process.file_processing'))
        
        current_app.logger.info(f'开始合并PDF文件，路径: {path}, 文件数量: {len(pdf_files)}')
        
        f = MyPdfFile(path)
        f.merge_pdf2pdf()
        
        current_app.logger.info('PDF合并成功完成')
        
        if is_ajax():
            return jsonify({'success': True, 'message': f'PDF合并成功，处理了 {len(pdf_files)} 个文件'})
        flash(f'PDF合并成功，处理了 {len(pdf_files)} 个文件')
        return redirect(url_for('utils_process.file_processing'))
    except Exception as e:
        error_msg = f'处理失败：{str(e)}'
        current_app.logger.error(f'PDF合并失败: {error_msg}')
        current_app.logger.error(f'错误详情: {traceback.format_exc()}')
        
        if is_ajax():
            return jsonify({'success': False, 'message': error_msg}), 500
        flash(error_msg)
        return redirect(url_for('utils_process.file_processing'))


@csrf.exempt
@utils_process.route('/images_to_pdf', methods=['POST'])
@login_required
@staff_only
def merge_images_to_pdf():
    try:
        path = request.form.get('imageFolderPath')
        if not path:
            if is_ajax():
                return jsonify({'success': False, 'message': '请提供图片路径'}), 400
            flash('请提供图片路径')
            return redirect(url_for('utils_process.file_processing'))
        
        # 规范化路径
        path = os.path.normpath(path)
        
        # 检查路径是否存在
        if not os.path.exists(path):
            if is_ajax():
                return jsonify({'success': False, 'message': '提供的路径不存在'}), 400
            flash('提供的路径不存在')
            return redirect(url_for('utils_process.file_processing'))
        
        # 判断是文件夹还是文件
        if os.path.isfile(path):
            # 如果是单个文件，检查是否为图片格式
            image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            file_ext = os.path.splitext(path)[1].lower()
            
            if file_ext not in image_extensions:
                error_msg = '指定的文件不是支持的图片格式（支持：jpg, jpeg, png, webp）'
                if is_ajax():
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg)
                return redirect(url_for('utils_process.file_processing'))
            
            # 获取文件所在的文件夹和文件名
            folder_path = os.path.dirname(path)
            file_name = os.path.basename(path)
            
            # 使用文件所在文件夹初始化MyPdfFile，并传递单个文件名
            f = MyPdfFile(folder_path)
            f.merge_images2pdf(single_file=file_name)
            
            if is_ajax():
                return jsonify({'success': True, 'message': f'图片 {file_name} 已成功转换为PDF'})
            flash(f'图片 {file_name} 已成功转换为PDF')
            return redirect(url_for('utils_process.file_processing'))
            
        elif os.path.isdir(path):
            # 如果是文件夹，合并文件夹内所有图片
            f = MyPdfFile(path)
            f.merge_images2pdf()
            
            if is_ajax():
                return jsonify({'success': True, 'message': '文件夹内所有图片已合并为PDF'})
            flash('文件夹内所有图片已合并为PDF')
            return redirect(url_for('utils_process.file_processing'))
        else:
            if is_ajax():
                return jsonify({'success': False, 'message': '提供的路径无效'}), 400
            flash('提供的路径无效')
            return redirect(url_for('utils_process.file_processing'))
            
    except Exception as e:
        if is_ajax():
            return jsonify({'success': False, 'message': f'处理失败：{str(e)}'}), 500
        flash(f'处理失败：{str(e)}')
        return redirect(url_for('utils_process.file_processing'))


@csrf.exempt
@utils_process.route('/word_to_pdf', methods=['POST'])
@login_required
@staff_only
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

@csrf.exempt
@utils_process.route('/split_screenshot_to_pdf', methods=['POST'])
@login_required
@staff_only
def split_screenshot_to_pdf():
    try:
        # 获取表单数据
        folder_path = request.form.get('screenshotFolderPath')
        margin_size = int(request.form.get('marginSize', 20))  # 默认20毫米边距
        
        if not folder_path:
            error_msg = '请提供长截图文件夹路径'
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

        # 检查文件夹中是否有图片文件
        image_files = [f for f in os.listdir(folder_path) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))]
        if not image_files:
            error_msg = f'文件夹中没有图片文件: {folder_path}'
            if is_ajax():
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg)
            return redirect(url_for('utils_process.file_processing'))

        # 处理长截图切分
        from App_new.utils.screenshot_splitter import ScreenshotSplitter
        splitter = ScreenshotSplitter(folder_path, margin_size)
        result = splitter.process_screenshots()

        # 返回成功信息
        success_msg = f'成功处理 {len(image_files)} 个长截图文件，生成 {result["pages"]} 页PDF'
        if is_ajax():
            return jsonify({
                'success': True, 
                'message': success_msg,
                'files_processed': len(image_files),
                'pages_generated': result["pages"]
            })
        flash(success_msg)
        return redirect(url_for('utils_process.file_processing'))

    except Exception as e:
        error_msg = f'长截图切分失败: {str(e)}'
        current_app.logger.error(f'长截图切分错误: {error_msg}\n{traceback.format_exc()}')
        if is_ajax():
            return jsonify({'success': False, 'message': error_msg}), 500
        flash(error_msg)
        return redirect(url_for('utils_process.file_processing'))


@csrf.exempt
@utils_process.route('/upload_images_to_pdf', methods=['POST'])
@login_required
@staff_only
def upload_images_to_pdf():
    """上传图片文件，合并为PDF后下载"""
    try:
        files = request.files.getlist('imageFiles')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'message': '请选择图片文件'}), 400

        from PIL import Image

        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        images = []

        # 按文件名排序
        sorted_files = sorted(files, key=lambda f: f.filename)

        for f in sorted_files:
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in image_extensions:
                continue
            img = Image.open(BytesIO(f.read()))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            images.append(img)

        if not images:
            return jsonify({'success': False, 'message': '没有找到有效的图片文件'}), 400

        # 合并为PDF到内存
        pdf_buffer = BytesIO()
        first_img = images[0]
        rest_imgs = images[1:] if len(images) > 1 else []
        first_img.save(pdf_buffer, 'PDF', save_all=True, append_images=rest_imgs)
        pdf_buffer.seek(0)

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='merged_images.pdf'
        )

    except Exception as e:
        current_app.logger.error(f'上传图片合并PDF失败: {str(e)}\n{traceback.format_exc()}')
        return jsonify({'success': False, 'message': f'处理失败：{str(e)}'}), 500


@csrf.exempt
@utils_process.route('/upload_pdf_to_pdf', methods=['POST'])
@login_required
@staff_only
def upload_pdf_to_pdf():
    """上传多个PDF文件，合并为一个PDF后下载"""
    try:
        files = request.files.getlist('pdfFiles')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'message': '请选择PDF文件'}), 400

        from PyPDF2 import PdfReader
        from App_new.utils.VisaForm import merge_readers_unified_width

        # 按文件名排序后读入各 PDF
        sorted_files = sorted(files, key=lambda f: f.filename)
        readers = []
        for f in sorted_files:
            if not f.filename.lower().endswith('.pdf'):
                continue
            # 将上传文件读入BytesIO，确保可seek
            file_bytes = BytesIO(f.read())
            try:
                readers.append(PdfReader(file_bytes, strict=False))
            except TypeError:
                readers.append(PdfReader(file_bytes))

        # 统一宽度合并（与“文件夹合并”共用同一实现）
        writer, total_pages, _target_width = merge_readers_unified_width(readers)

        if total_pages == 0:
            return jsonify({'success': False, 'message': '未能从PDF文件中提取有效页面'}), 400

        # 写入内存
        pdf_buffer = BytesIO()
        writer.write(pdf_buffer)
        pdf_buffer.seek(0)

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='merged.pdf'
        )

    except Exception as e:
        current_app.logger.error(f'上传PDF合并失败: {str(e)}\n{traceback.format_exc()}')
        return jsonify({'success': False, 'message': f'处理失败：{str(e)}'}), 500


@utils_process.route('/open_FuXin_pdf')
@login_required
@staff_only
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
@login_required
@staff_only
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
@login_required
@staff_only
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
@login_required
@staff_only
def files_home():
    """文件处理首页路由"""
    return render_template('shared/utils/文件处理首页.html')


@utils_process.route('/image_matting')
@login_required
@staff_only
def image_matting():
    """AI 抠图合并工具页面"""
    return render_template('shared/utils/抠图合并.html')


@csrf.exempt
@utils_process.route('/image_matting_process', methods=['POST'])
@login_required
@staff_only
def image_matting_process():
    """
    上传图片 -> AI 去背景 -> 可选合并/导出 PDF -> 返回结果文件下载。
    - 合并(merge != none): 返回单张 PNG, 或 PDF(勾选时)
    - 不合并(merge == none): 单张返回 PNG; 多张打包为 ZIP; 勾选 PDF 时同理返回 PDF/ZIP
    """
    try:
        from PIL import Image as _PILImage
        try:
            from App_new.utils.image_matting import matting, to_pdf_bytes
        except ImportError as imp_err:
            return jsonify({
                'success': False,
                'message': f'抠图功能所需依赖未安装(rembg/opencv 等): {imp_err}。'
                           f'请在服务器执行: pip install rembg onnxruntime opencv-python'
            }), 500

        files = request.files.getlist('imageFiles')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'message': '请选择图片文件'}), 400

        # 读取参数
        mode = request.form.get('mode', 'card')          # card | page
        bg = request.form.get('bg', 'white')             # white | transparent
        merge = request.form.get('merge', 'none')        # none | vertical | horizontal | grid
        want_pdf = request.form.get('pdf') in ('1', 'true', 'on', 'yes')

        if mode not in ('card', 'page'):
            mode = 'card'
        if bg not in ('white', 'transparent'):
            bg = 'white'
        if merge not in ('none', 'vertical', 'horizontal', 'grid'):
            merge = 'none'
        # 透明底无法转 PDF, 自动按白底处理 PDF
        transparent = (bg == 'transparent')

        # 解析上传图片
        image_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}
        sorted_files = sorted(files, key=lambda f: f.filename)
        pil_images, names = [], []
        for f in sorted_files:
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in image_exts:
                continue
            pil_images.append(_PILImage.open(BytesIO(f.read())))
            names.append(os.path.splitext(os.path.basename(f.filename))[0])

        if not pil_images:
            return jsonify({'success': False, 'message': '没有找到有效的图片文件'}), 400

        current_app.logger.info(
            f'抠图处理开始: 数量={len(pil_images)} 模式={mode} 背景={bg} 合并={merge} pdf={want_pdf}')

        result = matting(pil_images, mode=mode, bg=bg, merge=merge)

        # ---------- 合并模式: 返回单个文件 ----------
        if merge != 'none':
            merged = result['merged']
            if want_pdf:
                buf = to_pdf_bytes(merged)
                return send_file(buf, mimetype='application/pdf',
                                 as_attachment=True, download_name='抠图合并结果.pdf')
            buf = BytesIO()
            merged.save(buf, 'PNG')
            buf.seek(0)
            suffix = '_透明底' if transparent else ''
            return send_file(buf, mimetype='image/png',
                             as_attachment=True, download_name=f'抠图合并结果{suffix}.png')

        # ---------- 不合并模式 ----------
        singles = result['singles']
        # 单张直接返回
        if len(singles) == 1:
            if want_pdf:
                buf = to_pdf_bytes(singles[0])
                return send_file(buf, mimetype='application/pdf',
                                 as_attachment=True, download_name=f'{names[0]}_nobg.pdf')
            buf = BytesIO()
            singles[0].save(buf, 'PNG')
            buf.seek(0)
            return send_file(buf, mimetype='image/png',
                             as_attachment=True, download_name=f'{names[0]}_nobg.png')

        # 多张: 打包 ZIP
        import zipfile
        zip_buf = BytesIO()
        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for img, name in zip(singles, names):
                item = BytesIO()
                if want_pdf:
                    item = to_pdf_bytes(img)
                    zf.writestr(f'{name}_nobg.pdf', item.getvalue())
                else:
                    img.save(item, 'PNG')
                    zf.writestr(f'{name}_nobg.png', item.getvalue())
        zip_buf.seek(0)
        return send_file(zip_buf, mimetype='application/zip',
                         as_attachment=True, download_name='抠图结果.zip')

    except Exception as e:
        current_app.logger.error(f'抠图处理失败: {str(e)}\n{traceback.format_exc()}')
        return jsonify({'success': False, 'message': f'处理失败：{str(e)}'}), 500


@utils_process.route('/image/print/<path:image_path>')
def serve_print_image(image_path):
    """
    为打印提供优化后的小尺寸图片
    - 最大宽度 400px（A4 打印足够）
    - JPEG 质量 70%
    - 显著减少加载时间
    """
    try:
        from PIL import Image

        # 构建完整的图片路径
        static_folder = current_app.static_folder
        full_path = os.path.join(static_folder, image_path)

        if not os.path.exists(full_path):
            return 'Image not found', 404

        # 检查缓存目录
        cache_dir = os.path.join(static_folder, 'cache', 'print_images')
        os.makedirs(cache_dir, exist_ok=True)

        # 生成缓存文件名（基于原文件路径的哈希）
        import hashlib
        cache_key = hashlib.md5(image_path.encode()).hexdigest()
        cache_path = os.path.join(cache_dir, f'{cache_key}.jpg')

        # 检查缓存是否存在且有效（原文件未修改）
        if os.path.exists(cache_path):
            original_mtime = os.path.getmtime(full_path)
            cache_mtime = os.path.getmtime(cache_path)
            if cache_mtime > original_mtime:
                # 缓存有效，直接返回（带浏览器缓存头，重复打印不再重新下载）
                return send_file(cache_path, mimetype='image/jpeg', max_age=86400)

        # 处理图片
        with Image.open(full_path) as img:
            # 转换为 RGB（处理 PNG 透明通道）
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # 调整尺寸（最大宽度 400px，适合 A4 打印）
            max_width = 400
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # 保存到缓存
            img.save(cache_path, 'JPEG', quality=70, optimize=True)

        # 返回处理后的图片（带浏览器缓存头）
        return send_file(cache_path, mimetype='image/jpeg', max_age=86400)

    except Exception as e:
        current_app.logger.error(f'图片处理失败: {str(e)}')
        # 失败时返回原图
        return redirect(url_for('static', filename=image_path))
