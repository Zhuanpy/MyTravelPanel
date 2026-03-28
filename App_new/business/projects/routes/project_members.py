# -*- coding: utf-8 -*-
"""项目人员管理路由"""

import json
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
        
        # 检查是否已有人员，如果没有，则第一个添加的人员自动成为leader
        existing_members_count = ProjectMember.query.filter_by(header_id=project_id).count()
        is_first_member = existing_members_count == 0
        
        # 处理航空会员信息
        memberships = data.get('airline_memberships')
        memberships_json = json.dumps(memberships, ensure_ascii=False) if memberships else None

        member = ProjectMember(
            header_id=project_id,
            title=data.get('title'),
            member_name=data.get('member_name'),
            member_name_en=data.get('member_name_en'),
            member_role=data.get('member_role'),
            gender=data.get('gender'),
            date_of_birth=data.get('date_of_birth') or None,
            nationality=data.get('nationality'),
            member_phone=data.get('member_phone'),
            member_email=data.get('member_email'),
            id_type=data.get('id_type'),
            id_number=data.get('id_number'),
            passport_issuing_country=data.get('passport_issuing_country'),
            passport_expiry_date=data.get('passport_expiry_date') or None,
            airline_memberships=memberships_json,
            remarks=data.get('remarks'),
            is_leader=is_first_member  # 第一个人员自动设为leader
        )
        
        db.session.add(member)
        
        # 如果是第一个人员，同时更新项目Header的leader_name字段
        if is_first_member:
            leader_name = f"{member.title} {member.member_name}" if member.title else member.member_name
            header.leader_name = leader_name
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '人员添加成功' + ('（已自动设为Leader）' if is_first_member else ''),
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
        if 'gender' in data:
            member.gender = data['gender']
        if 'date_of_birth' in data:
            member.date_of_birth = data['date_of_birth'] or None
        if 'nationality' in data:
            member.nationality = data['nationality']
        if 'id_type' in data:
            member.id_type = data['id_type']
        if 'id_number' in data:
            member.id_number = data['id_number']
        if 'passport_issuing_country' in data:
            member.passport_issuing_country = data['passport_issuing_country']
        if 'passport_expiry_date' in data:
            member.passport_expiry_date = data['passport_expiry_date'] or None
        if 'remarks' in data:
            member.remarks = data['remarks']
        if 'airline_memberships' in data:
            memberships = data['airline_memberships']
            member.airline_memberships = json.dumps(memberships, ensure_ascii=False) if memberships else None

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


@project_members_bp.route('/<int:project_id>/members/<int:member_id>/set-leader', methods=['POST'])
def set_leader(project_id, member_id):
    """设置人员为Leader"""
    try:
        # 先取消该项目所有人员的Leader状态
        ProjectMember.query.filter_by(header_id=project_id).update({'is_leader': False})
        
        # 设置指定人员为Leader
        member = ProjectMember.query.filter_by(id=member_id, header_id=project_id).first_or_404()
        member.is_leader = True
        
        # 同时更新项目Header的leader_name字段
        header = ProjectHeader.query.get(project_id)
        if header:
            leader_name = f"{member.title} {member.member_name}" if member.title else member.member_name
            header.leader_name = leader_name
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{member.member_name} 已设为Leader',
            'data': member.to_dict()
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
        
        # 检查是否已有人员，如果没有，则第一个添加的人员自动成为leader
        existing_members_count = ProjectMember.query.filter_by(header_id=project_id).count()
        is_first_batch = existing_members_count == 0
        
        added_members = []
        for idx, m_data in enumerate(members_data):
            if not m_data.get('member_name'):
                continue
            
            # 如果是第一批且是第一个人员，自动设为leader
            is_first_member = is_first_batch and idx == 0
            
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
                remarks=m_data.get('remarks'),
                is_leader=is_first_member  # 第一个人员自动设为leader
            )
            db.session.add(member)
            added_members.append(member)
            
            # 如果是第一个人员，同时更新项目Header的leader_name字段
            if is_first_member:
                leader_name = f"{member.title} {member.member_name}" if member.title else member.member_name
                header.leader_name = leader_name
        
        db.session.commit()
        
        message = f'成功添加 {len(added_members)} 名人员'
        if is_first_batch and added_members:
            message += '（第一个人员已自动设为Leader）'
        
        return jsonify({
            'success': True,
            'message': message,
            'data': [m.to_dict() for m in added_members]
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

