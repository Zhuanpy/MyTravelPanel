"""
订单管理路由
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import current_user
from flask_wtf.csrf import generate_csrf
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import os
from werkzeug.utils import secure_filename

from ...utils.decorators import member_only, login_required
from ...exts import db
from ..models.order import Order, OrderItem, OrderDocument, Payment, ServiceTemplate, OrderStatus, ServiceType

# 创建订单蓝图
orders_bp = Blueprint('orders', __name__, url_prefix='/member/orders')


def is_mobile_device():
    """检测是否为移动设备"""
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone']
    return any(keyword in user_agent for keyword in mobile_keywords)


@orders_bp.route('/')
@orders_bp.route('/list')
@login_required
@member_only
def list():
    """订单列表"""
    # 移动设备跳转到手机版
    if is_mobile_device():
        return redirect(url_for('mobile.orders_list',
                                status=request.args.get('status', ''),
                                page=request.args.get('page', 1, type=int)))

    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # 获取筛选参数
        status = request.args.get('status', '')
        service_type = request.args.get('service_type', '')
        date_range = request.args.get('date_range', '')

        # 查询当前用户的订单
        query = Order.query.filter_by(user_id=current_user.id)

        if status:
            query = query.filter_by(status=status)

        if service_type:
            query = query.filter_by(service_type=service_type)

        if date_range:
            from datetime import datetime, timedelta
            now = datetime.now()
            if date_range == 'today':
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif date_range == 'week':
                start = now - timedelta(days=7)
            elif date_range == 'month':
                start = now - timedelta(days=30)
            elif date_range == 'quarter':
                start = now - timedelta(days=90)
            else:
                start = None
            if start:
                query = query.filter(Order.created_at >= start)

        # 按创建时间倒序排列
        query = query.order_by(Order.created_at.desc())

        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        orders = pagination.items

        return render_template('member/orders.html',
                             orders=orders,
                             pagination=pagination,
                             current_status=status,
                             current_service_type=service_type,
                             current_date_range=date_range)
    except Exception as e:
        current_app.logger.error(f'加载订单列表失败: {str(e)}')
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash(f'加载订单列表失败: {str(e)}', 'error')
        return render_template('member/orders.html',
                             orders=[], 
                             pagination=None, 
                             current_status='')


@orders_bp.route('/apply/<service_type>')
@login_required
@member_only
def apply_service(service_type):
    """申请服务页面"""
    try:
        # 暂时使用模拟数据（等待数据库表创建后再使用实际查询）
        service_templates = {
            'visa': {
                'service_type': 'visa',
                'service_name': '签证办理服务',
                'description': '为您提供专业的签证办理服务',
                'base_price': Decimal('50.00'),
                'currency': 'SGD',
                'processing_time': '3-5个工作日',
                'requirements': '护照有效期至少6个月，提供完整材料',
                'required_documents': ['护照原件', '2张2寸白底彩色照片', '签证申请表', '往返机票预订单', '酒店预订单']
            },
            'flight': {
                'service_type': 'flight',
                'service_name': '机票预订服务',
                'description': '提供全球航线机票预订服务',
                'base_price': Decimal('0.00'),
                'currency': 'SGD',
                'processing_time': '即时出票',
                'requirements': '提供准确的乘客信息和航班需求',
                'required_documents': ['护照信息', '联系方式']
            },
            'hotel': {
                'service_type': 'hotel',
                'service_name': '酒店预订服务',
                'description': '提供全球酒店预订服务',
                'base_price': Decimal('0.00'),
                'currency': 'SGD',
                'processing_time': '即时确认',
                'requirements': '提供入住日期和要求',
                'required_documents': ['入住人信息', '特殊要求']
            },
            'tour': {
                'service_type': 'tour',
                'service_name': '旅游套餐服务',
                'description': '精心设计的旅游线路',
                'base_price': Decimal('999.00'),
                'currency': 'SGD',
                'processing_time': '提前3天预订',
                'requirements': '至少提前3天预订，提供完整的旅客信息',
                'required_documents': ['护照信息', '紧急联系人', '特殊需求说明']
            }
        }
        
        # 获取服务模板（模拟数据）
        class ServiceMock:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        service_data = service_templates.get(service_type)
        if not service_data:
            flash('服务不存在或已停用', 'error')
            return redirect(url_for('member.services'))
        
        service_template = ServiceMock(service_data)
        
        # 获取用户信息
        user_profile = current_user.profile
        
        return render_template('member/order/apply_service.html',
                             service=service_template,
                             user_profile=user_profile)
    except Exception as e:
        current_app.logger.error(f'加载服务申请页面失败: {str(e)}')
        flash('加载页面失败，请稍后重试', 'error')
        return redirect(url_for('member.services'))


@orders_bp.route('/create', methods=['POST'])
@login_required
@member_only
def create_order():
    """创建订单"""
    try:
        # 调试：打印表单数据
        current_app.logger.info(f'Form data: {request.form.to_dict()}')
        current_app.logger.info(f'CSRF token in form: {request.form.get("csrf_token")}')
        
        # 获取表单数据
        service_type = request.form.get('service_type')
        service_name = request.form.get('service_name')
        description = request.form.get('description')
        base_price = Decimal(request.form.get('base_price', 0))
        
        # 客户信息
        customer_name = request.form.get('customer_name')
        customer_email = request.form.get('customer_email')
        customer_phone = request.form.get('customer_phone')
        customer_address = request.form.get('customer_address')
        
        # 特殊要求
        special_requirements = request.form.get('special_requirements')
        notes = request.form.get('notes')
        
        # 生成订单号
        order_number = f"ORD{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
        
        # 创建订单
        order = Order(
            order_number=order_number,
            user_id=current_user.id,
            service_type=service_type,
            service_name=service_name,
            description=description,
            base_price=base_price,
            total_amount=base_price,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            customer_address=customer_address,
            special_requirements=special_requirements,
            notes=notes,
            status=OrderStatus.DRAFT.value
        )
        
        db.session.add(order)
        db.session.flush()  # 获取订单ID
        
        # 处理订单项目
        item_names = request.form.getlist('item_name[]')
        item_descriptions = request.form.getlist('item_description[]')
        item_quantities = request.form.getlist('item_quantity[]')
        item_prices = request.form.getlist('item_price[]')
        
        for i, item_name in enumerate(item_names):
            if item_name.strip():
                quantity = int(item_quantities[i]) if item_quantities[i] else 1
                unit_price = Decimal(item_prices[i]) if item_prices[i] else 0
                
                order_item = OrderItem(
                    order_id=order.id,
                    item_name=item_name,
                    item_description=item_descriptions[i] if i < len(item_descriptions) else '',
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=quantity * unit_price
                )
                db.session.add(order_item)
        
        # 处理文件上传
        uploaded_files = request.files.getlist('documents[]')
        for file in uploaded_files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                if filename:
                    # 创建上传目录
                    upload_dir = os.path.join(current_app.static_folder, 'uploads', 'orders', str(order.id))
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # 保存文件
                    file_path = os.path.join(upload_dir, filename)
                    file.save(file_path)
                    
                    # 创建文档记录
                    document = OrderDocument(
                        order_id=order.id,
                        document_name=filename,
                        document_type='user_upload',
                        file_path=file_path,
                        file_size=os.path.getsize(file_path),
                        mime_type=file.content_type
                    )
                    db.session.add(document)
        
        # 重新计算总金额
        order.calculate_total()
        
        db.session.commit()
        
        flash('订单创建成功！', 'success')
        return redirect(url_for('orders.order_detail', order_id=order.id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'创建订单失败: {str(e)}')
        flash('创建订单失败，请稍后重试', 'error')
        return redirect(url_for('member.services'))


@orders_bp.route('/<int:order_id>')
@login_required
@member_only
def order_detail(order_id):
    """订单详情"""
    # 移动设备跳转到手机版
    if is_mobile_device():
        return redirect(url_for('mobile.order_detail', order_id=order_id))

    try:
        order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            flash('订单不存在', 'error')
            return redirect(url_for('orders.list'))
        
        # 待付款状态时获取付款配置
        payment_config = None
        if order.status == 'awaiting_payment':
            from App_new.shared.models.system_config import SystemConfig
            payment_config = SystemConfig.get_payment_config()

        return render_template('member/order/order_detail.html', order=order, payment_config=payment_config)
    except Exception as e:
        current_app.logger.error(f'加载订单详情失败: {str(e)}')
        flash('加载订单详情失败', 'error')
        return redirect(url_for('orders.list'))


@orders_bp.route('/<int:order_id>/edit', methods=['GET', 'POST'])
@login_required
@member_only
def edit_order(order_id):
    """编辑订单"""
    try:
        order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            flash('订单不存在', 'error')
            return redirect(url_for('orders.list'))
        
        if not order.can_modify():
            flash('订单状态不允许修改', 'error')
            return redirect(url_for('orders.order_detail', order_id=order_id))
        
        if request.method == 'POST':
            # 更新联系人信息
            order.customer_name = request.form.get('customer_name', order.customer_name)
            order.customer_email = request.form.get('customer_email', order.customer_email)
            order.customer_phone = request.form.get('customer_phone', order.customer_phone)
            order.special_requirements = request.form.get('special_requirements', order.special_requirements)
            order.updated_at = datetime.utcnow()

            # 更新订单项目（人数、日期）
            total_amount = Decimal('0')
            description_lines = []
            for item in order.order_items:
                props = item.properties or {}
                adult_count = int(request.form.get(f'item_{item.id}_adult', props.get('adult_count', item.quantity)))
                child_count = int(request.form.get(f'item_{item.id}_child', props.get('child_count', 0)))
                visit_date = request.form.get(f'item_{item.id}_visit_date', props.get('visit_date', ''))

                if adult_count < 1:
                    adult_count = 1
                if child_count < 0:
                    child_count = 0

                adult_price = Decimal(str(props.get('adult_price', float(item.unit_price))))
                child_price = Decimal(str(props.get('child_price', 0)))
                line_total = (adult_price * adult_count) + (child_price * child_count)

                item.quantity = adult_count + child_count
                item.total_price = line_total
                props['adult_count'] = adult_count
                props['child_count'] = child_count
                props['visit_date'] = visit_date
                item.properties = props
                # 标记JSON字段已修改
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(item, 'properties')

                total_amount += line_total

                # 重建描述行
                variant_name = props.get('variant_name', '')
                line_desc = item.item_name
                line_desc += f" (成人{adult_count}"
                if child_count > 0:
                    line_desc += f", 儿童{child_count}"
                line_desc += ")"
                if visit_date:
                    line_desc += f" 游玩日期: {visit_date}"
                description_lines.append(line_desc)

            order.base_price = total_amount
            order.total_amount = total_amount + (order.additional_fees or 0) - (order.discount_amount or 0)
            order.description = '\n'.join(description_lines)

            db.session.commit()

            flash('订单更新成功！', 'success')
            return redirect(url_for('orders.order_detail', order_id=order_id))
        
        # GET 请求：显示编辑表单
        # 这里可以复用 apply_service 模板，传入订单数据
        return render_template('member/order/edit_order.html', order=order)
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'编辑订单失败: {str(e)}')
        flash('编辑订单失败，请稍后重试', 'error')
        return redirect(url_for('orders.order_detail', order_id=order_id))


@orders_bp.route('/<int:order_id>/submit', methods=['POST'])
@login_required
@member_only
def submit_order(order_id):
    """提交订单"""
    try:
        order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            flash('订单不存在', 'error')
            return redirect(url_for('orders.list'))
        
        if order.status != OrderStatus.DRAFT.value:
            flash('订单状态不允许提交', 'error')
            return redirect(url_for('orders.order_detail', order_id=order_id))
        
        # 更新订单状态
        order.status = OrderStatus.PENDING.value
        order.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('订单提交成功！我们会尽快处理您的订单。', 'success')
        return redirect(url_for('orders.order_detail', order_id=order_id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'提交订单失败: {str(e)}')
        flash('提交订单失败，请稍后重试', 'error')
        return redirect(url_for('orders.order_detail', order_id=order_id))


@orders_bp.route('/<int:order_id>/confirm-payment', methods=['POST'])
@login_required
@member_only
def confirm_payment(order_id):
    """客户确认已付款"""
    try:
        order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            return jsonify({'success': False, 'message': '订单不存在'}), 404

        if order.status != 'awaiting_payment':
            return jsonify({'success': False, 'message': '订单状态不正确'}), 400

        # 添加付款备注，状态不变，等待员工确认
        order.notes = (order.notes or '') + f'\n[客户已确认付款 {datetime.utcnow().strftime("%Y-%m-%d %H:%M")}]'
        order.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'message': '已通知工作人员'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'确认付款失败: {str(e)}')
        return jsonify({'success': False, 'message': '操作失败'}), 500


@orders_bp.route('/<int:order_id>/cancel', methods=['POST'])
@login_required
@member_only
def cancel_order(order_id):
    """取消订单"""
    try:
        order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            flash('订单不存在', 'error')
            return redirect(url_for('orders.list'))
        
        if not order.can_cancel():
            flash('订单状态不允许取消', 'error')
            return redirect(url_for('orders.order_detail', order_id=order_id))
        
        # 更新订单状态
        order.status = OrderStatus.CANCELLED.value
        order.cancelled_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('订单已取消', 'success')
        return redirect(url_for('orders.order_detail', order_id=order_id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'取消订单失败: {str(e)}')
        flash('取消订单失败，请稍后重试', 'error')
        return redirect(url_for('orders.order_detail', order_id=order_id))


@orders_bp.route('/<int:order_id>/urge', methods=['POST'])
@login_required
@member_only
def urge_order(order_id):
    """催促订单处理 - 发邮件通知员工"""
    try:
        order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            return jsonify({'success': False, 'message': '订单不存在'}), 404

        # 只有待处理/待付款/已确认/处理中状态可以催促
        if order.status in ('completed', 'cancelled', 'refunded', 'draft'):
            return jsonify({'success': False, 'message': '当前订单状态无需催促'}), 400

        # 防频繁催促：检查上次催促时间（notes中记录）
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        notes = order.notes or ''
        if '[催促]' in notes:
            # 简单检查：最近1小时内不能重复催促
            import re
            urge_times = re.findall(r'\[催促\] (\d{4}-\d{2}-\d{2} \d{2}:\d{2})', notes)
            if urge_times:
                last_urge = datetime.strptime(urge_times[-1], '%Y-%m-%d %H:%M')
                if (now - last_urge) < timedelta(hours=1):
                    return jsonify({'success': False, 'message': '您已催促过，请稍后再试'}), 429

        # 发送催促邮件给员工
        try:
            from flask_mail import Mail, Message
            mail = Mail(current_app)

            sender_email = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME', 'noreply@joyesc.com')
            sender_str = f"悦行假期 Joyeful Escapes <{sender_email}>"

            recipients_str = current_app.config.get('DEFAULT_EMAIL_RECIPIENTS', '') or current_app.config.get('DEFAULT_EMAIL_RECIPIENT', '')
            recipients = [r.strip() for r in recipients_str.split(',') if r.strip()]
            if not recipients:
                current_app.logger.warning('未配置收件人邮箱')
                return jsonify({'success': False, 'message': '系统未配置收件人，请联系管理员'}), 500

            status_map = {
                'pending': '待处理', 'awaiting_payment': '待付款',
                'confirmed': '已确认', 'in_progress': '处理中'
            }
            status_text = status_map.get(order.status, order.status)

            subject = f'【客户催促】{order.order_number} - {order.service_name}'
            html_body = f'''
            <!DOCTYPE html>
            <html>
            <head><meta charset="UTF-8"></head>
            <body style="margin:0;padding:0;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:#f5f5f5;">
                <table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;background:#fff;">
                    <tr>
                        <td style="background:linear-gradient(135deg,#d97706,#f59e0b);padding:30px;text-align:center;border-radius:10px 10px 0 0;">
                            <h1 style="color:#fff;margin:0;font-size:22px;">⏰ 客户催促提醒</h1>
                            <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px;">订单号: {order.order_number}</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:30px;border:1px solid #e9ecef;border-top:none;">
                            <p style="color:#d97706;font-weight:600;font-size:15px;margin:0 0 20px;">客户 {order.customer_name} 催促处理以下订单：</p>
                            <table width="100%" style="border-collapse:collapse;">
                                <tr>
                                    <td style="padding:10px 0;border-bottom:1px solid #f3f4f6;color:#6b7280;font-size:14px;width:80px;">订单号</td>
                                    <td style="padding:10px 0;border-bottom:1px solid #f3f4f6;font-weight:600;font-size:14px;">{order.order_number}</td>
                                </tr>
                                <tr>
                                    <td style="padding:10px 0;border-bottom:1px solid #f3f4f6;color:#6b7280;font-size:14px;">服务</td>
                                    <td style="padding:10px 0;border-bottom:1px solid #f3f4f6;font-size:14px;">{order.service_name}</td>
                                </tr>
                                <tr>
                                    <td style="padding:10px 0;border-bottom:1px solid #f3f4f6;color:#6b7280;font-size:14px;">状态</td>
                                    <td style="padding:10px 0;border-bottom:1px solid #f3f4f6;font-size:14px;">{status_text}</td>
                                </tr>
                                <tr>
                                    <td style="padding:10px 0;border-bottom:1px solid #f3f4f6;color:#6b7280;font-size:14px;">金额</td>
                                    <td style="padding:10px 0;border-bottom:1px solid #f3f4f6;font-size:14px;font-weight:700;color:#059669;">{order.currency} {order.total_amount}</td>
                                </tr>
                                <tr>
                                    <td style="padding:10px 0;border-bottom:1px solid #f3f4f6;color:#6b7280;font-size:14px;">客户</td>
                                    <td style="padding:10px 0;border-bottom:1px solid #f3f4f6;font-size:14px;">{order.customer_name} ({order.customer_email})</td>
                                </tr>
                                <tr>
                                    <td style="padding:10px 0;color:#6b7280;font-size:14px;">下单时间</td>
                                    <td style="padding:10px 0;font-size:14px;">{order.created_at.strftime('%Y-%m-%d %H:%M') if order.created_at else '-'}</td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="background:#fffbeb;padding:20px 30px;text-align:center;border:1px solid #e9ecef;border-top:none;border-radius:0 0 10px 10px;">
                            <p style="color:#92400e;font-size:13px;margin:0;">请尽快登录后台处理该订单</p>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            '''

            msg = Message(
                subject=subject,
                sender=sender_str,
                recipients=recipients,
                html=html_body
            )
            mail.send(msg)
            current_app.logger.info(f"[催促邮件] 订单 {order.order_number} 催促邮件已发送给: {recipients}")

        except Exception as mail_err:
            current_app.logger.warning(f'催促邮件发送失败: {str(mail_err)}')
            return jsonify({'success': False, 'message': '邮件发送失败，请稍后再试'}), 500

        # 记录催促时间
        order.notes = (order.notes or '') + f'\n[催促] {now.strftime("%Y-%m-%d %H:%M")}'
        order.updated_at = now
        db.session.commit()

        return jsonify({'success': True, 'message': '已发送催促通知，工作人员将尽快处理'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'催促订单失败: {str(e)}')
        return jsonify({'success': False, 'message': '操作失败'}), 500


@orders_bp.route('/api/debug/models')
@login_required
@member_only
def api_debug_models():
    """调试：检查模型状态"""
    try:
        from sqlalchemy import inspect
        
        # 检查表是否存在
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        # 检查模型
        model_info = {
            'Order': str(Order.__tablename__),
            'OrderItem': str(OrderItem.__tablename__),
            'OrderDocument': str(OrderDocument.__tablename__),
            'Payment': str(Payment.__tablename__),
            'ServiceTemplate': str(ServiceTemplate.__tablename__)
        }
        
        # 尝试查询
        order_count = 0
        try:
            order_count = Order.query.count()
        except Exception as e:
            pass
        
        return jsonify({
            'success': True,
            'tables_in_db': tables,
            'models': model_info,
            'order_count': order_count,
            'member_orders_exists': 'member_orders' in tables
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@orders_bp.route('/api/service-templates')
@login_required
@member_only
def api_service_templates():
    """获取服务模板API"""
    try:
        service_type = request.args.get('type')
        templates = ServiceTemplate.query.filter_by(is_active=True)

        if service_type:
            templates = templates.filter_by(service_type=service_type)

        result = []
        for template in templates:
            result.append({
                'id': template.id,
                'service_type': template.service_type,
                'service_name': template.service_name,
                'description': template.description,
                'base_price': float(template.base_price),
                'currency': template.currency,
                'processing_time': template.processing_time,
                'requirements': template.requirements,
                'required_documents': template.required_documents
            })

        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        current_app.logger.error(f'获取服务模板失败: {str(e)}')
        return jsonify({
            'success': False,
            'message': '获取服务模板失败'
        }), 500


@orders_bp.route('/book-tour/<int:product_id>', methods=['GET', 'POST'])
@login_required
@member_only
def book_tour(product_id):
    """预订旅游产品"""
    # 移动设备跳转到手机版（仅GET请求）
    if is_mobile_device() and request.method == 'GET':
        return redirect(url_for('mobile.book_tour', product_id=product_id))

    try:
        from App_new.business.tour.models.Packagemodels import Product

        # 获取产品信息
        product = Product.query.get_or_404(product_id)

        # 检查产品是否可预订
        from datetime import date
        today = date.today()
        if product.product_status != 'active':
            flash('该产品目前不可预订', 'error')
            return redirect(url_for('public.tour_package_detail', package_id=product_id))

        if product.valid_until and product.valid_until < today:
            flash('该产品已过期', 'error')
            return redirect(url_for('public.tour_package_detail', package_id=product_id))

        if request.method == 'POST':
            # 处理预订提交
            try:
                # 获取表单数据
                travel_date = request.form.get('travel_date')
                adult_count = int(request.form.get('adult_count', 1))
                child_count = int(request.form.get('child_count', 0))
                infant_count = int(request.form.get('infant_count', 0))

                # 联系人信息
                contact_name = request.form.get('contact_name')
                contact_email = request.form.get('contact_email')
                contact_phone = request.form.get('contact_phone')

                # 特殊要求
                special_requirements = request.form.get('special_requirements', '')

                # 计算参考价格（工作人员会确认最终价格）
                base_price = Decimal(str(product.base_price or 0))
                child_price = Decimal(str(product.child_price or base_price * Decimal('0.7')))
                infant_price = Decimal(str(product.infant_price or 0))

                estimated_price = (base_price * adult_count) + (child_price * child_count) + (infant_price * infant_count)

                # 生成订单号
                order_number = f"TOUR{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

                # 构建产品详情描述
                destination = product.city_name or product.destination_city or '未指定'
                if product.city and product.city.country_name:
                    destination = f"{product.city.country_name} {destination}"

                duration = f"{product.duration_days}天{product.duration_days-1 if product.duration_days else 0}夜" if product.duration_days else "待定"

                description = f"""旅游产品: {product.product_name}
产品编号: {product.product_code or f'PKG-{product.id:04d}'}
目的地: {destination}
行程: {duration}
出发日期: {travel_date}
人数: 成人{adult_count}人"""
                if child_count > 0:
                    description += f", 儿童{child_count}人"
                if infant_count > 0:
                    description += f", 婴儿{infant_count}人"

                # 创建订单
                order = Order(
                    order_number=order_number,
                    user_id=current_user.id,
                    service_type='tour',
                    service_name=product.product_name,
                    description=description,
                    base_price=estimated_price,
                    total_amount=estimated_price,
                    currency=product.currency or 'SGD',
                    customer_name=contact_name,
                    customer_email=contact_email,
                    customer_phone=contact_phone,
                    special_requirements=special_requirements,
                    notes=f"产品ID: {product.id}, 出发日期: {travel_date}, 成人: {adult_count}, 儿童: {child_count}, 婴儿: {infant_count}",
                    status=OrderStatus.PENDING.value  # 直接设为待处理，等待工作人员确认价格
                )

                db.session.add(order)
                db.session.flush()

                # 添加订单项目
                order_item = OrderItem(
                    order_id=order.id,
                    item_name=product.product_name,
                    item_description=f"{destination} | {duration}",
                    item_type='tour_package',
                    quantity=adult_count + child_count + infant_count,
                    unit_price=base_price,
                    total_price=estimated_price,
                    properties={
                        'product_id': product.id,
                        'product_code': product.product_code,
                        'travel_date': travel_date,
                        'adult_count': adult_count,
                        'child_count': child_count,
                        'infant_count': infant_count,
                        'adult_price': float(base_price),
                        'child_price': float(child_price),
                        'infant_price': float(infant_price)
                    }
                )
                db.session.add(order_item)

                db.session.commit()

                # 发送邮件通知（不阻塞主流程）
                try:
                    from App_new.utils.email_service import send_order_notification, send_order_confirmation
                    send_order_notification(order)
                    send_order_confirmation(order)
                except Exception as mail_err:
                    current_app.logger.warning(f'订单邮件发送失败: {str(mail_err)}')

                flash('预订提交成功！我们的工作人员将尽快与您确认价格和行程详情。', 'success')
                return redirect(url_for('orders.order_detail', order_id=order.id))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f'创建旅游订单失败: {str(e)}')
                import traceback
                current_app.logger.error(traceback.format_exc())
                flash(f'预订失败: {str(e)}', 'error')
                return redirect(url_for('orders.book_tour', product_id=product_id))

        # GET 请求：显示预订表单
        # 准备产品数据用于模板
        destination = product.city_name or product.destination_city or '未指定'
        if product.city and product.city.country_name:
            destination = f"{product.city.country_name} {destination}"

        duration = f"{product.duration_days}天{product.duration_days-1 if product.duration_days else 0}夜" if product.duration_days else "待定"

        price_display = f"{product.currency or 'SGD'} {product.base_price:,.0f}" if product.base_price else "价格面议"

        product_data = {
            'id': product.id,
            'code': product.product_code or f'PKG-{product.id:04d}',
            'name': product.product_name,
            'destination': destination,
            'duration': duration,
            'duration_days': product.duration_days,
            'price': price_display,
            'base_price': float(product.base_price) if product.base_price else 0,
            'child_price': float(product.child_price) if product.child_price else 0,
            'infant_price': float(product.infant_price) if product.infant_price else 0,
            'currency': product.currency or 'SGD',
            'image': product.cover_image,
            'min_pax': product.min_pax,
            'max_pax': product.max_pax,
            'product_type': product.product_type
        }

        # 获取用户信息预填
        user_profile = current_user.profile if hasattr(current_user, 'profile') else None

        return render_template('member/order/book_tour.html',
                             product=product_data,
                             user_profile=user_profile)

    except Exception as e:
        current_app.logger.error(f'加载旅游预订页面失败: {str(e)}')
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash('加载页面失败，请稍后重试', 'error')
        return redirect(url_for('public.tour_packages'))


@orders_bp.route('/book-ticket/<int:product_id>', methods=['GET', 'POST'])
@login_required
@member_only
def book_ticket(product_id):
    """预订景点门票"""
    # 移动设备跳转到手机版（仅GET请求，如果手机版路由存在）
    if is_mobile_device() and request.method == 'GET':
        try:
            return redirect(url_for('mobile.book_ticket', product_id=product_id,
                                    variant_id=request.args.get('variant_id', ''),
                                    adult=request.args.get('adult', 1),
                                    child=request.args.get('child', 0)))
        except Exception:
            pass  # 手机版路由不存在，继续使用桌面版

    try:
        from App_new.business.products.models.products_unified import ProductsUnified
        from App_new.business.products.models.products_ticket_ext import ProductsTicketExt
        from App_new.business.products.models.products_ticket_variant import ProductsTicketVariant

        # 获取产品信息
        product = ProductsUnified.query.get_or_404(product_id)

        if product.product_status != 'active':
            flash('该产品目前不可预订', 'error')
            return redirect(url_for('public.attraction_detail', product_id=product_id))

        # 获取场馆信息
        ticket_ext = ProductsTicketExt.query.filter_by(product_id=product_id).first()

        # 获取所有激活的变体
        variants = ProductsTicketVariant.query.filter_by(
            product_id=product_id, is_active=True
        ).order_by(ProductsTicketVariant.sort_order).all()

        if not variants:
            flash('该产品暂无可预订的票种', 'error')
            return redirect(url_for('public.attraction_detail', product_id=product_id))

        # 获取URL参数预选的变体和人数
        selected_variant_id = request.args.get('variant_id', type=int)
        pre_adult = request.args.get('adult', 1, type=int)
        pre_child = request.args.get('child', 0, type=int)

        if request.method == 'POST':
            try:
                # 获取表单数据
                variant_id = request.form.get('variant_id', type=int)
                visit_date = request.form.get('visit_date')
                adult_count = int(request.form.get('adult_count', 1))
                child_count = int(request.form.get('child_count', 0))

                # 联系人信息
                contact_name = request.form.get('contact_name')
                contact_email = request.form.get('contact_email')
                contact_phone = request.form.get('contact_phone')
                special_requirements = request.form.get('special_requirements', '')

                # 获取选中的变体
                variant = ProductsTicketVariant.query.get(variant_id)
                if not variant or variant.product_id != product_id:
                    flash('所选票种不存在', 'error')
                    return redirect(url_for('orders.book_ticket', product_id=product_id))

                # 固定日期票必须选择游玩日期
                if (variant.date_type or 'open') == 'fixed' and not visit_date:
                    flash('该票种为固定日期票，请选择游玩日期', 'error')
                    return redirect(url_for('orders.book_ticket', product_id=product_id))

                # 计算价格
                adult_price = Decimal(str(variant.adult_selling_price or 0))
                child_price = Decimal(str(variant.child_selling_price or 0))
                estimated_price = (adult_price * adult_count) + (child_price * child_count)
                currency = variant.currency or 'SGD'

                # 生成订单号
                order_number = f"TKT{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

                # 构建描述
                location = product.country or ''
                if product.city:
                    location = f"{location} {product.city}" if location else product.city

                description = f"景点门票: {product.product_name}\n"
                description += f"票种: {variant.variant_name}\n"
                if location:
                    description += f"地点: {location}\n"
                if visit_date:
                    description += f"游玩日期: {visit_date}\n"
                description += f"人数: 成人{adult_count}人"
                if child_count > 0:
                    description += f", 儿童{child_count}人"

                # 创建订单
                order = Order(
                    order_number=order_number,
                    user_id=current_user.id,
                    service_type='ticket',
                    service_name=product.product_name,
                    description=description,
                    base_price=estimated_price,
                    total_amount=estimated_price,
                    currency=currency,
                    customer_name=contact_name,
                    customer_email=contact_email,
                    customer_phone=contact_phone,
                    special_requirements=special_requirements,
                    notes=f"产品ID: {product.id}, 变体ID: {variant.id}, 游玩日期: {visit_date}, 成人: {adult_count}, 儿童: {child_count}",
                    status=OrderStatus.PENDING.value
                )

                db.session.add(order)
                db.session.flush()

                # 添加订单项目
                order_item = OrderItem(
                    order_id=order.id,
                    item_name=f"{product.product_name} - {variant.variant_name}",
                    item_description=f"{location}" if location else '',
                    item_type='ticket',
                    quantity=adult_count + child_count,
                    unit_price=adult_price,
                    total_price=estimated_price,
                    properties={
                        'product_id': product.id,
                        'variant_id': variant.id,
                        'variant_name': variant.variant_name,
                        'visit_date': visit_date,
                        'adult_count': adult_count,
                        'child_count': child_count,
                        'adult_price': float(adult_price),
                        'child_price': float(child_price),
                        'delivery_type': variant.delivery_type
                    }
                )
                db.session.add(order_item)

                db.session.commit()

                # 发送邮件通知
                try:
                    from App_new.utils.email_service import send_order_notification, send_order_confirmation
                    send_order_notification(order)
                    send_order_confirmation(order)
                except Exception as mail_err:
                    current_app.logger.warning(f'订单邮件发送失败: {str(mail_err)}')

                flash('预订提交成功！我们的工作人员将尽快与您确认。', 'success')
                return redirect(url_for('orders.order_detail', order_id=order.id))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f'创建门票订单失败: {str(e)}')
                import traceback
                current_app.logger.error(traceback.format_exc())
                flash(f'预订失败: {str(e)}', 'error')
                return redirect(url_for('orders.book_ticket', product_id=product_id))

        # GET 请求：显示预订表单
        # 构建变体数据
        variants_data = []
        for v in variants:
            variants_data.append({
                'id': v.id,
                'name': v.variant_name,
                'name_en': v.variant_name_en,
                'description': v.description,
                'adult_price': float(v.adult_selling_price or 0),
                'child_price': float(v.child_selling_price or 0),
                'currency': v.currency or 'SGD',
                'date_type': v.date_type or 'open',
                'delivery_type': v.delivery_type,
                'includes': v.includes,
                'excludes': v.excludes,
                'important_notes': v.important_notes
            })

        # 产品数据
        location = product.country or ''
        if product.city:
            location = f"{location} {product.city}" if location else product.city

        product_data = {
            'id': product.id,
            'name': product.product_name,
            'name_en': product.product_name_en,
            'location': location,
            'cover_image': product.cover_image,
            'venue_name': ticket_ext.venue_name if ticket_ext else None,
            'opening_hours': ticket_ext.opening_hours if ticket_ext else None,
        }

        # 获取用户信息预填
        user_profile = current_user.profile if hasattr(current_user, 'profile') else None

        return render_template('member/order/book_ticket.html',
                             product=product_data,
                             variants=variants_data,
                             selected_variant_id=selected_variant_id,
                             pre_adult=pre_adult,
                             pre_child=pre_child,
                             user_profile=user_profile)

    except Exception as e:
        current_app.logger.error(f'加载门票预订页面失败: {str(e)}')
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash('加载页面失败，请稍后重试', 'error')
        return redirect(url_for('public.attractions'))
