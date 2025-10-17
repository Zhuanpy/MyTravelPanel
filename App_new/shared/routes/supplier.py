from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from App_new.exts import db, csrf
from App_new.shared.models.Suppliers import Supplier
from sqlalchemy.dialects.mysql import ENUM
from sqlalchemy import desc
import os
import subprocess
import platform

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
            city=request.form.get('city'),
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
        supplier.city = request.form.get('city')
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


@supplier.route('/open-folder/<int:supplier_id>', methods=['POST'])
def open_supplier_folder(supplier_id):
    """打开供应商本地文件夹"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        
        # 构建文件夹路径
        base_path = r"E:\MyProject\MyTravelWork\MyTravelPanel\资源\Supplier"
        
        # 获取供应商的国家和城市信息
        country = supplier.country or '未知国家'
        city = supplier.city or '未知城市'
        supplier_name = supplier.name
        
        # 清理供应商名称，移除特殊字符
        clean_name = supplier_name.replace('"', '').replace("'", "").replace('\\', '').replace('/', '').replace(':', '').replace('*', '').replace('?', '').replace('<', '').replace('>', '').replace('|', '')
        
        # 构建可能的路径
        possible_paths = [
            os.path.join(base_path, country, city, supplier_name),
            os.path.join(base_path, country, city, clean_name),
            os.path.join(base_path, supplier_name),
            os.path.join(base_path, clean_name),
        ]
        
        # 查找存在的文件夹
        folder_path = None
        folder_created = False
        
        for path in possible_paths:
            if os.path.exists(path) and os.path.isdir(path):
                folder_path = path
                break
        
        if not folder_path:
            try:
                # 使用第一个可能的路径作为目标路径
                folder_path = possible_paths[0]
                
                # 创建目录（包括所有父目录）
                os.makedirs(folder_path, exist_ok=True)
                
                # 验证目录是否创建成功
                if os.path.exists(folder_path) and os.path.isdir(folder_path):
                    # 标记为新创建的文件夹
                    folder_created = True
                else:
                    return jsonify({
                        'success': False,
                        'message': f'文件夹创建失败：{folder_path}'
                    })
                    
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'创建文件夹时发生错误：{str(e)}'
                })
        
        # 根据操作系统打开文件夹
        system = platform.system()
        
        if system == "Windows":
            # Windows 系统
            try:
                # 使用 explorer 命令打开文件夹
                subprocess.Popen(['explorer', folder_path])
                message = f'已创建并打开文件夹：{folder_path}' if folder_created else f'已打开文件夹：{folder_path}'
                return jsonify({
                    'success': True,
                    'message': message,
                    'folder_path': folder_path,
                    'created': folder_created
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'打开文件夹失败：{str(e)}'
                })
        
        elif system == "Darwin":  # macOS
            try:
                subprocess.Popen(['open', folder_path])
                message = f'已创建并打开文件夹：{folder_path}' if folder_created else f'已打开文件夹：{folder_path}'
                return jsonify({
                    'success': True,
                    'message': message,
                    'folder_path': folder_path,
                    'created': folder_created
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'打开文件夹失败：{str(e)}'
                })
        
        elif system == "Linux":
            try:
                subprocess.Popen(['xdg-open', folder_path])
                message = f'已创建并打开文件夹：{folder_path}' if folder_created else f'已打开文件夹：{folder_path}'
                return jsonify({
                    'success': True,
                    'message': message,
                    'folder_path': folder_path,
                    'created': folder_created
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'打开文件夹失败：{str(e)}'
                })
        
        else:
            return jsonify({
                'success': False,
                'message': f'不支持的操作系统：{system}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'打开文件夹时发生错误：{str(e)}'
        })