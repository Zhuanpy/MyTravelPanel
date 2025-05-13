from flask import Blueprint, render_template, request, redirect, url_for
from ..exts import db
from ..models import Supplier

# 创建蓝图
supplier = Blueprint('supplier', __name__)

@supplier.route('/')
def suppliers():
    suppliers = Supplier.query.all()
    return render_template('package/供应商信息展示.html', suppliers=suppliers)


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
            contact_person=request.form.get('contact_person'),
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            address=request.form.get('address'),
            country=request.form.get('country'),
            region=request.form.get('city'),
            status=request.form.get('status')
        )
        db.session.add(new_supplier)
        db.session.commit()
        return redirect(url_for('supplier.suppliers'))
    return render_template('package/供应商添加.html')

@supplier.route('/edit/<int:supplier_id>', methods=['GET', 'POST'])
def edit_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)

    if request.method == 'POST':
        supplier.name = request.form['name']
        supplier.contact_person = request.form.get('contact_person')
        supplier.phone = request.form.get('phone')
        supplier.email = request.form.get('email')
        supplier.address = request.form.get('address')
        supplier.country = request.form.get('country')
        supplier.city = request.form.get('city')
        supplier.status = request.form.get('status')
        db.session.commit()
        return redirect(url_for('suppliers'))
    return render_template('package/供应商信息编辑.html', supplier=supplier)

@supplier.route('/delete/<int:supplier_id>')
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    db.session.delete(supplier)
    db.session.commit()
    return redirect(url_for('supplier.suppliers'))