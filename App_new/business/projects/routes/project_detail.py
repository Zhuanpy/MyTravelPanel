# -*- coding: utf-8 -*-
"""
项目详情路由
包含项目详情显示、REF记录、财务统计等功能
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from ..services.project_service import ProjectService
from ..services.project_stats import ProjectStatsService
from App_new.utils.decorators import staff_only
from App_new.utils.permissions import can_access_project

from App_new.business.projects.models.ref import ProjectRef
from App_new.exts import db
from datetime import datetime
import traceback

# 创建蓝图
bp = Blueprint('detail', __name__)

@bp.route('/test')
def test_detail():
    """测试路由 - 验证基本功能"""
    return "项目详情路由工作正常！"

@bp.route('/<int:project_id>')
@login_required
@staff_only
def project_detail(project_id):
    """项目详情页面"""
    try:
        print(f"DEBUG: 访问项目详情页面，project_id: {project_id}")
        
        from App_new.business.projects.models.project import ProjectHeader
        from App_new.business.projects.models.project import CustomerCompany
        
        # 使用project_id查询ProjectHeader
        header = ProjectHeader.query.get_or_404(project_id)
        print(f"DEBUG: 找到项目 HID: {header.hid}, 描述: {header.desc}")
        
        # 员工等级权限检查
        if not can_access_project(header, current_user):
            flash('您没有权限访问此项目', 'error')
            return redirect(url_for('business_projects.list.list_projects'))
        
        # 手动加载相关的REF数据
        refs = ProjectRef.query.filter_by(header_id=project_id).all()
        header.refs = refs
        print(f"DEBUG: 加载了 {len(refs)} 个REF记录")

        # 获取上一个和下一个项目（优化查询）
        prev_header = ProjectHeader.query.filter(
            ProjectHeader.id < project_id
        ).order_by(ProjectHeader.id.desc()).limit(1).first()

        next_header = ProjectHeader.query.filter(
            ProjectHeader.id > project_id
        ).order_by(ProjectHeader.id.asc()).limit(1).first()

        # 获取公司信息（通过backref自动关联）
        company = header.company
        print(f"DEBUG: 公司信息: {company.company_name if company else 'None'}")

        # 获取所有活跃的公司列表供选择
        companies = CustomerCompany.query.filter_by(status='active').order_by(CustomerCompany.company_name).all()
        print(f"DEBUG: 加载了 {len(companies)} 个活跃公司")

        print(f"DEBUG: 准备渲染模板 business/projects/project_detail.html")
        return render_template('business/projects/project_detail.html',
                               header=header,
                               company=company,
                               companies=companies,
                               prev_header=prev_header,
                               next_header=next_header)
                               
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR: 加载项目详情失败")
        print(f"ERROR: 错误类型: {type(e).__name__}")
        print(f"ERROR: 错误信息: {error_msg}")
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR: 完整堆栈:\n{error_trace}")
        
        # 记录到日志文件
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"项目详情页面加载失败 [project_id={project_id}]: {error_msg}")
        logger.error(f"完整堆栈: {error_trace}")
        
        flash(f'加载项目详情失败：{error_msg}', 'error')
        return redirect(url_for('business_projects.list.list_projects'))

@bp.route('/<int:project_id>/refs')
@login_required
@staff_only
def project_refs(project_id):
    """项目REF记录列表"""
    try:
        project_service = ProjectService()
        
        # 获取项目信息
        project = project_service.get_project_by_id(project_id)
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        
        # 获取REF记录
        refs = project_service.get_project_refs(project_id)
        
        return jsonify({
            'success': True,
            'data': [ref.to_dict() for ref in refs]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<int:project_id>/stats')
@login_required
@staff_only
def project_stats(project_id):
    """项目统计信息"""
    try:
        stats_service = ProjectStatsService()
        
        # 获取项目统计
        stats = stats_service.get_project_stats(project_id)
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/header/<int:header_id>/reminder', methods=['POST', 'PUT'])
@login_required
@staff_only
def manage_reminder(header_id):
    """添加或更新项目提醒"""
    try:
        from App_new.business.projects.models.project import ProjectHeader
        
        # 获取项目
        header = ProjectHeader.query.get_or_404(header_id)
        
        # 获取请求数据
        data = request.get_json()
        reminder_event = data.get('reminder_event', '').strip()
        reminder_date_str = data.get('reminder_date', '')
        
        # 验证数据
        if not reminder_event:
            return jsonify({
                'success': False,
                'message': '提醒事件不能为空'
            }), 400
        
        if not reminder_date_str:
            return jsonify({
                'success': False,
                'message': '提醒日期不能为空'
            }), 400
        
        # 解析日期
        try:
            reminder_date = datetime.strptime(reminder_date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'message': '提醒日期格式不正确'
            }), 400
        
        # 检查日期不能早于今天
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if reminder_date < today:
            return jsonify({
                'success': False,
                'message': '提醒日期不能早于今天'
            }), 400
        
        # 更新提醒信息
        header.reminder_event = reminder_event
        header.reminder_date = reminder_date
        header.reminder_sent = False  # 重置发送状态
        
        db.session.commit()
        
        # 如果有提醒信息，同步到待办事项
        if header.reminder_event and header.reminder_date:
            try:
                from App_new.utils.reminder_utils import create_reminder_todo
                create_reminder_todo(header)
            except Exception as e:
                print(f"DEBUG: Failed to create reminder todo: {str(e)}")
        
        action = '添加' if request.method == 'POST' else '更新'
        return jsonify({
            'success': True,
            'message': f'提醒{action}成功'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Error managing reminder: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'操作失败：{str(e)}'
        }), 500


@bp.route('/header/<int:header_id>/reminder', methods=['DELETE'])
@login_required
@staff_only
def delete_reminder(header_id):
    """删除项目提醒"""
    try:
        from App_new.business.projects.models.project import ProjectHeader
        
        # 获取项目
        header = ProjectHeader.query.get_or_404(header_id)
        
        # 清除提醒信息
        header.reminder_event = None
        header.reminder_date = None
        header.reminder_sent = False
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '提醒删除成功'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Error deleting reminder: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除失败：{str(e)}'
        }), 500

@bp.route('/<int:project_id>/receipts')
@login_required
@staff_only
def project_receipts(project_id):
    """项目收款记录列表"""
    try:
        project_service = ProjectService()
        
        # 获取项目信息
        project = project_service.get_project_by_id(project_id)
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        
        # 获取收款记录
        receipts = project_service.get_project_receipts(project_id)
        
        return jsonify({
            'success': True,
            'data': [receipt.to_dict() for receipt in receipts]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<int:project_id>/payments')
@login_required
@staff_only
def project_payments(project_id):
    """项目付款记录列表"""
    try:
        project_service = ProjectService()
        
        # 获取项目信息
        project = project_service.get_project_by_id(project_id)
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        
        # 获取付款记录
        payments = project_service.get_project_payments(project_id)
        
        return jsonify({
            'success': True,
            'data': [payment.to_dict() for payment in payments]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<int:project_id>/documents')
@login_required
@staff_only
def project_documents(project_id):
    """项目文档列表"""
    try:
        project_service = ProjectService()
        
        # 获取项目信息
        project = project_service.get_project_by_id(project_id)
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        
        # 获取文档记录
        documents = project_service.get_project_documents(project_id)
        
        return jsonify({
            'success': True,
            'data': [doc.to_dict() for doc in documents]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 邮件功能 ====================

@bp.route('/<int:project_id>/email/templates')
@login_required
@staff_only
def get_email_templates(project_id):
    """获取可用的邮件模板列表"""
    try:
        from App_new.business.projects.models.project import EmailTemplate
        templates = EmailTemplate.query.filter_by(is_active=True).order_by(EmailTemplate.category, EmailTemplate.name).all()
        return jsonify({
            'success': True,
            'templates': [t.to_dict() for t in templates]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/<int:project_id>/email/contacts')
@login_required
@staff_only
def get_email_contacts(project_id):
    """获取项目关联公司的联系人列表"""
    try:
        from App_new.business.projects.models.project import ProjectHeader, CompanyContact
        
        header = ProjectHeader.query.get_or_404(project_id)
        contacts = []
        
        # 如果有关联公司，获取公司联系人
        if header.company_id:
            company_contacts = CompanyContact.query.filter_by(company_id=header.company_id).all()
            for c in company_contacts:
                if c.email:  # 只返回有邮箱的联系人
                    contacts.append({
                        'id': c.id,
                        'name': c.name,
                        'email': c.email,
                        'position': c.position,
                        'is_primary': c.is_primary
                    })
        
        # 添加项目头部的联系人信息（如果有邮箱）
        if header.contact:
            # 尝试从公司信息获取邮箱
            if header.company and header.company.contact_email:
                contacts.insert(0, {
                    'id': 0,
                    'name': header.contact,
                    'email': header.company.contact_email,
                    'position': '项目联系人',
                    'is_primary': True
                })
        
        return jsonify({
            'success': True,
            'contacts': contacts,
            'company_name': header.company.company_name if header.company else None
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/<int:project_id>/email/send', methods=['POST'])
@login_required
@staff_only
def send_project_email(project_id):
    """发送项目邮件"""
    try:
        from flask import current_app
        from flask_mail import Mail, Message
        from App_new.business.projects.models.project import ProjectHeader, ProjectEmail, EmailTemplate
        from werkzeug.utils import secure_filename
        import json
        import os
        import tempfile
        
        header = ProjectHeader.query.get_or_404(project_id)
        
        # 处理FormData（支持文件上传）
        if request.content_type and 'multipart/form-data' in request.content_type:
            recipients = json.loads(request.form.get('recipients', '[]'))
            cc = json.loads(request.form.get('cc', '[]'))
            subject = request.form.get('subject', '')
            body = request.form.get('body', '')
            template_id = request.form.get('template_id')
            attachment_count = int(request.form.get('attachment_count', 0))
        else:
            # 兼容JSON格式
            data = request.get_json()
            recipients = data.get('recipients', [])
            cc = data.get('cc', [])
            subject = data.get('subject', '')
            body = data.get('body', '')
            template_id = data.get('template_id')
            attachment_count = 0
        
        # 验证必填字段
        if not recipients:
            return jsonify({'success': False, 'message': '请选择收件人'}), 400
        if not subject:
            return jsonify({'success': False, 'message': '请输入邮件主题'}), 400
        if not body:
            return jsonify({'success': False, 'message': '请输入邮件内容'}), 400
        
        # 处理附件
        attachments_info = []
        temp_files = []  # 保存临时文件路径，发送后删除
        
        if attachment_count > 0:
            upload_folder = os.path.join(current_app.static_folder, 'uploads', 'email_attachments')
            os.makedirs(upload_folder, exist_ok=True)
            
            for i in range(attachment_count):
                file_key = f'attachment_{i}'
                if file_key in request.files:
                    file = request.files[file_key]
                    if file and file.filename:
                        # 保存临时文件
                        filename = secure_filename(file.filename)
                        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_')
                        unique_filename = timestamp + filename
                        file_path = os.path.join(upload_folder, unique_filename)
                        file.save(file_path)
                        temp_files.append(file_path)
                        
                        # 获取文件MIME类型
                        import mimetypes
                        mime_type, _ = mimetypes.guess_type(filename)
                        if not mime_type:
                            mime_type = 'application/octet-stream'
                        
                        attachments_info.append({
                            'name': filename,
                            'path': file_path,
                            'type': mime_type
                        })
        
        # 创建邮件记录
        email_record = ProjectEmail(
            header_id=project_id,
            template_id=int(template_id) if template_id else None,
            subject=subject,
            body=body,
            recipients=json.dumps(recipients),
            cc=json.dumps(cc),
            attachments=json.dumps(attachments_info),
            status='draft',
            created_by=current_user.username if current_user.is_authenticated else 'system'
        )
        db.session.add(email_record)
        
        # 发送邮件
        try:
            # 检查邮件配置
            mail_server = current_app.config.get('MAIL_SERVER')
            mail_username = current_app.config.get('MAIL_USERNAME')
            mail_password = current_app.config.get('MAIL_PASSWORD')
            mail_port = current_app.config.get('MAIL_PORT')
            mail_use_ssl = current_app.config.get('MAIL_USE_SSL', False)
            mail_use_tls = current_app.config.get('MAIL_USE_TLS', False)
            
            # 记录配置信息（用于调试，不记录密码）
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"邮件发送配置检查 - 服务器: {mail_server}, 端口: {mail_port}, SSL: {mail_use_ssl}, TLS: {mail_use_tls}, 用户名: {mail_username}")
            
            if not mail_server:
                raise ValueError('邮件服务器(MAIL_SERVER)未配置，请检查环境变量或配置文件')
            if not mail_username:
                raise ValueError('邮件用户名(MAIL_USERNAME)未配置，请检查环境变量或配置文件')
            if not mail_password:
                raise ValueError('邮件密码(MAIL_PASSWORD)未配置，请检查环境变量或配置文件')
            
            mail = Mail(current_app)
            sender_email = current_app.config.get('MAIL_DEFAULT_SENDER') or mail_username
            
            # 处理邮件正文：将换行符转换为HTML格式
            # 检查是否包含HTML标签（简单判断）
            has_html_tags = '<' in body and '>' in body and any(tag in body.lower() for tag in ['<br', '<p', '<div', '<span', '<h'])
            
            if not has_html_tags:
                # 纯文本格式，将换行符转换为<br>，并包装在HTML中
                # 先转义HTML特殊字符
                import html
                escaped_body = html.escape(body)
                html_body = escaped_body.replace('\n', '<br>')
                html_body = f'<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">{html_body}</div>'
            else:
                # 已经是HTML格式，但可能还有未转换的换行符，补充转换
                # 只转换不在HTML标签内的换行符（简单处理）
                html_body = body.replace('\n', '<br>')
            
            msg = Message(
                subject=subject,
                sender=sender_email,
                recipients=recipients,
                cc=cc if cc else None,
                html=html_body
            )
            
            # 添加附件
            for att_info in attachments_info:
                with open(att_info['path'], 'rb') as f:
                    msg.attach(
                        att_info['name'],
                        att_info['type'],
                        f.read()
                    )
            
            logger.info(f"准备发送邮件 - 主题: {subject}, 收件人: {recipients}, 抄送: {cc}")
            mail.send(msg)
            logger.info("邮件发送成功")
            
            # 更新发送状态
            email_record.status = 'sent'
            email_record.sent_at = datetime.utcnow()
            db.session.commit()
            
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception as e:
                    print(f"清理临时文件失败: {temp_file}, 错误: {e}")
            
            return jsonify({
                'success': True,
                'message': f'邮件发送成功，已发送至 {len(recipients)} 位收件人' + (f'，包含 {len(attachments_info)} 个附件' if attachments_info else ''),
                'email_id': email_record.id
            })
            
        except Exception as mail_error:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            
            # 记录详细错误信息
            error_detail = str(mail_error)
            error_traceback = traceback.format_exc()
            logger.error(f"邮件发送失败 - 错误: {error_detail}")
            logger.error(f"错误堆栈: {error_traceback}")
            
            # 检查常见错误原因并提供友好提示
            error_message = f'邮件发送失败：{error_detail}'
            
            # 常见错误提示
            if 'timeout' in error_detail.lower() or 'timed out' in error_detail.lower():
                error_message += '。可能原因：网络连接超时，请检查服务器是否能访问SMTP服务器'
            elif 'connection' in error_detail.lower() or 'refused' in error_detail.lower():
                error_message += '。可能原因：无法连接到SMTP服务器，请检查网络连接和防火墙设置'
            elif 'authentication' in error_detail.lower() or 'login' in error_detail.lower() or '535' in error_detail:
                error_message += '。可能原因：邮箱账号或密码错误，请检查MAIL_USERNAME和MAIL_PASSWORD配置'
            elif 'ssl' in error_detail.lower() or 'certificate' in error_detail.lower():
                error_message += '。可能原因：SSL/TLS证书验证失败，请检查MAIL_USE_SSL和MAIL_USE_TLS配置'
            elif '550' in error_detail or '553' in error_detail:
                error_message += '。可能原因：邮件被拒绝，请检查发件人地址和收件人地址是否正确'
            
            email_record.status = 'failed'
            email_record.error_message = error_detail
            db.session.commit()
            
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
            
            return jsonify({'success': False, 'message': error_message}), 500
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/<int:project_id>/email/history')
@login_required
@staff_only
def get_email_history(project_id):
    """获取项目邮件发送历史"""
    try:
        from App_new.business.projects.models.project import ProjectEmail
        
        emails = ProjectEmail.query.filter_by(header_id=project_id).order_by(ProjectEmail.created_at.desc()).all()
        return jsonify({
            'success': True,
            'emails': [e.to_dict() for e in emails]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== 邮件模板管理 ====================

@bp.route('/email/templates')
@login_required
@staff_only
def email_templates_list():
    """邮件模板列表页面"""
    from App_new.business.projects.models.project import EmailTemplate
    
    templates = EmailTemplate.query.order_by(EmailTemplate.category, EmailTemplate.name).all()
    categories = db.session.query(EmailTemplate.category).distinct().filter(EmailTemplate.category.isnot(None)).all()
    categories = [c[0] for c in categories]
    
    return render_template('business/projects/email_templates/list.html', 
                         templates=templates, 
                         categories=categories)


@bp.route('/email/templates/create', methods=['GET', 'POST'])
@login_required
@staff_only
def create_email_template():
    """创建邮件模板"""
    from App_new.business.projects.models.project import EmailTemplate
    
    if request.method == 'POST':
        try:
            template = EmailTemplate(
                name=request.form.get('name'),
                subject=request.form.get('subject'),
                body=request.form.get('body'),
                category=request.form.get('category'),
                is_active=request.form.get('is_active') == '1',
                created_by=current_user.username if current_user.is_authenticated else 'system'
            )
            db.session.add(template)
            db.session.commit()
            flash('模板创建成功！', 'success')
            return redirect(url_for('business_projects.detail.email_templates_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    
    categories = ['flight', 'hotel', 'visa', 'invoice', 'general']
    return render_template('business/projects/email_templates/form.html', 
                         template=None, 
                         categories=categories)


@bp.route('/email/templates/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_only
def edit_email_template(template_id):
    """编辑邮件模板"""
    from App_new.business.projects.models.project import EmailTemplate
    
    template = EmailTemplate.query.get_or_404(template_id)
    
    if request.method == 'POST':
        try:
            template.name = request.form.get('name')
            template.subject = request.form.get('subject')
            template.body = request.form.get('body')
            template.category = request.form.get('category')
            template.is_active = request.form.get('is_active') == '1'
            db.session.commit()
            flash('模板更新成功！', 'success')
            return redirect(url_for('business_projects.detail.email_templates_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    
    categories = ['flight', 'hotel', 'visa', 'invoice', 'general']
    return render_template('business/projects/email_templates/form.html', 
                         template=template, 
                         categories=categories)


@bp.route('/email/templates/<int:template_id>/delete', methods=['POST'])
@login_required
@staff_only
def delete_email_template(template_id):
    """删除邮件模板"""
    from App_new.business.projects.models.project import EmailTemplate
    
    template = EmailTemplate.query.get_or_404(template_id)
    try:
        db.session.delete(template)
        db.session.commit()
        flash('模板删除成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'error')
    
    return redirect(url_for('business_projects.detail.email_templates_list'))