from App_new.exts import db
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
    
    # 国旗文件名
    flag_file = db.Column(db.String(255), nullable=True, comment='国旗文件名')

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

    # 签证类型英文名（面向客户页面显示）
    visa_type_en = db.Column(db.String(100), nullable=True, comment='签证类型英文名')

    # 处理时间
    processing_time = db.Column(db.String(200), nullable=False)

    # 申请费用（售价）
    fee = db.Column(db.String(200), nullable=False)

    # 成本
    cost = db.Column(db.String(200), nullable=True, comment='成本价格')

    # 签证有效期（如：90天、1年多次）
    validity_period = db.Column(db.String(100), nullable=True, comment='签证有效期')

    # 签证说明
    introduction = db.Column(db.Text, nullable=True)
    
    # 时间字段
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment='更新时间')
    valid_until = db.Column(db.DateTime, nullable=True, comment='有效期')
    
    # 激活状态字段
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment='是否激活（显示在外部网页）')

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
            'cost': self.cost,
            'validity_period': self.validity_period,
            'introduction': self.introduction,
            'country_id': self.country_id,
            'country_name': self.country.country_name_CN if self.country else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'is_active': self.is_active,
            'identities': [identity.to_dict() for identity in self.identities],
            'links': [link.to_dict() for link in self.links]
        }


# 签证资料和文档的多对多关联表
visa_document_documents = db.Table('visa_document_documents',
    db.Column('visa_document_id', db.Integer, db.ForeignKey('visa_documents_request.id', ondelete='CASCADE'), primary_key=True),
    db.Column('document_id', db.Integer, db.ForeignKey('visa_documents_list.id', ondelete='CASCADE'), primary_key=True),
    db.Column('responsible_party', db.String(20), default='FOR_APPLICATION', comment='资料准备方：FOR_APPLICATION(申请人准备)/FOR_AGENT(旅行社准备)'),
    db.Column('display_order', db.Integer, default=0, comment='显示顺序')
)


class VisaDocuments(db.Model):

    __tablename__ = 'visa_documents_request'
    
    id = db.Column(db.Integer, primary_key=True)
    visa_type_id = db.Column(db.Integer, db.ForeignKey('visa_types.id', ondelete='CASCADE'), nullable=False)
    singapore_identity_id = db.Column(db.Integer, db.ForeignKey('visa_singapore_identity.id', ondelete='CASCADE'), nullable=True)  # 允许为空，表示共用资料
    additional_info = db.Column(db.Text, nullable=True)  # 旅行社补充信息
    applicant_additional_info = db.Column(db.Text, nullable=True)  # 申请人补充信息
    
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
        applicant_additional_info = []
        
        if share_doc and share_doc.additional_info and share_doc.additional_info != '待输入':
            additional_info.append(share_doc.additional_info)
        if specific_doc and specific_doc.additional_info and specific_doc.additional_info != 'None':
            if additional_info:
                additional_info.append("\n")
            additional_info.append(specific_doc.additional_info)
            
        if share_doc and share_doc.applicant_additional_info and share_doc.applicant_additional_info != '待输入':
            applicant_additional_info.append(share_doc.applicant_additional_info)
        if specific_doc and specific_doc.applicant_additional_info and specific_doc.applicant_additional_info != 'None':
            if applicant_additional_info:
                applicant_additional_info.append("\n")
            applicant_additional_info.append(specific_doc.applicant_additional_info)
        
        result = {
            'document_info': "\n".join(document_info) if document_info else "暂无文件资料",
            'additional_info': "\n".join(additional_info) if additional_info else "暂无补充信息",
            'applicant_additional_info': "\n".join(applicant_additional_info) if applicant_additional_info else "暂无申请人补充信息"
        }
        print(f"DEBUG: 返回结果: {result}")
        return result

    @classmethod
    def get_applicant_documents(cls, visa_type_id, singapore_identity_id):
        """获取申请人准备的文档资料（responsible_party='FOR_APPLICATION'）"""
        print(f"DEBUG: 查询申请人资料 - visa_type_id: {visa_type_id}, singapore_identity_id: {singapore_identity_id}")
        
        # 获取SHARE身份记录
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        share_identity_id = share_identity.id if share_identity else None
        
        # 获取SHARE共用资料
        share_doc = cls.query.filter_by(
            visa_type_id=visa_type_id,
            singapore_identity_id=share_identity_id
        ).first()
        
        # 获取特定身份资料
        specific_doc = None
        if singapore_identity_id and singapore_identity_id != share_identity_id:
            specific_doc = cls.query.filter_by(
                visa_type_id=visa_type_id,
                singapore_identity_id=singapore_identity_id
            ).first()
        
        # 收集申请人准备的文档，按display_order统一排序
        document_associations = []
        
        # 处理SHARE共用资料中的申请人文档
        if share_doc:
            try:
                # 尝试按display_order排序（如果字段存在）
                share_associations = db.session.query(visa_document_documents).filter_by(
                    visa_document_id=share_doc.id,
                    responsible_party='FOR_APPLICATION'
                ).order_by(visa_document_documents.c.display_order.asc()).all()
                
                for association in share_associations:
                    doc = VisaDocumentsList.query.get(association.document_id)
                    if doc:
                        document_associations.append({
                            'doc': doc,
                            'display_order': association.display_order or 0,
                            'visa_document_id': share_doc.id,
                            'identity_type': 'SHARE'
                        })
                        
            except Exception:
                # 如果display_order字段不存在，使用原来的方法
                for doc_association in share_doc.selected_documents:
                    association = db.session.query(visa_document_documents).filter_by(
                        visa_document_id=share_doc.id,
                        document_id=doc_association.id,
                        responsible_party='FOR_APPLICATION'
                    ).first()
                    if association:
                        document_associations.append({
                            'doc': doc_association,
                            'display_order': 0,  # 默认顺序
                            'visa_document_id': share_doc.id,
                            'identity_type': 'SHARE'
                        })
        
        # 处理特定身份资料中的申请人文档
        if specific_doc:
            try:
                # 尝试按display_order排序（如果字段存在）
                specific_associations = db.session.query(visa_document_documents).filter_by(
                    visa_document_id=specific_doc.id,
                    responsible_party='FOR_APPLICATION'
                ).order_by(visa_document_documents.c.display_order.asc()).all()
                
                for association in specific_associations:
                    doc = VisaDocumentsList.query.get(association.document_id)
                    if doc:
                        # 检查是否已经存在相同的文档（避免重复）
                        existing_doc = next((item for item in document_associations 
                                           if item['doc'].id == doc.id), None)
                        if not existing_doc:
                            document_associations.append({
                                'doc': doc,
                                'display_order': association.display_order or 0,
                                'visa_document_id': specific_doc.id,
                                'identity_type': specific_doc.singapore_identity.identity_zh if specific_doc.singapore_identity else 'UNKNOWN'
                            })
                        else:
                            # 如果文档已存在，更新display_order为更大的值（优先级更高）
                            existing_doc['display_order'] = max(existing_doc['display_order'], association.display_order or 0)
                            
            except Exception:
                # 如果display_order字段不存在，使用原来的方法
                for doc_association in specific_doc.selected_documents:
                    association = db.session.query(visa_document_documents).filter_by(
                        visa_document_id=specific_doc.id,
                        document_id=doc_association.id,
                        responsible_party='FOR_APPLICATION'
                    ).first()
                    if association:
                        # 检查是否已经存在相同的文档
                        existing_doc = next((item for item in document_associations 
                                           if item['doc'].id == doc_association.id), None)
                        if not existing_doc:
                            document_associations.append({
                                'doc': doc_association,
                                'display_order': 0,  # 默认顺序
                                'visa_document_id': specific_doc.id,
                                'identity_type': specific_doc.singapore_identity.identity_zh if specific_doc.singapore_identity else 'UNKNOWN'
                            })
        
        # 按display_order排序，然后提取文档列表
        document_associations.sort(key=lambda x: x['display_order'])
        applicant_documents = [item['doc'] for item in document_associations]
        
        # 格式化文档信息
        document_info = []
        if applicant_documents:
            for doc in applicant_documents:
                document_info.append(f"• {doc.name}")
        else:
            document_info.append("• 暂无申请人准备资料")
        
        # 收集补充信息
        additional_info = []
        applicant_additional_info = []
        
        # 收集旅行社补充信息
        share_additional = share_doc and share_doc.additional_info and share_doc.additional_info != '待输入'
        specific_additional = specific_doc and specific_doc.additional_info and specific_doc.additional_info != 'None'
        
        if share_additional:
            additional_info.append(share_doc.additional_info)
        if specific_additional:
            additional_info.append(specific_doc.additional_info)
            
        # 收集申请人补充信息
        share_applicant = share_doc and share_doc.applicant_additional_info and share_doc.applicant_additional_info != '待输入'
        specific_applicant = specific_doc and specific_doc.applicant_additional_info and specific_doc.applicant_additional_info != 'None'
        
        if share_applicant:
            applicant_additional_info.append(share_doc.applicant_additional_info)
        if specific_applicant:
            applicant_additional_info.append(specific_doc.applicant_additional_info)

        result = {
            'document_info': "\n".join(document_info),
            'additional_info': "\n".join(additional_info) if additional_info else "暂无补充信息",
            'applicant_additional_info': "\n".join(applicant_additional_info) if applicant_additional_info else "暂无申请人补充信息"
        }
        print(f"DEBUG: 申请人资料返回结果: {result}")
        return result

    @classmethod
    def insert_data(cls, visa_type_id, singapore_identity_id, additional_info=None, applicant_additional_info=None):
        """插入或更新签证文档信息"""
        # 检查是否已存在相同记录
        existing_doc = cls.query.filter_by(
            visa_type_id=visa_type_id,
            singapore_identity_id=singapore_identity_id
        ).first()
        
        if existing_doc:
            # 更新现有记录
            existing_doc.additional_info = additional_info
            existing_doc.applicant_additional_info = applicant_additional_info
        else:
            # 创建新记录
            new_doc = cls(
                visa_type_id=visa_type_id,
                singapore_identity_id=singapore_identity_id,
                additional_info=additional_info,
                applicant_additional_info=applicant_additional_info
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
    name_en = db.Column(db.String(150), nullable=True)  # 文档名称英文
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f'<VisaDocumentList {self.name}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'name_en': self.name_en,
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
    visa_countries_id = db.Column(db.Integer, db.ForeignKey('visa_countries.id', ondelete='CASCADE'), nullable=True)
    name = db.Column(db.String(50), nullable=False)
    link = db.Column(db.Text)

    # 建立与 VisaTypes 表的关系
    visa_type = db.relationship('VisaTypes', back_populates='links')
    
    # 建立与 VisaCountries 表的关系
    country = db.relationship('VisaCountries')

    def __repr__(self):
        return f"<VisaLink(id={self.id}, visa_type_id={self.visa_type_id}, name='{self.name}')>"
        
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'link': self.link,
            'visa_type_id': self.visa_type_id,
            'visa_countries_id': self.visa_countries_id,
            'country_name': self.country.country_name_CN if self.country else None
        }


class VisaVisitStats(db.Model):
    """签证访问统计模型"""
    __tablename__ = 'visa_visit_stats'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    visa_type_id = db.Column(db.Integer, db.ForeignKey('visa_types.id', ondelete='CASCADE'), nullable=False)
    visa_type_name = db.Column(db.String(100), nullable=False)
    country_name = db.Column(db.String(100), nullable=True)
    visitor_ip = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    referer = db.Column(db.Text, nullable=True)
    visit_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    session_id = db.Column(db.String(100), nullable=True)

    # 关系定义
    visa_type = db.relationship('VisaTypes', backref='visit_stats')

    def __repr__(self):
        return f"<VisaVisitStats(id={self.id}, visa_type='{self.visa_type_name}', visit_time='{self.visit_time}')>"

    @staticmethod
    def record_visit(visa_type_id, visa_type_name, country_name=None, visitor_ip=None, 
                    user_agent=None, referer=None, session_id=None):
        """记录访问统计"""
        try:
            visit_record = VisaVisitStats(
                visa_type_id=visa_type_id,
                visa_type_name=visa_type_name,
                country_name=country_name,
                visitor_ip=visitor_ip,
                user_agent=user_agent,
                referer=referer,
                session_id=session_id
            )
            db.session.add(visit_record)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"记录访问统计失败: {str(e)}")
            return False

    @staticmethod
    def get_visit_stats(visa_type_id=None, days=30):
        """获取访问统计"""
        try:
            query = VisaVisitStats.query
            if visa_type_id:
                query = query.filter_by(visa_type_id=visa_type_id)
            
            # 按时间过滤
            from datetime import datetime, timedelta
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(VisaVisitStats.visit_time >= start_date)
            
            return query.order_by(VisaVisitStats.visit_time.desc()).all()
        except Exception as e:
            print(f"获取访问统计失败: {str(e)}")
            return []

    @staticmethod
    def get_popular_visas(limit=10, days=30):
        """获取热门签证类型"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # 按签证类型分组统计访问次数
            popular_visas = db.session.query(
                VisaVisitStats.visa_type_id,
                VisaVisitStats.visa_type_name,
                VisaVisitStats.country_name,
                func.count(VisaVisitStats.id).label('visit_count')
            ).filter(
                VisaVisitStats.visit_time >= start_date
            ).group_by(
                VisaVisitStats.visa_type_id,
                VisaVisitStats.visa_type_name,
                VisaVisitStats.country_name
            ).order_by(
                func.count(VisaVisitStats.id).desc()
            ).limit(limit).all()
            
            return popular_visas
        except Exception as e:
            print(f"获取热门签证失败: {str(e)}")
            return []


class VisaProject(db.Model):

    __tablename__ = 'visa_projects'

    VALID_STATUSES = ['待递交', '待出签', '已出签', '忽略单']

    id = db.Column(db.Integer, primary_key=True)  # 项目唯一标识符
    project_folder_name = db.Column(db.String(100), nullable=False)  # 项目文件夹名称
    created_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # 创建时间
    visa_status = db.Column(db.String(50), nullable=False, default='待递交')  # 签证状态
    estimated_date = db.Column(db.Date, nullable=True)  # 预估完成日期
    country = db.Column(db.String(50), nullable=True)  # 国家（与 REF 共享，可为空）
    visa_type = db.Column(db.String(50), nullable=True)  # 签证类型
    applicant_name = db.Column(db.String(100), nullable=True)  # 申请人名字

    contact_name = db.Column(db.String(100), nullable=True)  # 联系人名字
    remarks = db.Column(db.Text, nullable=True)  # 备注信息
    hid_or_serial = db.Column(db.String(100), nullable=True)  # HID或序列号
    singapore_status = db.Column(db.String(50), nullable=True)  # 在新加坡身份

    # 与资料准备状态的一对多关系
    document_statuses = db.relationship('VisaProjectDocumentStatus', back_populates='project', cascade='all, delete-orphan')
    
    # 与项目系统的关联
    header_id = db.Column(db.Integer, db.ForeignKey('project_headers.id'), nullable=True, comment='关联的项目主表ID')
    ref_id = db.Column(db.Integer, db.ForeignKey('project_refs.id'), nullable=True, comment='关联的REF明细ID')
    
    # 关系定义
    header = db.relationship('ProjectHeader', backref='visa_projects')
    ref = db.relationship('ProjectRef', backref='visa_projects')

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


class VisaTemplateFiles(db.Model):
    """签证模板文件模型"""
    __tablename__ = 'visa_template_files'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    visa_type_id = db.Column(db.Integer, db.ForeignKey('visa_types.id', ondelete='CASCADE'), nullable=False)
    singapore_identity_id = db.Column(db.Integer, db.ForeignKey('visa_singapore_identity.id', ondelete='CASCADE'), nullable=True)  # 允许为空，表示共用模板
    template_name = db.Column(db.String(200), nullable=False)  # 模板名称
    template_type = db.Column(db.String(100), nullable=False)  # 模板类型：公司信、邀请信、申请表等
    file_path = db.Column(db.String(500), nullable=False)  # 文件路径
    file_size = db.Column(db.Integer, nullable=True)  # 文件大小（字节）
    file_type = db.Column(db.String(50), nullable=True)  # 文件类型（扩展名）
    description = db.Column(db.Text, nullable=True)  # 模板描述
    is_active = db.Column(db.Boolean, default=True)  # 是否激活
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系定义
    visa_type = db.relationship('VisaTypes', backref=db.backref('template_files', lazy='dynamic'))
    singapore_identity = db.relationship('VisaSingaporeIdentity', backref=db.backref('template_files', lazy='dynamic'))
    
    def __repr__(self):
        return f'<VisaTemplateFile(id={self.id}, template_name="{self.template_name}", visa_type_id={self.visa_type_id})>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'visa_type_id': self.visa_type_id,
            'visa_type_name': self.visa_type.visa_type if self.visa_type else None,
            'singapore_identity_id': self.singapore_identity_id,
            'identity_name': self.singapore_identity.identity_zh if self.singapore_identity else '共用',
            'template_name': self.template_name,
            'template_type': self.template_type,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_templates_by_visa_type(cls, visa_type_id, identity_id=None):
        """根据签证类型和身份获取模板文件"""
        query = cls.query.filter_by(visa_type_id=visa_type_id, is_active=True)
        if identity_id is not None:
            query = query.filter_by(singapore_identity_id=identity_id)
        return query.order_by(cls.template_type, cls.template_name).all()
    
    @classmethod
    def get_template_types(cls):
        """获取所有模板类型"""
        return db.session.query(cls.template_type).distinct().all()


class VisaProjectFile(db.Model):
    """签证项目上传文件模型"""
    __tablename__ = 'visa_project_files'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('visa_projects.id', ondelete='CASCADE'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)  # 原始文件名
    file_path = db.Column(db.String(500), nullable=False)  # 存储路径
    file_size = db.Column(db.Integer, nullable=True)  # 文件大小（字节）
    file_type = db.Column(db.String(50), nullable=True)  # 文件类型（扩展名）
    description = db.Column(db.String(500), nullable=True)  # 文件描述
    uploaded_by = db.Column(db.String(100), nullable=True)  # 上传人
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系定义
    project = db.relationship('VisaProject', backref=db.backref('files', lazy='dynamic', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<VisaProjectFile(id={self.id}, file_name="{self.file_name}", project_id={self.project_id})>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'description': self.description,
            'uploaded_by': self.uploaded_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def get_file_size_display(self):
        """获取友好的文件大小显示"""
        if not self.file_size:
            return '未知'
        if self.file_size < 1024:
            return f'{self.file_size} B'
        elif self.file_size < 1024 * 1024:
            return f'{self.file_size / 1024:.1f} KB'
        else:
            return f'{self.file_size / (1024 * 1024):.1f} MB'
