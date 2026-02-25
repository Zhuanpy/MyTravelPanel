# -*- coding: utf-8 -*-
"""
统一产品管理路由
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from datetime import datetime
import pandas as pd
import io
from App_new.exts import db
from App_new.business.products.models import (
    ProductsUnified,
    ProductCategory,
    ProductSubCategory,
    ProductsPrice,
    ProductsRule,
    PriceType,
    PeopleType,
)
from App_new.business.products.models.products_visa_ext import ProductsVisaExt
from App_new.business.products.models.products_ticket_ext import ProductsTicketExt, TicketType, TicketDelivery
from App_new.business.products.models.products_ticket_variant import ProductsTicketVariant
from App_new.business.products.services.visa_sync_service import VisaSyncService
from App_new.business.visa.models.Visamodels import VisaTypes, VisaCountries, VisaSingaporeIdentity, VisaDocuments

products_bp = Blueprint('products', __name__, url_prefix='/staff/products')


@products_bp.route('/')
@login_required
def index():
    """统一产品列表"""
    # 获取筛选参数
    category = request.args.get('category', '')
    status = request.args.get('status', '')
    country = request.args.get('country', '')
    keyword = request.args.get('keyword', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # 构建查询
    query = ProductsUnified.query

    if category:
        query = query.filter(ProductsUnified.product_category == category)

    if status:
        query = query.filter(ProductsUnified.product_status == status)

    if country:
        query = query.filter(ProductsUnified.country == country)

    if keyword:
        query = query.filter(
            db.or_(
                ProductsUnified.product_name.ilike(f'%{keyword}%'),
                ProductsUnified.product_code.ilike(f'%{keyword}%'),
                ProductsUnified.country.ilike(f'%{keyword}%'),
            )
        )

    # 排序
    query = query.order_by(ProductsUnified.created_at.desc())

    # 分页
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    products = pagination.items

    # 统计各分类数量
    category_counts = {}
    for cat_code, cat_name in ProductCategory.CHOICES:
        count = ProductsUnified.query.filter_by(product_category=cat_code).count()
        category_counts[cat_code] = {
            'name': cat_name,
            'count': count
        }

    # 获取所有国家/地区列表
    countries_query = db.session.query(ProductsUnified.country).filter(
        ProductsUnified.country.isnot(None),
        ProductsUnified.country != ''
    ).distinct().order_by(ProductsUnified.country)
    countries = [c[0] for c in countries_query.all()]

    return render_template(
        'business/products/product_list.html',
        products=products,
        pagination=pagination,
        categories=ProductCategory.CHOICES,
        category_counts=category_counts,
        countries=countries,
        current_category=category,
        current_status=status,
        current_country=country,
        keyword=keyword,
        now=datetime.utcnow(),
    )


@products_bp.route('/detail/<int:product_id>')
@login_required
def detail(product_id):
    """产品详情"""
    product = ProductsUnified.query.get_or_404(product_id)

    # 获取价格信息
    prices = ProductsPrice.query.filter_by(product_id=product_id).all()

    # 获取规则信息
    rules = ProductsRule.query.filter_by(product_id=product_id).all()

    # 获取门票变体（仅门票类产品）
    ticket_variants = []
    if product.product_category == 'ticket':
        ticket_variants = ProductsTicketVariant.query.filter_by(
            product_id=product_id
        ).order_by(ProductsTicketVariant.sort_order, ProductsTicketVariant.id).all()

    return render_template(
        'business/products/product_detail.html',
        product=product,
        prices=prices,
        rules=rules,
        ticket_variants=ticket_variants,
        ProductCategory=ProductCategory,
    )


@products_bp.route('/create')
@login_required
def create():
    """产品类别选择页面"""
    # 统计各分类数量
    category_counts = {}
    for cat_code, cat_name in ProductCategory.CHOICES:
        count = ProductsUnified.query.filter_by(product_category=cat_code).count()
        category_counts[cat_code] = {
            'name': cat_name,
            'count': count
        }

    return render_template(
        'business/products/product_create_selector.html',
        category_counts=category_counts,
    )


@products_bp.route('/create/<category>', methods=['GET', 'POST'])
@login_required
def create_by_category(category):
    """按类别创建产品"""
    # 验证类别
    valid_categories = [c[0] for c in ProductCategory.CHOICES]
    if category not in valid_categories:
        flash('无效的产品类别', 'error')
        return redirect(url_for('products.create'))

    # 对于已有专门管理页面的类别，重定向
    if category == ProductCategory.TOUR:
        return redirect(url_for('tour_products.add_product'))
    elif category == ProductCategory.VISA:
        return redirect(url_for('products.create_visa'))
    elif category == ProductCategory.TICKET:
        return redirect(url_for('products.create_ticket'))
    elif category == ProductCategory.FLIGHT:
        return redirect(url_for('flight_home.flight_home_page'))

    if request.method == 'POST':
        try:
            product_name = request.form.get('product_name')
            if not product_name:
                flash('请填写产品名称', 'error')
                return redirect(url_for('products.create_by_category', category=category))

            # 生成产品编号
            product_code = ProductsUnified.generate_product_code(category)

            # 创建产品
            product = ProductsUnified(
                product_code=product_code,
                product_name=product_name,
                product_short_name=request.form.get('product_short_name'),
                product_category=category,
                product_sub_category=request.form.get('product_sub_category'),
                product_status='draft',
                country=request.form.get('country'),
                city=request.form.get('city'),
                departure_city=request.form.get('departure_city'),
                destination=request.form.get('destination'),
                base_price=request.form.get('base_price', type=float),
                currency=request.form.get('currency', 'SGD'),
                description=request.form.get('description'),
                includes=request.form.get('includes'),
                excludes=request.form.get('excludes'),
                important_notes=request.form.get('important_notes'),
                created_by=current_user.username if current_user else None,
            )

            db.session.add(product)
            db.session.commit()

            flash('产品创建成功', 'success')
            return redirect(url_for('products.detail', product_id=product.id))

        except Exception as e:
            db.session.rollback()
            flash(f'创建失败: {str(e)}', 'error')
            return redirect(url_for('products.create_by_category', category=category))

    # 获取类别名称
    category_name = ProductCategory.get_label(category)

    # 获取子类别
    sub_categories = ProductSubCategory.CHOICES.get(category, [])

    return render_template(
        'business/products/product_form_category.html',
        product=None,
        category=category,
        category_name=category_name,
        sub_categories=sub_categories,
        mode='create',
    )


@products_bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit(product_id):
    """编辑产品"""
    product = ProductsUnified.query.get_or_404(product_id)

    if request.method == 'POST':
        try:
            # 更新产品信息
            product.product_name = request.form.get('product_name')
            product.product_short_name = request.form.get('product_short_name')
            product.product_sub_category = request.form.get('product_sub_category')
            product.country = request.form.get('country')
            product.city = request.form.get('city')
            product.departure_city = request.form.get('departure_city')
            product.destination = request.form.get('destination')
            product.base_price = request.form.get('base_price', type=float)
            product.currency = request.form.get('currency', 'SGD')
            product.description = request.form.get('description')
            product.includes = request.form.get('includes')
            product.excludes = request.form.get('excludes')
            product.important_notes = request.form.get('important_notes')
            product.updated_by = current_user.username if current_user else None

            db.session.commit()

            flash('产品更新成功', 'success')
            return redirect(url_for('products.detail', product_id=product.id))

        except Exception as e:
            db.session.rollback()
            flash(f'更新失败: {str(e)}', 'error')

    return render_template(
        'business/products/product_form.html',
        product=product,
        categories=ProductCategory.CHOICES,
        sub_categories=ProductSubCategory.CHOICES,
        mode='edit',
    )


@products_bp.route('/delete/<int:product_id>', methods=['POST'])
@login_required
def delete(product_id):
    """删除产品"""
    product = ProductsUnified.query.get_or_404(product_id)

    try:
        db.session.delete(product)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败: {str(e)}', 'error')

    # 保留筛选状态
    return redirect(request.referrer or url_for('products.index'))


@products_bp.route('/status/<int:product_id>', methods=['POST'])
@login_required
def update_status(product_id):
    """更新产品状态"""
    product = ProductsUnified.query.get_or_404(product_id)
    new_status = request.form.get('status')

    if new_status not in ['draft', 'active', 'inactive']:
        return jsonify({'success': False, 'message': '无效的状态'}), 400

    try:
        product.product_status = new_status
        db.session.commit()
        return jsonify({'success': True, 'message': '状态更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ========== API接口 ==========

@products_bp.route('/api/list')
@login_required
def api_list():
    """获取产品列表API"""
    category = request.args.get('category', '')
    status = request.args.get('status', '')
    keyword = request.args.get('keyword', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = ProductsUnified.query

    if category:
        query = query.filter(ProductsUnified.product_category == category)

    if status:
        query = query.filter(ProductsUnified.product_status == status)

    if keyword:
        query = query.filter(
            db.or_(
                ProductsUnified.product_name.ilike(f'%{keyword}%'),
                ProductsUnified.product_code.ilike(f'%{keyword}%'),
            )
        )

    query = query.order_by(ProductsUnified.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'success': True,
        'data': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    })


@products_bp.route('/api/detail/<int:product_id>')
@login_required
def api_detail(product_id):
    """获取产品详情API"""
    product = ProductsUnified.query.get_or_404(product_id)
    return jsonify({
        'success': True,
        'data': product.to_detail_dict()
    })


@products_bp.route('/api/categories')
@login_required
def api_categories():
    """获取产品分类API"""
    categories = []
    for code, name in ProductCategory.CHOICES:
        count = ProductsUnified.query.filter_by(product_category=code).count()
        categories.append({
            'code': code,
            'name': name,
            'count': count
        })

    return jsonify({
        'success': True,
        'data': categories
    })


@products_bp.route('/api/stats')
@login_required
def api_stats():
    """获取产品统计API"""
    total = ProductsUnified.query.count()
    active = ProductsUnified.query.filter_by(product_status='active').count()
    draft = ProductsUnified.query.filter_by(product_status='draft').count()
    inactive = ProductsUnified.query.filter_by(product_status='inactive').count()

    # 按分类统计
    by_category = {}
    for code, name in ProductCategory.CHOICES:
        by_category[code] = {
            'name': name,
            'total': ProductsUnified.query.filter_by(product_category=code).count(),
            'active': ProductsUnified.query.filter_by(product_category=code, product_status='active').count(),
        }

    return jsonify({
        'success': True,
        'data': {
            'total': total,
            'active': active,
            'draft': draft,
            'inactive': inactive,
            'by_category': by_category,
        }
    })


# ========== 签证产品管理 ==========

@products_bp.route('/visa/create', methods=['GET', 'POST'])
@login_required
def create_visa():
    """创建签证产品"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            visa_type_name = request.form.get('visa_type')
            processing_time = request.form.get('processing_time')
            fee = request.form.get('fee')
            cost = request.form.get('cost')
            validity_period = request.form.get('validity_period')
            introduction = request.form.get('introduction')
            country_id = request.form.get('country_id')
            identity_ids = request.form.getlist('identity_ids')
            is_active = request.form.get('is_active') == 'on'

            # 处理时间字段
            valid_until = None
            valid_until_str = request.form.get('valid_until')
            if valid_until_str:
                try:
                    valid_until = datetime.fromisoformat(valid_until_str)
                except ValueError:
                    pass

            # 创建签证类型记录
            new_visa_type = VisaTypes(
                visa_type=visa_type_name,
                processing_time=processing_time,
                fee=fee,
                cost=cost,
                validity_period=validity_period,
                introduction=introduction,
                country_id=country_id,
                valid_until=valid_until,
                is_active=is_active
            )

            # 添加身份关联
            if identity_ids:
                identities = VisaSingaporeIdentity.query.filter(
                    VisaSingaporeIdentity.id.in_(identity_ids)
                ).all()
                for identity in identities:
                    new_visa_type.identities.append(identity)
                    # 创建文档记录
                    new_doc = VisaDocuments(
                        visa_type_id=new_visa_type.id,
                        singapore_identity_id=identity.id
                    )
                    db.session.add(new_doc)

            db.session.add(new_visa_type)
            db.session.commit()

            # 同步到统一产品系统
            product = VisaSyncService.sync_visa_type_to_product(new_visa_type)
            db.session.commit()

            flash('签证产品创建成功！', 'success')
            return redirect(url_for('products.detail', product_id=product.id))

        except Exception as e:
            db.session.rollback()
            flash(f'创建失败: {str(e)}', 'error')
            return redirect(url_for('products.create_visa'))

    # GET 请求 - 显示创建表单
    countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
    singapore_identities = VisaSingaporeIdentity.query.filter(
        VisaSingaporeIdentity.identity_zh != 'SHARE'
    ).order_by(VisaSingaporeIdentity.identity_zh).all()

    return render_template(
        'business/products/visa/create_visa_product.html',
        countries=countries,
        singapore_identities=singapore_identities,
    )


@products_bp.route('/visa/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_visa(product_id):
    """编辑签证产品"""
    product = ProductsUnified.query.get_or_404(product_id)
    ext = ProductsVisaExt.query.filter_by(product_id=product_id).first()

    if not ext or not ext.visa_type_id:
        flash('未找到关联的签证类型', 'error')
        return redirect(url_for('products.detail', product_id=product_id))

    visa_type = VisaTypes.query.get(ext.visa_type_id)
    if not visa_type:
        flash('签证类型不存在', 'error')
        return redirect(url_for('products.detail', product_id=product_id))

    if request.method == 'POST':
        try:
            # 更新签证类型
            new_name = request.form.get('visa_type')
            if new_name and new_name != visa_type.visa_type:
                # 检查名称是否已存在
                existing = VisaTypes.query.filter_by(visa_type=new_name).first()
                if existing:
                    flash('签证类型名称已存在', 'error')
                    return redirect(url_for('products.edit_visa', product_id=product_id))
                visa_type.visa_type = new_name

            visa_type.processing_time = request.form.get('processing_time')
            visa_type.fee = request.form.get('fee')
            visa_type.cost = request.form.get('cost')
            visa_type.validity_period = request.form.get('validity_period')
            visa_type.introduction = request.form.get('introduction')
            visa_type.country_id = request.form.get('country_id')
            visa_type.is_active = request.form.get('is_active') == 'on'

            # 处理有效期
            valid_until_str = request.form.get('valid_until')
            if valid_until_str:
                try:
                    visa_type.valid_until = datetime.fromisoformat(valid_until_str)
                except ValueError:
                    pass

            # 处理身份关联
            identity_ids = request.form.getlist('identity_ids')
            visa_type.identities.clear()
            if identity_ids:
                identities = VisaSingaporeIdentity.query.filter(
                    VisaSingaporeIdentity.id.in_(identity_ids)
                ).all()
                for identity in identities:
                    visa_type.identities.append(identity)

            db.session.commit()

            # 同步到统一产品
            VisaSyncService.sync_visa_type_to_product(visa_type)
            db.session.commit()

            return redirect(url_for('products.detail', product_id=product_id))

        except Exception as e:
            db.session.rollback()
            flash(f'更新失败: {str(e)}', 'error')

    # GET 请求 - 显示编辑表单
    countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
    singapore_identities = VisaSingaporeIdentity.query.filter(
        VisaSingaporeIdentity.identity_zh != 'SHARE'
    ).order_by(VisaSingaporeIdentity.identity_zh).all()

    # 获取当前关联的身份ID
    current_identity_ids = [i.id for i in visa_type.identities]

    return render_template(
        'business/products/visa/edit_visa_product.html',
        product=product,
        visa_type=visa_type,
        countries=countries,
        singapore_identities=singapore_identities,
        current_identity_ids=current_identity_ids,
    )


# ========== 景点门票产品管理 ==========

def _get_ticket_form_context():
    """获取门票表单通用上下文"""
    return {
        'ticket_types': TicketType.CHOICES,
        'delivery_types': TicketDelivery.CHOICES,
        'people_types': PeopleType.CHOICES,
    }


def _save_ticket_prices(product_id, form):
    """保存门票价格数据"""
    people_types = form.getlist('price_people_type[]')
    costs = form.getlist('price_cost[]')
    sellings = form.getlist('price_selling[]')
    originals = form.getlist('price_original[]')
    price_ids = form.getlist('price_id[]')

    # 收集提交的已有价格ID
    submitted_ids = set()
    for pid in price_ids:
        if pid:
            submitted_ids.add(int(pid))

    # 删除被移除的价格行
    existing_prices = ProductsPrice.query.filter_by(product_id=product_id).all()
    for ep in existing_prices:
        if ep.id not in submitted_ids:
            db.session.delete(ep)

    # 更新或创建价格
    for i in range(len(people_types)):
        selling_val = sellings[i].strip() if i < len(sellings) else ''
        if not selling_val:
            continue

        cost_val = costs[i].strip() if i < len(costs) else ''
        original_val = originals[i].strip() if i < len(originals) else ''
        price_id = price_ids[i].strip() if i < len(price_ids) else ''

        if price_id:
            # 更新已有价格
            price = ProductsPrice.query.get(int(price_id))
            if price:
                price.people_type = people_types[i]
                price.cost_price = float(cost_val) if cost_val else None
                price.selling_price = float(selling_val)
                price.original_price = float(original_val) if original_val else None
        else:
            # 新建价格
            price = ProductsPrice(
                product_id=product_id,
                price_type='standard',
                people_type=people_types[i],
                cost_price=float(cost_val) if cost_val else None,
                selling_price=float(selling_val),
                original_price=float(original_val) if original_val else None,
                currency='SGD',
                is_active=True,
            )
            db.session.add(price)


@products_bp.route('/ticket/create', methods=['GET', 'POST'])
@login_required
def create_ticket():
    """创建景点门票产品"""
    if request.method == 'POST':
        try:
            product_name = request.form.get('product_name')
            if not product_name:
                flash('请填写景点名称', 'error')
                return redirect(url_for('products.create_ticket'))

            product_code = ProductsUnified.generate_product_code(ProductCategory.TICKET)

            product = ProductsUnified(
                product_code=product_code,
                product_name=product_name,
                product_name_en=request.form.get('product_name_en'),
                product_short_name=request.form.get('product_short_name'),
                product_category=ProductCategory.TICKET,
                product_status='draft',
                country=request.form.get('country'),
                city=request.form.get('city'),
                currency='SGD',
                cover_image=request.form.get('cover_image') or None,
                description=request.form.get('description'),
                includes=request.form.get('includes'),
                excludes=request.form.get('excludes'),
                important_notes=request.form.get('important_notes'),
                created_by=current_user.username if current_user else None,
            )
            db.session.add(product)
            db.session.flush()

            ticket_ext = ProductsTicketExt(
                product_id=product.id,
                ticket_type=request.form.get('ticket_type'),
                venue_name=request.form.get('venue_name'),
                venue_address=request.form.get('venue_address'),
                opening_hours=request.form.get('opening_hours'),
                duration_minutes=request.form.get('duration_minutes', type=int),
                delivery_type=request.form.get('delivery_type', 'e_ticket'),
                entry_method=request.form.get('entry_method'),
                tips=request.form.get('tips'),
                age_limit=request.form.get('age_limit'),
                height_limit=request.form.get('height_limit'),
                health_requirement=request.form.get('health_requirement'),
                need_reservation=request.form.get('need_reservation') == 'on',
            )
            db.session.add(ticket_ext)
            db.session.flush()
            product.ext_table_id = ticket_ext.id

            # 保存价格
            _save_ticket_prices(product.id, request.form)

            adult_price = ProductsPrice.query.filter_by(
                product_id=product.id, people_type='adult'
            ).first()
            if adult_price:
                product.base_price = adult_price.selling_price
                product.cost_price = adult_price.cost_price

            db.session.commit()
            flash('门票产品创建成功', 'success')
            return redirect(url_for('products.detail', product_id=product.id))

        except Exception as e:
            db.session.rollback()
            flash(f'创建失败: {str(e)}', 'error')
            return redirect(url_for('products.create_ticket'))

    # GET 请求
    context = _get_ticket_form_context()
    context.update({
        'product': None,
        'ticket_ext': None,
        'prices': [],
        'mode': 'create',
    })
    return render_template('business/products/ticket/create_ticket_product.html', **context)


@products_bp.route('/ticket/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_ticket(product_id):
    """编辑景点门票产品"""
    product = ProductsUnified.query.get_or_404(product_id)
    ticket_ext = ProductsTicketExt.query.filter_by(product_id=product_id).first()

    if request.method == 'POST':
        try:
            product.product_name = request.form.get('product_name')
            product.product_name_en = request.form.get('product_name_en')
            product.product_short_name = request.form.get('product_short_name')
            product.country = request.form.get('country')
            product.city = request.form.get('city')
            product.description = request.form.get('description')
            product.includes = request.form.get('includes')
            product.excludes = request.form.get('excludes')
            product.important_notes = request.form.get('important_notes')
            product.cover_image = request.form.get('cover_image') or None
            product.updated_by = current_user.username if current_user else None

            # 更新或创建门票扩展
            if not ticket_ext:
                ticket_ext = ProductsTicketExt(product_id=product_id)
                db.session.add(ticket_ext)

            ticket_ext.ticket_type = request.form.get('ticket_type')
            ticket_ext.venue_name = request.form.get('venue_name')
            ticket_ext.venue_address = request.form.get('venue_address')
            ticket_ext.opening_hours = request.form.get('opening_hours')
            ticket_ext.duration_minutes = request.form.get('duration_minutes', type=int)
            ticket_ext.delivery_type = request.form.get('delivery_type', 'e_ticket')
            ticket_ext.entry_method = request.form.get('entry_method')
            ticket_ext.tips = request.form.get('tips')
            ticket_ext.age_limit = request.form.get('age_limit')
            ticket_ext.height_limit = request.form.get('height_limit')
            ticket_ext.health_requirement = request.form.get('health_requirement')
            ticket_ext.need_reservation = request.form.get('need_reservation') == 'on'

            db.session.commit()
            flash('门票产品更新成功', 'success')
            return redirect(url_for('products.edit_ticket', product_id=product.id))

        except Exception as e:
            db.session.rollback()
            flash(f'更新失败: {str(e)}', 'error')

    # GET 请求 - 获取变体列表
    ticket_variants = ProductsTicketVariant.query.filter_by(
        product_id=product_id
    ).order_by(ProductsTicketVariant.sort_order, ProductsTicketVariant.id).all()

    context = _get_ticket_form_context()
    context.update({
        'product': product,
        'ticket_ext': ticket_ext,
        'ticket_variants': ticket_variants,
        'mode': 'edit',
    })
    return render_template('business/products/ticket/create_ticket_product.html', **context)


@products_bp.route('/ticket/list')
@login_required
def ticket_list():
    """景点门票产品列表"""
    # 筛选参数
    keyword = request.args.get('keyword', '').strip()
    ticket_type = request.args.get('ticket_type', '')
    country = request.args.get('country', '')
    status = request.args.get('status', '')
    sort = request.args.get('sort', '')  # 排序：views_desc / views_asc
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # 查询门票产品（不再有子产品，parent_id 不影响）
    query = ProductsUnified.query.outerjoin(
        ProductsTicketExt, ProductsTicketExt.product_id == ProductsUnified.id
    ).filter(
        ProductsUnified.product_category == 'ticket',
        ProductsUnified.parent_id.is_(None)
    )

    if keyword:
        query = query.filter(
            db.or_(
                ProductsUnified.product_name.ilike(f'%{keyword}%'),
                ProductsUnified.product_name_en.ilike(f'%{keyword}%'),
                ProductsUnified.product_code.ilike(f'%{keyword}%'),
                ProductsTicketExt.venue_name.ilike(f'%{keyword}%'),
            )
        )
    if ticket_type:
        query = query.filter(ProductsTicketExt.ticket_type == ticket_type)
    if country:
        query = query.filter(ProductsUnified.country == country)
    if status:
        query = query.filter(ProductsUnified.product_status == status)

    # 排序
    if sort == 'views_desc':
        query = query.order_by(ProductsUnified.view_count.desc(), ProductsUnified.created_at.desc())
    elif sort == 'views_asc':
        query = query.order_by(ProductsUnified.view_count.asc(), ProductsUnified.created_at.desc())
    else:
        query = query.order_by(ProductsUnified.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    products = pagination.items

    # 为每个产品补充扩展信息和变体列表
    for p in products:
        p._ticket_ext = ProductsTicketExt.query.filter_by(product_id=p.id).first()

        # 获取该产品的所有变体
        p._variants = ProductsTicketVariant.query.filter_by(product_id=p.id).order_by(
            ProductsTicketVariant.sort_order, ProductsTicketVariant.id
        ).all()
        p._variant_count = len(p._variants)

    # 国家列表（仅门票产品中的）
    countries = [c[0] for c in db.session.query(ProductsUnified.country).filter(
        ProductsUnified.product_category == 'ticket',
        ProductsUnified.country.isnot(None),
        ProductsUnified.country != ''
    ).distinct().order_by(ProductsUnified.country).all()]

    return render_template(
        'business/products/ticket/ticket_list.html',
        products=products,
        pagination=pagination,
        ticket_types=TicketType.CHOICES,
        countries=countries,
        current_filters={
            'keyword': keyword,
            'ticket_type': ticket_type,
            'country': country,
            'status': status,
            'sort': sort,
        }
    )


@products_bp.route('/ticket/<int:product_id>/toggle-status', methods=['POST'])
@login_required
def ticket_toggle_status(product_id):
    """切换门票产品状态"""
    product = ProductsUnified.query.get_or_404(product_id)
    if product.product_status == 'active':
        product.product_status = 'inactive'
    else:
        product.product_status = 'active'
    product.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'new_status': product.product_status})


@products_bp.route('/ticket/<int:product_id>/delete', methods=['POST'])
@login_required
def ticket_delete(product_id):
    """删除门票产品（同时删除扩展信息和变体）"""
    product = ProductsUnified.query.get_or_404(product_id)
    if product.product_category != 'ticket':
        return jsonify({'success': False, 'message': '该产品不是门票类型'}), 400

    try:
        # 删除变体
        ProductsTicketVariant.query.filter_by(product_id=product.id).delete()
        # 删除扩展信息
        ProductsTicketExt.query.filter_by(product_id=product.id).delete()
        # 删除主产品
        db.session.delete(product)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@products_bp.route('/ticket/variant/<int:variant_id>')
@login_required
def ticket_variant_get(variant_id):
    """获取单个变体详情（AJAX）"""
    variant = ProductsTicketVariant.query.get_or_404(variant_id)
    return jsonify({'success': True, 'variant': variant.to_dict()})


@products_bp.route('/ticket/<int:product_id>/variant/add', methods=['POST'])
@login_required
def ticket_variant_add(product_id):
    """添加变体（AJAX）"""
    product = ProductsUnified.query.get_or_404(product_id)
    if product.product_category != 'ticket':
        return jsonify({'success': False, 'message': '仅门票产品支持变体'})

    data = request.get_json()
    if not data or not data.get('variant_name'):
        return jsonify({'success': False, 'message': '变体名称不能为空'})

    variant = ProductsTicketVariant(
        product_id=product_id,
        variant_name=data['variant_name'],
        variant_name_en=data.get('variant_name_en') or None,
        description=data.get('description') or None,
        adult_selling_price=data.get('adult_selling_price') or None,
        adult_cost_price=data.get('adult_cost_price') or None,
        child_selling_price=data.get('child_selling_price') or None,
        child_cost_price=data.get('child_cost_price') or None,
        date_type=data.get('date_type') or 'open',
        delivery_type=data.get('delivery_type') or 'e_ticket',
        includes=data.get('includes') or None,
        excludes=data.get('excludes') or None,
        important_notes=data.get('important_notes') or None,
        sort_order=data.get('sort_order', 0),
        is_active=data.get('is_active', True),
    )
    db.session.add(variant)
    db.session.commit()
    return jsonify({'success': True, 'variant': variant.to_dict()})


@products_bp.route('/ticket/variant/<int:variant_id>/edit', methods=['POST'])
@login_required
def ticket_variant_edit(variant_id):
    """编辑变体（AJAX）"""
    variant = ProductsTicketVariant.query.get_or_404(variant_id)
    data = request.get_json()
    if not data or not data.get('variant_name'):
        return jsonify({'success': False, 'message': '变体名称不能为空'})

    variant.variant_name = data['variant_name']
    variant.variant_name_en = data.get('variant_name_en') or None
    variant.description = data.get('description') or None
    variant.adult_selling_price = data.get('adult_selling_price') or None
    variant.adult_cost_price = data.get('adult_cost_price') or None
    variant.child_selling_price = data.get('child_selling_price') or None
    variant.child_cost_price = data.get('child_cost_price') or None
    variant.date_type = data.get('date_type') or 'open'
    variant.delivery_type = data.get('delivery_type') or 'e_ticket'
    variant.includes = data.get('includes') or None
    variant.excludes = data.get('excludes') or None
    variant.important_notes = data.get('important_notes') or None
    variant.sort_order = data.get('sort_order', 0)
    variant.is_active = data.get('is_active', True)
    variant.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify({'success': True, 'variant': variant.to_dict()})


@products_bp.route('/ticket/variant/<int:variant_id>/delete', methods=['POST'])
@login_required
def ticket_variant_delete(variant_id):
    """删除变体（AJAX）"""
    variant = ProductsTicketVariant.query.get_or_404(variant_id)
    db.session.delete(variant)
    db.session.commit()
    return jsonify({'success': True})


@products_bp.route('/ticket/import', methods=['POST'])
@login_required
def ticket_import_excel():
    """Excel批量导入门票产品"""
    try:
        if 'excel_file' not in request.files:
            flash('请选择要上传的文件', 'error')
            return redirect(url_for('products.ticket_list'))

        file = request.files['excel_file']
        if file.filename == '' or not file.filename.endswith(('.xlsx', '.xls')):
            flash('只支持 .xlsx 和 .xls 格式的文件', 'error')
            return redirect(url_for('products.ticket_list'))

        df = pd.read_excel(file)

        # 验证必要列
        required_columns = ['产品名称']
        for col in required_columns:
            if col not in df.columns:
                flash(f'缺少必要的列: {col}', 'error')
                return redirect(url_for('products.ticket_list'))

        added_count = 0
        updated_count = 0
        error_count = 0

        # 门票类型映射
        ticket_type_map = {
            '景区门票': 'scenic', '景区': 'scenic',
            '演出门票': 'show', '演出': 'show',
            '活动体验': 'activity', '活动': 'activity',
            '博物馆': 'museum',
            '主题乐园': 'theme_park',
            '水上乐园': 'water_park',
        }

        def _parse_str(val):
            """解析字符串，返回None或有效字符串"""
            if pd.isna(val):
                return None
            s = str(val).strip()
            return s if s and s != 'nan' else None

        def _parse_price(val):
            """解析价格"""
            try:
                if pd.notna(val):
                    return float(val)
            except (ValueError, TypeError):
                pass
            return None

        def _import_main_product(index, row):
            """导入主产品行"""
            nonlocal added_count, updated_count, error_count

            product_name = _parse_str(row.get('产品名称'))
            if not product_name:
                return None

            product_name_en = _parse_str(row.get('英文名称'))
            product_code = _parse_str(row.get('产品编号'))
            country = _parse_str(row.get('国家'))
            city = _parse_str(row.get('城市'))
            venue_name = _parse_str(row.get('场馆名称'))
            venue_address = _parse_str(row.get('场馆地址'))
            ticket_type_str = _parse_str(row.get('门票类型'))
            ticket_type_val = ticket_type_map.get(ticket_type_str, ticket_type_str) if ticket_type_str else None

            is_active_str = str(row.get('状态', '')).strip().lower() if pd.notna(row.get('状态')) else ''
            is_active = is_active_str in ['激活', '已激活', 'active', 'yes', '是', '1', 'true']

            # 查找已有产品
            existing = None
            if product_code:
                existing = ProductsUnified.query.filter_by(product_code=product_code, product_category='ticket').first()
            if not existing:
                existing = ProductsUnified.query.filter_by(
                    product_name=product_name, product_category='ticket', parent_id=None
                ).first()

            if existing:
                existing.product_name = product_name
                if product_name_en:
                    existing.product_name_en = product_name_en
                if country:
                    existing.country = country
                if city:
                    existing.city = city
                existing.product_status = 'active' if is_active else 'inactive'
                existing.updated_at = datetime.utcnow()

                ext = ProductsTicketExt.query.filter_by(product_id=existing.id).first()
                if ext:
                    if ticket_type_val:
                        ext.ticket_type = ticket_type_val
                    if venue_name:
                        ext.venue_name = venue_name
                    if venue_address:
                        ext.venue_address = venue_address

                updated_count += 1
                return existing
            else:
                new_code = ProductsUnified.generate_product_code('ticket')
                product = ProductsUnified(
                    product_code=new_code,
                    product_name=product_name,
                    product_name_en=product_name_en,
                    product_category='ticket',
                    product_status='active' if is_active else 'inactive',
                    country=country,
                    city=city,
                    currency='SGD',
                    created_by=current_user.username if current_user.is_authenticated else None,
                )
                db.session.add(product)
                db.session.flush()

                ext = ProductsTicketExt(
                    product_id=product.id,
                    ticket_type=ticket_type_val,
                    venue_name=venue_name,
                    venue_address=venue_address,
                )
                db.session.add(ext)
                db.session.flush()
                product.ext_table_id = ext.id

                added_count += 1
                return product

        def _import_variant(index, row, parent_product):
            """导入变体行到 products_ticket_variant"""
            nonlocal added_count, updated_count

            variant_name = _parse_str(row.get('产品名称'))
            if not variant_name:
                return

            variant_name_en = _parse_str(row.get('英文名称'))
            description = _parse_str(row.get('描述'))
            adult_selling = _parse_price(row.get('成人售价'))
            adult_cost = _parse_price(row.get('成人成本'))
            child_selling = _parse_price(row.get('儿童售价'))
            child_cost = _parse_price(row.get('儿童成本'))

            is_active_str = str(row.get('状态', '')).strip().lower() if pd.notna(row.get('状态')) else ''
            is_active = is_active_str in ['激活', '已激活', 'active', 'yes', '是', '1', 'true']

            # 查找已有变体（按名称匹配）
            existing = ProductsTicketVariant.query.filter_by(
                product_id=parent_product.id, variant_name=variant_name
            ).first()

            if existing:
                if variant_name_en:
                    existing.variant_name_en = variant_name_en
                if description:
                    existing.description = description
                if adult_selling is not None:
                    existing.adult_selling_price = adult_selling
                if adult_cost is not None:
                    existing.adult_cost_price = adult_cost
                if child_selling is not None:
                    existing.child_selling_price = child_selling
                if child_cost is not None:
                    existing.child_cost_price = child_cost
                existing.is_active = is_active
                existing.updated_at = datetime.utcnow()
                updated_count += 1
            else:
                variant = ProductsTicketVariant(
                    product_id=parent_product.id,
                    variant_name=variant_name,
                    variant_name_en=variant_name_en,
                    description=description,
                    adult_selling_price=adult_selling,
                    adult_cost_price=adult_cost,
                    child_selling_price=child_selling,
                    child_cost_price=child_cost,
                    is_active=is_active,
                )
                db.session.add(variant)
                added_count += 1

        # === 分两轮导入：第一轮主产品，第二轮变体 ===
        parent_rows = []
        variant_rows = []

        for index, row in df.iterrows():
            parent_ref = _parse_str(row.get('主产品编号'))
            if parent_ref:
                variant_rows.append((index, row, parent_ref))
            else:
                parent_rows.append((index, row))

        # 第一轮：导入主产品
        for index, row in parent_rows:
            try:
                _import_main_product(index, row)
            except Exception as row_error:
                print(f"处理第 {index + 2} 行时出错: {row_error}")
                error_count += 1

        db.session.flush()

        # 第二轮：导入变体到 products_ticket_variant
        for index, row, parent_ref in variant_rows:
            try:
                parent_product = ProductsUnified.query.filter_by(
                    product_code=parent_ref, product_category='ticket'
                ).first()
                if not parent_product:
                    parent_product = ProductsUnified.query.filter_by(
                        product_name=parent_ref, product_category='ticket'
                    ).first()

                if not parent_product:
                    print(f"第 {index + 2} 行：主产品 '{parent_ref}' 不存在，跳过")
                    error_count += 1
                    continue

                _import_variant(index, row, parent_product)
            except Exception as row_error:
                print(f"处理第 {index + 2} 行时出错: {row_error}")
                error_count += 1

        db.session.commit()

        result_msg = f'导入完成：新增 {added_count} 条，更新 {updated_count} 条'
        if error_count > 0:
            result_msg += f'，失败 {error_count} 条'
        flash(result_msg, 'success' if error_count == 0 else 'warning')

    except Exception as e:
        db.session.rollback()
        flash(f'导入失败: {str(e)}', 'error')

    return redirect(url_for('products.ticket_list'))


@products_bp.route('/ticket/export')
@login_required
def ticket_export():
    """导出门票产品为Excel"""
    # 筛选参数（与列表页一致）
    keyword = request.args.get('keyword', '').strip()
    ticket_type = request.args.get('ticket_type', '')
    country = request.args.get('country', '')
    status = request.args.get('status', '')

    # 查询门票主产品
    query = ProductsUnified.query.outerjoin(
        ProductsTicketExt, ProductsTicketExt.product_id == ProductsUnified.id
    ).filter(
        ProductsUnified.product_category == 'ticket',
        ProductsUnified.parent_id.is_(None)
    )

    if keyword:
        query = query.filter(
            db.or_(
                ProductsUnified.product_name.ilike(f'%{keyword}%'),
                ProductsUnified.product_name_en.ilike(f'%{keyword}%'),
                ProductsUnified.product_code.ilike(f'%{keyword}%'),
                ProductsTicketExt.venue_name.ilike(f'%{keyword}%'),
            )
        )
    if ticket_type:
        query = query.filter(ProductsTicketExt.ticket_type == ticket_type)
    if country:
        query = query.filter(ProductsUnified.country == country)
    if status:
        query = query.filter(ProductsUnified.product_status == status)

    products = query.order_by(ProductsUnified.sort_order, ProductsUnified.id).all()

    ticket_type_label = {
        'scenic': '景区门票', 'show': '演出门票', 'activity': '活动体验',
        'museum': '博物馆', 'theme_park': '主题乐园', 'water_park': '水上乐园',
    }

    rows = []
    for p in products:
        ext = ProductsTicketExt.query.filter_by(product_id=p.id).first()

        # 主产品行
        rows.append({
            '产品编号': p.product_code or '',
            '主产品编号': '',
            '产品名称': p.product_name or '',
            '英文名称': p.product_name_en or '',
            '门票类型': ticket_type_label.get(ext.ticket_type, ext.ticket_type) if ext and ext.ticket_type else '',
            '国家': p.country or '',
            '城市': p.city or '',
            '场馆名称': ext.venue_name if ext and ext.venue_name else '',
            '场馆地址': ext.venue_address if ext and ext.venue_address else '',
            '成人售价': '',
            '成人成本': '',
            '儿童售价': '',
            '儿童成本': '',
            '状态': '激活' if p.product_status == 'active' else '未激活',
        })

        # 变体行
        variants = ProductsTicketVariant.query.filter_by(product_id=p.id).order_by(
            ProductsTicketVariant.sort_order, ProductsTicketVariant.id
        ).all()
        for v in variants:
            rows.append({
                '产品编号': '',
                '主产品编号': p.product_code or p.product_name,
                '产品名称': v.variant_name or '',
                '英文名称': v.variant_name_en or '',
                '门票类型': '',
                '国家': '',
                '城市': '',
                '场馆名称': '',
                '场馆地址': '',
                '成人售价': float(v.adult_selling_price) if v.adult_selling_price else '',
                '成人成本': float(v.adult_cost_price) if v.adult_cost_price else '',
                '儿童售价': float(v.child_selling_price) if v.child_selling_price else '',
                '儿童成本': float(v.child_cost_price) if v.child_cost_price else '',
                '状态': '激活' if v.is_active else '未激活',
            })

    df = pd.DataFrame(rows)
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    filename = f'ticket_products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    return send_file(output, download_name=filename, as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@products_bp.route('/ticket/import-template')
@login_required
def ticket_import_template():
    """下载门票产品导入模板"""
    df = pd.DataFrame(columns=[
        '产品编号', '主产品编号', '产品名称', '英文名称', '门票类型',
        '国家', '城市', '场馆名称', '场馆地址',
        '成人售价', '成人成本', '儿童售价', '儿童成本', '状态'
    ])
    # 示例行：主产品（主产品编号留空）
    df.loc[0] = ['', '', '新加坡环球影城', 'Universal Studios Singapore', '主题乐园',
                 'Singapore', 'Sentosa', 'Universal Studios', '8 Sentosa Gateway',
                 '', '', '', '', '激活']
    # 示例行：子产品（主产品编号填写编号或名称均可）
    df.loc[1] = ['', '新加坡环球影城', '普通门票', 'Standard Ticket', '',
                 '', '', '', '',
                 '88.00', '65.00', '68.00', '50.00', '激活']
    df.loc[2] = ['', '新加坡环球影城', '快捷通道门票', 'Express Pass', '',
                 '', '', '', '',
                 '168.00', '120.00', '128.00', '90.00', '激活']
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return send_file(output, download_name='ticket_import_template.xlsx', as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
