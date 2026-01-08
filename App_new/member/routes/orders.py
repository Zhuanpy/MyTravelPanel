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
        
        # 获取订单状态筛选
        status = request.args.get('status', '')
        
        # 调试信息
        current_app.logger.info(f'当前用户ID: {current_user.id}')
        current_app.logger.info(f'当前用户邮箱: {current_user.email}')
        
        # 查询所有订单（先不过滤用户）
        total_orders = Order.query.count()
        current_app.logger.info(f'数据库中总订单数: {total_orders}')
        
        # 查询当前用户的订单
        query = Order.query.filter_by(user_id=current_user.id)
        user_orders_count = query.count()
        current_app.logger.info(f'当前用户的订单数: {user_orders_count}')
        
        if status:
            query = query.filter_by(status=status)
            current_app.logger.info(f'筛选状态 {status} 后的订单数: {query.count()}')
        
        # 按创建时间倒序排列
        query = query.order_by(Order.created_at.desc())
        
        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        orders = pagination.items
        
        current_app.logger.info(f'返回的订单数: {len(orders)}')
        
        return render_template('member/orders.html',
                             orders=orders,
                             pagination=pagination,
                             current_status=status)
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
        
        return render_template('member/order/order_detail.html', order=order)
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
            # 更新订单信息
            order.customer_name = request.form.get('customer_name', order.customer_name)
            order.customer_email = request.form.get('customer_email', order.customer_email)
            order.customer_phone = request.form.get('customer_phone', order.customer_phone)
            order.customer_address = request.form.get('customer_address', order.customer_address)
            order.special_requirements = request.form.get('special_requirements', order.special_requirements)
            order.notes = request.form.get('notes', order.notes)
            order.updated_at = datetime.utcnow()
            
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
