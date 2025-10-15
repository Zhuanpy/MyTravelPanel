from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from App_new.exts import db, csrf
from App_new.shared.models.Suppliers import Supplier
from sqlalchemy.dialects.mysql import ENUM
from sqlalchemy import desc

# 创建蓝图
supplier = Blueprint('supplier', __name__)

@supplier.route('/')
def suppliers():
    # 获取分页和筛选参数
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    country = request.args.get('country', '')
    supplier_type = request.args.get('supplier_type', '')
    status = request.args.get('status', '')
    
    # 构建查询
    query = Supplier.query
    
    # 应用筛选条件
    if search:
        query = query.filter(
            (Supplier.name.contains(search)) |
            (Supplier.contact_person.contains(search))
        )
    if country:
        query = query.filter(Supplier.country == country)
    if supplier_type:
        query = query.filter(Supplier.supplier_type == supplier_type)
    if status:
        query = query.filter(Supplier.status == status)
    
    # 按点击次数降序排序，然后按创建时间降序排序，并分页
    suppliers = query.order_by(desc(Supplier.click_count), desc(Supplier.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # 从模型中获取供应商类型列表
    supplier_types = Supplier.get_supplier_type_choices()
    return render_template('shared/supplier/supplier_list.html', suppliers=suppliers, supplier_types=supplier_types)


@supplier.route('/supplier/<int:supplier_id>', methods=['GET'])
def view_supplier(supplier_id):
    # 获取供应商的详细信息
    supplier = Supplier.query.get_or_404(supplier_id)
    
    # 增加点击次数
    supplier.click_count = (supplier.click_count or 0) + 1
    db.session.commit()
    
    return render_template('shared/supplier/supplier_detail.html', supplier=supplier)


@supplier.route('/add', methods=['GET', 'POST'])
def add_supplier():
    if request.method == 'POST':
        new_supplier = Supplier(
            name=request.form['name'],
            supplier_type=request.form.get('supplier_type', 'other'),
            contact_person=request.form.get('contact_person'),
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            address=request.form.get('address'),
            country=request.form.get('country'),
            region=request.form.get('region'),
            status=request.form.get('status', 'active'),
            notes=request.form.get('notes')
        )
        db.session.add(new_supplier)
        db.session.commit()
        flash('供应商添加成功！', 'success')
        return redirect(url_for('supplier.suppliers'))
    
    # 从模型中获取供应商类型列表
    supplier_types = Supplier.get_supplier_type_choices()
    return render_template('shared/supplier/supplier_form.html', supplier=None, supplier_types=supplier_types)

@supplier.route('/edit/<int:supplier_id>', methods=['GET', 'POST'])
def edit_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    # 从模型中获取供应商类型列表
    supplier_types = Supplier.get_supplier_type_choices()

    if request.method == 'POST':
        supplier.name = request.form['name']
        supplier.supplier_type = request.form.get('supplier_type')
        supplier.contact_person = request.form.get('contact_person')
        supplier.phone = request.form.get('phone')
        supplier.email = request.form.get('email')
        supplier.address = request.form.get('address')
        supplier.country = request.form.get('country')
        supplier.region = request.form.get('region')
        supplier.status = request.form.get('status')
        supplier.notes = request.form.get('notes')
        db.session.commit()
        flash('供应商更新成功！', 'success')
        return redirect(url_for('supplier.suppliers'))
    return render_template('shared/supplier/supplier_form.html', supplier=supplier, supplier_types=supplier_types)

@supplier.route('/delete/<int:supplier_id>', methods=['GET', 'DELETE'])
@csrf.exempt
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    supplier_name = supplier.name
    
    try:
        db.session.delete(supplier)
        db.session.commit()
        
        # 如果是AJAX请求，返回JSON响应
        if request.method == 'DELETE':
            return jsonify({
                'success': True,
                'message': f'供应商 "{supplier_name}" 已成功删除'
            })
        else:
            # 如果是GET请求（直接访问），重定向到列表页面
            return redirect(url_for('supplier.suppliers'))
            
    except Exception as e:
        db.session.rollback()
        
        # 如果是AJAX请求，返回错误JSON响应
        if request.method == 'DELETE':
            return jsonify({
                'success': False,
                'message': f'删除供应商失败: {str(e)}'
            }), 500
        else:
            # 如果是GET请求，重定向到列表页面
            return redirect(url_for('supplier.suppliers'))

@supplier.route('/click/<int:supplier_id>', methods=['POST'])
@csrf.exempt
def track_supplier_click(supplier_id):
    """AJAX路由：追踪供应商点击"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        supplier.click_count = (supplier.click_count or 0) + 1
        db.session.commit()
        
        return jsonify({
            'success': True,
            'click_count': supplier.click_count,
            'message': '点击统计更新成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'点击统计更新失败: {str(e)}'
        })