from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from App.exts import db
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
        
        # 获取所有签证链接，并关联签证类型信息，使用分页
        pagination = db.session.query(VisaLinks, VisaTypes)\
            .join(VisaTypes)\
            .order_by(VisaTypes.visa_type, VisaLinks.name)\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        links = pagination.items
        
        # 获取所有签证类型用于添加新链接
        visa_types = VisaTypes.query.order_by(VisaTypes.visa_type).all()
        
        return render_template('visas/签证类型管理/签证链接管理.html',
                             links=links,
                             visa_types=visa_types,
                             pagination=pagination)
    except Exception as e:
        flash(f'获取链接列表时出错: {str(e)}', 'error')
        return redirect(url_for('visa_links.visa_link_page'))

@visa_links.route('/add_visa_link', methods=['GET', 'POST'])
def add_visa_link():
    """添加签证链接"""
    if request.method == 'POST':
        try:
            print("DEBUG: 开始处理添加签证链接请求")
            print(f"DEBUG: 请求头: {dict(request.headers)}")
            
            # 获取表单数据数组
            visa_type_ids = request.form.getlist('visa_type[]')
            names = request.form.getlist('name[]')
            links = request.form.getlist('link[]')
            
            print(f"DEBUG: 接收到的数据 - visa_type_ids: {visa_type_ids}")
            print(f"DEBUG: 接收到的数据 - names: {names}")
            print(f"DEBUG: 接收到的数据 - links: {links}")
            
            # 检查是否有数据
            if not visa_type_ids or not names or not links:
                error_msg = '请至少提交一个签证链接数据'
                print(f"DEBUG: 数据验证失败 - {error_msg}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return redirect(url_for('visa_links.visa_link_page'))
            
            # 检查数组长度是否匹配
            if len(visa_type_ids) != len(names) or len(visa_type_ids) != len(links):
                error_msg = '提交的数据格式不正确'
                print(f"DEBUG: 数组长度不匹配 - visa_type_ids: {len(visa_type_ids)}, names: {len(names)}, links: {len(links)}")
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
                link = links[i].strip()
                
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
                        link=link
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
    
    return redirect(url_for('visa_links.visa_link_page'))

@visa_links.route('/edit_visa_link/<int:link_id>', methods=['GET', 'POST'])
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
        return render_template('visas/签证类型管理/签证链接管理.html',
                             link=link,
                             visa_types=visa_types,
                             is_editing=True)
    except Exception as e:
        error_msg = f'获取链接信息时出错：{str(e)}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        flash(error_msg, 'error')
        return redirect(url_for('visa_links.visa_link_page'))

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


