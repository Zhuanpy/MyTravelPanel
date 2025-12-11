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
        # supplier_type 现在是从表单传来的 business_type_id
        try:
            supplier_type_id = int(supplier_type)
            query = query.filter(Supplier.supplier_type_id == supplier_type_id)
        except (ValueError, TypeError):
            pass
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
        supplier_type_id = request.form.get('supplier_type')
        if supplier_type_id:
            try:
                supplier_type_id = int(supplier_type_id)
            except (ValueError, TypeError):
                supplier_type_id = None
        else:
            supplier_type_id = None
            
        new_supplier = Supplier(
            name=request.form['name'],
            supplier_type_id=supplier_type_id,
            contact_person=request.form.get('contact_person'),
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            address=request.form.get('address'),
            country=request.form.get('country'),
            city=request.form.get('city'),
            status=request.form.get('status', 'active'),
            notes=request.form.get('notes')
        )
        db.session.add(new_supplier)
        db.session.commit()
        flash('供应商添加成功！', 'success')
        return redirect(url_for('supplier.suppliers'))
    
    # 从模型中获取供应商类型列表
    supplier_types = Supplier.get_supplier_type_choices()
    
    # 获取国家和城市列表
    from App_new.business.tour.models.Packagemodels import ProductCity
    countries = db.session.query(ProductCity.country_name).filter(
        ProductCity.country_name.isnot(None)
    ).distinct().order_by(ProductCity.country_name).all()
    countries = [c[0] for c in countries if c[0]]
    
    cities = db.session.query(ProductCity.city_name).filter(
        ProductCity.city_name.isnot(None)
    ).distinct().order_by(ProductCity.city_name).all()
    cities = [c[0] for c in cities if c[0]]
    
    # 按国家分组的城市数据
    cities_by_country = {}
    all_cities = ProductCity.query.filter(
        ProductCity.country_name.isnot(None),
        ProductCity.city_name.isnot(None)
    ).all()
    for city in all_cities:
        if city.country_name not in cities_by_country:
            cities_by_country[city.country_name] = []
        if city.city_name not in cities_by_country[city.country_name]:
            cities_by_country[city.country_name].append(city.city_name)
    
    return render_template('shared/supplier/supplier_form.html', supplier=None, supplier_types=supplier_types, countries=countries, cities=cities, cities_by_country=cities_by_country)

@supplier.route('/edit/<int:supplier_id>', methods=['GET', 'POST'])
def edit_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    # 从模型中获取供应商类型列表
    supplier_types = Supplier.get_supplier_type_choices()
    
    # 获取国家和城市列表
    from App_new.business.tour.models.Packagemodels import ProductCity
    countries = db.session.query(ProductCity.country_name).filter(
        ProductCity.country_name.isnot(None)
    ).distinct().order_by(ProductCity.country_name).all()
    countries = [c[0] for c in countries if c[0]]
    
    cities = db.session.query(ProductCity.city_name).filter(
        ProductCity.city_name.isnot(None)
    ).distinct().order_by(ProductCity.city_name).all()
    cities = [c[0] for c in cities if c[0]]
    
    # 按国家分组的城市数据
    cities_by_country = {}
    all_cities = ProductCity.query.filter(
        ProductCity.country_name.isnot(None),
        ProductCity.city_name.isnot(None)
    ).all()
    for city in all_cities:
        if city.country_name not in cities_by_country:
            cities_by_country[city.country_name] = []
        if city.city_name not in cities_by_country[city.country_name]:
            cities_by_country[city.country_name].append(city.city_name)

    if request.method == 'POST':
        supplier.name = request.form['name']
        supplier_type_id = request.form.get('supplier_type')
        if supplier_type_id:
            try:
                supplier.supplier_type_id = int(supplier_type_id)
            except (ValueError, TypeError):
                supplier.supplier_type_id = None
        else:
            supplier.supplier_type_id = None
        supplier.contact_person = request.form.get('contact_person')
        supplier.phone = request.form.get('phone')
        supplier.email = request.form.get('email')
        supplier.address = request.form.get('address')
        supplier.country = request.form.get('country')
        supplier.city = request.form.get('city')
        supplier.status = request.form.get('status')
        supplier.notes = request.form.get('notes')
        db.session.commit()
        flash('供应商更新成功！', 'success')
        return redirect(url_for('supplier.suppliers'))
    return render_template('shared/supplier/supplier_form.html', supplier=supplier, supplier_types=supplier_types, countries=countries, cities=cities, cities_by_country=cities_by_country)

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


@supplier.route('/upload-file/<int:supplier_id>', methods=['POST'])
@csrf.exempt
def upload_supplier_file(supplier_id):
    """上传供应商文件"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'})
        
        # 构建文件夹路径
        base_path = r"E:\MyProject\MyTravelWork\MyTravelPanel\资源\Supplier"
        country = supplier.country or '未知国家'
        city = supplier.city or '未知城市'
        supplier_name = supplier.name.replace('"', '').replace("'", "").replace('\\', '').replace('/', '').replace(':', '').replace('*', '').replace('?', '').replace('<', '').replace('>', '').replace('|', '')
        
        folder_path = os.path.join(base_path, country, city, supplier_name)
        
        # 确保文件夹存在
        os.makedirs(folder_path, exist_ok=True)
        
        # 保存文件
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        # 保留原文件名，避免中文问题
        original_filename = file.filename
        file_path = os.path.join(folder_path, original_filename)
        
        # 如果文件已存在，添加序号
        counter = 1
        base_name, ext = os.path.splitext(original_filename)
        while os.path.exists(file_path):
            original_filename = f"{base_name}_{counter}{ext}"
            file_path = os.path.join(folder_path, original_filename)
            counter += 1
        
        file.save(file_path)
        
        return jsonify({
            'success': True,
            'message': f'文件上传成功：{original_filename}',
            'filename': original_filename
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'上传失败：{str(e)}'
        })


@supplier.route('/list-files/<int:supplier_id>', methods=['GET'])
def list_supplier_files(supplier_id):
    """获取供应商文件列表"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        
        # 构建文件夹路径
        base_path = r"E:\MyProject\MyTravelWork\MyTravelPanel\资源\Supplier"
        country = supplier.country or '未知国家'
        city = supplier.city or '未知城市'
        supplier_name = supplier.name.replace('"', '').replace("'", "").replace('\\', '').replace('/', '').replace(':', '').replace('*', '').replace('?', '').replace('<', '').replace('>', '').replace('|', '')
        
        folder_path = os.path.join(base_path, country, city, supplier_name)
        
        files = []
        if os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    files.append({
                        'name': filename,
                        'size': stat.st_size,
                        'modified': stat.st_mtime
                    })
        
        # 按修改时间倒序
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            'success': True,
            'files': files,
            'folder_path': folder_path
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取文件列表失败：{str(e)}'
        })


@supplier.route('/toggle-status/<int:supplier_id>', methods=['POST'])
@csrf.exempt
def toggle_supplier_status(supplier_id):
    """切换供应商状态"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        supplier.status = 'inactive' if supplier.status == 'active' else 'active'
        db.session.commit()
        return jsonify({
            'success': True,
            'status': supplier.status,
            'message': f'状态已更新为：{"活跃" if supplier.status == "active" else "非活跃"}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'状态更新失败：{str(e)}'
        })


@supplier.route('/download-file/<int:supplier_id>/<path:filename>', methods=['GET'])
def download_supplier_file(supplier_id, filename):
    """下载供应商文件"""
    try:
        from flask import send_file
        supplier = Supplier.query.get_or_404(supplier_id)
        
        # 构建文件夹路径
        base_path = r"E:\MyProject\MyTravelWork\MyTravelPanel\资源\Supplier"
        country = supplier.country or '未知国家'
        city = supplier.city or '未知城市'
        supplier_name = supplier.name.replace('"', '').replace("'", "").replace('\\', '').replace('/', '').replace(':', '').replace('*', '').replace('?', '').replace('<', '').replace('>', '').replace('|', '')
        
        file_path = os.path.join(base_path, country, city, supplier_name, filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=filename)
        else:
            return jsonify({'success': False, 'message': '文件不存在'}), 404
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'下载失败：{str(e)}'}), 500


@supplier.route('/delete-file/<int:supplier_id>', methods=['POST'])
@csrf.exempt
def delete_supplier_file(supplier_id):
    """删除供应商文件"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        filename = request.json.get('filename')
        
        if not filename:
            return jsonify({'success': False, 'message': '文件名不能为空'})
        
        # 构建文件夹路径
        base_path = r"E:\MyProject\MyTravelWork\MyTravelPanel\资源\Supplier"
        country = supplier.country or '未知国家'
        city = supplier.city or '未知城市'
        supplier_name = supplier.name.replace('"', '').replace("'", "").replace('\\', '').replace('/', '').replace(':', '').replace('*', '').replace('?', '').replace('<', '').replace('>', '').replace('|', '')
        
        file_path = os.path.join(base_path, country, city, supplier_name, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'success': True, 'message': f'文件已删除：{filename}'})
        else:
            return jsonify({'success': False, 'message': '文件不存在'})
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'删除失败：{str(e)}'
        })