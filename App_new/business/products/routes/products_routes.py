# -*- coding: utf-8 -*-
"""
统一产品管理路由
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
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
    keyword = request.args.get('keyword', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # 构建查询
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

    return render_template(
        'business/products/product_list.html',
        products=products,
        pagination=pagination,
        categories=ProductCategory.CHOICES,
        category_counts=category_counts,
        current_category=category,
        current_status=status,
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

    return render_template(
        'business/products/product_detail.html',
        product=product,
        prices=prices,
        rules=rules,
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
        flash('产品删除成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败: {str(e)}', 'error')

    return redirect(url_for('products.index'))


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
