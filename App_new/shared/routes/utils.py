from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, send_file, abort
from flask_login import login_required, current_user
from App_new.utils.VisaForm import MyPdfFile
from App_new.utils.WordToPdf import WordToPDFConverter
from App_new.utils.decorators import staff_only
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


def _natural_key(name):
    """文件名自然排序：让 图2 排在 图10 前面（纯字典序会反过来）"""
    import re
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r'(\d+)', name or '')]


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
    """上传图片文件，合并为PDF后下载

    page_size 决定每页多大:
    - width (默认): 所有页统一成 A4 宽度, 高度按各自图片比例 —— 图片宽窄不一也不会页页不同
    - a4        : 统一排成 A4 页面(留白居中, 整本同一个方向)
    - origin    : 保持原图尺寸(旧行为, 图片宽度不同则页面宽度也不同)
    """
    try:
        files = request.files.getlist('imageFiles')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'message': '请选择图片文件'}), 400

        from PIL import Image
        from App_new.utils.image_matting import flatten_white, to_pdf_bytes_multi, to_pdf_bytes_uniform_width

        page_size = request.form.get('page_size', 'width')
        if page_size not in ('width', 'a4', 'origin'):
            page_size = 'width'

        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        images = []

        # 按文件名排序
        # 自然排序: 多页 PDF 的页序按文件名来, 让 图2 排在 图10 前面
        sorted_files = sorted(files, key=lambda f: _natural_key(f.filename))

        for f in sorted_files:
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in image_extensions:
                continue
            # 透明图直接 convert('RGB') 会变黑底, 统一走贴白底
            images.append(flatten_white(Image.open(BytesIO(f.read()))))

        if not images:
            return jsonify({'success': False, 'message': '没有找到有效的图片文件'}), 400

        current_app.logger.info(f'图片合并PDF: 数量={len(images)} 页面尺寸={page_size}')

        # ---------- A4 页面: 复用抠图那套排版(留白居中 + 整本方向统一) ----------
        if page_size == 'a4':
            pdf_buffer = to_pdf_bytes_multi(images)
            return send_file(pdf_buffer, mimetype='application/pdf',
                             as_attachment=True, download_name='merged_images.pdf')

        # ---------- 统一宽度: 每页都是 A4 宽, 高度按各自比例 ----------
        if page_size == 'width':
            pdf_buffer = to_pdf_bytes_uniform_width(images)
        else:
            # ---------- 原图尺寸: 老行为, 页面大小跟着图片像素走 ----------
            pdf_buffer = BytesIO()
            images[0].save(pdf_buffer, 'PDF', save_all=True, append_images=images[1:])
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


@utils_process.route('/files_home')
@login_required
@staff_only
def files_home():
    """文件处理首页路由"""
    return render_template('shared/utils/文件处理首页.html')


# 抠图处理模式: URL 参数 -> (内部模式, 标题, 说明)
MATTING_MODES = {
    'card': {
        'mode': 'card',
        'label': '证件 / 卡片',
        'desc': '保留圆角 + 自动摆正，适合身份证、银行卡、各类证件卡片',
        'icon': 'fas fa-id-card',
        'default_pdf': 'none',      # 卡片多数是拿 PNG 去排版
    },
    'passport': {
        'mode': 'page',
        'label': '护照 / 文件页',
        'desc': '透视校正，拉平成矩形，适合护照资料页、整页文件',
        'icon': 'fas fa-passport',
        'default_pdf': 'merged',    # 护照页多数是多张合成一个 PDF 交件
    },
}


@utils_process.route('/image_matting')
@login_required
@staff_only
def image_matting_entry():
    """不带参数访问时跳到默认模式(证件 / 卡片)"""
    return redirect(url_for('utils_process.image_matting', matting_type='card'))


@utils_process.route('/image_matting/<matting_type>')
@login_required
@staff_only
def image_matting(matting_type):
    """AI 抠图合并工具页面, 处理模式由 URL 参数指定(card / passport)"""
    # 兼容内部模式名 page 直接作为 URL 参数传入
    if matting_type == 'page':
        matting_type = 'passport'
    if matting_type not in MATTING_MODES:
        abort(404)
    return render_template(
        'shared/utils/抠图合并.html',
        matting_type=matting_type,
        matting_modes=MATTING_MODES,
        current_mode=MATTING_MODES[matting_type],
    )


@csrf.exempt
@utils_process.route('/image_matting_process', methods=['POST'])
@login_required
@staff_only
def image_matting_process():
    """
    上传图片 -> AI 去背景 -> 可选合并/导出 PDF -> 返回结果文件下载。

    输出由 merge(合并方式) 和 pdf_mode(PDF 方式) 共同决定:
    - merge != none: 多张先拼成一张, 输出单个 PNG 或单页 PDF
    - merge == none + pdf_mode=merged: 每张一页, 合成一个多页 PDF(一次下载)
    - merge == none + pdf_mode=each  : 每张单独 PDF, 打包 ZIP
    - merge == none + pdf_mode=none  : 单张返回 PNG, 多张打包 ZIP
    """
    try:
        from PIL import Image as _PILImage
        try:
            from App_new.utils.image_matting import (
                matting, to_pdf_bytes, to_pdf_bytes_multi, pick_orientation)
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
        mode = request.form.get('mode', 'card')          # card | page(别名 passport)
        bg = request.form.get('bg', 'white')             # white | transparent
        merge = request.form.get('merge', 'none')        # none | vertical | horizontal | grid
        # PDF 方式: none=不导出 | merged=多张合成一个多页 PDF | each=每张单独 PDF(打包 ZIP)
        pdf_mode = request.form.get('pdf_mode', '')
        if not pdf_mode:
            # 兼容老参数 pdf=1(以及 API 调用方): 默认合成一个多页 PDF
            pdf_mode = 'merged' if request.form.get('pdf') in ('1', 'true', 'on', 'yes') else 'none'
        if pdf_mode not in ('none', 'merged', 'each'):
            pdf_mode = 'none'
        want_pdf = (pdf_mode != 'none')
        # PDF 页面方向: auto=按多数图片统一 | portrait=全部竖 | landscape=全部横
        page_orient = request.form.get('page_orient', 'auto')
        if page_orient not in ('auto', 'portrait', 'landscape'):
            page_orient = 'auto'

        # 兼容路由参数别名 passport -> page
        if mode == 'passport':
            mode = 'page'
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
            f'抠图处理开始: 数量={len(pil_images)} 模式={mode} 背景={bg} '
            f'合并={merge} pdf={pdf_mode} 页面方向={page_orient}')

        result = matting(pil_images, mode=mode, bg=bg, merge=merge)

        # ---------- 合并模式: 返回单个文件 ----------
        if merge != 'none':
            merged = result['merged']
            if want_pdf:
                buf = to_pdf_bytes(merged, orientation=page_orient)
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
                buf = to_pdf_bytes(singles[0], orientation=page_orient)
                return send_file(buf, mimetype='application/pdf',
                                 as_attachment=True, download_name=f'{names[0]}_nobg.pdf')
            buf = BytesIO()
            singles[0].save(buf, 'PNG')
            buf.seek(0)
            return send_file(buf, mimetype='image/png',
                             as_attachment=True, download_name=f'{names[0]}_nobg.png')

        # 多张 + 合成 PDF: 每张一页, 返回一个多页 PDF
        if pdf_mode == 'merged':
            buf = to_pdf_bytes_multi(singles, orientation=page_orient)
            return send_file(buf, mimetype='application/pdf',
                             as_attachment=True, download_name='抠图结果.pdf')

        # 多张: 打包 ZIP(每张单独 PDF 时也统一方向, 打印才不会一横一竖)
        zip_orient = page_orient
        if pdf_mode == 'each' and zip_orient == 'auto':
            zip_orient = pick_orientation(singles)

        import zipfile
        zip_buf = BytesIO()
        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for img, name in zip(singles, names):
                item = BytesIO()
                if want_pdf:
                    item = to_pdf_bytes(img, orientation=zip_orient)
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


@utils_process.route('/image_merge')
@login_required
@staff_only
def image_merge():
    """多图拼接长图工具页面"""
    return render_template('shared/utils/截图拼接.html')


@csrf.exempt
@utils_process.route('/image_merge_process', methods=['POST'])
@login_required
@staff_only
def image_merge_process():
    """
    上传多张图片 -> 按顺序拼成一张长图 -> 返回文件下载。

    手机不支持长截图时只能连续截多张，这里拼回一整张。
    默认自动裁掉相邻两张之间滚动重复的内容。
    """
    try:
        from PIL import Image as _PILImage
        from App_new.utils.image_merge import merge_images, to_bytes

        files = request.files.getlist('imageFiles')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'message': '请选择图片文件'}), 400

        direction = request.form.get('direction', 'vertical')
        if direction not in ('vertical', 'horizontal'):
            direction = 'vertical'
        auto_overlap = request.form.get('auto_overlap') in ('1', 'true', 'on', 'yes')
        trim_chrome = request.form.get('trim_chrome') in ('1', 'true', 'on', 'yes')
        fmt = 'jpeg' if request.form.get('format') == 'jpeg' else 'png'

        try:
            gap = max(0, min(200, int(request.form.get('gap', 0) or 0)))
        except ValueError:
            gap = 0
        try:
            quality = max(60, min(100, int(request.form.get('quality', 90) or 90)))
        except ValueError:
            quality = 90

        # 解析上传图片
        image_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}
        parsed = []
        for index, f in enumerate(files):
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in image_exts:
                continue
            parsed.append((index, _PILImage.open(BytesIO(f.read()))))

        if not parsed:
            return jsonify({'success': False, 'message': '没有找到有效的图片文件'}), 400

        # 顺序：前端拖动排过序就按它给的下标，否则按文件名自然排序
        # （自然排序是为了 "图2" 排在 "图10" 前面，纯字典序会反过来）
        order_raw = (request.form.get('order') or '').strip()
        by_index = dict(parsed)
        if order_raw:
            try:
                wanted = [int(x) for x in order_raw.split(',') if x.strip() != '']
            except ValueError:
                wanted = []
            ordered = [by_index[i] for i in wanted if i in by_index]
            # 前端漏传的补在后面，避免整张图缺内容
            ordered += [img for i, img in parsed if i not in set(wanted)]
        else:
            names = {i: files[i].filename for i, _ in parsed}
            ordered = [img for i, img in sorted(parsed, key=lambda p: _natural_key(names[p[0]]))]

        if len(ordered) < 2:
            return jsonify({'success': False, 'message': '至少需要 2 张图片才能拼接'}), 400

        current_app.logger.info(
            f'图片拼接开始: 数量={len(ordered)} 方向={direction} '
            f'去重叠={auto_overlap} 去框架={trim_chrome} 格式={fmt}')

        merged, info = merge_images(ordered, direction=direction,
                                    auto_overlap=auto_overlap,
                                    trim_chrome=trim_chrome, gap=gap)
        buf, mimetype, ext = to_bytes(merged, fmt, quality)

        width, height = info['size']
        cut = sum(info['overlaps'])
        current_app.logger.info(
            f'图片拼接完成: {width}x{height} 去除重复 {cut}px '
            f'重叠明细={info["overlaps"]} 固定框架={info.get("chrome")}')

        return send_file(buf, mimetype=mimetype, as_attachment=True,
                         download_name=f'拼接长图_{width}x{height}.{ext}')

    except ValueError as e:
        # 尺寸超限之类的可预期错误，直接把原因给用户
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f'图片拼接失败: {str(e)}\n{traceback.format_exc()}')
        return jsonify({'success': False, 'message': f'拼接失败：{str(e)}'}), 500


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
