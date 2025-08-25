# -*- coding: utf-8 -*-
"""
项目服务类
包含项目的创建、读取、更新、删除等业务逻辑
"""

from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.receipt import ProjectReceipt
from App_new.business.projects.models.eo import ProjectEO
from datetime import datetime
import traceback

class ProjectService:
    """项目服务类"""
    
    def __init__(self):
        pass
    
    def get_project_by_id(self, project_id):
        """根据ID获取项目"""
        try:
            return ProjectHeader.query.get(project_id)
        except Exception as e:
            print(f"获取项目失败: {e}")
            return None
    
    def get_project_by_hid(self, hid):
        """根据项目编号获取项目"""
        try:
            return ProjectHeader.query.filter_by(hid=hid).first()
        except Exception as e:
            print(f"获取项目失败: {e}")
            return None
    
    def get_all_projects(self, page=1, per_page=30):
        """获取所有项目（分页）"""
        try:
            return ProjectHeader.query.order_by(
                ProjectHeader.created_at.desc()
            ).paginate(page=page, per_page=per_page, error_out=False)
        except Exception as e:
            print(f"获取项目列表失败: {e}")
            return None
    
    def get_projects_by_status(self, status):
        """根据状态获取项目"""
        try:
            return ProjectHeader.query.filter_by(status=status).order_by(
                ProjectHeader.created_at.desc()
            ).all()
        except Exception as e:
            print(f"获取项目失败: {e}")
            return []
    
    def get_profitable_projects(self):
        """获取盈利项目"""
        try:
            # 这里需要复杂的查询逻辑，暂时返回空列表
            # 实际实现需要计算每个项目的利润
            return []
        except Exception as e:
            print(f"获取盈利项目失败: {e}")
            return []
    
    def get_unpaid_projects(self):
        """获取未付款项目"""
        try:
            # 这里需要复杂的查询逻辑，暂时返回空列表
            # 实际实现需要计算每个项目的未付款金额
            return []
        except Exception as e:
            print(f"获取未付款项目失败: {e}")
            return []
    
    def create_project(self, project_data):
        """创建新项目"""
        try:
            # 验证项目编号唯一性
            if not self.validate_project_hid(project_data['hid']):
                raise ValueError(f"项目编号 {project_data['hid']} 已存在")
            
            # 创建项目对象
            project = ProjectHeader(**project_data)
            
            # 保存到数据库
            db.session.add(project)
            db.session.commit()
            
            return project
        except Exception as e:
            db.session.rollback()
            print(f"创建项目失败: {e}")
            traceback.print_exc()
            return None
    
    def update_project(self, project_id, update_data):
        """更新项目"""
        try:
            project = self.get_project_by_id(project_id)
            if not project:
                return False
            
            # 更新字段
            for key, value in update_data.items():
                if hasattr(project, key):
                    setattr(project, key, value)
            
            # 保存更改
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"更新项目失败: {e}")
            traceback.print_exc()
            return False
    
    def update_project_status(self, project_id, new_status):
        """更新项目状态"""
        try:
            project = self.get_project_by_id(project_id)
            if not project:
                return False
            
            project.status = new_status
            project.updated_at = datetime.utcnow()
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"更新项目状态失败: {e}")
            return False
    
    def delete_project(self, project_id):
        """删除项目"""
        try:
            project = self.get_project_by_id(project_id)
            if not project:
                return False
            
            # 检查是否可以删除
            if not self.can_delete_project(project_id):
                return False
            
            # 删除项目
            db.session.delete(project)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"删除项目失败: {e}")
            return False
    
    def duplicate_project(self, project_id):
        """复制项目"""
        try:
            original_project = self.get_project_by_id(project_id)
            if not original_project:
                return None
            
            # 生成新的项目编号
            new_hid = self.generate_project_hid()
            
            # 创建新项目数据
            new_project_data = {
                'hid': new_hid,
                'desc': f"{original_project.desc} (副本)",
                'company_id': original_project.company_id,
                'contact': original_project.contact,
                'contact_phone': original_project.contact_phone,
                'contact_email': original_project.contact_email,
                'type': original_project.type,
                'status': 'draft',  # 副本状态设为草稿
                'currency': original_project.currency,
                'leader_name': original_project.leader_name,
                'source': original_project.source,
                'country': original_project.country,
                'remarks': f"复制自项目 {original_project.hid}",
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'last_updated_by': 'system'
            }
            
            # 创建新项目
            return self.create_project(new_project_data)
        except Exception as e:
            print(f"复制项目失败: {e}")
            return None
    
    def get_project_refs(self, project_id):
        """获取项目的REF记录"""
        try:
            return ProjectRef.query.filter_by(header_id=project_id).order_by(
                ProjectRef.created_at.desc()
            ).all()
        except Exception as e:
            print(f"获取项目REF记录失败: {e}")
            return []
    
    def get_project_receipts(self, project_id):
        """获取项目的收款记录"""
        try:
            return ProjectReceipt.query.filter_by(header_id=project_id).order_by(
                ProjectReceipt.created_at.desc()
            ).all()
        except Exception as e:
            print(f"获取项目收款记录失败: {e}")
            return []
    
    def get_project_eos(self, project_id):
        """获取项目的EO记录"""
        try:
            return ProjectEO.query.filter_by(header_id=project_id).order_by(
                ProjectEO.created_at.desc()
            ).all()
        except Exception as e:
            print(f"获取项目EO记录失败: {e}")
            return []
    
    def can_delete_project(self, project_id):
        """检查项目是否可以删除"""
        try:
            # 检查是否有REF记录
            refs_count = ProjectRef.query.filter_by(header_id=project_id).count()
            if refs_count > 0:
                return False
            
            # 检查是否有收款记录
            receipts_count = ProjectReceipt.query.filter_by(header_id=project_id).count()
            if receipts_count > 0:
                return False
            
            # 检查是否有EO记录
            eos_count = ProjectEO.query.filter_by(header_id=project_id).count()
            if eos_count > 0:
                return False
            
            return True
        except Exception as e:
            print(f"检查项目删除权限失败: {e}")
            return False
    
    def generate_project_hid(self):
        """生成项目编号"""
        try:
            # 查找最后一个项目编号
            last_project = ProjectHeader.query.order_by(
                ProjectHeader.hid.desc()
            ).first()
            
            if last_project:
                # 提取数字部分并递增
                try:
                    last_number = int(last_project.hid[1:])
                    new_number = last_number + 1
                except ValueError:
                    new_number = 1
            else:
                new_number = 1
            
            return f"H{new_number:06d}"  # 格式: H000001, H000002, ...
        except Exception as e:
            print(f"生成项目编号失败: {e}")
            return f"H{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def validate_project_hid(self, hid):
        """验证项目编号唯一性"""
        try:
            existing_project = ProjectHeader.query.filter_by(hid=hid).first()
            return existing_project is None
        except Exception as e:
            print(f"验证项目编号失败: {e}")
            return False
    
    def search_projects(self, search_term, filters=None):
        """搜索项目"""
        try:
            query = ProjectHeader.query
            
            # 基础搜索
            if search_term:
                query = query.filter(
                    db.or_(
                        ProjectHeader.hid.like(f'%{search_term}%'),
                        ProjectHeader.desc.like(f'%{search_term}%'),
                        ProjectHeader.contact.like(f'%{search_term}%')
                    )
                )
            
            # 应用筛选条件
            if filters:
                if filters.get('status'):
                    query = query.filter(ProjectHeader.status == filters['status'])
                if filters.get('type'):
                    query = query.filter(ProjectHeader.type == filters['type'])
                if filters.get('company_id'):
                    query = query.filter(ProjectHeader.company_id == filters['company_id'])
            
            return query.order_by(ProjectHeader.created_at.desc()).all()
        except Exception as e:
            print(f"搜索项目失败: {e}")
            return []
