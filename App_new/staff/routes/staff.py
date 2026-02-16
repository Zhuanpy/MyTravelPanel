# -*- coding: utf-8 -*-
"""
员工模块路由 - 完整版本
包含所有员工功能模块
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app, send_from_directory, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from ...utils.decorators import staff_only
from ...utils.device_detector import mobile_redirect
from werkzeug.utils import secure_filename
import json
import os

# 创建员工蓝图
# 注意：此文件位于 App_new/staff/routes/ 下，而模板位于 App_new/staff/templates/
# 这里将模板目录指向上一层的 templates，模板渲染统一使用命名空间路径 'staff/xxx.html'
staff = Blueprint('staff', __name__, url_prefix='/staff', template_folder='../templates')

# ==================== 辅助函数 ====================
def allowed_file(filename, allowed_extensions):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def compress_and_resize_image(file_path, max_size=1200, quality=80, generate_thumbnail=True, thumb_size=300):
    """
    压缩和调整图片尺寸（优化网页加载速度）

    参数:
        file_path: 图片文件路径
        max_size: 最大宽度或高度（像素），默认1200（适合网页显示）
        quality: JPEG压缩质量（1-100），默认80
        generate_thumbnail: 是否生成缩略图，默认True
        thumb_size: 缩略图尺寸，默认300

    返回:
        dict: {'width': 宽度, 'height': 高度, 'file_size': 文件大小, 'thumbnail_path': 缩略图路径}
    """
    from PIL import Image
    import io

    result = {'width': None, 'height': None, 'file_size': None, 'thumbnail_path': None}

    try:
        with Image.open(file_path) as img:
            original_format = img.format
            original_size = os.path.getsize(file_path)

            # 处理 RGBA 模式（PNG透明图片）转换为 RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                # 创建白色背景
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # 获取原始尺寸
            width, height = img.size

            # 判断是否需要调整尺寸
            needs_resize = width > max_size or height > max_size

            if needs_resize:
                # 按比例缩放
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))

                # 使用高质量缩放算法
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                width, height = new_width, new_height

            # 保存压缩后的图片（统一使用JPEG格式以获得更好的压缩效果）
            # 如果原图是PNG且较小，保持PNG格式
            name, ext = os.path.splitext(file_path)

            if original_format == 'PNG' and original_size < 200 * 1024 and not needs_resize:
                # 小于200KB的PNG保持原格式
                img.save(file_path, 'PNG', optimize=True)
            else:
                # 转换为JPEG格式
                new_path = name + '.jpg'
                img.save(new_path, 'JPEG', quality=quality, optimize=True)

                # 验证新文件确实创建成功后，再删除原文件
                if os.path.exists(new_path) and os.path.getsize(new_path) > 0:
                    # 如果原文件不是jpg，删除原文件
                    if file_path.lower() != new_path.lower() and os.path.exists(file_path):
                        os.remove(file_path)
                    file_path = new_path
                else:
                    # 转换失败，保留原文件
                    current_app.logger.warning(f"JPEG转换失败，保留原文件: {file_path}")

            result['width'] = width
            result['height'] = height
            result['file_size'] = os.path.getsize(file_path)
            result['new_path'] = file_path

            # 生成缩略图
            if generate_thumbnail:
                thumb_dir = os.path.join(os.path.dirname(file_path), 'thumbnails')
                os.makedirs(thumb_dir, exist_ok=True)

                thumb_filename = 'thumb_' + os.path.basename(file_path)
                thumb_path = os.path.join(thumb_dir, thumb_filename)

                # 生成缩略图
                thumb_img = img.copy()
                thumb_img.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
                thumb_img.save(thumb_path, 'JPEG', quality=80, optimize=True)

                result['thumbnail_path'] = thumb_path

            # 记录压缩效果
            if original_size > 0:
                compression_ratio = (1 - result['file_size'] / original_size) * 100
                current_app.logger.info(
                    f"图片压缩完成: {os.path.basename(file_path)}, "
                    f"原始大小: {original_size/1024:.1f}KB, "
                    f"压缩后: {result['file_size']/1024:.1f}KB, "
                    f"压缩率: {compression_ratio:.1f}%"
                )

    except Exception as e:
        current_app.logger.error(f"图片压缩失败: {e}")
        # 即使压缩失败，也尝试获取基本信息
        try:
            with Image.open(file_path) as img:
                result['width'], result['height'] = img.size
            result['file_size'] = os.path.getsize(file_path)
            result['new_path'] = file_path
        except:
            pass

    return result

# ==================== 个人资料 ====================
@staff.route('/profile')
@login_required
@staff_only
def profile():
    """员工个人资料页面"""
    return render_template('staff/profile.html', user=current_user)


@staff.route('/card/<int:user_id>')
def business_card(user_id):
    """电子名片 - 公开页面，无需登录"""
    from ...auth.models.auth import AuthUser, UserProfile
    from ...business.tour.models.Packagemodels import CompanyInfo, HomeBanner
    import random

    user = AuthUser.query.get_or_404(user_id)
    # 检查用户是否有资料且设置为公开，或者是当前登录用户自己查看
    is_owner = current_user.is_authenticated and current_user.id == user_id
    if not is_owner and (not user.profile or not user.profile.is_public):
        flash('该名片不存在或未公开', 'warning')
        return redirect(url_for('auth.login'))

    company = CompanyInfo.query.first()

    # 从轮播图库中随机选取一张作为名片背景
    banners = HomeBanner.get_active_banners()
    banner_image = None
    if banners:
        banner = random.choice(banners)
        banner_image = url_for('static', filename=banner.image_path)

    return render_template('staff/business_card.html', user=user, company=company,
                           is_owner=is_owner, banner_image=banner_image)

@staff.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@staff_only
def edit_profile():
    """编辑员工个人资料"""
    from ...auth.models.auth import UserProfile
    from ...exts import db
    from werkzeug.utils import secure_filename
    import uuid
    import os

    if request.method == 'POST':
        try:
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            phone = request.form.get('phone', '').strip()
            position = request.form.get('position', '').strip()

            # 新增联系方式字段
            wechat_id = request.form.get('wechat_id', '').strip()
            whatsapp = request.form.get('whatsapp', '').strip()
            is_public = request.form.get('is_public') == '1'
            remove_wechat_qr = request.form.get('remove_wechat_qr') == '1'
            remove_whatsapp_qr = request.form.get('remove_whatsapp_qr') == '1'

            if not first_name:
                flash('姓名不能为空', 'error')
                return render_template('staff/edit_profile.html', user=current_user)

            # 辅助函数：处理二维码上传
            def save_qr_image(file_key, prefix):
                if file_key in request.files:
                    file = request.files[file_key]
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        name, ext = os.path.splitext(filename)
                        unique_filename = f"{prefix}_{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"

                        upload_folder = os.path.join(current_app.static_folder, 'uploads', 'qr_codes')
                        if not os.path.exists(upload_folder):
                            os.makedirs(upload_folder)

                        file_path = os.path.join(upload_folder, unique_filename)
                        file.save(file_path)
                        return f"uploads/qr_codes/{unique_filename}"
                return None

            # 辅助函数：删除旧二维码文件
            def delete_old_qr(qr_path):
                if qr_path:
                    old_file = os.path.join(current_app.static_folder, qr_path)
                    if os.path.exists(old_file):
                        os.remove(old_file)

            # 处理二维码上传
            wechat_qr_path = save_qr_image('wechat_qr', 'wechat_qr')
            whatsapp_qr_path = save_qr_image('whatsapp_qr', 'whatsapp_qr')

            # 更新用户资料
            if current_user.profile:
                current_user.profile.first_name = first_name
                current_user.profile.last_name = last_name
                current_user.profile.phone = phone
                current_user.profile.position = position
                current_user.profile.wechat_id = wechat_id
                current_user.profile.whatsapp = whatsapp
                current_user.profile.is_public = is_public

                # 处理微信二维码
                if remove_wechat_qr:
                    delete_old_qr(current_user.profile.wechat_qr)
                    current_user.profile.wechat_qr = None
                elif wechat_qr_path:
                    delete_old_qr(current_user.profile.wechat_qr)
                    current_user.profile.wechat_qr = wechat_qr_path

                # 处理WhatsApp二维码
                if remove_whatsapp_qr:
                    delete_old_qr(current_user.profile.whatsapp_qr)
                    current_user.profile.whatsapp_qr = None
                elif whatsapp_qr_path:
                    delete_old_qr(current_user.profile.whatsapp_qr)
                    current_user.profile.whatsapp_qr = whatsapp_qr_path
            else:
                # 如果用户没有资料，创建新的
                profile = UserProfile(
                    user_id=current_user.id,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    position=position
                )
                profile.wechat_id = wechat_id
                profile.whatsapp = whatsapp
                profile.is_public = is_public
                if wechat_qr_path:
                    profile.wechat_qr = wechat_qr_path
                if whatsapp_qr_path:
                    profile.whatsapp_qr = whatsapp_qr_path
                db.session.add(profile)

            db.session.commit()
            flash('资料更新成功', 'success')
            return redirect(url_for('staff.profile'))

        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')

    return render_template('staff/edit_profile.html', user=current_user)

@staff.route('/change-password', methods=['GET', 'POST'])
@login_required
@staff_only
def change_password():
    """员工修改密码"""
    from ...exts import db
    
    if request.method == 'POST':
        try:
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if not all([current_password, new_password, confirm_password]):
                flash('请填写所有字段', 'error')
                return render_template('staff/change_password.html')
            
            # 验证当前密码
            if not current_user.check_password(current_password):
                flash('当前密码错误', 'error')
                return render_template('staff/change_password.html')
            
            # 验证新密码
            if new_password != confirm_password:
                flash('两次输入的新密码不一致', 'error')
                return render_template('staff/change_password.html')
            
            if len(new_password) < 6:
                flash('新密码长度至少6位', 'error')
                return render_template('staff/change_password.html')
            
            # 更新密码（会自动递增session_version）
            current_user.set_password(new_password)
            db.session.commit()

            # 更新当前会话的版本号，避免自己被登出
            session['session_version'] = current_user.session_version

            flash('密码修改成功，其他设备需要重新登录', 'success')
            return redirect(url_for('staff.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'修改密码失败：{str(e)}', 'error')
    
    return render_template('staff/change_password.html')

# ==================== 仪表板 ====================
@staff.route('/dashboard')
@mobile_redirect('mobile.staff_dashboard')
@login_required
@staff_only
def dashboard():
    """员工仪表板 - 显示财务统计和待办提醒（优化查询性能）"""
    try:
        # 导入必要的模型
        from ...business.projects.models.project import ProjectHeader
        from ...business.projects.models.ref import ProjectRef
        from ...business.projects.models.eo import ProjectEO
        from ...business.projects.models.invoice import ProjectInvoice
        from ...business.projects.models.receipt import ProjectReceipt
        from ...exts import db
        from sqlalchemy import func
        from sqlalchemy.orm import joinedload

        # 获取本月起始时间
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # ========== 财务统计（使用聚合查询）==========
        # 本月销售额和成本（一次聚合查询）
        month_stats = db.session.query(
            func.coalesce(func.sum(ProjectRef.selling_price), 0).label('selling'),
            func.coalesce(func.sum(ProjectRef.cost_price), 0).label('cost')
        ).join(ProjectHeader).filter(
            ProjectHeader.created_at >= current_month_start
        ).first()

        month_selling = float(month_stats.selling) if month_stats else 0
        month_cost = float(month_stats.cost) if month_stats else 0
        month_profit = month_selling - month_cost

        # 待收款金额（聚合查询：未结算项目的销售总额 - 已收款总额）
        unsettled_selling = db.session.query(
            func.coalesce(func.sum(ProjectRef.selling_price), 0)
        ).join(ProjectHeader).filter(
            ProjectHeader.is_settled == False
        ).scalar() or 0

        total_received = db.session.query(
            func.coalesce(func.sum(ProjectReceipt.amount), 0)
        ).join(ProjectHeader).filter(
            ProjectHeader.is_settled == False
        ).scalar() or 0

        total_receivable = float(unsettled_selling) - float(total_received)

        # 待付款 EO 统计（聚合查询）
        pending_eo_stats = db.session.query(
            func.count(ProjectEO.id).label('count'),
            func.coalesce(func.sum(ProjectRef.cost_price), 0).label('amount')
        ).join(ProjectRef).filter(
            ProjectEO.is_paid == False,
            ProjectEO.status == 'confirmed'
        ).first()

        pending_eo_count = pending_eo_stats.count if pending_eo_stats else 0
        pending_eo_amount = float(pending_eo_stats.amount) if pending_eo_stats else 0

        stats = {
            'month_selling': month_selling,
            'month_profit': month_profit,
            'total_receivable': max(0, total_receivable),
            'pending_eo_count': pending_eo_count,
            'pending_eo_amount': pending_eo_amount,
        }

        # ========== 待付款 EO 列表（使用 joinedload 预加载）==========
        pending_eos = ProjectEO.query.options(
            joinedload(ProjectEO.ref).joinedload(ProjectRef.header),
            joinedload(ProjectEO.ref).joinedload(ProjectRef.supplier)
        ).filter(
            ProjectEO.is_paid == False,
            ProjectEO.status == 'confirmed'
        ).order_by(ProjectEO.created_at.desc()).limit(10).all()

        pending_eo_list = []
        for eo in pending_eos:
            if eo.ref and eo.ref.header:
                pending_eo_list.append({
                    'id': eo.id,
                    'eo_number': eo.eo_number,
                    'hid': eo.ref.header.hid,
                    'project_id': eo.ref.header.id,
                    'supplier': eo.ref.supplier.company_name if eo.ref.supplier else '-',
                    'amount': float(eo.ref.cost_price or 0),
                    'currency': eo.ref.currency or 'SGD',
                    'created_at': eo.created_at.strftime('%Y-%m-%d') if eo.created_at else '',
                })

        # ========== 待开发票的 REF（优化查询）==========
        # 获取所有已有发票的 REF ID
        invoiced_ref_ids = db.session.query(
            func.distinct(func.json_extract(ProjectInvoice.ref_ids, '$[*]'))
        ).filter(ProjectInvoice.status != 'cancelled').all()

        # 简化：直接查询有销售金额但没有EO发票关联的REF
        pending_invoice_refs = []
        refs_query = ProjectRef.query.options(
            joinedload(ProjectRef.header)
        ).join(ProjectHeader).filter(
            ProjectHeader.is_settled == False,
            ProjectRef.selling_price > 0
        ).order_by(ProjectRef.created_at.desc()).limit(50).all()

        for ref in refs_query:
            # 快速检查是否有发票（通过查询而不是调用方法）
            has_invoice = ProjectInvoice.query.filter(
                ProjectInvoice.header_id == ref.header_id,
                ProjectInvoice.status != 'cancelled',
                ProjectInvoice.ref_ids.like(f'%{ref.id}%')
            ).first() is not None

            if not has_invoice:
                pending_invoice_refs.append({
                    'id': ref.id,
                    'ref_number': ref.ref_number,
                    'hid': ref.header.hid if ref.header else '-',
                    'project_id': ref.header.id if ref.header else 0,
                    'description': ref.description or ref.detailed_description or '-',
                    'amount': float(ref.selling_price),
                    'currency': ref.currency or 'SGD',
                })
                if len(pending_invoice_refs) >= 10:
                    break

        # ========== 最近项目（最近10个，优化查询）==========
        # 先获取最近10个项目的ID
        recent_headers = ProjectHeader.query.options(
            joinedload(ProjectHeader.company)
        ).order_by(ProjectHeader.created_at.desc()).limit(10).all()

        recent_project_ids = [p.id for p in recent_headers]

        # 一次性获取这些项目的财务汇总
        project_stats = {}
        if recent_project_ids:
            stats_query = db.session.query(
                ProjectRef.header_id,
                func.coalesce(func.sum(ProjectRef.selling_price), 0).label('selling'),
                func.coalesce(func.sum(ProjectRef.cost_price), 0).label('cost')
            ).filter(
                ProjectRef.header_id.in_(recent_project_ids)
            ).group_by(ProjectRef.header_id).all()

            for row in stats_query:
                project_stats[row.header_id] = {
                    'selling': float(row.selling),
                    'cost': float(row.cost)
                }

        recent_projects = []
        for project in recent_headers:
            ps = project_stats.get(project.id, {'selling': 0, 'cost': 0})
            recent_projects.append({
                'id': project.id,
                'hid': project.hid,
                'desc': project.desc or '-',
                'company': project.company.company_name if project.company else '-',
                'total_selling': ps['selling'],
                'total_profit': ps['selling'] - ps['cost'],
                'is_settled': project.is_settled,
                'created_at': project.created_at.strftime('%Y-%m-%d') if project.created_at else '',
            })

        return render_template('staff/staff_dashboard.html',
                             stats=stats,
                             pending_eo_list=pending_eo_list,
                             pending_invoice_refs=pending_invoice_refs,
                             recent_projects=recent_projects)

    except Exception as e:
        # 错误处理
        current_app.logger.error(f'加载员工仪表板失败: {str(e)}')
        import traceback
        traceback.print_exc()
        flash(f'加载仪表板失败：{str(e)}', 'error')

        return render_template('staff/staff_dashboard.html',
                             stats={
                                 'month_selling': 0,
                                 'month_profit': 0,
                                 'total_receivable': 0,
                                 'pending_eo_count': 0,
                                 'pending_eo_amount': 0,
                             },
                             pending_eo_list=[],
                             pending_invoice_refs=[],
                             recent_projects=[])

# ==================== 项目管理功能已移至 projects.py ====================

# ==================== 报价管理 ====================
@staff.route('/quotes')
@login_required
@staff_only
def quotes():
    """报价列表"""
    try:
        # 获取筛选参数
        status = request.args.get('status', '')
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # 模拟报价数据
        all_quotes = [
            {
                'id': 1,
                'quote_no': 'QT240001',
                'client': 'ABC公司',
                'project_name': '新加坡商务团队签证',
                'status': 'pending',
                'total_amount': 5000.00,
                'created_at': datetime(2024, 1, 15, 10, 30),
                'valid_until': datetime(2024, 1, 25, 10, 30)
            },
            {
                'id': 2,
                'quote_no': 'QT240002',
                'client': 'XYZ旅行社',
                'project_name': '泰国旅游团队套餐',
                'status': 'approved',
                'total_amount': 12000.00,
                'created_at': datetime(2024, 1, 16, 9, 15),
                'valid_until': datetime(2024, 1, 26, 9, 15)
            }
        ]
        
        # 应用筛选
        filtered_quotes = all_quotes
        
        if status:
            filtered_quotes = [q for q in filtered_quotes if q['status'] == status]
        if search:
            search_lower = search.lower()
            filtered_quotes = [q for q in filtered_quotes 
                               if search_lower in q['client'].lower() 
                               or search_lower in q['project_name'].lower()]
        
        # 分页
        total = len(filtered_quotes)
        start = (page - 1) * per_page
        end = start + per_page
        quotes_page = filtered_quotes[start:end]
        
        return render_template('staff/staff_quotes.html',
                             quotes=quotes_page,
                             current_page=page,
                             total_pages=(total + per_page - 1) // per_page,
                             total=total,
                             status=status,
                             search=search,
                             now=datetime.now())
    except Exception as e:
        flash(f'加载报价列表失败：{str(e)}', 'error')
        return render_template('staff/staff_quotes.html',
                             quotes=[],
                             current_page=1,
                             total_pages=1,
                             total=0,
                             status='',
                             search='',
                             now=datetime.now())

@staff.route('/create_quote', methods=['GET', 'POST'])
@login_required
@staff_only
def create_quote():
    """创建报价"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            quote_data = {
                'client': request.form.get('client'),
                'project_name': request.form.get('project_name'),
                'description': request.form.get('description'),
                'items': request.form.getlist('items[]'),
                'quantities': request.form.getlist('quantities[]'),
                'unit_prices': request.form.getlist('unit_prices[]'),
                'valid_days': int(request.form.get('valid_days', 30))
            }
            
            # 生成报价编号
            quote_no = 'QT240999'  # 模拟编号
            
            flash('报价创建成功！', 'success')
            return redirect(url_for('staff.quotes'))
            
        except Exception as e:
            flash(f'创建报价失败：{str(e)}', 'error')
    
    return render_template('staff/create_quote.html')

# ==================== 文件管理 ====================
@staff.route('/files')
@login_required
@staff_only
def files():
    """文件列表"""
    try:
        # 获取筛选参数
        file_type = request.args.get('type', '')
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # 获取实际上传的文件
        upload_folder = current_app.config['UPLOAD_FOLDER']
        all_files = []
        
        if os.path.exists(upload_folder):
            for filename in os.listdir(upload_folder):
                file_path = os.path.join(upload_folder, filename)
                if os.path.isfile(file_path):
                    # 获取文件信息
                    file_stat = os.stat(file_path)
                    file_size = file_stat.st_size
                    
                    # 确定文件类型
                    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                    if file_ext in ['pdf']:
                        file_type_display = 'pdf'
                    elif file_ext in ['doc', 'docx']:
                        file_type_display = 'document'
                    elif file_ext in ['xls', 'xlsx']:
                        file_type_display = 'excel'
                    elif file_ext in ['jpg', 'jpeg', 'png', 'gif']:
                        file_type_display = 'image'
                    elif file_ext in ['zip', 'rar']:
                        file_type_display = 'archive'
                    else:
                        file_type_display = 'document'
                    
                    # 格式化文件大小
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    else:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"
                    
                    all_files.append({
                        'id': len(all_files) + 1,
                        'filename': filename,
                        'file_type': file_type_display,
                        'size': size_str,
                        'uploaded_by': current_user.username,
                        'uploaded_at': datetime.fromtimestamp(file_stat.st_mtime),
                        'project': '未分类',
                        'category': 'other'
                    })
        
        # 按上传时间倒序排列
        all_files.sort(key=lambda x: x['uploaded_at'], reverse=True)
        
        # 应用筛选
        filtered_files = all_files
        
        if file_type:
            filtered_files = [f for f in filtered_files if f['file_type'] == file_type]
        if search:
            search_lower = search.lower()
            filtered_files = [f for f in filtered_files 
                               if search_lower in f['filename'].lower() 
                               or search_lower in f['project'].lower()]
        
        # 分页
        total = len(filtered_files)
        start = (page - 1) * per_page
        end = start + per_page
        files_page = filtered_files[start:end]
        
        return render_template('staff/staff_files.html',
                             files=files_page,
                             current_page=page,
                             total_pages=(total + per_page - 1) // per_page,
                             total=total,
                             file_type=file_type,
                             search=search)
    except Exception as e:
        flash(f'加载文件列表失败：{str(e)}', 'error')
        return render_template('staff/staff_files.html',
                             files=[],
                             current_page=1,
                             total_pages=1,
                             total=0)

@staff.route('/upload_file', methods=['GET', 'POST'])
@login_required
@staff_only
def upload_file():
    """上传文件"""
    if request.method == 'POST':
        try:
            # 检查是否有文件
            if 'file' not in request.files:
                flash('没有选择文件', 'error')
                return render_template('staff/staff_upload.html')
            
            file = request.files['file']
            if file.filename == '':
                flash('没有选择文件', 'error')
                return render_template('staff/staff_upload.html')
            
            # 获取其他表单数据
            filename = request.form.get('filename', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', '')
            project = request.form.get('project', '')
            tags = request.form.get('tags', '').strip()
            
            # 基础验证
            if not category:
                flash('请选择文件分类', 'error')
                return render_template('staff/staff_upload.html')
            
            # 检查文件类型
            allowed_extensions = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar'}
            if not allowed_file(file.filename, allowed_extensions):
                flash('不支持的文件类型', 'error')
                return render_template('staff/staff_upload.html')
            
            # 确保上传目录存在
            upload_folder = current_app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            # 保存文件
            if filename:
                # 使用用户指定的文件名，但需要添加扩展名
                file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                if file_ext:
                    filename = f"{filename}.{file_ext}"
                else:
                    filename = filename
            else:
                # 使用原始文件名
                filename = secure_filename(file.filename)
            
            # 确保文件名唯一
            file_path = os.path.join(upload_folder, filename)
            counter = 1
            while os.path.exists(file_path):
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{counter}{ext}"
                file_path = os.path.join(upload_folder, filename)
                counter += 1
            
            # 保存文件
            file.save(file_path)
            
            # 这里可以保存文件信息到数据库
            # 暂时只显示成功消息
            
            flash(f'文件上传成功！文件名：{filename}', 'success')
            return redirect(url_for('staff.files'))
            
        except Exception as e:
            flash(f'文件上传失败：{str(e)}', 'error')
    
    return render_template('staff/staff_upload.html')

@staff.route('/download/<filename>')
@login_required
@staff_only
def download_file(filename):
    """下载文件"""
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, filename)
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(upload_folder, filename, as_attachment=True)
        else:
            flash('文件不存在', 'error')
            return redirect(url_for('staff.files'))
    except Exception as e:
        flash(f'下载文件失败：{str(e)}', 'error')
        return redirect(url_for('staff.files'))

@staff.route('/delete_file/<filename>')
@login_required
@staff_only
def delete_file(filename):
    """删除文件"""
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, filename)
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            os.remove(file_path)
            flash(f'文件 {filename} 删除成功', 'success')
        else:
            flash('文件不存在', 'error')
    except Exception as e:
        flash(f'删除文件失败：{str(e)}', 'error')
    
    return redirect(url_for('staff.files'))

# ==================== API 路由 ====================
@staff.route('/api/stats')
@login_required
@staff_only
def api_stats():
    """获取统计数据"""
    try:
        # 导入必要的模型
        from ...business.projects.models.project import ProjectHeader, CustomerCompany
        from ...business.projects.models.ref import ProjectRef
        from datetime import datetime
        
        # 构建基础查询
        base_query = ProjectHeader.query
        
        # 根据员工等级过滤项目
        if current_user.role and current_user.role.name == 'staff':
            # 检查用户资料中的员工等级
            staff_level = 1  # 默认等级
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1
            
            if staff_level == 1:
                # 1级员工只能看到自己的项目
                base_query = base_query.filter(ProjectHeader.staff_id == current_user.id)
            # 2级员工可以看到所有项目，不需要额外过滤

        # 获取真实统计数据
        total_projects = base_query.count()
        active_projects = base_query.filter_by(status='active').count()
        
        # 计算本月完成的项目
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        completed_this_month = base_query.filter(
            ProjectHeader.status == 'completed',
            ProjectHeader.updated_at >= current_month_start
        ).count()
        
        # 计算待处理报价（状态为draft的项目）
        pending_quotes = base_query.filter_by(status='draft').count()
        
        # 计算财务数据
        all_projects = base_query.all()
        total_revenue = 0
        total_cost = 0
        
        for project in all_projects:
            refs = ProjectRef.query.filter_by(header_id=project.id).all()
            for ref in refs:
                if ref.selling_price:
                    total_revenue += float(ref.selling_price)
                if ref.cost_price:
                    total_cost += float(ref.cost_price)
        
        total_profit = total_revenue - total_cost
        
        stats = {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'pending_quotes': pending_quotes,
            'completed_this_month': completed_this_month,
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'total_profit': total_profit
        }
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@staff.route('/api/recent-projects')
@login_required
@staff_only
def api_recent_projects():
    """获取最近项目"""
    try:
        # 导入必要的模型
        from ...business.projects.models.project import ProjectHeader, CustomerCompany
        from ...business.projects.models.ref import ProjectRef
        
        # 构建基础查询
        base_query = ProjectHeader.query
        
        # 根据员工等级过滤项目
        if current_user.role and current_user.role.name == 'staff':
            # 检查用户资料中的员工等级
            staff_level = 1  # 默认等级
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1
            
            if staff_level == 1:
                # 1级员工只能看到自己的项目
                base_query = base_query.filter(ProjectHeader.staff_id == current_user.id)
            # 2级员工可以看到所有项目，不需要额外过滤

        # 获取最近的项目（最近10个）
        recent_projects_query = base_query.order_by(ProjectHeader.created_at.desc()).limit(10)
        projects = []
        
        for project in recent_projects_query:
            # 计算项目财务数据
            refs = ProjectRef.query.filter_by(header_id=project.id).all()
            total_selling_price = sum([float(ref.selling_price or 0) for ref in refs])
            total_cost_price = sum([float(ref.cost_price or 0) for ref in refs])
            total_profit = total_selling_price - total_cost_price
            
            # 获取客户公司名称
            client_name = '未指定客户'
            if project.company_id and project.company:
                client_name = project.company.company_name
            
            # 构建项目数据
            project_data = {
                'id': project.id,
                'hid': project.hid,
                'name': project.desc or f'项目 {project.hid}',
                'client': client_name,
                'leader': project.leader_name or '未指定负责人',
                'contact': project.contact or '未指定联系人',
                'status': project.status,
                'type': project.type or '综合',
                'created_at': project.created_at.strftime('%Y-%m-%d %H:%M') if project.created_at else '',
                'updated_at': project.updated_at.strftime('%Y-%m-%d %H:%M') if project.updated_at else '',
                'total_selling': total_selling_price,
                'total_cost': total_cost_price,
                'total_profit': total_profit,
                'ref_count': len(refs)
            }
            projects.append(project_data)
        
        return jsonify({
            'success': True,
            'data': projects
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@staff.route('/api/pending-tasks')
@login_required
@staff_only
def api_pending_tasks():
    """获取待处理任务"""
    try:
        # 导入必要的模型
        from ...shared.models.Utilsmodels import Todo
        
        # 获取未完成的待办事项（真正的待处理任务）
        pending_tasks = []
        
        # 构建基础查询
        base_query = Todo.query.filter_by(is_completed=False)
        
        # 根据员工等级过滤待办事项
        if current_user.role and current_user.role.name == 'staff':
            # 检查用户资料中的员工等级
            staff_level = 1  # 默认等级
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1
            
            if staff_level == 1:
                # 1级员工只能看到自己创建的待办事项
                base_query = base_query.filter(Todo.user_id == current_user.id)
            # 2级员工可以看到所有待办事项，不需要额外过滤
        
        todos = base_query.order_by(Todo.created_at.desc()).all()
        
        for todo in todos[:5]:  # 限制显示5个任务
            # 转换优先级数字为文本
            priority_map = {1: 'high', 2: 'medium', 3: 'low'}
            priority_text = priority_map.get(todo.priority, 'medium')
            
            task_data = {
                'id': todo.id,
                'title': todo.title,
                'description': todo.description or f'待办事项: {todo.title}',
                'priority': priority_text,
                'due_date': todo.due_date.strftime('%Y-%m-%d') if todo.due_date else '未设置',
                'type': 'todo'
            }
            pending_tasks.append(task_data)
        
        return jsonify({
            'success': True,
            'data': pending_tasks
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== 任务管理 ====================
@staff.route('/tasks')
@login_required
@staff_only
def tasks():
    """任务中心 - 重定向到todo_list页面"""
    return redirect(url_for('utils_blue.render_todo_list'))

# ==================== 客户管理 ====================
@staff.route('/customers')
@login_required
@staff_only
def customers():
    """客户列表"""
    try:
        # 获取筛选参数
        status = request.args.get('status', '')
        industry = request.args.get('industry', '')
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # 模拟客户数据
        all_customers = [
            {
                'id': 1,
                'company_name': 'ABC旅行社',
                'company_code': 'ABC001',
                'contact_person': '张经理',
                'contact_phone': '+86 138 0013 8000',
                'contact_email': 'zhang@abc.com',
                'industry': 'travel',
                'status': 'active',
                'credit_limit': 100000.00,
                'created_at': datetime(2024, 1, 15)
            },
            {
                'id': 2,
                'company_name': 'XYZ企业',
                'company_code': 'XYZ002',
                'contact_person': '李总',
                'contact_phone': '+86 139 0023 9000',
                'contact_email': 'li@xyz.com',
                'industry': 'business',
                'status': 'active',
                'credit_limit': 200000.00,
                'created_at': datetime(2024, 1, 16)
            },
            {
                'id': 3,
                'company_name': 'DEF教育集团',
                'company_code': 'DEF003',
                'contact_person': '王主任',
                'contact_phone': '+86 137 0033 7000',
                'contact_email': 'wang@def.com',
                'industry': 'education',
                'status': 'pending',
                'credit_limit': 50000.00,
                'created_at': datetime(2024, 1, 17)
            }
        ]
        
        # 应用筛选
        filtered_customers = all_customers
        
        if status:
            filtered_customers = [c for c in filtered_customers if c['status'] == status]
        if industry:
            filtered_customers = [c for c in filtered_customers if c['industry'] == industry]
        if search:
            search_lower = search.lower()
            filtered_customers = [c for c in filtered_customers 
                                 if search_lower in c['company_name'].lower() 
                                 or search_lower in c['contact_person'].lower()
                                 or search_lower in c['company_code'].lower()]
        
        # 分页
        total = len(filtered_customers)
        start = (page - 1) * per_page
        end = start + per_page
        customers_page = filtered_customers[start:end]
        
        return render_template('staff/staff_customers.html',
                             customers=customers_page,
                             current_page=page,
                             total_pages=(total + per_page - 1) // per_page,
                             total=total,
                             status=status,
                             industry=industry,
                             search=search)
    except Exception as e:
        flash(f'加载客户列表失败：{str(e)}', 'error')
        return render_template('staff/staff_customers.html',
                             customers=[],
                             current_page=1,
                             total_pages=1,
                             total=0,
                             status='',
                             industry='',
                             search='')

# ==================== 供应商管理 ====================
@staff.route('/suppliers')
@login_required
@staff_only
def suppliers():
    """供应商列表"""
    try:
        # 获取筛选参数
        status = request.args.get('status', '')
        supplier_type = request.args.get('supplier_type', '')
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # 模拟供应商数据
        all_suppliers = [
            {
                'id': 1,
                'name': '新加坡签证中心',
                'address': '新加坡市中心商务区',
                'contact_person': '陈经理',
                'phone': '+65 9123 4567',
                'email': 'chen@sgvisa.com',
                'supplier_type': 'visa',
                'country': '新加坡',
                'region': '市中心',
                'status': 'active',
                'created_at': datetime(2024, 1, 15)
            },
            {
                'id': 2,
                'name': '泰国航空代理',
                'address': '曼谷素万那普机场',
                'contact_person': 'Somchai',
                'phone': '+66 81 234 5678',
                'email': 'somchai@thaiair.com',
                'supplier_type': 'flight',
                'country': '泰国',
                'region': '曼谷',
                'status': 'active',
                'created_at': datetime(2024, 1, 16)
            },
            {
                'id': 3,
                'name': '马来西亚酒店联盟',
                'address': '吉隆坡双子塔附近',
                'contact_person': 'Ahmad',
                'phone': '+60 12 345 6789',
                'email': 'ahmad@myhotel.com',
                'supplier_type': 'hotel',
                'country': '马来西亚',
                'region': '吉隆坡',
                'status': 'pending',
                'created_at': datetime(2024, 1, 17)
            }
        ]
        
        # 应用筛选
        filtered_suppliers = all_suppliers
        
        if status:
            filtered_suppliers = [s for s in filtered_suppliers if s['status'] == status]
        if supplier_type:
            filtered_suppliers = [s for s in filtered_suppliers if s['supplier_type'] == supplier_type]
        if search:
            search_lower = search.lower()
            filtered_suppliers = [s for s in filtered_suppliers 
                                 if search_lower in s['name'].lower() 
                                 or search_lower in s['contact_person'].lower()
                                 or search_lower in s['supplier_type'].lower()]
        
        # 分页
        total = len(filtered_suppliers)
        start = (page - 1) * per_page
        end = start + per_page
        suppliers_page = filtered_suppliers[start:end]
        
        return render_template('staff/staff_suppliers.html',
                             suppliers=suppliers_page,
                             current_page=page,
                             total_pages=(total + per_page - 1) // per_page,
                             total=total,
                             status=status,
                             supplier_type=supplier_type,
                             search=search)
    except Exception as e:
        flash(f'加载供应商列表失败：{str(e)}', 'error')
        return render_template('staff/staff_suppliers.html',
                             suppliers=[],
                             current_page=1,
                             total_pages=1,
                             total=0,
                             status='',
                             supplier_type='',
                             search='')

# ==================== 业务类型管理 ====================
@staff.route('/business_types')
@login_required
@staff_only
def business_types():
    """业务类型列表"""
    try:
        # 获取筛选参数
        category = request.args.get('category', '')
        status = request.args.get('status', '')
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # 模拟业务类型数据
        all_business_types = [
            {
                'id': 1,
                'code': 'VISA_SG',
                'name_cn': '新加坡签证',
                'name_en': 'Singapore Visa',
                'description': '新加坡各类签证服务，包括旅游签证、商务签证、工作签证等',
                'category': 'visa',
                'parent_id': None,
                'level': 1,
                'sort_order': 1,
                'is_active': True,
                'icon': 'fas fa-passport',
                'color': '#007bff',
                'created_at': datetime(2024, 1, 15)
            },
            {
                'id': 2,
                'code': 'VISA_SG_TOURIST',
                'name_cn': '新加坡旅游签证',
                'name_en': 'Singapore Tourist Visa',
                'description': '新加坡旅游签证，适用于短期旅游观光',
                'category': 'visa',
                'parent_id': 1,
                'level': 2,
                'sort_order': 1,
                'is_active': True,
                'icon': 'fas fa-plane',
                'color': '#28a745',
                'created_at': datetime(2024, 1, 15)
            },
            {
                'id': 3,
                'code': 'FLIGHT_INTL',
                'name_cn': '国际机票',
                'name_en': 'International Flight',
                'description': '国际航班机票预订服务',
                'category': 'flight',
                'parent_id': None,
                'level': 1,
                'sort_order': 2,
                'is_active': True,
                'icon': 'fas fa-plane',
                'color': '#ffc107',
                'created_at': datetime(2024, 1, 16)
            },
            {
                'id': 4,
                'code': 'TOUR_PACKAGE',
                'name_cn': '旅游套餐',
                'name_en': 'Tour Package',
                'description': '完整的旅游套餐服务，包括机票、酒店、景点等',
                'category': 'tour',
                'parent_id': None,
                'level': 1,
                'sort_order': 3,
                'is_active': True,
                'icon': 'fas fa-suitcase',
                'color': '#17a2b8',
                'created_at': datetime(2024, 1, 17)
            }
        ]
        
        # 应用筛选
        filtered_types = all_business_types
        
        if category:
            filtered_types = [t for t in filtered_types if t['category'] == category]
        if status:
            if status == 'active':
                filtered_types = [t for t in filtered_types if t['is_active']]
            else:
                filtered_types = [t for t in filtered_types if not t['is_active']]
        if search:
            search_lower = search.lower()
            filtered_types = [t for t in filtered_types 
                             if search_lower in t['name_cn'].lower() 
                             or search_lower in t['name_en'].lower()
                             or search_lower in t['code'].lower()
                             or (t['description'] and search_lower in t['description'].lower())]
        
        # 分页
        total = len(filtered_types)
        start = (page - 1) * per_page
        end = start + per_page
        types_page = filtered_types[start:end]
        
        return render_template('staff/staff_business_types.html',
                             business_types=types_page,
                             current_page=page,
                             total_pages=(total + per_page - 1) // per_page,
                             total=total,
                             category=category,
                             status=status,
                             search=search)
    except Exception as e:
        flash(f'加载业务类型列表失败：{str(e)}', 'error')
        return render_template('staff/staff_business_types.html',
                             business_types=[],
                             current_page=1,
                             total_pages=1,
                             total=0,
                             category='',
                             status='',
                             search='')

# ==================== 工作报告 ====================
@staff.route('/reports')
@login_required
@staff_only
def reports():
    """工作报告"""
    try:
        # 获取报告参数
        report_type = request.args.get('type', 'monthly')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        # 模拟报告数据
        report_data = {
            'total_projects': 15,
            'completed_projects': 8,
            'pending_projects': 5,
            'cancelled_projects': 2,
            'total_revenue': 25000.00,
            'total_cost': 18000.00,
            'total_profit': 7000.00,
            'profit_margin': 28.0
        }
        
        return render_template('staff/staff_reports.html',
                             report_data=report_data,
                             report_type=report_type,
                             start_date=start_date,
                             end_date=end_date)
    except Exception as e:
        flash(f'加载报告失败：{str(e)}', 'error')
        return render_template('staff/staff_reports.html',
                             report_data={},
                             report_type='monthly',
                             start_date='',
                             end_date='')


# ==================== 首页轮播图管理 ====================

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_image_file(filename):
    """检查是否为允许的图片格式"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


@staff.route('/home-banners')
@login_required
@staff_only
def home_banners():
    """首页轮播图管理列表"""
    from ...business.tour.models.Packagemodels import HomeBanner
    
    try:
        banners = HomeBanner.get_all_banners()
        return render_template('staff/home_banners.html', banners=banners)
    except Exception as e:
        flash(f'加载轮播图列表失败：{str(e)}', 'error')
        return render_template('staff/home_banners.html', banners=[])


@staff.route('/home-banners/upload', methods=['POST'])
@login_required
@staff_only
def upload_home_banner():
    """上传首页轮播图"""
    from ...business.tour.models.Packagemodels import HomeBanner
    from ...exts import db
    
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': '请选择图片文件'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'message': '请选择图片文件'}), 400
        
        if not allowed_image_file(file.filename):
            return jsonify({'success': False, 'message': '不支持的图片格式，请上传 PNG、JPG、JPEG、GIF 或 WEBP 格式'}), 400
        
        # 保存图片
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = filename.rsplit('.', 1)[1].lower()
        new_filename = f"banner_{timestamp}.{ext}"
        
        # 创建上传目录
        upload_dir = os.path.join('App_new', 'static', 'uploads', 'banners')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, new_filename)
        file.save(file_path)
        
        # 获取表单数据
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        link_url = request.form.get('link_url', '').strip()
        
        # 获取当前最大排序号
        max_order = db.session.query(db.func.max(HomeBanner.sort_order)).scalar() or 0
        
        # 创建数据库记录
        banner = HomeBanner(
            title=title or None,
            description=description or None,
            image_path=f"uploads/banners/{new_filename}",
            link_url=link_url or None,
            sort_order=max_order + 1,
            is_active=True,
            created_by=current_user.username
        )
        
        db.session.add(banner)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': '轮播图上传成功',
            'banner': {
                'id': banner.id,
                'title': banner.title,
                'image_path': banner.image_path,
                'is_active': banner.is_active
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'上传失败：{str(e)}'}), 500


@staff.route('/home-banners/from-library', methods=['POST'])
@login_required
@staff_only
def banner_from_library():
    """从图片库选择图片作为轮播图"""
    from ...business.tour.models.Packagemodels import HomeBanner, ImageLibrary
    from ...exts import db

    try:
        data = request.get_json()
        image_id = data.get('image_id')
        if not image_id:
            return jsonify({'success': False, 'message': '请选择图片'}), 400

        image = ImageLibrary.query.get(image_id)
        if not image:
            return jsonify({'success': False, 'message': '图片不存在'}), 404

        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        link_url = data.get('link_url', '').strip()

        max_order = db.session.query(db.func.max(HomeBanner.sort_order)).scalar() or 0

        banner = HomeBanner(
            title=title or image.title or None,
            description=description or None,
            image_path=image.image_path,
            link_url=link_url or None,
            sort_order=max_order + 1,
            is_active=True,
            created_by=current_user.username
        )

        db.session.add(banner)
        image.increment_usage()
        db.session.commit()

        return jsonify({'success': True, 'message': '轮播图添加成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'添加失败：{str(e)}'}), 500


@staff.route('/home-banners/<int:banner_id>/delete', methods=['POST'])
@login_required
@staff_only
def delete_home_banner(banner_id):
    """删除首页轮播图"""
    from ...business.tour.models.Packagemodels import HomeBanner
    from ...exts import db
    
    try:
        banner = HomeBanner.query.get_or_404(banner_id)
        
        # 删除图片文件
        if banner.image_path:
            file_path = os.path.join('App_new', 'static', banner.image_path)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    current_app.logger.warning(f"删除图片文件失败: {e}")
        
        db.session.delete(banner)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '轮播图已删除'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败：{str(e)}'}), 500


@staff.route('/home-banners/<int:banner_id>/toggle', methods=['POST'])
@login_required
@staff_only
def toggle_home_banner(banner_id):
    """切换轮播图启用/禁用状态"""
    from ...business.tour.models.Packagemodels import HomeBanner
    from ...exts import db
    
    try:
        banner = HomeBanner.query.get_or_404(banner_id)
        banner.is_active = not banner.is_active
        db.session.commit()
        
        status = '启用' if banner.is_active else '禁用'
        return jsonify({'success': True, 'message': f'轮播图已{status}', 'is_active': banner.is_active})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'操作失败：{str(e)}'}), 500


@staff.route('/home-banners/<int:banner_id>/update', methods=['POST'])
@login_required
@staff_only
def update_home_banner(banner_id):
    """更新轮播图信息"""
    from ...business.tour.models.Packagemodels import HomeBanner
    from ...exts import db
    
    try:
        banner = HomeBanner.query.get_or_404(banner_id)
        
        data = request.get_json()
        if data:
            if 'title' in data:
                banner.title = data['title'].strip() or None
            if 'description' in data:
                banner.description = data['description'].strip() or None
            if 'link_url' in data:
                banner.link_url = data['link_url'].strip() or None
            if 'sort_order' in data:
                banner.sort_order = int(data['sort_order'])
        
        db.session.commit()
        return jsonify({'success': True, 'message': '更新成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'}), 500


@staff.route('/home-banners/reorder', methods=['POST'])
@login_required
@staff_only
def reorder_home_banners():
    """重新排序轮播图"""
    from ...business.tour.models.Packagemodels import HomeBanner
    from ...exts import db
    
    try:
        data = request.get_json()
        order_list = data.get('order', [])  # [banner_id, banner_id, ...]
        
        for index, banner_id in enumerate(order_list):
            banner = HomeBanner.query.get(banner_id)
            if banner:
                banner.sort_order = index
        
        db.session.commit()
        return jsonify({'success': True, 'message': '排序已更新'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'排序失败：{str(e)}'}), 500


# ==================== 图片库管理 ====================
@staff.route('/image-library')
@login_required
@staff_only
def image_library():
    """图片库管理页面"""
    from ...business.tour.models.Packagemodels import ImageLibrary
    from ...exts import db
    from collections import Counter

    try:
        # 获取查询参数
        category = request.args.get('category', '')
        search = request.args.get('search', '')
        tag_filter = request.args.get('tag', '')

        # 构建查询
        query = ImageLibrary.query
        if category:
            query = query.filter_by(category=category)
        if search:
            query = query.filter(
                ImageLibrary.title.contains(search) |
                ImageLibrary.tags.contains(search)
            )
        if tag_filter:
            query = query.filter(ImageLibrary.tags.contains(tag_filter))

        images = query.order_by(ImageLibrary.created_at.desc()).all()

        # 检测原图文件是否存在
        import os
        static_folder = current_app.static_folder
        for img in images:
            file_path = os.path.join(static_folder, img.image_path.replace('/', os.sep))
            img.file_exists = os.path.isfile(file_path)

        # 获取分类列表
        categories = db.session.query(ImageLibrary.category).distinct().all()
        categories = [c[0] for c in categories if c[0]]

        # 统计所有标签及其使用次数
        all_tags = []
        all_images = ImageLibrary.query.all()
        for img in all_images:
            if img.tags:
                # 分割标签（支持中英文逗号）
                tags = [t.strip() for t in img.tags.replace('，', ',').split(',') if t.strip()]
                all_tags.extend(tags)

        # 统计标签出现次数，按次数降序排列
        tag_counts = Counter(all_tags)
        tags_with_counts = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))

        return render_template('staff/image_library.html',
                             images=images,
                             categories=categories,
                             tags_with_counts=tags_with_counts,
                             current_category=category,
                             current_search=search,
                             current_tag=tag_filter)
    except Exception as e:
        flash(f'加载图片库失败：{str(e)}', 'error')
        return render_template('staff/image_library.html', images=[], categories=[], tags_with_counts=[], current_category='', current_search='', current_tag='')


@staff.route('/image-library/upload', methods=['POST'])
@login_required
@staff_only
def upload_image_library():
    """上传图片到图片库（自动压缩）"""
    from ...business.tour.models.Packagemodels import ImageLibrary
    from ...exts import db

    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': '请选择图片文件'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'message': '请选择图片文件'}), 400

        if not allowed_file(file.filename, {'png', 'jpg', 'jpeg', 'gif', 'webp'}):
            return jsonify({'success': False, 'message': '不支持的图片格式'}), 400

        # 保存原始图片
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        new_filename = f"library_{timestamp}{ext}"

        upload_dir = os.path.join('App_new', 'static', 'uploads', 'image_library')
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, new_filename)
        file.save(file_path)

        # 压缩和调整图片尺寸（优化网页加载速度）
        compress_result = compress_and_resize_image(
            file_path,
            max_size=1200,  # 最大1200像素，适合网页显示
            quality=80,     # JPEG质量80%
            generate_thumbnail=True,
            thumb_size=300  # 缩略图300px足够
        )

        # 获取压缩后的信息
        width = compress_result.get('width')
        height = compress_result.get('height')
        file_size = compress_result.get('file_size')
        final_path = compress_result.get('new_path', file_path)

        # 更新文件名（可能已转换为jpg）
        final_filename = os.path.basename(final_path)

        # 获取表单数据
        title = request.form.get('title', '').strip()
        tags = request.form.get('tags', '').strip()
        category = request.form.get('category', 'other').strip()

        # 创建数据库记录
        image = ImageLibrary(
            title=title or None,
            image_path=f"uploads/image_library/{final_filename}",
            tags=tags or None,
            category=category or 'other',
            file_size=file_size,
            width=width,
            height=height,
            is_active=True,
            created_by=current_user.username
        )
        
        db.session.add(image)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '图片上传成功',
            'image': {
                'id': image.id,
                'title': image.title,
                'image_path': image.image_path,
                'usage_count': image.usage_count
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"上传图片失败: {e}")
        return jsonify({'success': False, 'message': f'上传失败：{str(e)}'}), 500


@staff.route('/image-library/<int:image_id>/delete', methods=['POST'])
@login_required
@staff_only
def delete_image_library(image_id):
    """删除图片库中的图片"""
    from ...business.tour.models.Packagemodels import ImageLibrary
    from ...exts import db
    
    try:
        image = ImageLibrary.query.get_or_404(image_id)
        
        # 检查使用次数
        if image.usage_count > 0:
            return jsonify({
                'success': False, 
                'message': f'此图片正在被 {image.usage_count} 个产品使用，无法删除'
            }), 400
        
        # 删除图片文件
        if image.image_path:
            file_path = os.path.join('App_new', 'static', image.image_path)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    current_app.logger.warning(f"删除图片文件失败: {e}")
        
        db.session.delete(image)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '图片已删除'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败：{str(e)}'}), 500


@staff.route('/image-library/batch-delete', methods=['POST'])
@login_required
@staff_only
def batch_delete_image_library():
    """批量删除图片库中的图片"""
    from ...business.tour.models.Packagemodels import ImageLibrary
    from ...exts import db
    
    try:
        data = request.get_json()
        image_ids = data.get('image_ids', [])
        
        if not image_ids:
            return jsonify({'success': False, 'message': '请选择要删除的图片'}), 400
        
        deleted_count = 0
        skipped_count = 0
        skipped_reasons = []
        
        for image_id in image_ids:
            image = ImageLibrary.query.get(image_id)
            if not image:
                skipped_count += 1
                continue
            
            # 检查使用次数
            if image.usage_count > 0:
                skipped_count += 1
                skipped_reasons.append(f'图片ID {image_id} 正在被使用')
                continue
            
            # 删除图片文件
            if image.image_path:
                file_path = os.path.join('App_new', 'static', image.image_path)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        current_app.logger.warning(f"删除图片文件失败: {e}")
            
            db.session.delete(image)
            deleted_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'成功删除 {deleted_count} 张图片',
            'deleted_count': deleted_count,
            'skipped_count': skipped_count
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"批量删除图片失败: {e}")
        return jsonify({'success': False, 'message': f'批量删除失败：{str(e)}'}), 500


@staff.route('/image-library/clean-missing', methods=['POST'])
@login_required
@staff_only
def clean_missing_images():
    """清理文件丢失的图片记录"""
    from ...business.tour.models.Packagemodels import ImageLibrary
    from ...exts import db

    try:
        images = ImageLibrary.query.all()
        static_folder = current_app.static_folder
        deleted_count = 0

        for img in images:
            file_path = os.path.join(static_folder, img.image_path.replace('/', os.sep))
            if not os.path.isfile(file_path):
                # 同时删除缩略图（如果存在）
                thumb_path = img.image_path.replace(
                    'uploads/image_library/',
                    'uploads/image_library/thumbnails/thumb_'
                )
                thumb_full = os.path.join(static_folder, thumb_path.replace('/', os.sep))
                if os.path.isfile(thumb_full):
                    try:
                        os.remove(thumb_full)
                    except Exception:
                        pass
                db.session.delete(img)
                deleted_count += 1

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'已清理 {deleted_count} 条丢失记录',
            'deleted_count': deleted_count
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"清理丢失图片失败: {e}")
        return jsonify({'success': False, 'message': f'清理失败：{str(e)}'}), 500


@staff.route('/image-library/batch-download', methods=['POST'])
@login_required
@staff_only
def batch_download_image_library():
    """批量下载图片库中的图片（打包为ZIP，含Excel配置文件）"""
    from ...business.tour.models.Packagemodels import ImageLibrary
    import zipfile
    import io

    try:
        data = request.get_json()
        if not data or 'image_ids' not in data:
            return jsonify({'success': False, 'message': '请提供图片ID列表'}), 400

        image_ids = data['image_ids']
        if not image_ids:
            return jsonify({'success': False, 'message': '请选择要下载的图片'}), 400

        # 查询图片
        images = ImageLibrary.query.filter(ImageLibrary.id.in_(image_ids)).all()
        if not images:
            return jsonify({'success': False, 'message': '未找到指定的图片'}), 404

        # 创建内存中的ZIP文件
        memory_file = io.BytesIO()

        # 用于记录图片信息，生成Excel
        image_data_for_excel = []
        filename_mapping = {}  # 原始路径 -> ZIP中的文件名

        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for image in images:
                # 构建文件路径
                file_path = os.path.join('App_new', 'static', image.image_path)
                if os.path.exists(file_path):
                    # 使用原始文件名（保持一致性，方便重新导入时匹配）
                    original_filename = os.path.basename(image.image_path)
                    zip_filename = original_filename

                    # 确保文件名唯一
                    counter = 1
                    base_name, ext = os.path.splitext(original_filename)
                    while zip_filename in [info.filename for info in zf.filelist]:
                        zip_filename = f"{base_name}_{counter}{ext}"
                        counter += 1

                    zf.write(file_path, f"images/{zip_filename}")
                    filename_mapping[image.id] = zip_filename

                    # 记录图片信息
                    image_data_for_excel.append({
                        '文件名': zip_filename,
                        '标题': image.title or '',
                        '标签': image.tags or '',
                        '分类': image.category or 'other',
                    })

            # 生成 Excel 配置文件
            try:
                import pandas as pd

                # 创建数据表
                df = pd.DataFrame(image_data_for_excel)

                # 创建说明表
                instructions = [
                    ['图片库配置文件使用说明'],
                    [''],
                    ['此文件包含下载图片的元数据信息，您可以：'],
                    ['1. 修改标题、标签、分类后，与图片一起重新上传'],
                    ['2. 系统会根据文件名自动匹配并更新图片信息'],
                    [''],
                    ['字段说明：'],
                    ['- 文件名：图片文件名（请勿修改，用于匹配）'],
                    ['- 标题：图片的标题或描述'],
                    ['- 标签：多个标签用英文逗号分隔，例如：风景,旅游,海滩'],
                    ['- 分类：可选值 tour(旅游产品), destination(目的地), product(产品相关), other(其他)'],
                    [''],
                    ['重新导入步骤：'],
                    ['1. 修改本文件中的标题、标签、分类'],
                    ['2. 在图片库页面点击"批量导入"'],
                    ['3. 上传此 Excel 文件'],
                    ['4. 选择 images 文件夹中的图片'],
                    ['5. 点击上传，系统会自动匹配并应用配置'],
                ]
                df_instructions = pd.DataFrame(instructions)

                # 写入 Excel 到内存
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='图片配置', index=False)
                    df_instructions.to_excel(writer, sheet_name='使用说明', index=False, header=False)

                excel_buffer.seek(0)
                zf.writestr('图片配置.xlsx', excel_buffer.read())

            except ImportError:
                # 如果没有 pandas/openpyxl，使用 CSV 作为备选
                import csv
                csv_buffer = io.StringIO()
                writer = csv.DictWriter(csv_buffer, fieldnames=['文件名', '标题', '标签', '分类'])
                writer.writeheader()
                writer.writerows(image_data_for_excel)
                zf.writestr('图片配置.csv', csv_buffer.getvalue().encode('utf-8-sig'))

        memory_file.seek(0)

        # 返回ZIP文件
        from flask import send_file
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'图片库_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        )

    except Exception as e:
        current_app.logger.error(f"批量下载图片失败: {e}")
        return jsonify({'success': False, 'message': f'批量下载失败：{str(e)}'}), 500


@staff.route('/image-library/<int:image_id>/update', methods=['POST'])
@login_required
@staff_only
def update_image_library(image_id):
    """更新图片库信息"""
    from ...business.tour.models.Packagemodels import ImageLibrary
    from ...exts import db
    
    try:
        image = ImageLibrary.query.get_or_404(image_id)
        
        title = request.form.get('title', '').strip()
        tags = request.form.get('tags', '').strip()
        category = request.form.get('category', '').strip()
        
        if title:
            image.title = title
        if tags:
            image.tags = tags
        if category:
            image.category = category
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': '更新成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'}), 500


@staff.route('/image-library/batch-update', methods=['POST'])
@login_required
@staff_only
def batch_update_image_library():
    """批量更新图片库标签（根据文件名匹配）"""
    from ...business.tour.models.Packagemodels import ImageLibrary
    from ...exts import db

    try:
        data = request.get_json()
        if not data or 'updates' not in data:
            return jsonify({'success': False, 'message': '请提供更新数据'}), 400

        updates = data['updates']
        if not updates:
            return jsonify({'success': False, 'message': '没有可更新的数据'}), 400

        updated_count = 0
        not_found_count = 0
        not_found_files = []

        for item in updates:
            filename = item.get('文件名', '').strip()
            if not filename:
                continue

            # 根据文件名查找图片（支持完整路径或仅文件名）
            # 尝试直接匹配 image_path 的文件名部分
            image = ImageLibrary.query.filter(
                ImageLibrary.image_path.endswith(filename)
            ).first()

            if image:
                # 更新字段
                if item.get('标题'):
                    image.title = str(item['标题']).strip()
                if item.get('标签'):
                    # 标准化标签（将中文逗号转为英文逗号）
                    tags = str(item['标签']).strip().replace('，', ',')
                    image.tags = tags
                if item.get('分类'):
                    image.category = str(item['分类']).strip()

                updated_count += 1
            else:
                not_found_count += 1
                if len(not_found_files) < 5:
                    not_found_files.append(filename)

        db.session.commit()

        # 构建返回消息
        message = f'成功更新 {updated_count} 张图片'
        if not_found_count > 0:
            message += f'，{not_found_count} 张未找到匹配'
            if not_found_files:
                message += f'（如：{", ".join(not_found_files[:3])}）'

        return jsonify({
            'success': True,
            'message': message,
            'updated_count': updated_count,
            'not_found_count': not_found_count
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"批量更新图片失败: {e}")
        return jsonify({'success': False, 'message': f'批量更新失败：{str(e)}'}), 500


@staff.route('/image-library/batch-upload', methods=['POST'])
@login_required
@staff_only
def batch_upload_image_library():
    """批量上传图片到图片库（自动压缩，支持Excel配置）"""
    from ...business.tour.models.Packagemodels import ImageLibrary
    from ...exts import db
    import random
    import string

    try:
        if 'images' not in request.files:
            return jsonify({'success': False, 'message': '请选择图片文件'}), 400

        files = request.files.getlist('images')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'message': '请选择至少一张图片'}), 400

        # 获取批量设置的标签和分类（默认值）
        default_tags = request.form.get('default_tags', '').strip()
        default_category = request.form.get('default_category', 'other').strip()

        # 解析 Excel 配置文件（如果有）
        excel_config = {}
        excel_file = request.files.get('excel_config')
        if excel_file and excel_file.filename:
            try:
                import pandas as pd
                # 读取 Excel 文件
                df = pd.read_excel(excel_file, sheet_name=0)
                current_app.logger.info(f"Excel 列名: {list(df.columns)}")

                # 标准化列名
                df.columns = df.columns.str.strip()

                # 构建文件名到配置的映射
                for _, row in df.iterrows():
                    filename = str(row.get('文件名', '')).strip()
                    if filename:
                        tags_value = row.get('标签', '')
                        excel_config[filename] = {
                            'title': str(row.get('标题', '')).strip() if pd.notna(row.get('标题')) else '',
                            'tags': str(tags_value).strip() if pd.notna(tags_value) else '',
                            'category': str(row.get('分类', '')).strip() if pd.notna(row.get('分类')) else ''
                        }

                current_app.logger.info(f"Excel 配置已加载，共 {len(excel_config)} 条记录")
                # 打印前3条记录用于调试
                for i, (fn, cfg) in enumerate(list(excel_config.items())[:3]):
                    current_app.logger.info(f"  Excel记录{i+1}: 文件名={fn}, 标签={cfg.get('tags')}")

            except Exception as e:
                import traceback
                current_app.logger.warning(f"解析 Excel 配置失败: {e}")
                current_app.logger.warning(traceback.format_exc())

        upload_dir = os.path.join('App_new', 'static', 'uploads', 'image_library')
        os.makedirs(upload_dir, exist_ok=True)

        success_count = 0
        failed_files = []
        matched_count = 0  # Excel 配置匹配计数
        total_original_size = 0
        total_compressed_size = 0

        for file in files:
            if not file.filename:
                continue

            try:
                if not allowed_file(file.filename, {'png', 'jpg', 'jpeg', 'gif', 'webp'}):
                    failed_files.append(f"{file.filename} (格式不支持)")
                    continue

                # 保存原始图片
                original_filename = file.filename  # 保留原始文件名用于匹配
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                name, ext = os.path.splitext(filename)
                new_filename = f"library_{timestamp}_{random_suffix}{ext}"

                file_path = os.path.join(upload_dir, new_filename)
                file.save(file_path)

                # 记录原始大小
                original_size = os.path.getsize(file_path)
                total_original_size += original_size

                # 压缩和调整图片尺寸（优化网页加载速度）
                compress_result = compress_and_resize_image(
                    file_path,
                    max_size=1200,  # 降低至1200px，适合网页显示
                    quality=80,     # 略微降低质量，减小文件体积
                    generate_thumbnail=True,
                    thumb_size=300  # 缩略图300px足够
                )

                # 获取压缩后的信息
                width = compress_result.get('width')
                height = compress_result.get('height')
                file_size = compress_result.get('file_size', original_size)
                final_path = compress_result.get('new_path', file_path)
                total_compressed_size += file_size

                # 更新文件名（可能已转换为jpg）
                final_filename = os.path.basename(final_path)

                # 从 Excel 配置获取元数据，或使用默认值
                # 尝试多种方式匹配文件名
                config = excel_config.get(original_filename, {})

                # 如果直接匹配失败，尝试只用文件名部分匹配（去掉路径）
                if not config:
                    import os as os_module
                    base_filename = os_module.path.basename(original_filename)
                    config = excel_config.get(base_filename, {})

                # 如果还是失败，尝试不区分大小写匹配
                if not config:
                    for excel_filename, excel_data in excel_config.items():
                        if excel_filename.lower() == original_filename.lower() or \
                           excel_filename.lower() == base_filename.lower():
                            config = excel_data
                            break

                if config:
                    matched_count += 1
                    current_app.logger.info(f"Excel匹配成功: {original_filename} -> 标签: {config.get('tags')}")
                else:
                    current_app.logger.info(f"Excel未匹配: {original_filename}, Excel中的文件名: {list(excel_config.keys())[:3]}")

                # 标题：优先使用Excel配置，否则使用文件名
                title = config.get('title') or name
                # 标签：优先使用Excel配置，否则使用默认值
                tags = config.get('tags') or default_tags
                # 分类：优先使用Excel配置，否则使用默认值
                category = config.get('category') or default_category or 'other'

                # 标准化标签（将中文逗号转为英文逗号）
                if tags:
                    tags = tags.replace('，', ',')

                # 验证文件确实存在后再创建数据库记录
                if not os.path.exists(final_path):
                    failed_files.append(f"{file.filename} (压缩后文件不存在)")
                    current_app.logger.error(f"文件不存在: {final_path}")
                    continue

                # 创建数据库记录
                image = ImageLibrary(
                    title=title,
                    image_path=f"uploads/image_library/{final_filename}",
                    tags=tags or None,
                    category=category,
                    file_size=file_size,
                    width=width,
                    height=height,
                    is_active=True,
                    created_by=current_user.username
                )

                db.session.add(image)
                success_count += 1

            except Exception as e:
                current_app.logger.error(f"Error uploading {file.filename}: {e}")
                failed_files.append(f"{file.filename} ({str(e)})")
                continue

        db.session.commit()

        # 构建返回消息（包含压缩统计和Excel匹配统计）
        message = f'成功上传 {success_count} 张图片'
        if excel_config:
            message += f'（{matched_count} 张匹配Excel配置）'
        if total_original_size > 0 and total_compressed_size > 0:
            saved_size = total_original_size - total_compressed_size
            saved_percent = (saved_size / total_original_size) * 100
            message += f'，已压缩节省 {saved_size/1024/1024:.1f}MB'

        if failed_files:
            message += f'，{len(failed_files)} 张失败：' + ', '.join(failed_files[:5])
            if len(failed_files) > 5:
                message += f' 等共 {len(failed_files)} 张'

        return jsonify({
            'success': True,
            'message': message,
            'success_count': success_count,
            'failed_count': len(failed_files),
            'failed_files': failed_files,
            'excel_matched_count': matched_count,
            'compression_stats': {
                'original_size': total_original_size,
                'compressed_size': total_compressed_size,
                'saved_size': total_original_size - total_compressed_size
            }
        })
        
    except Exception as e:
        if 'db' in locals():
            db.session.rollback()
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        current_app.logger.error(f"批量上传图片失败: {error_msg}\n{error_trace}")
        # 确保返回JSON格式
        try:
            return jsonify({
                'success': False, 
                'message': f'批量上传失败：{error_msg}',
                'error_type': type(e).__name__
            }), 500
        except:
            # 如果连jsonify都失败，返回最简单的JSON字符串
            from flask import Response
            return Response(
                f'{{"success": false, "message": "批量上传失败：{error_msg}"}}',
                mimetype='application/json',
                status=500
            )


@staff.route('/image-library/list', methods=['GET'])
@login_required
@staff_only
def list_image_library():
    """获取图片库列表（API）"""
    from ...business.tour.models.Packagemodels import ImageLibrary
    
    try:
        category = request.args.get('category', '')
        search = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        query = ImageLibrary.query.filter_by(is_active=True)
        
        if category:
            query = query.filter_by(category=category)
        if search:
            query = query.filter(
                ImageLibrary.title.contains(search) | 
                ImageLibrary.tags.contains(search)
            )
        
        pagination = query.order_by(ImageLibrary.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        images = [{
            'id': img.id,
            'title': img.title,
            'image_path': img.image_path,
            'tags': img.tags,
            'category': img.category,
            'usage_count': img.usage_count or 0,
            'width': img.width,
            'height': img.height
        } for img in pagination.items]
        
        return jsonify({
            'success': True,
            'images': images,
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@staff.route('/image-library/cleanup', methods=['POST'])
@login_required
@staff_only
def cleanup_image_library():
    """清理无效的图片记录（原图文件不存在的记录）"""
    from ...business.tour.models.Packagemodels import ImageLibrary
    from ...exts import db

    try:
        images = ImageLibrary.query.all()
        deleted_count = 0
        deleted_ids = []

        for image in images:
            if image.image_path:
                # 检查原图是否存在
                full_path = os.path.join(current_app.static_folder, image.image_path)
                if not os.path.exists(full_path):
                    # 删除缩略图（如果存在）
                    if image.thumbnail_path:
                        thumb_full_path = os.path.join(current_app.static_folder, image.thumbnail_path)
                        if os.path.exists(thumb_full_path):
                            try:
                                os.remove(thumb_full_path)
                            except:
                                pass

                    deleted_ids.append(image.id)
                    db.session.delete(image)
                    deleted_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'已清理 {deleted_count} 条无效记录',
            'deleted_count': deleted_count,
            'deleted_ids': deleted_ids
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== 客户咨询管理 ====================

@staff.route('/inquiries')
@login_required
@staff_only
def inquiry_list():
    """客户咨询列表"""
    from ...shared.models.contact_inquiry import ContactInquiry
    from ...exts import db

    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = ContactInquiry.query

    if status_filter:
        query = query.filter(ContactInquiry.status == status_filter)

    query = query.order_by(ContactInquiry.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # 统计各状态数量
    stats = {
        'total': ContactInquiry.query.count(),
        'new': ContactInquiry.query.filter_by(status='new').count(),
        'read': ContactInquiry.query.filter_by(status='read').count(),
        'replied': ContactInquiry.query.filter_by(status='replied').count(),
        'closed': ContactInquiry.query.filter_by(status='closed').count(),
    }

    return render_template('staff/inquiries/inquiry_list.html',
                           inquiries=pagination.items,
                           pagination=pagination,
                           status_filter=status_filter,
                           stats=stats)


@staff.route('/inquiries/<int:inquiry_id>/status', methods=['POST'])
@login_required
@staff_only
def inquiry_update_status(inquiry_id):
    """更新咨询状态"""
    from ...shared.models.contact_inquiry import ContactInquiry
    from ...exts import db

    inquiry = ContactInquiry.query.get_or_404(inquiry_id)
    data = request.get_json()
    new_status = data.get('status')

    if new_status not in ('new', 'read', 'replied', 'closed'):
        return jsonify({'success': False, 'message': '无效的状态'}), 400

    inquiry.status = new_status
    if new_status == 'read' and not inquiry.read_at:
        inquiry.read_at = datetime.utcnow()
    elif new_status == 'replied' and not inquiry.replied_at:
        inquiry.replied_at = datetime.utcnow()

    db.session.commit()
    return jsonify({'success': True, 'message': '状态已更新'})


@staff.route('/inquiries/<int:inquiry_id>/notes', methods=['POST'])
@login_required
@staff_only
def inquiry_update_notes(inquiry_id):
    """更新内部备注"""
    from ...shared.models.contact_inquiry import ContactInquiry
    from ...exts import db

    inquiry = ContactInquiry.query.get_or_404(inquiry_id)
    data = request.get_json()
    inquiry.staff_notes = data.get('notes', '')
    db.session.commit()
    return jsonify({'success': True, 'message': '备注已保存'})


@staff.route('/inquiries/<int:inquiry_id>/delete', methods=['POST'])
@login_required
@staff_only
def inquiry_delete(inquiry_id):
    """删除咨询记录"""
    from ...shared.models.contact_inquiry import ContactInquiry
    from ...exts import db

    inquiry = ContactInquiry.query.get_or_404(inquiry_id)
    db.session.delete(inquiry)
    db.session.commit()
    return jsonify({'success': True, 'message': '已删除'})


# ==================== 会员订单管理 ====================

@staff.route('/member-orders')
@login_required
@staff_only
def member_order_list():
    """会员订单列表"""
    from ...member.models.order import Order, OrderStatus, ServiceType
    from ...exts import db

    status_filter = request.args.get('status', '')
    service_filter = request.args.get('service_type', '')
    keyword = request.args.get('keyword', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Order.query

    if status_filter:
        query = query.filter(Order.status == status_filter)
    if service_filter:
        query = query.filter(Order.service_type == service_filter)
    if keyword:
        query = query.filter(
            db.or_(
                Order.order_number.ilike(f'%{keyword}%'),
                Order.customer_name.ilike(f'%{keyword}%'),
                Order.customer_phone.ilike(f'%{keyword}%'),
                Order.service_name.ilike(f'%{keyword}%'),
            )
        )

    query = query.order_by(Order.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # 统计各状态数量
    stats = {
        'total': Order.query.count(),
        'pending': Order.query.filter_by(status=OrderStatus.PENDING.value).count(),
        'confirmed': Order.query.filter_by(status=OrderStatus.CONFIRMED.value).count(),
        'in_progress': Order.query.filter_by(status=OrderStatus.IN_PROGRESS.value).count(),
        'completed': Order.query.filter_by(status=OrderStatus.COMPLETED.value).count(),
        'cancelled': Order.query.filter_by(status=OrderStatus.CANCELLED.value).count(),
    }

    # 服务类型列表
    service_type_labels = {
        'visa': '签证服务',
        'flight': '机票预订',
        'hotel': '酒店预订',
        'tour': '旅游套餐',
        'insurance': '旅游保险',
        'transfer': '接送服务',
    }

    return render_template('staff/member_orders/order_list.html',
                           orders=pagination.items,
                           pagination=pagination,
                           status_filter=status_filter,
                           service_filter=service_filter,
                           keyword=keyword,
                           stats=stats,
                           service_type_labels=service_type_labels)


@staff.route('/member-orders/<int:order_id>')
@login_required
@staff_only
def member_order_detail(order_id):
    """会员订单详情"""
    from ...member.models.order import Order

    order = Order.query.get_or_404(order_id)

    # 标记为已读（pending → confirmed 提示员工处理）
    return render_template('staff/member_orders/order_detail.html', order=order)


@staff.route('/member-orders/<int:order_id>/status', methods=['POST'])
@login_required
@staff_only
def member_order_update_status(order_id):
    """更新订单状态"""
    from ...member.models.order import Order, OrderStatus
    from ...exts import db

    order = Order.query.get_or_404(order_id)
    data = request.get_json()
    new_status = data.get('status')

    valid_statuses = [s.value for s in OrderStatus]
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'message': '无效的状态'}), 400

    order.status = new_status
    now = datetime.utcnow()
    if new_status == OrderStatus.CONFIRMED.value and not order.confirmed_at:
        order.confirmed_at = now
    elif new_status == OrderStatus.COMPLETED.value and not order.completed_at:
        order.completed_at = now
    elif new_status == OrderStatus.CANCELLED.value and not order.cancelled_at:
        order.cancelled_at = now

    db.session.commit()
    return jsonify({'success': True, 'message': '状态已更新'})


@staff.route('/member-orders/<int:order_id>/price', methods=['POST'])
@login_required
@staff_only
def member_order_update_price(order_id):
    """更新订单价格"""
    from ...member.models.order import Order
    from ...exts import db
    from decimal import Decimal

    order = Order.query.get_or_404(order_id)
    data = request.get_json()

    try:
        base_price = Decimal(str(data.get('base_price', order.base_price)))
        additional_fees = Decimal(str(data.get('additional_fees', order.additional_fees or 0)))
        discount_amount = Decimal(str(data.get('discount_amount', order.discount_amount or 0)))

        order.base_price = base_price
        order.additional_fees = additional_fees
        order.discount_amount = discount_amount
        order.total_amount = base_price + additional_fees - discount_amount

        db.session.commit()
        return jsonify({'success': True, 'message': '价格已更新', 'total': float(order.total_amount)})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@staff.route('/member-orders/<int:order_id>/notes', methods=['POST'])
@login_required
@staff_only
def member_order_update_notes(order_id):
    """更新订单备注"""
    from ...member.models.order import Order
    from ...exts import db

    order = Order.query.get_or_404(order_id)
    data = request.get_json()
    order.notes = data.get('notes', '')
    db.session.commit()
    return jsonify({'success': True, 'message': '备注已保存'})
