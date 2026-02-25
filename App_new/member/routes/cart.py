"""
购物车路由
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import current_user
from datetime import datetime
from decimal import Decimal
import uuid

from ...utils.decorators import member_only, login_required
from ...exts import db
from ..models.cart import CartItem
from ..models.order import Order, OrderItem, OrderStatus

cart_bp = Blueprint('cart', __name__, url_prefix='/member/cart')


@cart_bp.route('/')
@login_required
@member_only
def cart_page():
    """购物车页面"""
    items = CartItem.query.filter_by(user_id=current_user.id).order_by(CartItem.created_at.desc()).all()

    # 计算总金额
    cart_total = sum(item.line_total for item in items)
    currency = items[0].currency if items else 'SGD'

    return render_template('member/cart/cart.html',
                         items=items,
                         cart_total=cart_total,
                         currency=currency)


@cart_bp.route('/add', methods=['POST'])
@login_required
@member_only
def add_to_cart():
    """加入购物车（AJAX）"""
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        variant_id = data.get('variant_id')
        adult_qty = int(data.get('adult_qty', 1))
        child_qty = int(data.get('child_qty', 0))
        visit_date = data.get('visit_date') or None

        if not product_id or not variant_id:
            return jsonify({'success': False, 'message': '参数不完整'}), 400

        # 验证产品和变体存在且激活
        from App_new.business.products.models.products_unified import ProductsUnified
        from App_new.business.products.models.products_ticket_variant import ProductsTicketVariant

        product = ProductsUnified.query.filter_by(id=product_id, product_status='active').first()
        if not product:
            return jsonify({'success': False, 'message': '产品不存在或已下架'}), 404

        variant = ProductsTicketVariant.query.filter_by(id=variant_id, product_id=product_id, is_active=True).first()
        if not variant:
            return jsonify({'success': False, 'message': '票种不存在或已下架'}), 404

        # 检查是否已有相同变体
        existing = CartItem.query.filter_by(
            user_id=current_user.id,
            variant_id=variant_id
        ).first()

        if existing:
            # 累加数量
            existing.adult_qty = (existing.adult_qty or 0) + adult_qty
            existing.child_qty = (existing.child_qty or 0) + child_qty
            # 更新价格快照
            existing.adult_price = variant.adult_selling_price or 0
            existing.child_price = variant.child_selling_price or 0
            if visit_date:
                existing.visit_date = visit_date
            existing.updated_at = datetime.utcnow()
        else:
            # 构建快照信息
            location = product.country or ''
            if product.city:
                location = f"{location} {product.city}" if location else product.city

            properties = {
                'product_name': product.product_name,
                'product_name_en': product.product_name_en,
                'variant_name': variant.variant_name,
                'variant_name_en': variant.variant_name_en,
                'cover_image': product.cover_image,
                'location': location,
                'delivery_type': variant.delivery_type,
                'date_type': variant.date_type or 'open',
            }

            item = CartItem(
                user_id=current_user.id,
                product_id=product_id,
                variant_id=variant_id,
                adult_qty=adult_qty,
                child_qty=child_qty,
                adult_price=variant.adult_selling_price or 0,
                child_price=variant.child_selling_price or 0,
                currency=variant.currency or 'SGD',
                visit_date=visit_date,
                properties=properties
            )
            db.session.add(item)

        db.session.commit()

        # 返回购物车数量
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()

        return jsonify({
            'success': True,
            'message': '已加入购物车',
            'cart_count': cart_count
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'加入购物车失败: {str(e)}')
        return jsonify({'success': False, 'message': '操作失败，请稍后重试'}), 500


@cart_bp.route('/update/<int:item_id>', methods=['POST'])
@login_required
@member_only
def update_cart_item(item_id):
    """修改购物车项目数量（AJAX）"""
    try:
        data = request.get_json()
        adult_qty = int(data.get('adult_qty', 1))
        child_qty = int(data.get('child_qty', 0))

        item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first()
        if not item:
            return jsonify({'success': False, 'message': '项目不存在'}), 404

        # 至少保留1个成人
        if adult_qty < 1:
            adult_qty = 1
        if child_qty < 0:
            child_qty = 0

        item.adult_qty = adult_qty
        item.child_qty = child_qty
        item.updated_at = datetime.utcnow()
        db.session.commit()

        # 重新计算总金额
        all_items = CartItem.query.filter_by(user_id=current_user.id).all()
        cart_total = sum(i.line_total for i in all_items)
        cart_count = len(all_items)

        return jsonify({
            'success': True,
            'line_total': round(item.line_total, 2),
            'cart_total': round(cart_total, 2),
            'cart_count': cart_count,
            'currency': item.currency
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'更新购物车失败: {str(e)}')
        return jsonify({'success': False, 'message': '操作失败'}), 500


@cart_bp.route('/remove/<int:item_id>', methods=['POST'])
@login_required
@member_only
def remove_cart_item(item_id):
    """删除购物车项目（AJAX）"""
    try:
        item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first()
        if not item:
            return jsonify({'success': False, 'message': '项目不存在'}), 404

        db.session.delete(item)
        db.session.commit()

        # 重新计算
        all_items = CartItem.query.filter_by(user_id=current_user.id).all()
        cart_total = sum(i.line_total for i in all_items)
        cart_count = len(all_items)
        currency = all_items[0].currency if all_items else 'SGD'

        return jsonify({
            'success': True,
            'cart_total': round(cart_total, 2),
            'cart_count': cart_count,
            'currency': currency
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'删除购物车项目失败: {str(e)}')
        return jsonify({'success': False, 'message': '操作失败'}), 500


@cart_bp.route('/count')
@login_required
@member_only
def cart_count():
    """获取购物车数量（AJAX）"""
    count = CartItem.query.filter_by(user_id=current_user.id).count()
    return jsonify({'count': count})


@cart_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
@member_only
def checkout():
    """结算页面"""
    items = CartItem.query.filter_by(user_id=current_user.id).order_by(CartItem.created_at.desc()).all()

    if not items:
        flash('购物车为空', 'warning')
        return redirect(url_for('public.attractions'))

    if request.method == 'POST':
        try:
            # 获取联系人信息
            contact_name = request.form.get('contact_name', '').strip()
            contact_email = request.form.get('contact_email', '').strip()
            contact_phone = request.form.get('contact_phone', '').strip()
            special_requirements = request.form.get('special_requirements', '').strip()

            if not contact_name or not contact_email or not contact_phone:
                flash('请填写完整的联系人信息', 'error')
                return redirect(url_for('cart.checkout'))

            # 重新校验变体价格并计算总额
            from App_new.business.products.models.products_ticket_variant import ProductsTicketVariant

            total_amount = Decimal('0')
            order_items_data = []

            for item in items:
                variant = ProductsTicketVariant.query.filter_by(id=item.variant_id, is_active=True).first()
                if not variant:
                    flash(f'票种 "{item.properties.get("variant_name", "")}" 已下架，请从购物车中删除', 'error')
                    return redirect(url_for('cart.cart_page'))

                # 使用实时价格
                adult_price = Decimal(str(variant.adult_selling_price or 0))
                child_price = Decimal(str(variant.child_selling_price or 0))
                line_total = (adult_price * item.adult_qty) + (child_price * item.child_qty)
                total_amount += line_total

                # 获取每项的游玩日期
                visit_date = request.form.get(f'visit_date_{item.id}', '')

                # 固定日期票必须选择日期
                date_type = (variant.date_type or 'open')
                if date_type == 'fixed' and not visit_date:
                    flash(f'请为 "{item.properties.get("variant_name", "")}" 选择游玩日期', 'error')
                    return redirect(url_for('cart.checkout'))

                props = item.properties or {}
                order_items_data.append({
                    'item': item,
                    'variant': variant,
                    'adult_price': adult_price,
                    'child_price': child_price,
                    'line_total': line_total,
                    'visit_date': visit_date,
                    'product_name': props.get('product_name', ''),
                    'variant_name': props.get('variant_name', ''),
                    'location': props.get('location', ''),
                })

            # 生成订单号
            order_number = f"TKT{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

            # 构建描述
            product_names = list(set(d['product_name'] for d in order_items_data))
            if len(product_names) == 1:
                service_name = product_names[0]
            else:
                service_name = f"景点门票 ({len(order_items_data)}项)"

            description_lines = []
            for d in order_items_data:
                line = f"{d['product_name']} - {d['variant_name']}"
                line += f" (成人{d['item'].adult_qty}"
                if d['item'].child_qty > 0:
                    line += f", 儿童{d['item'].child_qty}"
                line += ")"
                if d['visit_date']:
                    line += f" 游玩日期: {d['visit_date']}"
                description_lines.append(line)
            description = '\n'.join(description_lines)

            currency = items[0].currency or 'SGD'

            # 创建订单
            order = Order(
                order_number=order_number,
                user_id=current_user.id,
                service_type='ticket',
                service_name=service_name,
                description=description,
                base_price=total_amount,
                total_amount=total_amount,
                currency=currency,
                customer_name=contact_name,
                customer_email=contact_email,
                customer_phone=contact_phone,
                special_requirements=special_requirements,
                status=OrderStatus.PENDING.value
            )
            db.session.add(order)
            db.session.flush()

            # 创建订单项目
            for d in order_items_data:
                oi = OrderItem(
                    order_id=order.id,
                    item_name=f"{d['product_name']} - {d['variant_name']}",
                    item_description=d['location'],
                    item_type='ticket',
                    quantity=d['item'].adult_qty + d['item'].child_qty,
                    unit_price=d['adult_price'],
                    total_price=d['line_total'],
                    properties={
                        'product_id': d['item'].product_id,
                        'variant_id': d['item'].variant_id,
                        'variant_name': d['variant_name'],
                        'visit_date': d['visit_date'],
                        'adult_count': d['item'].adult_qty,
                        'child_count': d['item'].child_qty,
                        'adult_price': float(d['adult_price']),
                        'child_price': float(d['child_price']),
                        'delivery_type': (d['item'].properties or {}).get('delivery_type', ''),
                    }
                )
                db.session.add(oi)

            # 清空购物车
            CartItem.query.filter_by(user_id=current_user.id).delete()

            db.session.commit()

            # 发送邮件通知
            try:
                from App_new.utils.email_service import send_order_notification, send_order_confirmation
                send_order_notification(order)
                send_order_confirmation(order)
            except Exception as mail_err:
                current_app.logger.warning(f'订单邮件发送失败: {str(mail_err)}')

            flash('订单提交成功！我们的工作人员将尽快与您确认。', 'success')
            return redirect(url_for('orders.order_detail', order_id=order.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'购物车结算失败: {str(e)}')
            import traceback
            current_app.logger.error(traceback.format_exc())
            flash(f'结算失败: {str(e)}', 'error')
            return redirect(url_for('cart.checkout'))

    # GET：显示结算页面
    cart_total = sum(item.line_total for item in items)
    currency = items[0].currency if items else 'SGD'
    user_profile = current_user.profile if hasattr(current_user, 'profile') else None

    return render_template('member/cart/checkout.html',
                         items=items,
                         cart_total=cart_total,
                         currency=currency,
                         user_profile=user_profile)
