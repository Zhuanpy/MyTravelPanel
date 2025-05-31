from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from ..exts import db
from ..models import VisaLinks, VisaTypes, VisaCountries

"""
签证链接管理 (visa_links.py):
链接列表页面 (/visa/links/visa_link_page)
添加链接 (/visa/links/add_visa_link)
编辑链接 (/visa/links/edit_visa_link/<id>)
删除链接 (/visa/links/delete_visa_link/<id>)

"""
visa_links = Blueprint('visa_links', __name__)


@visa_links.route('/visa_link/add_visa_link', methods=['GET', 'POST'])
def add_visa_link():
    """添加签证链接"""
    if request.method == 'POST':
        try:
            # 获取表单数据数组
            visa_types = request.form.getlist('visa_type[]')
            names = request.form.getlist('name[]')
            links = request.form.getlist('link[]')
            
            # 检查是否有数据
            if not visa_types or not names or not links:
                flash('请至少提交一个签证链接数据', 'error')
                return redirect(url_for('visa_links.visa_link_page'))
            
            # 检查数组长度是否匹配
            if len(visa_types) != len(names) or len(visa_types) != len(links):
                flash('提交的数据格式不正确', 'error')
                return redirect(url_for('visa_links.visa_link_page'))
            
            # 成功添加的计数
            success_count = 0
            error_count = 0
            
            # 处理每个签证链接
            for i in range(len(visa_types)):
                visa_type = visa_types[i].strip()
                name = names[i].strip()
                link = links[i].strip()
                
                # 跳过空字段
                if not visa_type or not name or not link:
                    continue
                
                # 验证链接格式
                if not link.startswith(('http://', 'https://')):
                    error_count += 1
                    continue
                
                # 验证签证类型是否存在
                visa_type_exists = VisaTypes.query.filter_by(visa_type=visa_type).first()
                if not visa_type_exists:
                    error_count += 1
                    continue
                
                try:
                    # 创建新签证链接记录
                    new_link = VisaLinks(
                        visa_type=visa_type,
                        name=name,
                        link=link
                    )
                    db.session.add(new_link)
                    success_count += 1
                except Exception as e:
                    db.session.rollback()
                    error_count += 1
                    print(f"Error adding visa link: {str(e)}")
            
            # 提交事务
            if success_count > 0:
                db.session.commit()
                if error_count > 0:
                    flash(f'已成功添加 {success_count} 个链接，{error_count} 个链接添加失败', 'warning')
                else:
                    flash(f'已成功添加 {success_count} 个链接', 'success')
            else:
                flash('所有链接添加失败', 'error')
                
            return redirect(url_for('visa_links.visa_link_page'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'添加链接时出错：{str(e)}', 'error')
            return redirect(url_for('visa_links.visa_link_page'))
    
    return redirect(url_for('visa_links.visa_link_page'))

@visa_links.route('/edit_visa_link/<int:link_id>', methods=['GET', 'POST'])
def edit_visa_link(link_id):
    """编辑签证链接"""
    try:
        link = VisaLinks.query.get_or_404(link_id)

        if request.method == 'POST':
            # 验证必填字段
            if not all(field in request.form and request.form[field].strip() 
                      for field in ['visa_type', 'name', 'link']):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': '所有字段都是必填的'}), 400
                flash('所有字段都是必填的', 'error')
                return redirect(url_for('visa_links.visa_link_page'))

            # 验证 URL 格式
            if not request.form['link'].startswith(('http://', 'https://')):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': '请输入有效的URL地址（以http://或https://开头）'}), 400
                flash('请输入有效的URL地址（以http://或https://开头）', 'error')
                return redirect(url_for('visa_links.visa_link_page'))

            # 验证签证类型是否存在
            new_visa_type = request.form['visa_type'].strip()
            visa_type_exists = VisaTypes.query.filter_by(visa_type=new_visa_type).first()
            if not visa_type_exists:
                error_msg = '指定的签证类型不存在'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return redirect(url_for('visa_links.visa_link_page'))

            # 更新数据
            link.visa_type = new_visa_type
            link.name = request.form['name'].strip()
            link.link = request.form['link'].strip()

            try:
                db.session.commit()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True, 'message': '链接更新成功！'})
                flash('链接更新成功！', 'success')
                return redirect(url_for('visa_links.visa_link_page'))
            except Exception as e:
                db.session.rollback()
                error_msg = f'保存更改时出错：{str(e)}'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 500
                flash(error_msg, 'error')
                return redirect(url_for('visa_links.visa_link_page'))

        # GET 请求返回重定向
        return redirect(url_for('visa_links.visa_link_page'))

    except Exception as e:
        error_msg = f'处理请求时出错：{str(e)}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        flash(error_msg, 'error')
        return redirect(url_for('visa_links.visa_link_page'))

@visa_links.route('/delete_visa_link/<int:link_id>', methods=['POST'])
def delete_visa_link(link_id):
    """删除签证链接"""
    link = VisaLinks.query.get_or_404(link_id)

    try:
        db.session.delete(link)
        db.session.commit()
        flash('链接删除成功！', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'删除链接时出错：{str(e)}', 'error')

    return redirect(url_for('visa_links.visa_link_page'))

@visa_links.route('/visa_link_page')
def visa_link_page():
    """签证链接管理页面路由"""
    page = request.args.get('page', 1, type=int)
    filter_visa_type = request.args.get('visa_type', '')
    filter_country = request.args.get('country', '')
    filter_name = request.args.get('name', '')
    
    # 构建基础查询
    query = db.session.query(VisaLinks, VisaTypes.country_id)\
        .join(VisaTypes, VisaLinks.visa_type == VisaTypes.visa_type)
    
    # 应用筛选条件
    if filter_visa_type:
        query = query.filter(VisaLinks.visa_type.ilike(f'%{filter_visa_type}%'))
    
    if filter_country:
        country = VisaCountries.query.filter(VisaCountries.country_name_CN.ilike(f'%{filter_country}%')).first()
        if country:
            query = query.filter(VisaTypes.country_id == country.id)
    
    if filter_name:
        query = query.filter(VisaLinks.name.ilike(f'%{filter_name}%'))
    
    # 获取所有可用的签证类型和国家（用于筛选下拉框）
    all_visa_types = db.session.query(VisaTypes.visa_type).distinct().all()
    all_countries = VisaCountries.query.all()
    
    # 获取所有国家及其对应的签证类型，使用joinedload预加载关系
    visa_countries = VisaCountries.query\
        .options(db.joinedload(VisaCountries.visa_types))\
        .order_by(VisaCountries.country_name_CN)\
        .all()
    
    # 应用排序和分页
    query = query.order_by(VisaLinks.id.desc())
    pagination = query.paginate(page=page, per_page=10, error_out=False)
    
    # 处理结果
    visa_links_with_country = []
    for link, country_id in pagination.items:
        country = VisaCountries.query.get(country_id)
        country_name = country.country_name_CN if country else "未知"
        
        link_info = {
            'id': link.id,
            'visa_type': link.visa_type,
            'name': link.name,
            'link': link.link,
            'country_name': country_name
        }
        visa_links_with_country.append(link_info)
    
    # 获取总记录数
    total_count = query.count()
    
    return render_template('visas/签证链接管理.html', 
                         visa_links=visa_links_with_country,
                         pagination=pagination,
                         all_visa_types=all_visa_types,
                         all_countries=all_countries,
                         total_count=total_count,
                         filter_visa_type=filter_visa_type,
                         filter_country=filter_country,
                         filter_name=filter_name,
                         visa_countries=visa_countries)



""" 签证链接管理 开始  """

"""
@visa_routes.route('/visa_link_page')
def visa_link_page():
    # 签证链接管理页面路由
    page = request.args.get('page', 1, type=int)
    filter_visa_type = request.args.get('visa_type', '')
    filter_country = request.args.get('country', '')
    filter_name = request.args.get('name', '')
    
    # 构建基础查询
    query = db.session.query(VisaLinks, VisaTypes.country_id)\
        .join(VisaTypes, VisaLinks.visa_type == VisaTypes.visa_type)
    
    # 应用筛选条件
    if filter_visa_type:
        query = query.filter(VisaLinks.visa_type.ilike(f'%{filter_visa_type}%'))
    
    if filter_country:
        country = VisaCountries.query.filter(VisaCountries.country_name_CN.ilike(f'%{filter_country}%')).first()
        if country:
            query = query.filter(VisaTypes.country_id == country.id)
    
    if filter_name:
        query = query.filter(VisaLinks.name.ilike(f'%{filter_name}%'))
    
    # 获取所有可用的签证类型和国家（用于筛选下拉框）
    all_visa_types = db.session.query(VisaTypes.visa_type).distinct().all()
    all_countries = VisaCountries.query.all()
    
    # 获取所有国家及其对应的签证类型，使用joinedload预加载关系
    visa_countries = VisaCountries.query\
        .options(db.joinedload(VisaCountries.visa_types))\
        .order_by(VisaCountries.country_name_CN)\
        .all()
    
    # 应用排序和分页
    query = query.order_by(VisaLinks.id.desc())
    pagination = query.paginate(page=page, per_page=10, error_out=False)
    
    # 处理结果
    visa_links_with_country = []
    for link, country_id in pagination.items:
        country = VisaCountries.query.get(country_id)
        country_name = country.country_name_CN if country else "未知"
        
        link_info = {
            'id': link.id,
            'visa_type': link.visa_type,
            'name': link.name,
            'link': link.link,
            'country_name': country_name
        }
        visa_links_with_country.append(link_info)
    
    # 获取总记录数
    total_count = query.count()
    
    return render_template('visas/签证链接管理.html', 
                         visa_links=visa_links_with_country,
                         pagination=pagination,
                         all_visa_types=all_visa_types,
                         all_countries=all_countries,
                         total_count=total_count,
                         filter_visa_type=filter_visa_type,
                         filter_country=filter_country,
                         filter_name=filter_name,
                         visa_countries=visa_countries)

@visa_routes.route('/visa_link/add_visa_link', methods=['GET', 'POST'])
def add_visa_link():
     # 添加签证链接
    if request.method == 'POST':
        try:
            # 获取表单数据数组
            visa_types = request.form.getlist('visa_type[]')
            names = request.form.getlist('name[]')
            links = request.form.getlist('link[]')
            
            # 检查是否有数据
            if not visa_types or not names or not links:
                flash('请至少提交一个签证链接数据', 'error')
                return redirect(url_for('visa_routes.visa_link_page'))
            
            # 检查数组长度是否匹配
            if len(visa_types) != len(names) or len(visa_types) != len(links):
                flash('提交的数据格式不正确', 'error')
                return redirect(url_for('visa_routes.visa_link_page'))
            
            # 成功添加的计数
            success_count = 0
            error_count = 0
            
            # 处理每个签证链接
            for i in range(len(visa_types)):
                visa_type = visa_types[i].strip()
                name = names[i].strip()
                link = links[i].strip()
                
                # 跳过空字段
                if not visa_type or not name or not link:
                    continue
                
                # 验证链接格式
                if not link.startswith(('http://', 'https://')):
                    error_count += 1
                    continue
                
                # 验证签证类型是否存在
                visa_type_exists = VisaTypes.query.filter_by(visa_type=visa_type).first()
                if not visa_type_exists:
                    error_count += 1
                    continue
                
                try:
                    # 创建新签证链接记录
                    new_link = VisaLinks(
                        visa_type=visa_type,
                        name=name,
                        link=link
                    )
                    db.session.add(new_link)
                    success_count += 1
                except Exception as e:
                    db.session.rollback()
                    error_count += 1
                    print(f"Error adding visa link: {str(e)}")
            
            # 提交事务
            if success_count > 0:
                db.session.commit()
                if error_count > 0:
                    flash(f'已成功添加 {success_count} 个链接，{error_count} 个链接添加失败', 'warning')
                else:
                    flash(f'已成功添加 {success_count} 个链接', 'success')
            else:
                flash('所有链接添加失败', 'error')
                
            return redirect(url_for('visa_routes.visa_link_page'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'添加链接时出错：{str(e)}', 'error')
            return redirect(url_for('visa_routes.visa_link_page'))
    
    return redirect(url_for('visa_routes.visa_link_page'))

@visa_routes.route('/visa_link/edit_visa_link/<int:id>', methods=['GET', 'POST'])
def edit_visa_link(id):
    try:
        visa_link = VisaLinks.query.get_or_404(id)

        if request.method == 'POST':
            # 验证必填字段
            if not all(field in request.form and request.form[field].strip() 
                      for field in ['visa_type', 'name', 'link']):
                flash('所有字段都是必填的', 'error')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': '所有字段都是必填的'}), 400
                return render_template('visas/签证链接编辑.html', visa_link=visa_link)

            # 验证 URL 格式
            if not request.form['link'].startswith(('http://', 'https://')):
                flash('请输入有效的URL地址（以http://或https://开头）', 'error')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': '请输入有效的URL地址（以http://或https://开头）'}), 400
                return render_template('visas/签证链接编辑.html', visa_link=visa_link)

            # 验证签证类型是否存在
            new_visa_type = request.form['visa_type'].strip()
            visa_type_exists = VisaTypes.query.filter_by(visa_type=new_visa_type).first()
            if not visa_type_exists:
                error_msg = '指定的签证类型不存在'
                flash(error_msg, 'error')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 400
                return render_template('visas/签证链接编辑.html', visa_link=visa_link)

            # 更新数据
            visa_link.visa_type = new_visa_type
            visa_link.name = request.form['name'].strip()
            visa_link.link = request.form['link'].strip()

            try:
                db.session.commit()
                flash('链接更新成功！', 'success')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True, 'message': '链接更新成功！'})
                return redirect(url_for('visa_routes.visa_link_page'))
            except Exception as e:
                db.session.rollback()
                error_msg = f'保存更改时出错：{str(e)}'
                flash(error_msg, 'error')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 500
                return render_template('visas/签证链接编辑.html', visa_link=visa_link)

        # 获取所有可用的签证类型供选择
        available_visa_types = VisaTypes.query.all()
        return render_template('visas/签证链接编辑.html', 
                             visa_link=visa_link,
                             available_visa_types=available_visa_types)

    except Exception as e:
        error_msg = f'处理请求时出错：{str(e)}'
        flash(error_msg, 'error')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        return redirect(url_for('visa_routes.visa_link_page'))

@visa_routes.route('/visa_link/delete/<int:id>', methods=['POST'])
def delete_visa_link(id):
    visa_link = VisaLinks.query.get_or_404(id)

    try:
        db.session.delete(visa_link)
        db.session.commit()
        flash('签证链接删除成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除链接时出错：{str(e)}', 'error')
    
    return redirect(url_for('visa_routes.visa_link_page'))

 签证链接管理 结束 """


#
