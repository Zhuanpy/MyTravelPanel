from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from App.models.Product.BusinessType import BusinessType
from ..exts import db

business_types = Blueprint('business_types', __name__)

@business_types.route('/')
def list_types():
    """业务类型列表"""
    types = BusinessType.query.order_by(BusinessType.sort_order).all()
    return render_template('business_types/list.html', types=types)

@business_types.route('/create', methods=['GET', 'POST'])
def create_type():
    """创建业务类型"""
    if request.method == 'POST':
        try:
            new_type = BusinessType(
                name=request.form['name'],
                code=request.form['code'],
                description=request.form.get('description'),
                sort_order=int(request.form.get('sort_order', 0))
            )
            db.session.add(new_type)
            db.session.commit()
            return redirect(url_for('business_types.list_types'))
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    return render_template('business_types/create.html')

@business_types.route('/<int:type_id>/edit', methods=['GET', 'POST'])
def edit_type(type_id):
    """编辑业务类型"""
    type_obj = BusinessType.query.get_or_404(type_id)
    
    if request.method == 'POST':
        try:
            type_obj.name = request.form['name']
            type_obj.code = request.form['code']
            type_obj.description = request.form.get('description')
            type_obj.sort_order = int(request.form.get('sort_order', 0))
            type_obj.is_active = request.form.get('is_active') == 'true'
            
            db.session.commit()
            return redirect(url_for('business_types.list_types'))
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    return render_template('business_types/edit.html', type=type_obj)

@business_types.route('/<int:type_id>/toggle', methods=['POST'])
def toggle_type(type_id):
    """切换业务类型状态"""
    type_obj = BusinessType.query.get_or_404(type_id)
    try:
        type_obj.is_active = not type_obj.is_active
        db.session.commit()
        return jsonify({'success': True, 'is_active': type_obj.is_active})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@business_types.route('/init', methods=['POST'])
def init_types():
    """初始化默认业务类型"""
    try:
        BusinessType.init_default_types()
        return redirect(url_for('business_types.list_types'))
    except Exception as e:
        return jsonify({'error': str(e)}), 400 