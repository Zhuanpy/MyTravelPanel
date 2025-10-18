# -*- coding: utf-8 -*-
"""
旅游产品管理蓝图
包含产品的CRUD操作
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
import pandas as pd
from io import BytesIO

from sqlalchemy import or_
from openpyxl.utils import get_column_letter

from App_new.exts import db, csrf
from App_new.business.tour.models.Packagemodels import Product, ProductItinerary, ProductPriceVariant
from App_new.shared.models.Suppliers import Supplier
from App_new.utils.decorators import staff_only

# 创建蓝图
tour_products_bp = Blueprint('tour_products', __name__, url_prefix='/tour/products')

# 允许的图片扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file, upload_folder='uploads/tour_products'):
    """保存上传的文件，返回相对路径（相对于 App_new/static）"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{timestamp}{ext}"

        upload_path = os.path.join('App_new/static', upload_folder)
        os.makedirs(upload_path, exist_ok=True)

        filepath = os.path.join(upload_path, filename)
        file.save(filepath)

        # 返回存入数据库使用的相对路径
        return os.path.join(upload_folder, filename).replace('\\', '/')
    return None


@tour_products_bp.route('/')
@tour_products_bp.route('/list')
@login_required
@staff_only
def product_list():
    """产品列表页面 - 支持筛选、搜索和分页"""
    # 获取筛选参数
    supplier_id = request.args.get('supplier', type=int)
    country = request.args.get('country', '')
    city = request.args.get('city', '')
    status = request.args.get('status', '')
    keyword = request.args.get('keyword', '')
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)  # 每页20个产品

    query = Product.query

    if supplier_id:
        query = query.filter(Product.supplier_id == supplier_id)
    if country:
        # 通过 city 关联筛选国家
        from App_new.business.tour.models.Packagemodels import ProductCity
        query = query.join(ProductCity, Product.city_id == ProductCity.id).filter(ProductCity.country_name == country)
    if city:
        query = query.filter(Product.city_name == city)
    if status:
        query = query.filter(Product.product_status == status)
    if keyword:
        query = query.filter(
            or_(
                Product.product_name.like(f'%{keyword}%'),
                Product.product_description.like(f'%{keyword}%')
            )
        )

    # 执行分页查询
    pagination = query.order_by(Product.created_at.desc()).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    products = pagination.items

    # 添加产品显示属性
    from datetime import date
    today = date.today()
    for product in products:
        if product.supplier:
            product.supplier_display_name = product.supplier.name
        else:
            product.supplier_display_name = '未指定供应商'
        
        # 判断是否过期
        product.is_expired = (product.valid_until and product.valid_until < today)
        
        # 确保所有字段都不显示 None
        if product.product_description == 'None':
            product.product_description = None
        if product.country == 'None':
            product.country = '未知'
        if product.city_name == 'None':
            product.city_name = None
        if product.departure_city == 'None':
            product.departure_city = None
        if product.destination_city == 'None':
            product.destination_city = None

    suppliers = Supplier.query.filter(
        Supplier.supplier_type.in_(['tour_operator', 'travel_agency', 'local_operator'])
    ).order_by(Supplier.name).all()

    # 从 ProductCity 表获取国家列表
    from App_new.business.tour.models.Packagemodels import ProductCity
    countries = db.session.query(ProductCity.country_name).filter(
        ProductCity.country_name.isnot(None)
    ).distinct().order_by(ProductCity.country_name).all()
    countries = [c[0] for c in countries if c[0]]

    cities = db.session.query(Product.city_name).filter(
        Product.city_name.isnot(None)
    ).distinct().order_by(Product.city_name).all()
    cities = [c[0] for c in cities if c[0]]

    return render_template('business/tour/products/product_list.html',
                         products=products,
                         pagination=pagination,
                         suppliers=suppliers,
                         countries=countries,
                         cities=cities,
                         current_filters={
                             'supplier': supplier_id,
                             'country': country,
                             'city': city,
                             'status': status,
                             'keyword': keyword
                         })


@tour_products_bp.route('/add', methods=['GET', 'POST'])
@login_required
@staff_only
def add_product():
    """添加产品"""
    if request.method == 'POST':
        try:
            tags_input = request.form.get('tags', '').strip()
            tags_list = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
            tags_json = json.dumps(tags_list, ensure_ascii=False)

            cover_image_path = None
            if 'cover_image' in request.files:
                cover_file = request.files['cover_image']
                cover_image_path = save_uploaded_file(cover_file)

            gallery_paths = []
            if 'gallery_images' in request.files:
                gallery_files = request.files.getlist('gallery_images')
                for file in gallery_files:
                    if file and file.filename:
                        path = save_uploaded_file(file)
                        if path:
                            gallery_paths.append(path)
            gallery_json = json.dumps(gallery_paths) if gallery_paths else None

            # 解析并转换表单字段（做了类型保护）
            supplier_id = request.form.get('supplier_id') or None
            if supplier_id:
                try:
                    supplier_id = int(supplier_id)
                except ValueError:
                    supplier_id = None

            # 处理 city_id（从 city_name 获取）
            city_name = request.form.get('city_name')
            city_id = None
            if city_name:
                from App_new.business.tour.models.Packagemodels import ProductCity
                city = ProductCity.query.filter_by(city_name=city_name).first()
                if city:
                    city_id = city.id

            # 安全转换数字字段
            duration_days = request.form.get('duration_days', '').strip()
            duration_days_val = int(duration_days) if duration_days else None
            
            min_pax = request.form.get('min_pax', '1').strip()
            min_pax_val = int(min_pax) if min_pax else 1
            
            max_pax = request.form.get('max_pax', '').strip()
            max_pax_val = int(max_pax) if max_pax else None
            
            base_price = request.form.get('base_price', '').strip()
            base_price_val = float(base_price) if base_price else None
            
            child_price = request.form.get('child_price', '').strip()
            child_price_val = float(child_price) if child_price else None
            
            infant_price = request.form.get('infant_price', '').strip()
            infant_price_val = float(infant_price) if infant_price else None
            
            single_supplement = request.form.get('single_room_supplement', '').strip()
            single_supplement_val = float(single_supplement) if single_supplement else None
            
            is_featured = request.form.get('is_featured', '0').strip()
            is_featured_val = bool(int(is_featured)) if is_featured else False
            
            valid_from = request.form.get('valid_from', '').strip()
            valid_from_val = datetime.strptime(valid_from, '%Y-%m-%d').date() if valid_from else None
            
            valid_until = request.form.get('valid_until', '').strip()
            valid_until_val = datetime.strptime(valid_until, '%Y-%m-%d').date() if valid_until else None

            product = Product(
                product_name=request.form['product_name'],
                supplier_id=supplier_id,
                product_code=request.form.get('product_code') or None,
                city_id=city_id,
                city_name=city_name,
                departure_city=request.form.get('departure_city') or None,
                destination_city=request.form.get('destination_city') or None,
                product_type=request.form.get('product_type') or None,
                duration_days=duration_days_val,
                min_pax=min_pax_val,
                max_pax=max_pax_val,
                base_price=base_price_val,
                child_price=child_price_val,
                infant_price=infant_price_val,
                single_room_supplement=single_supplement_val,
                currency=request.form.get('currency', 'SGD'),
                product_description=request.form.get('product_description') or None,
                highlights=request.form.get('highlights') or None,
                included_services=request.form.get('included_services') or None,
                excluded_services=request.form.get('excluded_services') or None,
                important_notes=request.form.get('important_notes') or None,
                suitable_season=request.form.get('suitable_season') or None,
                difficulty_level=request.form.get('difficulty_level') or None,
                tags=tags_json,
                cover_image=cover_image_path,
                gallery_images=gallery_json,
                product_status=request.form.get('product_status', 'draft'),
                is_featured=is_featured_val,
                valid_from=valid_from_val,
                valid_until=valid_until_val,
                created_by=current_user.username
            )

            db.session.add(product)
            db.session.commit()

            flash('产品创建成功！', 'success')
            return redirect(url_for('tour_products.product_detail', product_id=product.id))

        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            flash(f'创建失败：{str(e)}', 'error')

    suppliers = Supplier.query.filter(
        Supplier.supplier_type.in_(['tour_operator', 'travel_agency', 'local_operator'])
    ).order_by(Supplier.name).all()

    return render_template('business/tour/products/product_form.html',
                         product=None,
                         suppliers=suppliers,
                         itineraries=[])


@tour_products_bp.route('/<int:product_id>')
@login_required
@staff_only
def product_detail(product_id):
    """产品详情页"""
    product = Product.query.get_or_404(product_id)
    itineraries = ProductItinerary.query.filter_by(product_id=product_id).order_by(ProductItinerary.day_number).all()

    return render_template('business/tour/products/product_detail.html',
                         product=product,
                         itineraries=itineraries)


@tour_products_bp.route('/<int:product_id>/itinerary/<int:itinerary_id>')
@login_required
@staff_only
def get_itinerary(product_id, itinerary_id):
    try:
        itinerary = ProductItinerary.query.get_or_404(itinerary_id)
        if itinerary.product_id != product_id:
            return jsonify({'success': False, 'message': '行程不属于该产品'}), 400
        return jsonify({'success': True, 'itinerary': itinerary.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@tour_products_bp.route('/<int:product_id>/itinerary/add', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def add_itinerary(product_id):
    """添加行程 - API"""
    try:
        # 添加调试日志
        print(f"=== 添加行程 ===")
        print(f"Product ID: {product_id}")
        print(f"Form data: {dict(request.form)}")
        print(f"Files: {list(request.files.keys())}")
        
        product = Product.query.get_or_404(product_id)

        # 获取表单数据，使用 get 方法防止 KeyError
        day_number = request.form.get('day_number')
        day_title = request.form.get('day_title')
        
        if not day_number or not day_title:
            return jsonify({'success': False, 'message': '天数和行程安排不能为空'}), 400
        
        itinerary = ProductItinerary(
            product_id=product_id,
            day_number=int(day_number),
            day_title=day_title
        )

        for i in range(1, 4):
            img_field = f'image{i}'
            if img_field in request.files:
                img_file = request.files[img_field]
                if img_file and img_file.filename:
                    img_path = save_uploaded_file(img_file, upload_folder='uploads/tour_itinerary')
                    if img_path:
                        setattr(itinerary, img_field, img_path)

        db.session.add(itinerary)
        db.session.commit()
        
        print(f"✅ 行程添加成功！ID: {itinerary.id}")
        return jsonify({'success': True, 'message': '行程添加成功！'})

    except Exception as e:
        db.session.rollback()
        print(f"❌ 添加行程失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'保存失败：{str(e)}'}), 500


@tour_products_bp.route('/<int:product_id>/itinerary/<int:itinerary_id>/update', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def update_itinerary(product_id, itinerary_id):
    try:
        # 添加调试日志
        print(f"=== 更新行程 ===")
        print(f"Product ID: {product_id}, Itinerary ID: {itinerary_id}")
        print(f"Form data: {dict(request.form)}")
        print(f"Files: {list(request.files.keys())}")
        
        itinerary = ProductItinerary.query.get_or_404(itinerary_id)
        if itinerary.product_id != product_id:
            return jsonify({'success': False, 'message': '行程不属于该产品'}), 400

        # 获取表单数据，使用 get 方法防止 KeyError
        day_number = request.form.get('day_number')
        day_title = request.form.get('day_title')
        
        if not day_number or not day_title:
            return jsonify({'success': False, 'message': '天数和行程安排不能为空'}), 400
        
        itinerary.day_number = int(day_number)
        itinerary.day_title = day_title

        for i in range(1, 4):
            img_field = f'image{i}'
            if img_field in request.files:
                img_file = request.files[img_field]
                if img_file and img_file.filename:
                    img_path = save_uploaded_file(img_file, upload_folder='uploads/tour_itinerary')
                    if img_path:
                        setattr(itinerary, img_field, img_path)

        itinerary.updated_at = datetime.utcnow()
        db.session.commit()
        
        print(f"✅ 行程更新成功！ID: {itinerary.id}")
        return jsonify({'success': True, 'message': '行程更新成功！'})

    except Exception as e:
        db.session.rollback()
        print(f"❌ 更新行程失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'保存失败：{str(e)}'}), 500


@tour_products_bp.route('/<int:product_id>/itinerary/<int:itinerary_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def delete_itinerary(product_id, itinerary_id):
    try:
        itinerary = ProductItinerary.query.get_or_404(itinerary_id)
        if itinerary.product_id != product_id:
            return jsonify({'success': False, 'message': '行程不属于该产品'}), 400
        db.session.delete(itinerary)
        db.session.commit()
        return jsonify({'success': True, 'message': '行程删除成功！'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@tour_products_bp.route('/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_only
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        try:
            tags_input = request.form.get('tags', '').strip()
            tags_list = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
            tags_json = json.dumps(tags_list, ensure_ascii=False)

            if 'cover_image' in request.files:
                cover_file = request.files['cover_image']
                if cover_file and cover_file.filename:
                    cover_image_path = save_uploaded_file(cover_file)
                    if cover_image_path:
                        product.cover_image = cover_image_path

            if 'gallery_images' in request.files:
                gallery_paths = []
                gallery_files = request.files.getlist('gallery_images')
                for file in gallery_files:
                    if file and file.filename:
                        path = save_uploaded_file(file)
                        if path:
                            gallery_paths.append(path)
                if gallery_paths:
                    product.gallery_images = json.dumps(gallery_paths)

            supplier_id = request.form.get('supplier_id') or None
            if supplier_id:
                try:
                    supplier_id = int(supplier_id)
                except ValueError:
                    supplier_id = None

            # 处理 city_id（从 city_name 获取）
            city_name = request.form.get('city_name')
            city_id = None
            if city_name:
                from App_new.business.tour.models.Packagemodels import ProductCity
                city = ProductCity.query.filter_by(city_name=city_name).first()
                if city:
                    city_id = city.id

            product.product_name = request.form['product_name']
            product.supplier_id = supplier_id
            product.product_code = request.form.get('product_code') or None
            product.city_id = city_id
            product.city_name = city_name
            product.departure_city = request.form.get('departure_city') or None
            product.destination_city = request.form.get('destination_city') or None
            product.product_type = request.form.get('product_type') or None
            
            # 安全转换数字字段
            duration_days = request.form.get('duration_days', '').strip()
            product.duration_days = int(duration_days) if duration_days else None
            
            min_pax = request.form.get('min_pax', '1').strip()
            product.min_pax = int(min_pax) if min_pax else 1
            
            max_pax = request.form.get('max_pax', '').strip()
            product.max_pax = int(max_pax) if max_pax else None
            
            base_price = request.form.get('base_price', '').strip()
            product.base_price = float(base_price) if base_price else None
            
            child_price = request.form.get('child_price', '').strip()
            product.child_price = float(child_price) if child_price else None
            
            infant_price = request.form.get('infant_price', '').strip()
            product.infant_price = float(infant_price) if infant_price else None
            
            single_supplement = request.form.get('single_room_supplement', '').strip()
            product.single_room_supplement = float(single_supplement) if single_supplement else None
            
            product.currency = request.form.get('currency', 'SGD')
            product.product_description = request.form.get('product_description') or None
            product.highlights = request.form.get('highlights') or None
            product.included_services = request.form.get('included_services') or None
            product.excluded_services = request.form.get('excluded_services') or None
            product.important_notes = request.form.get('important_notes') or None
            product.suitable_season = request.form.get('suitable_season') or None
            product.difficulty_level = request.form.get('difficulty_level') or None
            product.tags = tags_json
            product.product_status = request.form.get('product_status', 'draft')
            
            # 安全转换 is_featured
            is_featured = request.form.get('is_featured', '0').strip()
            product.is_featured = bool(int(is_featured)) if is_featured else False
            
            # 安全转换日期字段
            valid_from = request.form.get('valid_from', '').strip()
            product.valid_from = datetime.strptime(valid_from, '%Y-%m-%d').date() if valid_from else None
            
            valid_until = request.form.get('valid_until', '').strip()
            product.valid_until = datetime.strptime(valid_until, '%Y-%m-%d').date() if valid_until else None
            product.updated_at = datetime.utcnow()

            db.session.commit()

            flash('产品更新成功！', 'success')
            return redirect(url_for('tour_products.edit_product', product_id=product.id))

        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            flash(f'更新失败：{str(e)}', 'error')

    suppliers = Supplier.query.filter(
        Supplier.supplier_type.in_(['tour_operator', 'travel_agency', 'local_operator'])
    ).order_by(Supplier.name).all()

    itineraries = ProductItinerary.query.filter_by(product_id=product_id).order_by(ProductItinerary.day_number).all()
    price_variants = ProductPriceVariant.query.filter_by(product_id=product_id).all()

    return render_template('business/tour/products/product_form.html',
                         product=product,
                         suppliers=suppliers,
                         itineraries=itineraries,
                         price_variants=price_variants)


@tour_products_bp.route('/<int:product_id>/delete', methods=['POST'])
@login_required
@staff_only
def delete_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()
        flash('产品删除成功！', 'success')
        return redirect(url_for('tour_products.product_list'))
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'danger')
        return redirect(url_for('tour_products.product_list'))


# ========================================
# 价格变体管理 API
# ========================================

@tour_products_bp.route('/<int:product_id>/price-variants')
@login_required
@staff_only
def get_price_variants(product_id):
    try:
        variants = ProductPriceVariant.query.filter_by(product_id=product_id).all()
        return jsonify({'success': True, 'variants': [v.to_dict() for v in variants]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@tour_products_bp.route('/<int:product_id>/price-variants/<int:variant_id>')
@login_required
@staff_only
def get_price_variant(product_id, variant_id):
    try:
        variant = ProductPriceVariant.query.get_or_404(variant_id)
        if variant.product_id != product_id:
            return jsonify({'success': False, 'message': '价格变体不属于该产品'}), 400
        return jsonify({'success': True, 'variant': variant.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@tour_products_bp.route('/<int:product_id>/price-variants/add', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def add_price_variant(product_id):
    try:
        product = Product.query.get_or_404(product_id)

        variant = ProductPriceVariant(
            product_id=product_id,
            variant_name=request.form['variant_name'],
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date() if request.form.get('start_date') else None,
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form.get('end_date') else None,
            min_pax=int(request.form['min_pax']) if request.form.get('min_pax') else None,
            max_pax=int(request.form['max_pax']) if request.form.get('max_pax') else None,
            adult_price=float(request.form['adult_price']),
            child_price=float(request.form['child_price']) if request.form.get('child_price') else None,
            infant_price=float(request.form['infant_price']) if request.form.get('infant_price') else None,
            single_room_supplement=float(request.form['single_room_supplement']) if request.form.get('single_room_supplement') else None,
            currency=request.form.get('currency', 'SGD'),
            is_active=bool(int(request.form.get('is_active', 1)))
        )

        db.session.add(variant)
        db.session.commit()

        return jsonify({'success': True, 'message': '价格变体添加成功！'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@tour_products_bp.route('/<int:product_id>/price-variants/<int:variant_id>/update', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def update_price_variant(product_id, variant_id):
    try:
        variant = ProductPriceVariant.query.get_or_404(variant_id)
        if variant.product_id != product_id:
            return jsonify({'success': False, 'message': '价格变体不属于该产品'}), 400

        variant.variant_name = request.form['variant_name']
        variant.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date() if request.form.get('start_date') else None
        variant.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form.get('end_date') else None
        variant.min_pax = int(request.form['min_pax']) if request.form.get('min_pax') else None
        variant.max_pax = int(request.form['max_pax']) if request.form.get('max_pax') else None
        variant.adult_price = float(request.form['adult_price'])
        variant.child_price = float(request.form['child_price']) if request.form.get('child_price') else None
        variant.infant_price = float(request.form['infant_price']) if request.form.get('infant_price') else None
        variant.single_room_supplement = float(request.form['single_room_supplement']) if request.form.get('single_room_supplement') else None
        variant.currency = request.form.get('currency', 'SGD')
        variant.is_active = bool(int(request.form.get('is_active', 1)))
        variant.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({'success': True, 'message': '价格变体更新成功！'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@tour_products_bp.route('/<int:product_id>/price-variants/<int:variant_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def delete_price_variant(product_id, variant_id):
    try:
        variant = ProductPriceVariant.query.get_or_404(variant_id)
        if variant.product_id != product_id:
            return jsonify({'success': False, 'message': '价格变体不属于该产品'}), 400
        db.session.delete(variant)
        db.session.commit()
        return jsonify({'success': True, 'message': '价格变体删除成功！'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# Excel 导入导出功能
# ========================================

@tour_products_bp.route('/export/excel')
@login_required
@staff_only
def export_excel():
    try:
        products = Product.query.all()
        data = []
        for product in products:
            data.append({
                'ID': product.id,
                '供应商': product.supplier.name if product.supplier else '',
                '产品编号': product.product_code or '',
                '产品名称': product.product_name,
                '产品类型': product.product_type or '',
                '国家': product.country or '',
                '城市': product.city_name or '',
                '出发城市': product.departure_city or '',
                '目的地城市': product.destination_city or '',
                '行程天数': product.duration_days or '',
                '最少人数': product.min_pax or '',
                '最多人数': product.max_pax or '',
                '成人价格': product.base_price or '',
                '儿童价格': product.child_price or '',
                '婴儿价格': product.infant_price or '',
                '单房差': product.single_room_supplement or '',
                '货币': product.currency or 'SGD',
                '产品描述': product.product_description or '',
                '产品亮点': product.highlights or '',
                '包含服务': product.included_services or '',
                '不包含服务': product.excluded_services or '',
                '重要提示': product.important_notes or '',
                '适合季节': product.suitable_season or '',
                '难度等级': product.difficulty_level or '',
                '标签': product.tags or '',
                '产品状态': product.product_status or 'draft',
                '有效期从': product.valid_from.strftime('%Y-%m-%d') if product.valid_from else '',
                '有效期至': product.valid_until.strftime('%Y-%m-%d') if product.valid_until else '',
                '创建时间': product.created_at.strftime('%Y-%m-%d %H:%M:%S') if product.created_at else '',
                '更新时间': product.updated_at.strftime('%Y-%m-%d %H:%M:%S') if product.updated_at else '',
            })

        df = pd.DataFrame(data)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='产品数据')
            worksheet = writer.sheets['产品数据']
            for idx, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                col_letter = get_column_letter(idx + 1)
                worksheet.column_dimensions[col_letter].width = min(max_length, 50)

        output.seek(0)
        filename = f'tour_products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        flash(f'导出失败：{str(e)}', 'danger')
        return redirect(url_for('tour_products.product_list'))


@tour_products_bp.route('/import/excel', methods=['POST'])
@login_required
@staff_only
def import_excel():
    try:
        if 'file' not in request.files:
            flash('请选择要上传的文件', 'danger')
            return redirect(url_for('tour_products.product_list'))

        file = request.files['file']
        if file.filename == '':
            flash('未选择文件', 'danger')
            return redirect(url_for('tour_products.product_list'))

        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            flash('只支持 Excel 文件（.xlsx, .xls）', 'danger')
            return redirect(url_for('tour_products.product_list'))

        df = pd.read_excel(file, engine='openpyxl')

        imported_count = 0
        updated_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                supplier = None
                if pd.notna(row.get('供应商')):
                    supplier = Supplier.query.filter_by(name=str(row['供应商']).strip()).first()

                product = None
                if pd.notna(row.get('ID')):
                    product = Product.query.get(int(row['ID']))
                elif pd.notna(row.get('产品编号')) and str(row['产品编号']).strip():
                    product = Product.query.filter_by(product_code=str(row['产品编号']).strip()).first()

                # 处理 city_id（从 city_name 获取）
                city_name = str(row['城市']).strip() if pd.notna(row.get('城市')) else None
                city_id = None
                if city_name:
                    from App_new.business.tour.models.Packagemodels import ProductCity
                    city = ProductCity.query.filter_by(city_name=city_name).first()
                    if city:
                        city_id = city.id

                product_data = {
                    'supplier_id': supplier.id if supplier else None,
                    'product_code': str(row['产品编号']).strip() if pd.notna(row.get('产品编号')) else None,
                    'product_name': str(row['产品名称']).strip(),
                    'product_type': str(row['产品类型']).strip() if pd.notna(row.get('产品类型')) else None,
                    'city_id': city_id,
                    'city_name': city_name,
                    'departure_city': str(row['出发城市']).strip() if pd.notna(row.get('出发城市')) else None,
                    'destination_city': str(row['目的地城市']).strip() if pd.notna(row.get('目的地城市')) else None,
                    'duration_days': int(row['行程天数']) if pd.notna(row.get('行程天数')) else None,
                    'min_pax': int(row['最少人数']) if pd.notna(row.get('最少人数')) else 1,
                    'max_pax': int(row['最多人数']) if pd.notna(row.get('最多人数')) else None,
                    'base_price': float(row['成人价格']) if pd.notna(row.get('成人价格')) else None,
                    'child_price': float(row['儿童价格']) if pd.notna(row.get('儿童价格')) else None,
                    'infant_price': float(row['婴儿价格']) if pd.notna(row.get('婴儿价格')) else None,
                    'single_room_supplement': float(row['单房差']) if pd.notna(row.get('单房差')) else None,
                    'currency': str(row['货币']).strip() if pd.notna(row.get('货币')) else 'SGD',
                    'product_description': str(row['产品描述']).strip() if pd.notna(row.get('产品描述')) else None,
                    'highlights': str(row['产品亮点']).strip() if pd.notna(row.get('产品亮点')) else None,
                    'included_services': str(row['包含服务']).strip() if pd.notna(row.get('包含服务')) else None,
                    'excluded_services': str(row['不包含服务']).strip() if pd.notna(row.get('不包含服务')) else None,
                    'important_notes': str(row['重要提示']).strip() if pd.notna(row.get('重要提示')) else None,
                    'suitable_season': str(row['适合季节']).strip() if pd.notna(row.get('适合季节')) else None,
                    'difficulty_level': str(row['难度等级']).strip() if pd.notna(row.get('难度等级')) else None,
                    'tags': str(row['标签']).strip() if pd.notna(row.get('标签')) else None,
                    'product_status': str(row['产品状态']).strip() if pd.notna(row.get('产品状态')) else 'draft',
                }

                if pd.notna(row.get('有效期从')):
                    try:
                        product_data['valid_from'] = pd.to_datetime(row['有效期从']).date()
                    except:
                        pass

                if pd.notna(row.get('有效期至')):
                    try:
                        product_data['valid_until'] = pd.to_datetime(row['有效期至']).date()
                    except:
                        pass

                if product:
                    for key, value in product_data.items():
                        setattr(product, key, value)
                    product.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    product = Product(**product_data)
                    product.created_by = f'EXCEL_IMPORT_{current_user.username}'
                    db.session.add(product)
                    imported_count += 1

            except Exception as e:
                errors.append(f'第 {index + 2} 行导入失败: {str(e)}')
                continue

        if imported_count > 0 or updated_count > 0:
            db.session.commit()
            flash(f'导入成功！新增 {imported_count} 个产品，更新 {updated_count} 个产品', 'success')
        else:
            flash('没有导入任何数据', 'warning')

        if errors:
            for error in errors[:5]:
                flash(error, 'danger')
            if len(errors) > 5:
                flash(f'还有 {len(errors) - 5} 个错误未显示', 'warning')

    except Exception as e:
        db.session.rollback()
        flash(f'导入失败：{str(e)}', 'danger')

    return redirect(url_for('tour_products.product_list'))


@tour_products_bp.route('/download/template')
@login_required
@staff_only
def download_template():
    """下载 Excel 导入模板"""
    try:
        template_data = {
            'ID': ['', '留空则新建，填写则更新'],
            '供应商': ['供应商名称', '必须是系统中已存在的供应商'],
            '产品编号': ['SG-CITY-001', '可选，唯一标识'],
            '产品名称': ['新加坡3天2晚自由行', '必填'],
            '产品类型': ['自由行', '可选：跟团游/自由行/定制游/当地游'],
            '国家': ['新加坡', '必填'],
            '城市': ['新加坡', '可选'],
            '出发城市': ['北京', '可选'],
            '目的地城市': ['新加坡', '可选'],
            '行程天数': [3, '必填，数字'],
            '最少人数': [2, '可选，默认1'],
            '最多人数': [40, '可选'],
            '成人价格': [1200, '可选，数字'],
            '儿童价格': [800, '可选，数字'],
            '婴儿价格': [0, '可选，数字'],
            '单房差': [200, '可选，数字'],
            '货币': ['SGD', '可选，默认SGD'],
            '产品描述': ['体验新加坡的现代与传统', '可选'],
            '产品亮点': ['鱼尾狮公园\n滨海湾花园', '可选，多行用换行分隔'],
            '包含服务': ['往返机票\n酒店住宿', '可选'],
            '不包含服务': ['签证费用\n个人消费', '可选'],
            '重要提示': ['请确保护照有效期6个月以上', '可选'],
            '适合季节': ['全年', '可选'],
            '难度等级': ['简单', '可选：简单/中等/困难'],
            '标签': ['蜜月,豪华,亲子', '可选，逗号分隔'],
            '产品状态': ['active', '可选：active/draft/inactive，默认draft'],
            '有效期从': ['2025-01-01', '可选，格式：YYYY-MM-DD'],
            '有效期至': ['2025-12-31', '可选，格式：YYYY-MM-DD'],
            '创建时间': ['', '系统自动生成'],
            '更新时间': ['', '系统自动生成'],
        }

        df = pd.DataFrame(template_data)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='导入模板')
            worksheet = writer.sheets['导入模板']
            for idx, col in enumerate(df.columns):
                col_letter = get_column_letter(idx + 1)
                worksheet.column_dimensions[col_letter].width = 20

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='tour_products_template.xlsx'
        )

    except Exception as e:
        flash(f'下载模板失败：{str(e)}', 'danger')
        return redirect(url_for('tour_products.product_list'))
