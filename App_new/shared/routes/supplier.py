from flask import Blueprint, render_template, request, redirect, url_for
from App_new.exts import db
from App_new.shared.models.Suppliers import Supplier
from sqlalchemy.dialects.mysql import ENUM

# 创建蓝图
supplier = Blueprint('supplier', __name__)

@supplier.route('/')
def suppliers():
    # 获取所有供应商
    suppliers = Supplier.query.all()
    # 从模型中获取供应商类型列表
    supplier_types = Supplier.get_supplier_types()
    return render_template('package/供应商信息展示.html', suppliers=suppliers, supplier_types=supplier_types)


@supplier.route('/supplier/<int:supplier_id>', methods=['GET'])
def view_supplier(supplier_id):
    # 获取供应商的详细信息
    supplier = Supplier.query.get_or_404(supplier_id)
    return render_template('package/供应商信息详细.html', supplier=supplier)


@supplier.route('/add', methods=['GET', 'POST'])
def add_supplier():
    if request.method == 'POST':
        new_supplier = Supplier(
            name=request.form['name'],
            supplier_type=request.form.get('supplier_type'),
            contact_person=request.form.get('contact_person'),
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            address=request.form.get('address'),
            country=request.form.get('country'),
            region=request.form.get('region'),
            status=request.form.get('status', 'active')
        )
        db.session.add(new_supplier)
        db.session.commit()
        return redirect(url_for('supplier.suppliers'))
    
    # 从模型中获取供应商类型列表
    supplier_types = Supplier.get_supplier_types()
    return render_template('package/供应商添加.html', supplier_types=supplier_types)

@supplier.route('/edit/<int:supplier_id>', methods=['GET', 'POST'])
def edit_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    # 从模型中获取供应商类型列表
    supplier_types = Supplier.get_supplier_types()

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
        db.session.commit()
        return redirect(url_for('supplier.suppliers'))
    return render_template('package/供应商信息编辑.html', supplier=supplier, supplier_types=supplier_types)

@supplier.route('/delete/<int:supplier_id>')
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    db.session.delete(supplier)
    db.session.commit()
    return redirect(url_for('supplier.suppliers'))