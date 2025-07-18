from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from App.exts import db, csrf
from App.models import VisaLinks, VisaTypes, VisaCountries

"""
签证链接管理 (visa_links.py):
链接列表页面 (/visa/links/visa_link_page)
添加链接 (/visa/links/add_visa_link)
编辑链接 (/visa/links/edit_visa_link/<id>)
删除链接 (/visa/links/delete_visa_link/<id>)
"""
visa_links = Blueprint('visa_links', __name__)

@visa_links.route('/')
def visa_link_page():
    """签证链接管理页面"""
    try:
        # 获取页码参数，默认为1
        page = request.args.get('page', 1, type=int)
        per_page = 20  # 每页显示20条数据
        
        # 获取筛选参数
        filter_visa_type = request.args.get('filter_visa_type', '')
        filter_country = request.args.get('filter_country', '')
        
        # 构建查询
        query = db.session.query(VisaLinks, VisaTypes, VisaCountries)\
            .join(VisaTypes, VisaLinks.visa_type_id == VisaTypes.id)\
            .outerjoin(VisaCountries, VisaLinks.visa_countries_id == VisaCountries.id)
        
        # 应用筛选条件
        if filter_visa_type:
            query = query.filter(VisaTypes.id == filter_visa_type)
        
        if filter_country:
            query = query.filter(VisaCountries.id == filter_country)
        
        # 排序和分页
        pagination = query.order_by(VisaTypes.visa_type, VisaLinks.name)\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        links = pagination.items
        
        # 获取所有签证类型用于添加新链接和筛选
        visa_types = VisaTypes.query.order_by(VisaTypes.visa_type).all()
        countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
        
        return render_template('visas/签证类型管理/签证链接管理.html',
                             links=links,
                             visa_types=visa_types,
                             countries=countries,
                             pagination=pagination,
                             filter_visa_type=filter_visa_type,
                             filter_country=filter_country)
    except Exception as e:
        flash(f'获取链接列表时出错: {str(e)}', 'error')
        # 重定向到签证首页而不是同一个页面，避免循环重定向
        return redirect(url_for('visa_home.home'))

@visa_links.route('/add_visa_link', methods=['GET', 'POST'])
@csrf.exempt
def add_visa_link():
    """添加签证链接"""
    if request.method == 'POST':
        try:
            print("DEBUG: 开始处理添加签证链接请求")
            print(f"DEBUG: 请求头: {dict(request.headers)}")
            
            # 获取表单数据数组
            visa_type_ids = request.form.getlist('visa_type[]')
            names = request.form.getlist('name[]')
            links_ = request.form.getlist('link[]')
            countries_ids = request.form.getlist('visa_countries_id[]')
            
            print(f"DEBUG: 接收到的数据 - visa_type_ids: {visa_type_ids}")
            print(f"DEBUG: 接收到的数据 - names: {names}")
            print(f"DEBUG: 接收到的数据 - links_: {links_}")
            
            # 检查是否有数据
            if not visa_type_ids or not names or not links_:
                error_msg = '请至少提交一个签证链接数据'
                print(f"DEBUG: 数据验证失败 - {error_msg}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return redirect(url_for('visa_links.visa_link_page'))
            
            # 检查数组长度是否匹配
            if len(visa_type_ids) != len(names) or len(visa_type_ids) != len(links_):
                error_msg = '提交的数据格式不正确'
                print(f"DEBUG: 数组长度不匹配 - visa_type_ids: {len(visa_type_ids)}, names: {len(names)}, links_: {len(links_)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return redirect(url_for('visa_links.visa_link_page'))
            
            # 成功添加的计数
            success_count = 0
            error_count = 0
            
            # 处理每个签证链接
            for i in range(len(visa_type_ids)):
                visa_type_id = visa_type_ids[i].strip()
                name = names[i].strip()
                link = links_[i].strip()
                visa_countries_id = countries_ids[i].strip() if i < len(countries_ids) else None
                
                print(f"DEBUG: 处理第{i+1}个链接 - visa_type_id: {visa_type_id}, name: {name}, link: {link}")
                
                # 跳过空字段
                if not visa_type_id or not name or not link:
                    print(f"DEBUG: 跳过空字段")
                    continue
                
                # 验证链接格式
                if not link.startswith(('http://', 'https://')):
                    print(f"DEBUG: 链接格式不正确: {link}")
                    error_count += 1
                    continue
                
                # 验证签证类型是否存在
                visa_type_exists = VisaTypes.query.get(visa_type_id)
                if not visa_type_exists:
                    print(f"DEBUG: 签证类型不存在: {visa_type_id}")
                    error_count += 1
                    continue
                
                try:
                    # 创建新签证链接记录
                    new_link = VisaLinks(
                        visa_type_id=visa_type_id,
                        name=name,
                        link=link,
                        visa_countries_id=visa_countries_id
                    )
                    db.session.add(new_link)
                    success_count += 1
                    print(f"DEBUG: 成功添加链接: {name}")
                except Exception as e:
                    db.session.rollback()
                    error_count += 1
                    print(f"Error adding visa link: {str(e)}")
            
            # 提交事务
            if success_count > 0:
                try:
                    db.session.commit()
                    print(f"DEBUG: 数据库提交成功")
                except Exception as e:
                    db.session.rollback()
                    print(f"DEBUG: 数据库提交失败: {str(e)}")
                    error_msg = f'数据库保存失败：{str(e)}'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': error_msg}), 500
                    flash(error_msg, 'error')
                    return redirect(url_for('visa_links.visa_link_page'))
                
                if error_count > 0:
                    message = f'已成功添加 {success_count} 个链接，{error_count} 个链接添加失败'
                    message_type = 'warning'
                else:
                    message = f'已成功添加 {success_count} 个链接'
                    message_type = 'success'
            else:
                message = '所有链接添加失败'
                message_type = 'error'
            
            print(f"DEBUG: 处理完成 - success_count: {success_count}, error_count: {error_count}")
            
            # 根据请求类型返回不同响应
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response_data = {
                    'success': success_count > 0,
                    'message': message,
                    'success_count': success_count,
                    'error_count': error_count
                }
                print(f"DEBUG: 返回AJAX响应: {response_data}")
                return jsonify(response_data)
            else:
                flash(message, message_type)
                return redirect(url_for('visa_links.visa_link_page'))
        
        except Exception as e:
            db.session.rollback()
            error_msg = f'添加链接时出错：{str(e)}'
            print(f"DEBUG: 异常处理: {error_msg}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 500
            flash(error_msg, 'error')
            return redirect(url_for('visa_links.visa_link_page'))
    
    # GET 请求时重定向到主页面
    return redirect(url_for('visa_links.visa_link_page'))

@visa_links.route('/edit_visa_link/<int:link_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_visa_link(link_id):
    """编辑签证链接"""
    try:
        link = VisaLinks.query.get_or_404(link_id)

        if request.method == 'POST':
            try:
                # 获取表单数据
                visa_type_id = request.form.get('visa_type')
                name = request.form.get('name')
                link_url = request.form.get('link')
                visa_countries_id = request.form.get('visa_countries_id')

                # 验证数据
                if not visa_type_id or not name or not link_url:
                    error_msg = '所有字段都是必填的'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': error_msg}), 400
                    flash(error_msg, 'error')
                    return redirect(url_for('visa_links.edit_visa_link', link_id=link_id))

                # 验证链接格式
                if not link_url.startswith(('http://', 'https://')):
                    error_msg = '链接格式不正确'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': error_msg}), 400
                    flash(error_msg, 'error')
                    return redirect(url_for('visa_links.edit_visa_link', link_id=link_id))

                # 验证签证类型是否存在
                visa_type = VisaTypes.query.get(visa_type_id)
                if not visa_type:
                    error_msg = '签证类型不存在'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': error_msg}), 400
                    flash(error_msg, 'error')
                    return redirect(url_for('visa_links.edit_visa_link', link_id=link_id))

                # 更新链接信息
                link.visa_type_id = visa_type_id
                link.name = name
                link.link = link_url
                link.visa_countries_id = visa_countries_id

                db.session.commit()
                
                success_msg = '链接更新成功'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True, 'message': success_msg})
                flash(success_msg, 'success')
                return redirect(url_for('visa_links.visa_link_page'))

            except Exception as e:
                db.session.rollback()
                error_msg = f'更新链接时出错：{str(e)}'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 500
                flash(error_msg, 'error')
                return redirect(url_for('visa_links.edit_visa_link', link_id=link_id))
        
        # GET 请求，显示编辑表单
        visa_types = VisaTypes.query.order_by(VisaTypes.visa_type).all()
        countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
        return render_template('visas/签证类型管理/签证链接管理.html',
                             link=link,
                             visa_types=visa_types,
                             countries=countries,
                             is_editing=True)
    except Exception as e:
        error_msg = f'获取链接信息时出错：{str(e)}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        flash(error_msg, 'error')
        # 重定向到签证首页而不是同一个页面，避免循环重定向
        return redirect(url_for('visa_home.home'))

@visa_links.route('/delete_visa_link/<int:link_id>')
def delete_visa_link(link_id):
    """删除签证链接"""
    try:
        link = VisaLinks.query.get_or_404(link_id)
        db.session.delete(link)
        db.session.commit()
        flash('链接删除成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除链接时出错：{str(e)}', 'error')

    return redirect(url_for('visa_links.visa_link_page'))


