from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from ..exts import db
from ..models import VisaLinks, VisaTypes, VisaCountries

"""
签证链接管理 (visa_links.py):
链接列表页面 (/visa/links/visa_link_page)
添加链接 (/visa/links/add_visa_link)
编辑链接 (/visa/links/edit_visa_link/<id>)
删除链接 (/visa/links/delete_visa_link/<id>)
"""
visa_links = Blueprint('visa_links', __name__)

@visa_links.route('/visa_link_page')
def visa_link_page():
    """签证链接管理页面"""
    try:
        # 获取所有签证链接，并关联签证类型信息
        links = db.session.query(VisaLinks, VisaTypes)\
            .join(VisaTypes)\
            .order_by(VisaTypes.visa_type, VisaLinks.name)\
            .all()
        
        # 获取所有签证类型用于添加新链接
        visa_types = VisaTypes.query.order_by(VisaTypes.visa_type).all()
        
        return render_template('visas/签证链接管理.html',
                             links=links,
                             visa_types=visa_types)
    except Exception as e:
        flash(f'获取链接列表时出错: {str(e)}', 'error')
        return redirect(url_for('visa_home.home'))

@visa_links.route('/visa_link/add_visa_link', methods=['GET', 'POST'])
def add_visa_link():
    """添加签证链接"""
    if request.method == 'POST':
        try:
            # 获取表单数据数组
            visa_type_ids = request.form.getlist('visa_type[]')
            names = request.form.getlist('name[]')
            links = request.form.getlist('link[]')
            
            # 检查是否有数据
            if not visa_type_ids or not names or not links:
                flash('请至少提交一个签证链接数据', 'error')
                return redirect(url_for('visa_links.visa_link_page'))
            
            # 检查数组长度是否匹配
            if len(visa_type_ids) != len(names) or len(visa_type_ids) != len(links):
                flash('提交的数据格式不正确', 'error')
                return redirect(url_for('visa_links.visa_link_page'))
            
            # 成功添加的计数
            success_count = 0
            error_count = 0
            
            # 处理每个签证链接
            for i in range(len(visa_type_ids)):
                visa_type_id = visa_type_ids[i].strip()
                name = names[i].strip()
                link = links[i].strip()
                
                # 跳过空字段
                if not visa_type_id or not name or not link:
                    continue
                
                # 验证链接格式
                if not link.startswith(('http://', 'https://')):
                    error_count += 1
                    continue
                
                # 验证签证类型是否存在
                visa_type_exists = VisaTypes.query.get(visa_type_id)
                if not visa_type_exists:
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

@visa_links.route('/visa_link/edit_visa_link/<int:link_id>', methods=['GET', 'POST'])
def edit_visa_link(link_id):
    """编辑签证链接"""
    link = VisaLinks.query.get_or_404(link_id)
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            visa_type_id = request.form.get('visa_type')
            name = request.form.get('name')
            link_url = request.form.get('link')
            
            # 验证数据
            if not visa_type_id or not name or not link_url:
                flash('所有字段都是必填的', 'error')
                return redirect(url_for('visa_links.edit_visa_link', link_id=link_id))
            
            # 验证链接格式
            if not link_url.startswith(('http://', 'https://')):
                flash('链接格式不正确', 'error')
                return redirect(url_for('visa_links.edit_visa_link', link_id=link_id))
            
            # 验证签证类型是否存在
            visa_type = VisaTypes.query.get(visa_type_id)
            if not visa_type:
                flash('签证类型不存在', 'error')
                return redirect(url_for('visa_links.edit_visa_link', link_id=link_id))
            
            # 更新链接信息
            link.visa_type_id = visa_type_id
            link.name = name
            link.link = link_url
            
            db.session.commit()
            flash('链接更新成功', 'success')
            return redirect(url_for('visa_links.visa_link_page'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新链接时出错：{str(e)}', 'error')
            return redirect(url_for('visa_links.edit_visa_link', link_id=link_id))
    
    # GET 请求，显示编辑表单
    visa_types = VisaTypes.query.order_by(VisaTypes.visa_type).all()
    return render_template('visas/签证链接管理.html',
                         link=link,
                         visa_types=visa_types,
                         is_editing=True)

@visa_links.route('/visa_link/delete_visa_link/<int:link_id>')
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


