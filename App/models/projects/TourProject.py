from ...exts import db
from datetime import datetime
import json

# tour_group 行程团信息表
class TourGroup(db.Model):
    """行程团信息模型"""
    __tablename__ = 'tour_group'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False, comment='行程名称')
    departure_date = db.Column(db.Date, nullable=False, comment='出发日期')
    return_date = db.Column(db.Date, nullable=False, comment='返回日期')
    pax = db.Column(db.Integer, nullable=False, comment='人数')
    agency = db.Column(db.String(200), nullable=True, comment='旅行社')
    operator = db.Column(db.String(200), nullable=True, comment='地接社')
    hotel_info = db.Column(db.String(500), nullable=True, comment='酒店说明')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    project_id = db.Column(db.Integer, db.ForeignKey('tour_project.id'), nullable=False, comment='所属项目')
    project_type = db.Column(db.String(50), nullable=True, comment='项目类型')
    created_by = db.Column(db.String(100), nullable=True, comment='创建人')
    group_code = db.Column(db.String(100), nullable=True, comment='团编号')
    group_status = db.Column(db.String(50), nullable=True, comment='团状态')
    transport = db.Column(db.Text, nullable=True, comment='交通工具')
    meals = db.Column(db.Text, nullable=True, comment='用餐安排')
    attractions = db.Column(db.Text, nullable=True, comment='景点/活动')
    included_items = db.Column(db.Text, nullable=True, comment='包含项目')
    excluded_items = db.Column(db.Text, nullable=True, comment='不包含项目')
    important_notes = db.Column(db.Text, nullable=True, comment='注意事项')

    # 关联关系
    project = db.relationship('TourProject', backref=db.backref('groups', lazy='dynamic'))
    # 行程关联，按日期升序
    itineraries = db.relationship(
        'TourItinerary',
        backref='tour_group',
        lazy='dynamic',
        order_by='TourItinerary.date'
    )

    def __repr__(self):
        return f'<TourGroup {self.title}>'

    @property
    def duration_days(self):
        """计算行程天数（包含出发当天）"""
        if self.departure_date and self.return_date:
            return (self.return_date - self.departure_date).days + 1
        return 0

# tour itinerary  每日行程表
class TourItinerary(db.Model):
    """每日行程模型"""
    __tablename__ = 'tour_itinerary'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tour_id = db.Column(db.Integer, db.ForeignKey('tour_group.id'), nullable=False, comment='外键，关联 tour_group.id')
    day_title = db.Column(db.String(200), nullable=False, comment='日期标题（如 Day 1: Arrival）')
    date = db.Column(db.Date, nullable=False, comment='日期')
    content = db.Column(db.Text, nullable=False, comment='行程详情（HTML 或纯文本）')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    def __repr__(self):
        return f'<TourItinerary {self.day_title}>'

    @property
    def day_number(self):
        """获取天数（从 day_title 中提取）"""
        import re
        match = re.search(r'Day\s+(\d+)', self.day_title, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    

# 定义 tour_project 表的模型
class TourProject(db.Model):

    __tablename__ = 'tour_project'

    id = db.Column(db.Integer, primary_key=True)  # 自增主键
    project_name = db.Column(db.String(100), nullable=False)  # 项目名称
    project_hid = db.Column(db.String(255), nullable=True)  # 项目HID，允许为空
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间
    project_status = db.Column(db.String(50), nullable=False)  # 项目状态
    folder_name = db.Column(db.String(100), nullable=False)  # 项目状态
    contact_person = db.Column(db.String(100), nullable=False)  # 联系人
    contact_info = db.Column(db.String(100), nullable=False)  # 联系方式
    remarks = db.Column(db.Text, nullable=True)  # 备注
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间
    project_type = db.Column(db.String(50), nullable=True, comment='项目类型')
    budget = db.Column(db.Float, nullable=True, comment='项目预算')

    def __init__(self, project_name, project_hid, project_status, folder_name, contact_person, contact_info, remarks,
                 created_at=None):
        self.project_name = project_name
        self.project_hid = project_hid
        self.project_status = project_status
        self.folder_name = folder_name
        self.contact_person = contact_person
        self.contact_info = contact_info
        self.remarks = remarks
        self.created_at = created_at or datetime.utcnow()

    def save(self):
        """保存或更新当前实例到数据库"""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, project_id):
        """通过 ID 获取实例"""
        return cls.query.get(project_id)

    def to_dict(self):
        """将模型实例转化为字典，用于 JSON 响应"""
        return {
            "id": self.id,
            "project_name": self.project_name,
            "project_hid": self.project_hid,
            "created_at": self.created_at.strftime('%Y-%m-%d'),
            "project_status": self.project_status,
            "folder_name": self.folder_name,
            "contact_person": self.contact_person,
            "contact_info": self.contact_info,
            "remarks": self.remarks
        }
