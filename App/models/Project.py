from ..exts import db
from datetime import datetime

class Project(db.Model):
    """项目主表"""
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    hid = db.Column(db.String(20), unique=True, nullable=False, comment='项目编号')
    project_name = db.Column(db.String(100), nullable=False, comment='项目名称')
    client_name = db.Column(db.String(100), nullable=False, comment='客户名称')
    description = db.Column(db.Text, comment='项目描述')
    status = db.Column(db.Enum('draft', 'active', 'completed', 'cancelled'), 
                      default='draft', nullable=False, comment='项目状态')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    refs = db.relationship('ProjectRef', backref='project', cascade='all, delete-orphan')

    @classmethod
    def generate_hid(cls):
        """生成项目编号 HID"""
        # 格式: H + 年月日 + 3位序号, 例如: H2024031001
        today = datetime.now()
        date_str = today.strftime('%Y%m%d')
        
        # 查找当天最后一个编号
        last_hid = cls.query.filter(
            cls.hid.like(f'H{date_str}%')
        ).order_by(cls.hid.desc()).first()

        if last_hid:
            last_number = int(last_hid.hid[-3:])
            new_number = str(last_number + 1).zfill(3)
        else:
            new_number = '001'

        return f'H{date_str}{new_number}'

class ProjectRef(db.Model):
    """项目REF表"""
    __tablename__ = 'project_refs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    ref_number = db.Column(db.String(30), unique=True, nullable=False, comment='REF编号')
    ref_type_id = db.Column(db.Integer, db.ForeignKey('business_types.id'), nullable=False, comment='REF类型ID')
    description = db.Column(db.String(200), nullable=False, comment='描述')
    status = db.Column(db.Enum('draft', 'processing', 'completed', 'cancelled'),
                      default='draft', nullable=False, comment='状态')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    eos = db.relationship('ProjectEO', backref='ref', cascade='all, delete-orphan')
    ref_type = db.relationship('BusinessType', backref='refs')

    @classmethod
    def generate_ref_number(cls, project_hid):
        """生成REF编号"""
        # 检查项目是否存在（仅在非新项目时检查）
        today = datetime.now().strftime('%Y%m%d')
        if not project_hid.endswith(today):
            project = Project.query.filter_by(hid=project_hid).first()
            if not project:
                raise ValueError(f'项目编号 {project_hid} 不存在')

        # 查找当前项目最后一个REF编号
        last_ref = cls.query.filter(
            cls.ref_number.like(f'{project_hid}-R%')
        ).order_by(cls.ref_number.desc()).first()

        if last_ref:
            last_number = int(last_ref.ref_number.split('-R')[1])
            new_number = str(last_number + 1).zfill(2)
        else:
            new_number = '01'

        return f'{project_hid}-R{new_number}'

class ProjectEO(db.Model):
    """项目EO表"""
    __tablename__ = 'project_eos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=False)
    eo_number = db.Column(db.String(30), unique=True, nullable=False, comment='EO编号')
    supplier_type = db.Column(db.Enum('visa', 'flight', 'hotel', 'transport', 'local_operator', 'other'),
                            nullable=False, comment='供应商类型')
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False, comment='金额')
    remarks = db.Column(db.Text, comment='备注')
    status = db.Column(db.Enum('draft', 'confirmed', 'paid', 'cancelled'),
                      default='draft', nullable=False, comment='状态')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    supplier = db.relationship('Supplier', backref='eos') 