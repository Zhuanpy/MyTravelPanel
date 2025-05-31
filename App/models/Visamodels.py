from ..exts import db
from datetime import datetime
import logging
from sqlalchemy.orm import validates


class VisaCountries(db.Model):
    __tablename__ = 'visa_countries'

    # id (主键，自增)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # 国家名称（中文），确保唯一且不可为空
    country_name_CN = db.Column(db.String(100), unique=True, nullable=False)

    # 国家名称（英文），确保唯一且不可为空
    country_name_EN = db.Column(db.String(100), unique=True, nullable=False)

    # 国家代码（3个字母代码），确保唯一且不可为空
    country_code = db.Column(db.String(3), unique=True, nullable=False)

    # 添加与VisaTypes的关系
    visa_types = db.relationship('VisaTypes', back_populates='country')

    def __repr__(self):
        return f"<VisaCountry(id={self.id}, country_name_CN='{self.country_name_CN}', country_code='{self.country_code}')>"

    @staticmethod
    def get_by_code(country_code):
        """根据国家代码获取国家记录"""
        return VisaCountries.query.filter_by(country_code=country_code).first() or None

    @staticmethod
    def get_all_countries():
        """获取所有国家记录"""
        return VisaCountries.query.all() or []


# 这个表会将 VisaTypes 与 VisaDocuments 表进行关联，构建多对多关系。
visa_type_documents = db.Table(
    'visa_type_documents',
    db.Column('visa_type_id', db.Integer, db.ForeignKey('visa_types.id'), primary_key=True),
    db.Column('document_id', db.Integer, db.ForeignKey('visa_documents.id'), primary_key=True)
)

# 这个表会将 VisaTypes 与 VisaSingaporeIdentity 表进行关联，构建多对多关系。
visa_type_identities = db.Table(
    'visa_type_identities',
    db.Column('visa_type_id', db.Integer, db.ForeignKey('visa_types.id', ondelete='CASCADE'), primary_key=True),
    db.Column('identity_id', db.Integer, db.ForeignKey('visa_singapore_identity.id', ondelete='CASCADE'), primary_key=True)
)

class VisaSingaporeIdentity(db.Model):
    """身份信息模型"""
    __tablename__ = 'visa_singapore_identity'  # 指定表名

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    identity_zh = db.Column(db.String(50), nullable=False, unique=True)
    identity_en = db.Column(db.String(100), nullable=False, unique=True)
    remarks = db.Column(db.Text, nullable=True)

    # 多对多关系
    visa_types = db.relationship('VisaTypes', 
                               secondary=visa_type_identities,
                               back_populates='identities')

    def __repr__(self):
        return f'<Identity {self.identity_zh}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'identity_zh': self.identity_zh,
            'identity_en': self.identity_en,
            'remarks': self.remarks
        }


class VisaTypes(db.Model):
    __tablename__ = 'visa_types'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # 签证类别名称
    visa_type = db.Column(db.String(50), nullable=False)

    # 处理时间
    processing_time = db.Column(db.String(200), nullable=False)

    # 申请费用
    fee = db.Column(db.String(200), nullable=False)

    # 外键关系 - 国家
    country_id = db.Column(db.Integer, db.ForeignKey('visa_countries.id'), nullable=False)
    
    # 关系定义
    country = db.relationship('VisaCountries', back_populates='visa_types')
    
    # 多对多关系
    identities = db.relationship('VisaSingaporeIdentity',
                               secondary=visa_type_identities,
                               back_populates='visa_types')

    def __repr__(self):
        return f"<VisaType(id={self.id}, visa_type='{self.visa_type}', country_id={self.country_id})>"

    @staticmethod
    def get_by_country(country_id):
        """根据国家ID获取签证类别"""
        return VisaTypes.query.filter_by(country_id=country_id).all() or []

    @staticmethod
    def get_all_types():
        """获取所有签证类别"""
        return VisaTypes.query.all() or []
        
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'visa_type': self.visa_type,
            'processing_time': self.processing_time,
            'fee': self.fee,
            'country_id': self.country_id,
            'country_name': self.country.country_name_CN if self.country else None,
            'identities': [identity.to_dict() for identity in self.identities]
        }


class VisaDocuments(db.Model):

    __tablename__ = 'visa_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    visa_type = db.Column(db.String(100), nullable=False)
    singapore_identity = db.Column(db.String(50), nullable=True)  # 允许为空，表示共用资料
    document_info = db.Column(db.Text, nullable=True)
    additional_info = db.Column(db.Text, nullable=True)
    
    @classmethod
    def get_document_info(cls, visa_type, singapore_identity):
        """获取指定国家和身份的文档信息，包括共用资料"""
        # 获取共用资料
        common_doc = cls.query.filter_by(
            visa_type=visa_type,
            singapore_identity='SHARE'
        ).first()
        
        # 获取特定身份资料
        specific_doc = cls.query.filter_by(
            visa_type=visa_type,
            singapore_identity=singapore_identity
        ).first()
        
        # 合并文档信息
        document_info = []
        if common_doc and common_doc.document_info:
            document_info.append("【共用资料】")
            document_info.append(common_doc.document_info)
        
        if specific_doc and specific_doc.document_info:
            if document_info:
                document_info.append("\n【特定身份资料】")
            document_info.append(specific_doc.document_info)
        
        # 合并补充信息
        additional_info = []
        if common_doc and common_doc.additional_info:
            additional_info.append(common_doc.additional_info)
        if specific_doc and specific_doc.additional_info:
            if additional_info:
                additional_info.append("\n")
            additional_info.append(specific_doc.additional_info)
        
        return {
            'document_info': "\n".join(document_info) if document_info else "暂无文件资料",
            'additional_info': "\n".join(additional_info) if additional_info else "暂无补充信息"
        }
    
    @classmethod
    def insert_data(cls, visa_type, singapore_identity, document_info, additional_info=None):
        """插入或更新签证文档信息"""
        # 检查是否已存在相同记录
        existing_doc = cls.query.filter_by(
            visa_type=visa_type,
            singapore_identity=singapore_identity
        ).first()
        
        if existing_doc:
            # 更新现有记录
            existing_doc.document_info = document_info
            existing_doc.additional_info = additional_info
        else:
            # 创建新记录
            new_doc = cls(
                visa_type=visa_type,
                singapore_identity=singapore_identity,
                document_info=document_info,
                additional_info=additional_info
            )
            db.session.add(new_doc)
        
        try:
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logging.error(f"保存签证文档时发生错误: {str(e)}")
            return False


class VisaLinks(db.Model):

    __tablename__ = 'visalinks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    visa_type = db.Column(db.String(50), db.ForeignKey('visa_types.visa_type'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    link = db.Column(db.Text)

    # 建立与 VisaTypes 表的关系
    visa_type_rel = db.relationship('VisaTypes', backref=db.backref('links', lazy='dynamic'))

    def __repr__(self):
        return f"<VisaLink(id={self.id}, visa_type='{self.visa_type}', name='{self.name}')>"


class VisaProject(db.Model):

    __tablename__ = 'visa_projects'

    VALID_STATUSES = ['待递交', '待出签', '已出签', '忽略单']

    id = db.Column(db.Integer, primary_key=True)  # 项目唯一标识符
    project_folder_name = db.Column(db.String(100), nullable=False)  # 项目文件夹名称
    created_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # 创建时间
    visa_status = db.Column(db.String(50), nullable=False, default='待递交')  # 签证状态
    estimated_date = db.Column(db.Date, nullable=True)  # 预估完成日期
    visa_type = db.Column(db.String(50), nullable=True)  # 签证类型
    applicant_name = db.Column(db.String(100), nullable=True)  # 申请人名字
    
    contact_name = db.Column(db.String(100), nullable=True)  # 联系人名字
    remarks = db.Column(db.Text, nullable=True)  # 备注信息
    hid_or_serial = db.Column(db.String(100), nullable=True)  # HID或序列号
    singapore_status = db.Column(db.String(50), nullable=True)  # 在新加坡身份

    def __init__(self, name, visa_status='待递交', estimated_date=None):
        if visa_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid visa status. Must be one of: {', '.join(self.VALID_STATUSES)}")
        self.name = name
        self.visa_status = visa_status
        self.estimated_date = estimated_date

    @validates('visa_status')
    def validate_status(self, key, status):
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid visa status. Must be one of: {', '.join(self.VALID_STATUSES)}")
        return status

