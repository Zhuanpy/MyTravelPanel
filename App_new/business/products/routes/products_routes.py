# -*- coding: utf-8 -*-
"""
统一产品管理路由
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
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
        return redirect(url_for('visa_basic.visa_type_list'))
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
