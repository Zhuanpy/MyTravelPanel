from App_new.exts import db
from datetime import datetime
import json


class TourItineraryTemplate(db.Model):
    """每日行程模板库

    payload 存的就是 tour_projects._group_to_template() 产出的那份 JSON —— 与
    「导出模板」下载的 .json 文件同一个结构。里面每天记的是 day_offset（相对
    出发日的天数偏移）而不是绝对日期，所以同一份模板套到任何出发日期上都能
    自动排好。

    权限：全员共享可调用，仅创建人与管理员可改名/覆盖/删除。
    """
    __tablename__ = 'tour_itinerary_templates'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    name = db.Column(db.String(200), nullable=False, comment='模板名称')
    destination = db.Column(db.String(100), nullable=True, comment='目的地/线路标签，便于筛选')
    duration_days = db.Column(db.Integer, nullable=True, comment='行程天数，由 payload 算出并冗余，便于列表展示与筛选')
    remarks = db.Column(db.Text, nullable=True, comment='备注')

    payload = db.Column(db.Text, nullable=False, comment='模板正文 JSON（days / included_items / excluded_items / important_notes）')

    # 只作追溯用，故意不建外键：来源团组被删除时不应牵连模板
    source_group_id = db.Column(db.Integer, nullable=True, comment='来源团组ID（仅追溯）')

    created_by_id = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=True, comment='创建人ID')
    created_by_name = db.Column(db.String(100), nullable=True, comment='创建人显示名（缓存，防止关联查不到时列表空白）')

    use_count = db.Column(db.Integer, default=0, nullable=False, comment='被调用次数')
    last_used_at = db.Column(db.DateTime, nullable=True, comment='最近调用时间')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = db.relationship('AuthUser', foreign_keys=[created_by_id])

    def __repr__(self):
        return f'<TourItineraryTemplate {self.name}>'

    @property
    def template_data(self):
        """解析后的模板正文；payload 坏掉时返回空 dict 而不是抛异常（列表页不能因一条坏数据整页挂掉）"""
        try:
            data = json.loads(self.payload) if self.payload else {}
            return data if isinstance(data, dict) else {}
        except (ValueError, TypeError):
            return {}

    @property
    def creator_display_name(self):
        """创建人显示名：关联 → profile → username → 缓存字段兜底"""
        if self.creator:
            prof = getattr(self.creator, 'profile', None)
            if prof and hasattr(prof, 'get_full_name'):
                name = prof.get_full_name()
                if name:
                    return name
            if self.creator.username:
                return self.creator.username
        return self.created_by_name

    def can_edit(self, user):
        """是否可改名/覆盖/删除：创建人本人或管理员"""
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        role = getattr(user, 'role', None)
        if role is not None and getattr(role, 'name', None) == 'admin':
            return True
        return self.created_by_id is not None and self.created_by_id == user.id

    def to_dict(self, current_user=None):
        return {
            'id': self.id,
            'name': self.name,
            'destination': self.destination,
            'duration_days': self.duration_days,
            'remarks': self.remarks,
            'source_group_id': self.source_group_id,
            'created_by_id': self.created_by_id,
            'created_by_name': self.creator_display_name,
            'use_count': self.use_count or 0,
            'last_used_at': self.last_used_at.strftime('%Y-%m-%d %H:%M') if self.last_used_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None,
            'day_count': len(self.template_data.get('days') or []),
            'can_edit': self.can_edit(current_user),
        }
