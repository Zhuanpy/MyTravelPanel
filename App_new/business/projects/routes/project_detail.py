# -*- coding: utf-8 -*-
"""
项目详情路由
包含项目详情显示、REF记录、财务统计等功能
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required
from ..services.project_service import ProjectService
from ..services.project_stats import ProjectStatsService
from App_new.utils.decorators import staff_only

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
        print(f"DEBUG: 访问项目详情页面，project_id: {project_id}")  # 调试信息
        
        from App_new.business.projects.models.project import ProjectHeader
        from App_new.business.projects.models.project import CustomerCompany
        
        # 使用project_id查询ProjectHeader
        header = ProjectHeader.query.get_or_404(project_id)
        print(f"DEBUG: 找到项目: {header.hid}")  # 调试信息
        
        # 手动加载相关的REF数据
        refs = ProjectRef.query.filter_by(header_id=project_id).all()
        header.refs = refs
        print(f"DEBUG: 加载了 {len(refs)} 个REF记录")  # 调试信息

        # 获取上一个和下一个项目（优化查询）
        prev_header = ProjectHeader.query.filter(
            ProjectHeader.id < project_id
        ).order_by(ProjectHeader.id.desc()).limit(1).first()

        next_header = ProjectHeader.query.filter(
            ProjectHeader.id > project_id
        ).order_by(ProjectHeader.id.asc()).limit(1).first()

        # 获取公司信息（通过backref自动关联）
        company = header.company
        print(f"DEBUG: 公司信息: {company.company_name if company else 'None'}")  # 调试信息

        # 获取所有活跃的公司列表供选择
        companies = CustomerCompany.query.filter_by(status='active').order_by(CustomerCompany.company_name).all()

        print(f"DEBUG: 准备渲染模板")  # 调试信息
        return render_template('business/projects/project_detail.html',
                               header=header,
                               company=company,
                               companies=companies,
                               prev_header=prev_header,
                               next_header=next_header)
    except Exception as e:
        print(f"DEBUG: 错误: {str(e)}")  # 调试信息
        import traceback
        traceback.print_exc()  # 打印完整错误堆栈
        flash(f'加载项目详情失败：{str(e)}', 'error')
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