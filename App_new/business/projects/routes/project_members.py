# -*- coding: utf-8 -*-
"""项目人员管理路由"""

from flask import Blueprint, request, jsonify
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.project_member import ProjectMember

project_members_bp = Blueprint('project_members', __name__)


@project_members_bp.route('/<int:project_id>/members', methods=['GET'])
def get_members(project_id):
    """获取项目人员列表"""
    try:
        header = ProjectHeader.query.get_or_404(project_id)
        members = ProjectMember.query.filter_by(header_id=project_id).order_by(ProjectMember.id).all()
        return jsonify({
            'success': True,
            'data': [m.to_dict() for m in members],
            'count': len(members)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@project_members_bp.route('/<int:project_id>/members', methods=['POST'])
def add_member(project_id):
    """添加项目人员"""
    try:
        header = ProjectHeader.query.get_or_404(project_id)
        data = request.get_json()
        
        if not data.get('member_name'):
            return jsonify({'success': False, 'message': '人员姓名不能为空'}), 400
        
        member = ProjectMember(
            header_id=project_id,
            title=data.get('title'),
            member_name=data.get('member_name'),
            member_name_en=data.get('member_name_en'),
            member_role=data.get('member_role'),
            member_phone=data.get('member_phone'),
            member_email=data.get('member_email'),
            id_type=data.get('id_type'),
            id_number=data.get('id_number'),
            remarks=data.get('remarks')
        )
        
        db.session.add(member)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '人员添加成功',
            'data': member.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@project_members_bp.route('/<int:project_id>/members/<int:member_id>', methods=['PUT'])
def update_member(project_id, member_id):
    """更新项目人员信息"""
    try:
        member = ProjectMember.query.filter_by(id=member_id, header_id=project_id).first_or_404()
        data = request.get_json()
        
        if 'member_name' in data:
            if not data['member_name']:
                return jsonify({'success': False, 'message': '人员姓名不能为空'}), 400
            member.member_name = data['member_name']
        
        if 'title' in data:
            member.title = data['title']
        if 'member_name_en' in data:
            member.member_name_en = data['member_name_en']
        if 'member_role' in data:
            member.member_role = data['member_role']
        if 'member_phone' in data:
            member.member_phone = data['member_phone']
        if 'member_email' in data:
            member.member_email = data['member_email']
        if 'id_type' in data:
            member.id_type = data['id_type']
        if 'id_number' in data:
            member.id_number = data['id_number']
        if 'remarks' in data:
            member.remarks = data['remarks']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '人员信息更新成功',
            'data': member.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@project_members_bp.route('/<int:project_id>/members/<int:member_id>', methods=['DELETE'])
def delete_member(project_id, member_id):
    """删除项目人员"""
    try:
        member = ProjectMember.query.filter_by(id=member_id, header_id=project_id).first_or_404()
        member_name = member.member_name
        
        db.session.delete(member)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'人员 {member_name} 已删除'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@project_members_bp.route('/<int:project_id>/members/batch', methods=['POST'])
def batch_add_members(project_id):
    """批量添加项目人员"""
    try:
        header = ProjectHeader.query.get_or_404(project_id)
        data = request.get_json()
        members_data = data.get('members', [])
        
        if not members_data:
            return jsonify({'success': False, 'message': '人员列表不能为空'}), 400
        
        added_members = []
        for m_data in members_data:
            if not m_data.get('member_name'):
                continue
            
            member = ProjectMember(
                header_id=project_id,
                title=m_data.get('title'),
                member_name=m_data.get('member_name'),
                member_name_en=m_data.get('member_name_en'),
                member_role=m_data.get('member_role'),
                member_phone=m_data.get('member_phone'),
                member_email=m_data.get('member_email'),
                id_type=m_data.get('id_type'),
                id_number=m_data.get('id_number'),
                remarks=m_data.get('remarks')
            )
            db.session.add(member)
            added_members.append(member)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功添加 {len(added_members)} 名人员',
            'data': [m.to_dict() for m in added_members]
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

