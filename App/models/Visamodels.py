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
    
    # 与VisaLinks的一对多关系
    links = db.relationship('VisaLinks', back_populates='visa_type', cascade='all, delete-orphan')

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
            'identities': [identity.to_dict() for identity in self.identities],
            'links': [link.to_dict() for link in self.links]
        }


# 签证资料和文档的多对多关联表
visa_document_documents = db.Table('visa_document_documents',
    db.Column('visa_document_id', db.Integer, db.ForeignKey('visa_documents_request.id', ondelete='CASCADE'), primary_key=True),
    db.Column('document_id', db.Integer, db.ForeignKey('visa_documents_list.id', ondelete='CASCADE'), primary_key=True)
)


class VisaDocuments(db.Model):

    __tablename__ = 'visa_documents_request'
    
    id = db.Column(db.Integer, primary_key=True)
    visa_type_id = db.Column(db.Integer, db.ForeignKey('visa_types.id', ondelete='CASCADE'), nullable=False)
    singapore_identity_id = db.Column(db.Integer, db.ForeignKey('visa_singapore_identity.id', ondelete='CASCADE'), nullable=True)  # 允许为空，表示共用资料
    additional_info = db.Column(db.Text, nullable=True)
    
    # 关系定义
    visa_type = db.relationship('VisaTypes', backref=db.backref('visa_documents', lazy='dynamic'))
    singapore_identity = db.relationship('VisaSingaporeIdentity', backref=db.backref('visa_documents', lazy='dynamic'))
    
    # 与VisaDocumentsList的多对多关系
    selected_documents = db.relationship('VisaDocumentsList', 
                                       secondary=visa_document_documents,
                                       backref=db.backref('visa_documents', lazy='dynamic'))

    @classmethod
    def get_document_info(cls, visa_type_id, singapore_identity_id):
        """获取指定国家和身份的文档信息，包括共用资料"""
        print(f"DEBUG: 查询文档信息 - visa_type_id: {visa_type_id}, singapore_identity_id: {singapore_identity_id}")
        
        # 获取SHARE身份记录
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        if not share_identity:
            print("DEBUG: 没有找到SHARE身份记录")
            share_identity_id = None
        else:
            share_identity_id = share_identity.id
            print(f"DEBUG: SHARE身份ID: {share_identity_id}")
        
        # 获取SHARE共用资料（使用SHARE身份ID）
        share_doc = cls.query.filter_by(
            visa_type_id=visa_type_id,
            singapore_identity_id=share_identity_id
        ).first()
        print(f"DEBUG: SHARE共用资料查询结果: {share_doc}")
        
        # 如果SHARE记录不存在，自动创建一个
        if not share_doc and share_identity_id:
            print(f"DEBUG: 未找到SHARE共用资料记录，正在创建...")
            share_doc = cls(
                visa_type_id=visa_type_id,
                singapore_identity_id=share_identity_id,  # 使用SHARE身份ID
                additional_info='待输入'
            )
            db.session.add(share_doc)
            db.session.commit()
            print(f"DEBUG: SHARE共用资料记录创建成功，ID: {share_doc.id}")
        
        if share_doc:
            print(f"DEBUG: SHARE共用资料文档数量: {len(share_doc.selected_documents) if share_doc.selected_documents else 0}")
            print(f"DEBUG: SHARE共用资料文档列表: {[d.name for d in share_doc.selected_documents] if share_doc.selected_documents else []}")
        
        # 获取特定身份资料
        specific_doc = None
        if singapore_identity_id and singapore_identity_id != share_identity_id:  # 排除SHARE
            specific_doc = cls.query.filter_by(
                visa_type_id=visa_type_id,
                singapore_identity_id=singapore_identity_id
            ).first()
            print(f"DEBUG: 特定身份资料查询结果: {specific_doc}")
            if specific_doc:
                print(f"DEBUG: 特定身份资料文档数量: {len(specific_doc.selected_documents) if specific_doc.selected_documents else 0}")
                print(f"DEBUG: 特定身份资料文档列表: {[d.name for d in specific_doc.selected_documents] if specific_doc.selected_documents else []}")
            else:
                print(f"DEBUG: 未找到特定身份资料记录")
        
        # 合并文档信息
        document_info = []
        
        # 处理SHARE共用资料 - 总是包含，即使为空也显示标题
        if share_doc:
            if share_doc.selected_documents:
                document_info.append("【共用资料】")
                for doc in share_doc.selected_documents:
                    document_info.append(f"• {doc.name}")
            else:
                # 即使没有文档，也显示共用资料标题
                document_info.append("【共用资料】")
                document_info.append("• 暂无共用资料")
        
        # 处理特定身份资料
        if specific_doc and specific_doc.selected_documents:
            if document_info:
                document_info.append("\n【特定身份资料】")
            else:
                document_info.append("【特定身份资料】")
            for doc in specific_doc.selected_documents:
                document_info.append(f"• {doc.name}")
        elif specific_doc:
            # 特定身份记录存在但没有文档
            if document_info:
                document_info.append("\n【特定身份资料】")
            else:
                document_info.append("【特定身份资料】")
            document_info.append("• 暂无特定身份资料")
        
        # 合并补充信息
        additional_info = []
        if share_doc and share_doc.additional_info and share_doc.additional_info != '待输入':
            additional_info.append(share_doc.additional_info)
        if specific_doc and specific_doc.additional_info and specific_doc.additional_info != 'None':
            if additional_info:
                additional_info.append("\n")
            additional_info.append(specific_doc.additional_info)
        
        result = {
            'document_info': "\n".join(document_info) if document_info else "暂无文件资料",
            'additional_info': "\n".join(additional_info) if additional_info else "暂无补充信息"
        }
        print(f"DEBUG: 返回结果: {result}")
        return result

    @classmethod
    def insert_data(cls, visa_type_id, singapore_identity_id, additional_info=None):
        """插入或更新签证文档信息"""
        # 检查是否已存在相同记录
        existing_doc = cls.query.filter_by(
            visa_type_id=visa_type_id,
            singapore_identity_id=singapore_identity_id
        ).first()
        
        if existing_doc:
            # 更新现有记录
            existing_doc.additional_info = additional_info
        else:
            # 创建新记录
            new_doc = cls(
                visa_type_id=visa_type_id,
                singapore_identity_id=singapore_identity_id,
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


class VisaDocumentsList(db.Model):
    __tablename__ = 'visa_documents_list'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)
    
    def __repr__(self):
        return f'<VisaDocumentList {self.name}>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category
        }
    
    def get_visa_documents_info(self):
        """获取关联的签证资料信息"""
        visa_docs = []
        for visa_doc in self.visa_documents:
            visa_docs.append({
                'id': visa_doc.id,
                'visa_type': visa_doc.visa_type.visa_type if visa_doc.visa_type else None,
                'singapore_identity': visa_doc.singapore_identity.identity_zh if visa_doc.singapore_identity else None
            })
        return visa_docs


class VisaLinks(db.Model):

    __tablename__ = 'visa_type_links'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    visa_type_id = db.Column(db.Integer, db.ForeignKey('visa_types.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    link = db.Column(db.Text)

    # 建立与 VisaTypes 表的关系
    visa_type = db.relationship('VisaTypes', back_populates='links')

    def __repr__(self):
        return f"<VisaLink(id={self.id}, visa_type_id={self.visa_type_id}, name='{self.name}')>"
        
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'link': self.link,
            'visa_type_id': self.visa_type_id
        }


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

    # 与资料准备状态的一对多关系
    document_statuses = db.relationship('VisaProjectDocumentStatus', back_populates='project', cascade='all, delete-orphan')

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


class VisaProjectDocumentStatus(db.Model):
    """项目资料准备状态模型"""
    __tablename__ = 'visa_project_document_status'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('visa_projects.id', ondelete='CASCADE'), nullable=False)
    document_name = db.Column(db.String(200), nullable=False)  # 资料名称
    document_type = db.Column(db.String(50), nullable=False)  # 资料类型：'document' 或 'additional'
    is_ready = db.Column(db.Boolean, default=False)  # 是否已准备好
    notes = db.Column(db.Text, nullable=True)  # 备注信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系定义
    project = db.relationship('VisaProject', back_populates='document_statuses')
    
    def __repr__(self):
        return f'<VisaProjectDocumentStatus(project_id={self.project_id}, document_name="{self.document_name}", is_ready={self.is_ready})>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'document_name': self.document_name,
            'document_type': self.document_type,
            'is_ready': self.is_ready,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

