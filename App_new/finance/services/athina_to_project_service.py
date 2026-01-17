# -*- coding: utf-8 -*-
"""
Athina 数据导入到项目系统服务
分步骤导入：HID+REF -> EO -> Invoice -> Receipt
支持从 Athina CSV 文件导入
"""

import csv
import io
import json
import traceback
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from App_new.exts import db
from App_new.finance.models.athina_booking import AthinaBookingHeader, AthinaBookingDetail
from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.project_member import ProjectMember
from App_new.business.projects.models.eo import ProjectEO
from App_new.business.projects.models.invoice import ProjectInvoice, InvoiceItem
from App_new.business.projects.models.receipt import ProjectReceipt
from App_new.business.projects.models.supplier_payment import SupplierPayment
from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment
from App_new.shared.models.business_types import BusinessType
from App_new.business.flight.models.flight import ProjectFlightPassenger, ProjectFlightSegment


class AthinaToProjectService:
    """Athina 数据导入到项目系统服务"""

    # Athina book_type 到 BusinessType.code 的映射
    BOOK_TYPE_MAPPING = {
        'Air': 'air_ticket',
        'Hotel': 'hotel',
        'Car': 'car_rental',
        'Rail': 'rail',
        'Insurance': 'insurance',
        'Tour': 'tour',
        'Cruise': 'cruise',
        'Transfer': 'transfer',
        'Ticket': 'ticket',
        'Package': 'tour_package',
        'Visa': 'visa',
        'Other': 'other',
        'Miscellanous': 'other',  # Athina 杂项类型
        'Miscellaneous': 'other',  # 正确拼写版本
        'Misc': 'other',
        # 其他可能的映射
        'HTL': 'hotel',
        'FLT': 'air_ticket',
        'TRF': 'transfer',
        'INS': 'insurance',
    }

    def __init__(self, current_user_id=None, current_user_name=None):
        """初始化服务

        Args:
            current_user_id: 当前用户ID，用于设置导入项目的 staff_id
            current_user_name: 当前用户名，用于设置导入项目的 staff_name（如果CSV中没有）
        """
        self.current_user_id = current_user_id
        self.current_user_name = current_user_name
        self.errors = []
        self.warnings = []
        self.stats = {
            'headers_created': 0,
            'headers_updated': 0,
            'refs_created': 0,
            'refs_updated': 0,
            'members_created': 0,
            'eos_created': 0,
            'eos_updated': 0,
            'invoices_created': 0,
            'invoices_updated': 0,
            'receipts_created': 0,
            'receipts_updated': 0,
            'payment_vouchers_created': 0,
            'payment_vouchers_updated': 0,
        }

    def _get_or_create_other_type(self):
        """获取或创建 'other' 业务类型"""
        # 先按 code 查找
        other_type = BusinessType.query.filter_by(code='other').first()
        if other_type:
            return other_type.id

        # 再按名称查找（可能 code 不同但名称是 "其他"）
        other_type = BusinessType.query.filter(
            db.or_(
                BusinessType.name == '其他',
                BusinessType.name_en == 'Other',
                BusinessType.code.in_(['misc', 'miscellaneous', 'others'])
            )
        ).first()
        if other_type:
            return other_type.id

        # 都没找到，创建新的
        try:
            other_type = BusinessType(
                code='other',
                name='其他服务',  # 使用不同名称避免冲突
                name_en='Other',
                product_code_prefix='OTH',
                description='其他服务',
                is_active=True,
                sort_order=99
            )
            db.session.add(other_type)
            db.session.flush()
            self.warnings.append('已自动创建 "其他服务" 业务类型')
            return other_type.id
        except Exception as e:
            # 如果还是失败，返回任意一个可用的类型
            fallback = BusinessType.query.filter_by(is_active=True).first()
            if fallback:
                self.warnings.append(f'无法创建 "其他" 类型，使用 "{fallback.name}" 代替')
                return fallback.id
            self.errors.append(f'无法获取业务类型: {str(e)}')
            return None

    def _get_business_type_id(self, book_type):
        """根据 Athina book_type 获取 BusinessType ID"""
        if not book_type:
            # 默认使用 'other' 类型
            return self._get_or_create_other_type()

        # 尝试映射
        code = self.BOOK_TYPE_MAPPING.get(book_type)
        if code:
            bt = BusinessType.query.filter_by(code=code).first()
            if bt:
                return bt.id

        # 尝试直接匹配 code
        bt = BusinessType.query.filter_by(code=book_type.lower()).first()
        if bt:
            return bt.id

        # 尝试匹配 name_en
        bt = BusinessType.query.filter(
            BusinessType.name_en.ilike(f'%{book_type}%')
        ).first()
        if bt:
            return bt.id

        # 默认使用 'other'
        return self._get_or_create_other_type()

    def _find_or_create_company(self, company_name):
        """根据公司名称查找或创建公司

        匹配逻辑：
        1. 去掉特殊字符，统一大写后比较
        2. 如果匹配现有数据，使用现有数据
        3. 如果不存在，创建新的公司
        """
        if not company_name:
            return None

        company_name = company_name.strip()
        normalized_input = self._normalize_name(company_name).upper()

        if not normalized_input:
            return None

        # 查找所有客户公司，进行标准化比较
        all_customers = CustomerCompany.query.filter(
            CustomerCompany.is_customer == True
        ).all()

        for customer in all_customers:
            normalized_existing = self._normalize_name(customer.company_name).upper()
            if normalized_existing == normalized_input:
                # 找到匹配的公司
                return customer.id

        # 也在所有公司中查找（可能还没标记为客户）
        all_companies = CustomerCompany.query.all()
        for company in all_companies:
            normalized_existing = self._normalize_name(company.company_name).upper()
            if normalized_existing == normalized_input:
                # 找到匹配的公司，标记为客户
                if not company.is_customer:
                    company.is_customer = True
                    self.warnings.append(f'已将 "{company.company_name}" 标记为客户')
                return company.id

        # 未找到，创建新的客户公司
        try:
            new_company = CustomerCompany(
                company_name=company_name,
                is_customer=True,
                is_supplier=False,
                status='active',
                remarks='由 Athina CSV 导入自动创建',
            )
            db.session.add(new_company)
            db.session.flush()  # 获取 ID

            self.warnings.append(f'已创建新客户公司: {company_name}')
            return new_company.id

        except Exception as e:
            self.errors.append(f'创建公司 "{company_name}" 失败: {str(e)}')
            return None

    def _normalize_name(self, name):
        """标准化名称：去掉特殊字符，只保留字母数字和空格，转小写"""
        import re
        if not name:
            return ''
        # 去掉特殊字符，只保留字母、数字、空格
        normalized = re.sub(r'[^a-zA-Z0-9\s]', '', name)
        # 合并多个空格为一个
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip().lower()

    def _find_supplier(self, supplier_name):
        """根据供应商名称查找或创建供应商

        匹配逻辑：
        1. 去掉特殊字符后比较
        2. 如果匹配现有数据，使用现有数据
        3. 如果不存在，创建新的供应商
        """
        if not supplier_name:
            return None

        supplier_name = supplier_name.strip()
        normalized_input = self._normalize_name(supplier_name)

        if not normalized_input:
            return None

        # 查找所有供应商，进行标准化比较
        all_suppliers = CustomerCompany.query.filter(
            CustomerCompany.is_supplier == True
        ).all()

        for supplier in all_suppliers:
            normalized_existing = self._normalize_name(supplier.company_name)
            if normalized_existing == normalized_input:
                # 找到匹配的供应商
                return supplier.id

        # 也尝试在所有公司中查找（可能还没标记为供应商）
        all_companies = CustomerCompany.query.all()
        for company in all_companies:
            normalized_existing = self._normalize_name(company.company_name)
            if normalized_existing == normalized_input:
                # 找到匹配的公司，标记为供应商
                if not company.is_supplier:
                    company.is_supplier = True
                    self.warnings.append(f'已将公司 "{company.company_name}" 标记为供应商')
                return company.id

        # 未找到，创建新的供应商
        try:
            new_supplier = CustomerCompany(
                company_name=supplier_name,
                is_customer=False,
                is_supplier=True,
                status='active',
                remarks=f'由 Athina CSV 导入自动创建',
            )
            db.session.add(new_supplier)
            db.session.flush()  # 获取 ID

            self.warnings.append(f'已创建新供应商: {supplier_name}')
            return new_supplier.id

        except Exception as e:
            self.errors.append(f'创建供应商 "{supplier_name}" 失败: {str(e)}')
            return None

    def get_importable_athina_headers_paginated(self, search=None, filter_imported=None, page=1, per_page=20):
        """获取可导入的 Athina Header 列表（分页版本，性能优化）

        Args:
            search: 搜索关键词（HID 或公司名）
            filter_imported: 筛选已导入/未导入状态
            page: 页码
            per_page: 每页数量

        Returns:
            dict: 包含 items, total, pages 等分页信息
        """
        from sqlalchemy import func
        from App_new.finance.models.athina_booking import AthinaBookingDetail

        # 先获取已导入的 HID 集合（避免 SQL 层面的 collation 冲突）
        imported_hids_set = {p.hid for p in db.session.query(ProjectHeader.hid).all()}

        # 子查询：获取每个 header 的 details 数量
        details_count_subq = db.session.query(
            AthinaBookingDetail.header_id,
            func.count(AthinaBookingDetail.id).label('details_count')
        ).filter(
            AthinaBookingDetail.is_subtotal == False
        ).group_by(
            AthinaBookingDetail.header_id
        ).subquery()

        # 主查询
        query = db.session.query(
            AthinaBookingHeader,
            func.coalesce(details_count_subq.c.details_count, 0).label('details_count')
        ).outerjoin(
            details_count_subq,
            AthinaBookingHeader.id == details_count_subq.c.header_id
        )

        # 搜索条件
        if search:
            query = query.filter(
                db.or_(
                    AthinaBookingHeader.booking_header_id.contains(search),
                    AthinaBookingHeader.corporate_name.contains(search)
                )
            )

        # 排序
        query = query.order_by(AthinaBookingHeader.booking_header_id.asc())

        # 如果需要筛选已导入/未导入，在 Python 层面处理
        if filter_imported in ('imported', 'not_imported'):
            # 获取所有符合搜索条件的记录，然后在 Python 中筛选
            all_items = query.all()
            if filter_imported == 'imported':
                filtered_items = [(h, c) for h, c in all_items if h.booking_header_id in imported_hids_set]
            else:
                filtered_items = [(h, c) for h, c in all_items if h.booking_header_id not in imported_hids_set]

            total = len(filtered_items)
            start = (page - 1) * per_page
            end = start + per_page
            items_raw = filtered_items[start:end]
        else:
            # 不需要筛选，直接数据库分页
            total = query.count()
            items_raw = query.offset((page - 1) * per_page).limit(per_page).all()

        # 批量获取已导入项目的详情
        hids = [item[0].booking_header_id for item in items_raw]
        imported_projects = {
            p.hid: p for p in ProjectHeader.query.filter(ProjectHeader.hid.in_(hids)).all()
        } if hids else {}

        # 构造结果
        result = []
        for header, details_count in items_raw:
            is_imported = header.booking_header_id in imported_hids_set
            result.append({
                'athina_header': header,
                'is_imported': is_imported,
                'project_header': imported_projects.get(header.booking_header_id),
                'details_count': details_count,
            })

        return {
            'items': result,
            'total': total,
            'pages': (total + per_page - 1) // per_page if per_page > 0 else 1,
            'page': page,
            'per_page': per_page,
            'has_prev': page > 1,
            'has_next': page * per_page < total,
        }

    def get_importable_athina_headers(self, search=None, filter_imported=None):
        """获取可导入的 Athina Header 列表（兼容旧接口，但建议使用分页版本）"""
        result = self.get_importable_athina_headers_paginated(search, filter_imported, page=1, per_page=10000)
        return result['items']

    def import_header_and_refs(self, athina_header_id, options=None):
        """导入单个 Athina Header 及其 REF 到项目系统

        Args:
            athina_header_id: Athina Header ID
            options: 导入选项 dict
                - create_eo: 是否同时创建 EO (默认 False)
                - create_invoice: 是否同时创建 Invoice (默认 False)

        Returns:
            dict: 导入结果
        """
        options = options or {}
        create_eo = options.get('create_eo', False)
        create_invoice = options.get('create_invoice', False)

        try:
            athina_header = AthinaBookingHeader.query.get(athina_header_id)
            if not athina_header:
                return {'success': False, 'message': f'未找到 Athina Header: {athina_header_id}'}

            hid = athina_header.booking_header_id

            # 检查是否已存在
            existing_header = ProjectHeader.query.filter_by(hid=hid).first()
            if existing_header:
                return {'success': False, 'message': f'项目 {hid} 已存在，请使用更新功能'}

            # 获取公司 ID
            company_id = self._find_or_create_company(athina_header.corporate_name)

            # 获取非小计的明细记录
            details = athina_header.details.filter_by(is_subtotal=False).all()
            if not details:
                return {'success': False, 'message': f'Athina Header {hid} 没有明细记录'}

            # 获取第一个 detail 的描述作为项目描述
            first_detail = details[0]
            desc = first_detail.itin_desc or f'{athina_header.corporate_name}'

            # 创建 ProjectHeader
            project_header = ProjectHeader(
                hid=hid,
                desc=desc[:200] if desc else '-',  # 限制长度
                company_id=company_id,
                staff_name=athina_header.consultant.upper() if athina_header.consultant else athina_header.consultant,
                currency='SGD',
                status='active',
                created_at=athina_header.book_date or datetime.utcnow(),
            )
            db.session.add(project_header)
            db.session.flush()  # 获取 ID

            self.stats['headers_created'] += 1

            # 创建 ProjectRef
            refs_created = []
            for detail in details:
                if not detail.booking_ref:
                    continue

                # 检查 REF 是否已存在
                ref_number = f'R{detail.booking_ref}'
                existing_ref = ProjectRef.query.filter_by(ref_number=ref_number).first()
                if existing_ref:
                    self.warnings.append(f'REF {ref_number} 已存在，跳过')
                    continue

                # 获取业务类型 ID
                ref_type_id = self._get_business_type_id(detail.book_type)
                if not ref_type_id:
                    self.warnings.append(f'未找到业务类型: {detail.book_type}，使用默认类型')
                    ref_type_id = self._get_business_type_id('Other')

                # 获取供应商 ID
                supplier_id = self._find_supplier(detail.supplier)

                # 创建 REF
                project_ref = ProjectRef(
                    header_id=project_header.id,
                    ref_number=ref_number,
                    description=detail.itin_desc[:100] if detail.itin_desc else '-',
                    detailed_description=detail.itin_desc[:200] if detail.itin_desc else '-',
                    ref_type_id=ref_type_id,
                    supplier_id=supplier_id,
                    selling_price=detail.gross_amount or Decimal('0'),
                    cost_price=detail.local_cost or Decimal('0'),
                    currency=detail.gross_curr or 'SGD',
                    status='completed' if athina_header.is_all_invoiced else 'confirmed',
                    payment_status='paid' if detail.balance == 0 else 'unpaid',
                    extra_info=json.dumps({
                        'athina_booking_ref': detail.booking_ref,
                        'client_name': detail.client_name,
                        'dep_date': detail.dep_date.isoformat() if detail.dep_date else None,
                        'book_type': detail.book_type,
                        'original_supplier': detail.supplier,
                    }),
                    created_at=detail.book_date or datetime.utcnow(),
                )
                db.session.add(project_ref)
                db.session.flush()

                refs_created.append({
                    'ref': project_ref,
                    'detail': detail,
                })
                self.stats['refs_created'] += 1

            # 可选：创建 EO
            if create_eo:
                for item in refs_created:
                    ref = item['ref']
                    detail = item['detail']
                    if ref.cost_price and ref.cost_price > 0:
                        self._create_eo_for_ref(ref, detail)

            # 可选：创建 Invoice
            if create_invoice:
                self._create_invoices_for_header(project_header, details)

            db.session.commit()

            return {
                'success': True,
                'message': f'成功导入项目 {hid}',
                'project_header_id': project_header.id,
                'refs_created': len(refs_created),
                'warnings': self.warnings,
            }

        except Exception as e:
            db.session.rollback()
            error_msg = f'导入失败: {str(e)}\n{traceback.format_exc()}'
            self.errors.append(error_msg)
            return {'success': False, 'message': error_msg}

    def _create_eo_for_ref(self, project_ref, athina_detail):
        """为 REF 创建 EO"""
        try:
            # 生成 EO 编号
            eo_number = ProjectEO.generate_eo_number() if hasattr(ProjectEO, 'generate_eo_number') else f'EO{project_ref.id}'

            eo = ProjectEO(
                ref_id=project_ref.id,
                eo_number=eo_number,
                supplier_id=project_ref.supplier_id,
                amount=project_ref.cost_price,
                cost_price=project_ref.cost_price,
                currency=project_ref.currency,
                status='pending',
                created_at=datetime.utcnow(),
            )
            db.session.add(eo)
            self.stats['eos_created'] += 1

        except Exception as e:
            self.warnings.append(f'创建 EO 失败 (REF {project_ref.ref_number}): {str(e)}')

    def _create_invoices_for_header(self, project_header, athina_details):
        """为项目创建发票"""
        try:
            # 按 invoice_no 分组
            invoice_groups = {}
            for detail in athina_details:
                if detail.invoice_no:
                    if detail.invoice_no not in invoice_groups:
                        invoice_groups[detail.invoice_no] = {
                            'invoice_no': detail.invoice_no,
                            'invoice_date': detail.invoice_date,
                            'details': [],
                            'total_amount': Decimal('0'),
                        }
                    invoice_groups[detail.invoice_no]['details'].append(detail)
                    invoice_groups[detail.invoice_no]['total_amount'] += (detail.gross_amount or Decimal('0'))

            # 创建发票
            for inv_no, inv_data in invoice_groups.items():
                # 检查发票是否已存在
                existing = ProjectInvoice.query.filter_by(
                    header_id=project_header.id,
                    invoice_number=inv_no
                ).first()
                if existing:
                    continue

                invoice = ProjectInvoice(
                    header_id=project_header.id,
                    invoice_number=inv_no,
                    invoice_date=inv_data['invoice_date'] or datetime.utcnow().date(),
                    amount=inv_data['total_amount'],
                    currency='SGD',
                    status='issued',
                    created_at=datetime.utcnow(),
                )
                db.session.add(invoice)
                self.stats['invoices_created'] += 1

        except Exception as e:
            self.warnings.append(f'创建发票失败: {str(e)}')

    def batch_import(self, athina_header_ids, options=None):
        """批量导入多个 Athina Header

        Args:
            athina_header_ids: Athina Header ID 列表
            options: 导入选项

        Returns:
            dict: 批量导入结果
        """
        results = {
            'success': 0,
            'failed': 0,
            'details': [],
        }

        for header_id in athina_header_ids:
            result = self.import_header_and_refs(header_id, options)
            if result['success']:
                results['success'] += 1
            else:
                results['failed'] += 1
            results['details'].append(result)

        return {
            'success': True,
            'message': f"批量导入完成: 成功 {results['success']}，失败 {results['failed']}",
            'results': results,
            'stats': self.stats,
        }

    def generate_eos_for_project(self, project_header_id):
        """为项目的所有 REF 生成 EO

        Args:
            project_header_id: 项目 Header ID

        Returns:
            dict: 生成结果
        """
        try:
            header = ProjectHeader.query.get(project_header_id)
            if not header:
                return {'success': False, 'message': '项目不存在'}

            eos_created = 0
            for ref in header.refs:
                # 检查是否已有 EO
                if ref.eos:
                    continue

                # 只为有成本的 REF 创建 EO
                if ref.cost_price and ref.cost_price > 0:
                    eo_number = ProjectEO.generate_eo_number() if hasattr(ProjectEO, 'generate_eo_number') else f'EO{ref.id}'

                    eo = ProjectEO(
                        ref_id=ref.id,
                        eo_number=eo_number,
                        supplier_id=ref.supplier_id,
                        amount=ref.cost_price,
                        cost_price=ref.cost_price,
                        currency=ref.currency,
                        status='pending',
                    )
                    db.session.add(eo)
                    eos_created += 1

            db.session.commit()
            return {
                'success': True,
                'message': f'成功创建 {eos_created} 个 EO',
                'eos_created': eos_created,
            }

        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'生成 EO 失败: {str(e)}'}

    def generate_receipt_from_balance(self, project_header_id):
        """根据余额信息生成收款记录

        Args:
            project_header_id: 项目 Header ID

        Returns:
            dict: 生成结果
        """
        try:
            header = ProjectHeader.query.get(project_header_id)
            if not header:
                return {'success': False, 'message': '项目不存在'}

            # 查找对应的 Athina Header
            athina_header = AthinaBookingHeader.query.filter_by(
                booking_header_id=header.hid
            ).first()

            if not athina_header:
                return {'success': False, 'message': '未找到对应的 Athina 数据'}

            # 如果余额为0或负数，表示已收款
            if athina_header.sub_total_balance is not None and athina_header.sub_total_balance <= 0:
                # 检查是否已有收款记录
                existing_receipt = ProjectReceipt.query.filter_by(
                    header_id=header.id
                ).first()

                if existing_receipt:
                    return {'success': False, 'message': '已有收款记录'}

                # 创建收款记录
                total_selling = sum(
                    float(ref.selling_price) if ref.selling_price else 0
                    for ref in header.refs
                )

                if total_selling > 0:
                    receipt = ProjectReceipt(
                        header_id=header.id,
                        amount=Decimal(str(total_selling)),
                        receipt_date=datetime.utcnow().date(),
                        payment_method='transfer',
                        status='confirmed',
                        remarks='从 Athina 系统导入（余额为0）',
                    )
                    db.session.add(receipt)
                    db.session.commit()

                    return {
                        'success': True,
                        'message': f'成功创建收款记录，金额: {total_selling}',
                    }

            return {'success': False, 'message': 'Athina 余额不为0，无法自动创建收款记录'}

        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'生成收款记录失败: {str(e)}'}

    # ==========================================================================
    # CSV 文件导入方法
    # ==========================================================================

    def _parse_decimal(self, value, default=Decimal('0')):
        """安全解析 Decimal 值"""
        if not value or value.strip() == '':
            return default
        try:
            # 移除逗号和空格
            cleaned = value.replace(',', '').strip()
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return default

    def _parse_date(self, value, formats=None):
        """安全解析日期"""
        if not value or value.strip() == '':
            return None
        formats = formats or ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']
        for fmt in formats:
            try:
                return datetime.strptime(value.strip(), fmt)
            except ValueError:
                continue
        return None

    def _read_csv_file(self, file_content, encoding='utf-8'):
        """读取 CSV 文件内容，返回字典列表"""
        try:
            # 尝试多种编码
            encodings_to_try = [encoding, 'utf-8-sig', 'gbk', 'latin-1']
            content = None
            for enc in encodings_to_try:
                try:
                    if isinstance(file_content, bytes):
                        content = file_content.decode(enc)
                    else:
                        content = file_content
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                raise ValueError('无法解析文件编码')

            # 解析 CSV
            reader = csv.DictReader(io.StringIO(content))
            return list(reader)

        except Exception as e:
            self.errors.append(f'读取 CSV 文件失败: {str(e)}')
            return []

    def import_reservation_csv(self, file_content, options=None):
        """从 Reservation Listing Report.csv 导入 HID + REF

        实际 CSV 格式:
        行1: Corporate Name,,Client Name,Booking Ref,... (表头，第一列名错误，实际应为空或HID)
        行2: Booking Header: 876 ,,,,,... (HID 行)
        行3: ,公司名,客户名,1269,... (数据行，第一列空，第二列是公司名)
        行4: ,,,,,,,Sub Total,... (汇总行)

        注意：CSV 表头第一列错误地命名为 Corporate Name，实际第一列是空的或 HID 标记，
        真正的公司名在第二列（表头为空）。

        Args:
            file_content: CSV 文件内容 (bytes 或 str)
            options: 导入选项
                - create_eo: 是否同时创建 EO
                - create_invoice: 是否同时创建 Invoice

        Returns:
            dict: 导入结果
        """
        import re

        # 确保 session 状态干净
        try:
            db.session.rollback()
        except:
            pass

        options = options or {}
        create_eo = options.get('create_eo', False)
        create_invoice = options.get('create_invoice', False)

        rows = self._read_csv_file(file_content)
        if not rows:
            return {'success': False, 'message': 'CSV 文件为空或解析失败'}

        # 获取表头字段名列表，用于检测列位置
        header_keys = list(rows[0].keys()) if rows else []

        # 检测 Corporate Name 是否错误地作为第一列表头
        # 如果第一列表头是 Corporate Name，那么真正的公司名在第二列（索引1）
        corporate_name_col_index = None
        first_header = header_keys[0] if header_keys else ''
        if 'Corporate Name' in first_header or 'corporate name' in first_header.lower():
            # 第一列表头是 Corporate Name，但实际公司名在第二列
            corporate_name_col_index = 1  # 索引1是真正的公司名列

        # 按 Booking Header (HID) 分组
        hid_groups = {}
        current_hid = None

        for row in rows:
            # 获取第一列的值（可能是 "Booking Header: XXX" 或空）
            first_col_key = list(row.keys())[0] if row else ''
            first_col_val = row.get(first_col_key, '').strip() if row else ''

            # 检查是否是 HID 行: "Booking Header: 876 " 格式
            hid_match = re.match(r'Booking Header:\s*(\d+)', first_col_val)
            if hid_match:
                hid_number = hid_match.group(1)
                current_hid = f'H{hid_number}'
                continue

            # 辅助函数：从多个可能的字段名获取值
            def get_field(names, default=''):
                if isinstance(names, str):
                    names = [names]
                for name in names:
                    val = row.get(name, '').strip()
                    if val:
                        return val
                return default

            # 获取字段值
            values = list(row.values())

            # 获取公司名 - 优先使用列位置（如果检测到表头错位）
            corporate_name = ''
            if corporate_name_col_index is not None and len(values) > corporate_name_col_index:
                # 使用检测到的正确列位置
                val = values[corporate_name_col_index].strip() if values[corporate_name_col_index] else ''
                if val and not val.isdigit() and 'Booking Header' not in val:
                    corporate_name = val

            # 如果还没获取到，尝试从字段名获取
            if not corporate_name:
                corporate_name = get_field(['Corporate Name', 'Company'])
                # 检查获取的值是否是 HID 标记（如果是则清空）
                if corporate_name and ('Booking Header' in corporate_name or corporate_name.isdigit()):
                    corporate_name = ''

            # 如果仍然没有，尝试从第二列或第三列获取
            if not corporate_name:
                for idx in [1, 2]:
                    if len(values) > idx and values[idx]:
                        val = values[idx].strip()
                        if val and not val.isdigit() and 'Booking Header' not in val and 'Sub Total' not in val:
                            corporate_name = val
                            break

            client_name = get_field(['Client Name', 'Pax Name'])
            booking_ref = get_field(['Booking Ref', 'Ref'])
            book_type = get_field(['Book Type', 'Type'])
            book_date = get_field(['Book Date'])
            dep_date = get_field(['Dep Date'])
            itin_desc = get_field(['Itin Desc', 'Itinerary', 'Description'])
            gross_curr = get_field(['Gross Curr', 'Currency']) or 'SGD'
            gross = get_field(['Gross'])
            gross_tax = get_field(['Gross Tax'])
            disc = get_field(['Disc'])
            local_gross = get_field(['Local Gross'])
            local_cost = get_field(['Local Cost'])
            balance = get_field(['Balance'])
            supplier = get_field(['Supplier'])
            consultant = get_field(['Consultant'])
            consultant = consultant.upper() if consultant else consultant
            sales_consultant = get_field(['Sales Consultant'])
            sales_consultant = sales_consultant.upper() if sales_consultant else sales_consultant
            invoice_no = get_field(['Invoice No'])
            invoice_date = get_field(['Invoice Date'])

            # 跳过 Sub Total 行和没有 Booking Ref 的行
            if not booking_ref or itin_desc == 'Sub Total':
                continue

            # 如果还没有 HID，跳过这行
            if not current_hid:
                self.warnings.append(f'无法确定 Booking Ref {booking_ref} 的 HID，跳过')
                continue

            # 初始化 HID 分组
            if current_hid not in hid_groups:
                hid_groups[current_hid] = {
                    'hid': current_hid,
                    'corporate_name': '',
                    'consultant': consultant,
                    'sales_consultant': sales_consultant,
                    'book_date': self._parse_date(book_date),
                    'refs': [],
                }

            # 更新公司名（使用第一个非空的）
            if corporate_name and not hid_groups[current_hid]['corporate_name']:
                hid_groups[current_hid]['corporate_name'] = corporate_name

            # 添加 REF 数据
            hid_groups[current_hid]['refs'].append({
                'booking_ref': booking_ref,
                'client_name': client_name,
                'book_type': book_type,
                'book_date': self._parse_date(book_date),
                'dep_date': self._parse_date(dep_date),
                'itin_desc': itin_desc,
                'gross_curr': gross_curr,
                'gross': self._parse_decimal(gross),
                'gross_tax': self._parse_decimal(gross_tax),
                'disc': self._parse_decimal(disc),
                'local_gross': self._parse_decimal(local_gross),
                'local_cost': self._parse_decimal(local_cost),
                'balance': self._parse_decimal(balance),
                'supplier': supplier,
                'consultant': consultant,
                'sales_consultant': sales_consultant,
                'invoice_no': invoice_no,
                'invoice_date': self._parse_date(invoice_date),
            })

        # 导入每个 HID 分组
        results = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'details': [],
        }

        for hid, group_data in hid_groups.items():
            result = self._import_csv_header_group(group_data, create_eo, create_invoice)
            if result['success']:
                results['success'] += 1
            elif result.get('skipped'):
                results['skipped'] += 1
            else:
                results['failed'] += 1
            results['details'].append(result)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'保存失败: {str(e)}'}

        return {
            'success': True,
            'message': f"导入完成: 成功 {results['success']}，跳过 {results['skipped']}，失败 {results['failed']}",
            'results': results,
            'stats': self.stats,
            'warnings': self.warnings,
        }

    def _import_csv_header_group(self, group_data, create_eo=False, create_invoice=False):
        """从 CSV 分组数据导入单个 HID 及其 REF

        Args:
            group_data: 分组数据 dict
            create_eo: 是否创建 EO
            create_invoice: 是否创建 Invoice

        Returns:
            dict: 导入结果
        """
        hid = group_data['hid']

        # 获取公司 ID
        company_id = self._find_or_create_company(group_data['corporate_name'])

        # 获取描述（使用第一个 REF 的描述）
        desc = '-'
        if group_data['refs']:
            desc = group_data['refs'][0].get('itin_desc', '-') or '-'

        try:
            # 获取 staff_name，优先使用 CSV 中的 consultant，如果没有则使用当前用户名
            staff_name = group_data.get('consultant') or self.current_user_name

            # 检查是否已存在
            existing_header = ProjectHeader.query.filter_by(hid=hid).first()

            if existing_header:
                # 更新已存在的 ProjectHeader
                project_header = existing_header
                project_header.desc = desc[:200] if desc else project_header.desc
                project_header.company_id = company_id or project_header.company_id
                project_header.staff_name = staff_name or project_header.staff_name
                project_header.operator_names = group_data.get('consultant') or project_header.operator_names
                project_header.salesperson_names = group_data.get('sales_consultant') or project_header.salesperson_names
                project_header.updated_at = datetime.utcnow()
                self.stats['headers_updated'] += 1
            else:
                # 创建新的 ProjectHeader
                project_header = ProjectHeader(
                    hid=hid,
                    desc=desc[:200] if desc else '-',
                    company_id=company_id,
                    staff_id=self.current_user_id,
                    staff_name=staff_name,
                    operator_names=group_data.get('consultant'),
                    salesperson_names=group_data.get('sales_consultant'),
                    currency='SGD',
                    status='active',
                    created_at=group_data.get('book_date') or datetime.utcnow(),
                )
                db.session.add(project_header)
                db.session.flush()
                self.stats['headers_created'] += 1

            # 创建 ProjectRef
            refs_created = []
            invoice_data_list = []

            for ref_data in group_data['refs']:
                booking_ref = ref_data['booking_ref']
                if not booking_ref:
                    continue

                # REF 编号格式
                ref_number = f"R{booking_ref}" if not booking_ref.startswith('R') else booking_ref

                # 获取业务类型 ID
                ref_type_id = self._get_business_type_id(ref_data['book_type'])

                # 获取供应商 ID
                supplier_id = self._find_supplier(ref_data['supplier'])

                # 检查 REF 是否已存在
                existing_ref = ProjectRef.query.filter_by(ref_number=ref_number).first()

                if existing_ref:
                    # 更新已存在的 REF
                    project_ref = existing_ref
                    project_ref.header_id = project_header.id
                    project_ref.description = ref_data['itin_desc'][:100] if ref_data['itin_desc'] else project_ref.description
                    project_ref.detailed_description = ref_data['itin_desc'][:200] if ref_data['itin_desc'] else project_ref.detailed_description
                    project_ref.ref_type_id = ref_type_id or project_ref.ref_type_id
                    project_ref.supplier_id = supplier_id or project_ref.supplier_id
                    project_ref.selling_price = ref_data['gross'] or project_ref.selling_price
                    project_ref.cost_price = ref_data['local_cost'] or project_ref.cost_price
                    project_ref.currency = ref_data['gross_curr'] or project_ref.currency
                    project_ref.status = 'completed' if ref_data['invoice_no'] else project_ref.status
                    project_ref.payment_status = 'paid' if ref_data['balance'] == 0 else project_ref.payment_status
                    project_ref.extra_info = json.dumps({
                        'athina_booking_ref': booking_ref,
                        'client_name': ref_data['client_name'],
                        'dep_date': ref_data['dep_date'].isoformat() if ref_data['dep_date'] else None,
                        'book_type': ref_data['book_type'],
                        'original_supplier': ref_data['supplier'],
                        'source': 'csv_import',
                        'updated_at': datetime.utcnow().isoformat(),
                    })
                    self.stats['refs_updated'] += 1
                else:
                    # 创建新的 REF
                    project_ref = ProjectRef(
                        header_id=project_header.id,
                        ref_number=ref_number,
                        description=ref_data['itin_desc'][:100] if ref_data['itin_desc'] else '-',
                        detailed_description=ref_data['itin_desc'][:200] if ref_data['itin_desc'] else '-',
                        ref_type_id=ref_type_id,
                        supplier_id=supplier_id,
                        selling_price=ref_data['gross'] or Decimal('0'),
                        cost_price=ref_data['local_cost'] or Decimal('0'),
                        currency=ref_data['gross_curr'] or 'SGD',
                        status='completed' if ref_data['invoice_no'] else 'confirmed',
                        payment_status='paid' if ref_data['balance'] == 0 else 'unpaid',
                        extra_info=json.dumps({
                            'athina_booking_ref': booking_ref,
                            'client_name': ref_data['client_name'],
                            'dep_date': ref_data['dep_date'].isoformat() if ref_data['dep_date'] else None,
                            'book_type': ref_data['book_type'],
                            'original_supplier': ref_data['supplier'],
                            'source': 'csv_import',
                        }),
                        created_at=ref_data['book_date'] or datetime.utcnow(),
                    )
                    db.session.add(project_ref)
                    db.session.flush()
                    self.stats['refs_created'] += 1

                refs_created.append({
                    'ref': project_ref,
                    'data': ref_data,
                })

                # 如果是机票类型，创建乘客和航段记录
                if ref_data['book_type'] and ref_data['book_type'].lower() in ['airline', 'air']:
                    self._create_flight_records_from_csv(project_ref, ref_data)

                # 收集发票数据
                if ref_data['invoice_no']:
                    invoice_data_list.append({
                        'invoice_no': ref_data['invoice_no'],
                        'invoice_date': ref_data['invoice_date'],
                        'amount': ref_data['gross'],
                    })

            # 可选：创建 EO
            if create_eo:
                for item in refs_created:
                    ref = item['ref']
                    if ref.cost_price and ref.cost_price > 0:
                        self._create_eo_from_csv(ref, item['data'])

            # 可选：创建 Invoice
            if create_invoice and invoice_data_list:
                self._create_invoices_from_csv(project_header, invoice_data_list)

            # 创建项目人员（从 Client Name 提取）
            members_created = self._create_project_members_from_csv(project_header, group_data['refs'])

            return {
                'success': True,
                'message': f'成功导入项目 {hid}',
                'hid': hid,
                'refs_created': len(refs_created),
                'members_created': members_created,
            }

        except Exception as e:
            self.errors.append(f'导入 {hid} 失败: {str(e)}')
            return {'success': False, 'message': f'导入失败: {str(e)}'}

    def _create_project_members_from_csv(self, project_header, refs_data):
        """从 CSV 数据创建项目人员

        从 refs_data 中提取 client_name，去重后创建 ProjectMember 记录。
        支持解析称谓（MR/MS/MISS/MASTER 等）。

        Args:
            project_header: ProjectHeader 实例
            refs_data: REF 数据列表

        Returns:
            int: 创建的人员数量
        """
        import re

        try:
            # 收集所有非空的 client_name（去重）
            client_names = set()
            for ref_data in refs_data:
                client_name = ref_data.get('client_name', '').strip()
                if client_name:
                    client_names.add(client_name)

            if not client_names:
                return 0

            # 获取已存在的人员名单（用于去重）
            existing_members = ProjectMember.query.filter_by(header_id=project_header.id).all()
            existing_names = set()
            for member in existing_members:
                # 标准化比较：去掉空格，转大写
                normalized = (member.member_name or '').upper().replace(' ', '')
                existing_names.add(normalized)

            members_created = 0
            is_first = len(existing_members) == 0  # 如果没有已存在的人员，第一个设为 leader

            for client_name in sorted(client_names):  # 排序保证顺序一致
                # 解析称谓（MR/MS/MISS/MASTER/MRS/MSTR）
                title = None
                name_without_title = client_name

                # 称谓可能在名字末尾，如 "WANG MINGMING MR"
                title_pattern = r'\b(MR|MS|MISS|MASTER|MRS|MSTR|DR|PROF)\b'
                title_match = re.search(title_pattern, client_name.upper())
                if title_match:
                    title = title_match.group(1)
                    # 从名字中移除称谓
                    name_without_title = re.sub(title_pattern, '', client_name, flags=re.IGNORECASE).strip()
                    # 清理多余空格
                    name_without_title = re.sub(r'\s+', ' ', name_without_title).strip()

                # 用去掉称谓后的名字进行标准化比较（避免重复）
                normalized_name = (name_without_title or client_name).upper().replace(' ', '')
                if normalized_name in existing_names:
                    continue  # 跳过已存在的

                # 创建 ProjectMember
                member = ProjectMember(
                    header_id=project_header.id,
                    title=title,
                    member_name=name_without_title or client_name,
                    member_name_en=name_without_title or client_name,
                    is_leader=is_first,
                    remarks='从 Athina CSV 导入',
                )
                db.session.add(member)
                members_created += 1
                is_first = False  # 只有第一个是 leader

                # 添加到已存在集合，避免同一批次重复
                existing_names.add(normalized_name)

            self.stats['members_created'] = self.stats.get('members_created', 0) + members_created
            return members_created

        except Exception as e:
            self.warnings.append(f'创建项目人员失败: {str(e)}')
            return 0

    def _create_flight_records_from_csv(self, project_ref, ref_data):
        """从 CSV 数据为机票类型 REF 创建乘客和航段记录

        Args:
            project_ref: ProjectRef 实例
            ref_data: REF 数据字典，包含 client_name, gross, local_cost, itin_desc, dep_date 等

        解析规则：
        - client_name: 乘客姓名
        - gross: 售价
        - local_cost: 成本
        - itin_desc: 航段描述，格式如 "SIN/PER/SIN"，解析为多个航段
        - dep_date: 出发日期，用于航段的起飞时间
        """
        import re

        try:
            # 检查是否已存在乘客记录（避免重复创建）
            existing_passenger = ProjectFlightPassenger.query.filter_by(ref_id=project_ref.id).first()
            if existing_passenger:
                # 已存在记录，更新信息
                existing_passenger.selling_price = ref_data.get('gross') or existing_passenger.selling_price
                existing_passenger.cost_price = ref_data.get('local_cost') or existing_passenger.cost_price
                self.stats['flight_passengers_updated'] = self.stats.get('flight_passengers_updated', 0) + 1
            else:
                # 创建乘客记录
                client_name = ref_data.get('client_name', '').strip()
                if client_name:
                    # 解析乘客类型（从称谓判断）
                    passenger_type = 'adult'
                    if 'MASTER' in client_name.upper() or 'MSTR' in client_name.upper():
                        passenger_type = 'child'
                    elif 'INFANT' in client_name.upper() or 'INF' in client_name.upper():
                        passenger_type = 'infant'

                    # 去掉称谓获取纯姓名
                    name_clean = client_name
                    title_pattern = r'\b(MR|MS|MISS|MASTER|MRS|MSTR|DR|PROF|INF|INFANT)\b'
                    name_clean = re.sub(title_pattern, '', client_name, flags=re.IGNORECASE).strip()
                    name_clean = re.sub(r'\s+', ' ', name_clean).strip()

                    passenger = ProjectFlightPassenger(
                        ref_id=project_ref.id,
                        name=name_clean or client_name,
                        passenger_type=passenger_type,
                        selling_price=ref_data.get('gross') or Decimal('0'),
                        cost_price=ref_data.get('local_cost') or Decimal('0'),
                    )
                    db.session.add(passenger)
                    self.stats['flight_passengers_created'] = self.stats.get('flight_passengers_created', 0) + 1

            # 解析航段信息 (如 "SIN/PER/SIN" -> ["SIN", "PER", "SIN"])
            itin_desc = ref_data.get('itin_desc', '').strip()
            if itin_desc and '/' in itin_desc:
                # 检查是否已存在航段记录
                existing_segments = ProjectFlightSegment.query.filter_by(ref_id=project_ref.id).count()
                if existing_segments > 0:
                    # 已存在航段记录，跳过创建
                    pass
                else:
                    # 解析机场代码
                    airports = [a.strip().upper() for a in itin_desc.split('/') if a.strip()]

                    if len(airports) >= 2:
                        # 获取出发日期，用于航段时间（默认用当前日期）
                        dep_date = ref_data.get('dep_date') or datetime.utcnow()
                        if isinstance(dep_date, str):
                            try:
                                dep_date = datetime.strptime(dep_date, '%Y-%m-%d')
                            except:
                                dep_date = datetime.utcnow()

                        # 创建航段（每两个相邻机场构成一个航段）
                        for i in range(len(airports) - 1):
                            departure_airport = airports[i][:3]  # 确保只取3位机场代码
                            arrival_airport = airports[i + 1][:3]

                            # 计算航段时间（简单估算：每个航段间隔1天）
                            segment_dep_time = dep_date.replace(hour=8, minute=0, second=0, microsecond=0)
                            segment_arr_time = dep_date.replace(hour=12, minute=0, second=0, microsecond=0)

                            # 如果不是第一个航段，日期往后推
                            if i > 0:
                                segment_dep_time = segment_dep_time + timedelta(days=i)
                                segment_arr_time = segment_arr_time + timedelta(days=i)

                            segment = ProjectFlightSegment(
                                ref_id=project_ref.id,
                                flight_number='TBA',  # 待确认
                                departure_airport=departure_airport,
                                arrival_airport=arrival_airport,
                                departure_time=segment_dep_time,
                                arrival_time=segment_arr_time,
                                cabin_class='Economy',  # 默认经济舱
                                cabin_code='Y',  # 默认Y舱
                                status='confirmed',
                            )
                            db.session.add(segment)
                            self.stats['flight_segments_created'] = self.stats.get('flight_segments_created', 0) + 1

        except Exception as e:
            self.warnings.append(f'创建机票记录失败 (REF {project_ref.ref_number}): {str(e)}')

    def _create_eo_from_csv(self, project_ref, ref_data):
        """从 CSV 数据为 REF 创建 EO"""
        try:
            eo_number = ProjectEO.generate_eo_number() if hasattr(ProjectEO, 'generate_eo_number') else f'EO{project_ref.id}'

            eo = ProjectEO(
                ref_id=project_ref.id,
                eo_number=eo_number,
                supplier_id=project_ref.supplier_id,
                amount=project_ref.cost_price,
                cost_price=project_ref.cost_price,
                currency=project_ref.currency,
                status='pending',
                created_at=datetime.utcnow(),
            )
            db.session.add(eo)
            self.stats['eos_created'] += 1

        except Exception as e:
            self.warnings.append(f'创建 EO 失败 (REF {project_ref.ref_number}): {str(e)}')

    def _create_invoices_from_csv(self, project_header, invoice_data_list):
        """从 CSV 数据创建发票"""
        try:
            # 按 invoice_no 分组
            invoice_groups = {}
            for data in invoice_data_list:
                inv_no = data['invoice_no']
                if not inv_no:
                    continue
                if inv_no not in invoice_groups:
                    invoice_groups[inv_no] = {
                        'invoice_no': inv_no,
                        'invoice_date': data['invoice_date'],
                        'total_amount': Decimal('0'),
                    }
                invoice_groups[inv_no]['total_amount'] += (data['amount'] or Decimal('0'))

            # 创建发票
            for inv_no, inv_data in invoice_groups.items():
                existing = ProjectInvoice.query.filter_by(
                    header_id=project_header.id,
                    invoice_number=inv_no
                ).first()
                if existing:
                    continue

                invoice = ProjectInvoice(
                    header_id=project_header.id,
                    invoice_number=inv_no,
                    invoice_date=inv_data['invoice_date'] or datetime.utcnow().date(),
                    amount=inv_data['total_amount'],
                    currency='SGD',
                    status='issued',
                    created_at=datetime.utcnow(),
                )
                db.session.add(invoice)
                self.stats['invoices_created'] += 1

        except Exception as e:
            self.warnings.append(f'创建发票失败: {str(e)}')

    def import_eo_csv(self, file_content):
        """从 Exchange Order Listing Report.csv 导入 EO

        CSV 字段:
        EONo,Cancel,EO Date,Booking Header,Booking Ref,Conf Code,Dep Date,Type,
        Supplier,Company,Department,Pax Name,Itinerary,Curr,Gross,Cost Tax,Disc,
        Payment No,Paid Date,Pay Amount,Status

        Args:
            file_content: CSV 文件内容

        Returns:
            dict: 导入结果
        """
        # 确保 session 状态干净
        try:
            db.session.rollback()
        except:
            pass

        rows = self._read_csv_file(file_content)
        if not rows:
            return {'success': False, 'message': 'CSV 文件为空或解析失败'}

        results = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'details': [],
        }

        for row in rows:
            # 解析字段
            eo_no = row.get('EONo', '').strip()
            cancel = row.get('Cancel', '').strip()
            eo_date = row.get('EO Date', '').strip()
            booking_header = row.get('Booking Header', '').strip()
            booking_ref = row.get('Booking Ref', '').strip()
            conf_code = row.get('Conf Code', '').strip()
            dep_date = row.get('Dep Date', '').strip()
            eo_type = row.get('Type', '').strip()
            supplier = row.get('Supplier', '').strip()
            pax_name = row.get('Pax Name', '').strip()
            itinerary = row.get('Itinerary', '').strip()
            curr = row.get('Curr', '').strip() or 'SGD'
            gross = row.get('Gross', '').strip()
            cost_tax = row.get('Cost Tax', '').strip()
            disc = row.get('Disc', '').strip()
            payment_no = row.get('Payment No', '').strip()
            paid_date = row.get('Paid Date', '').strip()
            pay_amount = row.get('Pay Amount', '').strip()
            status = row.get('Status', '').strip()

            # 跳过空行或已取消的 EO (Cancel = "Checked" 表示取消)
            if not eo_no or cancel.lower() == 'checked':
                continue

            # 构建 HID (CSV 中是数字，需要加 H 前缀)
            hid = f"H{booking_header}" if booking_header and not booking_header.startswith('H') else booking_header

            # 构建 REF 编号
            ref_number = f"R{booking_ref}" if booking_ref and not booking_ref.startswith('R') else booking_ref

            # 查找对应的 ProjectRef
            project_ref = ProjectRef.query.filter_by(ref_number=ref_number).first()

            if not project_ref:
                # 尝试通过 HID 查找项目，再匹配 REF
                if hid:
                    project_header = ProjectHeader.query.filter_by(hid=hid).first()
                    if project_header:
                        # 尝试通过 extra_info 中的 athina_booking_ref 匹配
                        for ref in project_header.refs:
                            extra_info = json.loads(ref.extra_info) if ref.extra_info else {}
                            if extra_info.get('athina_booking_ref') == booking_ref:
                                project_ref = ref
                                break

            if not project_ref:
                results['skipped'] += 1
                results['details'].append({
                    'success': False,
                    'skipped': True,
                    'eo_no': eo_no,
                    'message': f'未找到对应的 REF: {ref_number} (HID: {hid})',
                })
                continue

            try:
                # 更新 REF 的供应商（如果需要）
                if supplier:
                    supplier_id = self._find_supplier(supplier)
                    if supplier_id and project_ref.supplier_id != supplier_id:
                        project_ref.supplier_id = supplier_id

                # 更新 REF 的成本价格
                gross_amount = self._parse_decimal(gross)
                if gross_amount > 0:
                    project_ref.cost_price = gross_amount
                    project_ref.currency = curr

                # 保存 Pax Name 到 REF 的 extra_info
                if pax_name:
                    try:
                        extra_info = json.loads(project_ref.extra_info) if project_ref.extra_info else {}
                    except:
                        extra_info = {}
                    extra_info['pax_name'] = pax_name
                    extra_info['itinerary'] = itinerary
                    extra_info['dep_date'] = dep_date
                    project_ref.extra_info = json.dumps(extra_info)

                # 解析税费和折扣
                tax_amount = self._parse_decimal(cost_tax)
                disc_amount = self._parse_decimal(disc)

                # 解析付款金额和日期（先解析，用于判断状态）
                pay_amount_decimal = self._parse_decimal(pay_amount)
                paid_date_parsed = self._parse_date(paid_date)
                has_payment_info = (payment_no and payment_no != '0') or pay_amount_decimal > 0 or paid_date_parsed

                # 确定 EO 状态
                # Paid-P = 已付款, Unpaid-N = 未付款
                # 注意：只有同时满足 Status=Paid 且有付款信息时才设为已付款
                eo_status = 'confirmed'  # 默认已确认
                if 'cancel' in status.lower():
                    eo_status = 'cancelled'
                elif 'paid' in status.lower() and has_payment_info:
                    # 必须有付款信息才能设为已付款
                    eo_status = 'paid'

                # 检查 EO 编号是否已存在
                existing_eo = ProjectEO.query.filter_by(eo_number=eo_no).first()

                if existing_eo:
                    # 更新已存在的 EO
                    eo = existing_eo
                    eo.ref_id = project_ref.id
                    eo.eo_date = self._parse_date(eo_date) or eo.eo_date
                    eo.conf_code = conf_code if conf_code else eo.conf_code
                    eo.tax = tax_amount or eo.tax
                    eo.discount = disc_amount or eo.discount
                    eo.payment_no = payment_no if payment_no and payment_no != '0' else eo.payment_no
                    eo.paid_date = paid_date_parsed or eo.paid_date
                    eo.pay_amount = pay_amount_decimal if pay_amount_decimal > 0 else eo.pay_amount
                    eo.payment_remarks = json.dumps({
                        'pax_name': pax_name,
                        'itinerary': itinerary,
                        'dep_date': dep_date,
                        'type': eo_type,
                        'athina_status': status,
                        'source': 'csv_import',
                        'updated_at': datetime.utcnow().isoformat(),
                    })
                    eo.external_system = 'Athina'
                    eo.external_status = status
                    eo.external_reference = f"EO{eo_no}"
                    eo.status = eo_status
                    self.stats['eos_updated'] += 1
                    results['success'] += 1
                    results['details'].append({
                        'success': True,
                        'eo_no': eo_no,
                        'ref_number': project_ref.ref_number,
                        'message': f'成功更新 EO {eo_no}',
                    })
                else:
                    # 创建新的 EO
                    eo = ProjectEO(
                        ref_id=project_ref.id,
                        eo_number=eo_no,
                        eo_date=self._parse_date(eo_date),
                        conf_code=conf_code if conf_code else None,
                        tax=tax_amount,
                        discount=disc_amount,
                        payment_no=payment_no if payment_no and payment_no != '0' else None,
                        paid_date=paid_date_parsed,
                        pay_amount=pay_amount_decimal if pay_amount_decimal > 0 else None,
                        payment_remarks=json.dumps({
                            'pax_name': pax_name,
                            'itinerary': itinerary,
                            'dep_date': dep_date,
                            'type': eo_type,
                            'athina_status': status,
                            'source': 'csv_import',
                        }),
                        external_system='Athina',
                        external_status=status,
                        external_reference=f"EO{eo_no}",
                        status=eo_status,
                    )
                    db.session.add(eo)
                    self.stats['eos_created'] += 1
                    results['success'] += 1
                    results['details'].append({
                        'success': True,
                        'eo_no': eo_no,
                        'ref_number': project_ref.ref_number,
                        'message': f'成功创建 EO {eo_no}',
                    })

            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'success': False,
                    'eo_no': eo_no,
                    'message': f'创建 EO 失败: {str(e)}',
                })
                self.errors.append(f'创建 EO {eo_no} 失败: {str(e)}')

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'保存失败: {str(e)}'}

        return {
            'success': True,
            'message': f"EO 导入完成: 成功 {results['success']}，跳过 {results['skipped']}，失败 {results['failed']}",
            'results': results,
            'stats': self.stats,
            'warnings': self.warnings,
        }

    def import_invoice_csv(self, file_content):
        """从 Invoice Listing Report.csv 导入 Invoice

        实际 CSV 格式:
        行1: ,Booking Header,Company,Type,Invoice No,... (表头，第一列可能为空)
        行2: Invoice No: 11024 ,,,... (发票分组行)
        行3: ,918,SOLIDTEK...,INV,11024,1190,1254,... (数据行，第一列空)
        行4: ,,,,,,,,,,,,,300.00,... (汇总行，无 Booking Header)

        注意：CSV 表头第一列可能为空，实际数据列从第二列开始。

        Args:
            file_content: CSV 文件内容

        Returns:
            dict: 导入结果
        """
        import re

        # 确保 session 状态干净
        try:
            db.session.rollback()
        except:
            pass

        rows = self._read_csv_file(file_content)
        if not rows:
            return {'success': False, 'message': 'CSV 文件为空或解析失败'}

        # 获取表头字段名列表，用于检测列位置
        header_keys = list(rows[0].keys()) if rows else []

        # 检测第一列表头是否为空，如果是则数据列位置需要调整
        first_col_empty = not header_keys[0].strip() if header_keys else False

        # 按 Invoice No 分组
        invoice_groups = {}
        current_invoice_no = None

        for row in rows:
            # 获取第一列的值，检查是否是发票分组行 "Invoice No: 11024 "
            first_col_key = list(row.keys())[0] if row else ''
            first_col_val = row.get(first_col_key, '').strip() if row else ''

            # 检查是否是发票分组行
            inv_match = re.match(r'Invoice No:\s*(\d+)', first_col_val)
            if inv_match:
                current_invoice_no = inv_match.group(1)
                continue

            values = list(row.values())

            # 辅助函数：从字段名或位置获取值
            def get_field_or_pos(field_names, pos_index, default=''):
                """优先从字段名获取，如果失败则从位置获取"""
                if isinstance(field_names, str):
                    field_names = [field_names]
                # 先尝试字段名
                for name in field_names:
                    val = row.get(name, '').strip()
                    if val and 'Invoice No:' not in val:
                        return val
                # 字段名获取失败，尝试从位置获取（处理表头和数据错位的情况）
                if len(values) > pos_index:
                    val = values[pos_index].strip() if values[pos_index] else ''
                    if val and 'Invoice No:' not in val:
                        return val
                return default

            # 解析字段 - 使用字段名和位置双重方式
            booking_header = get_field_or_pos(['Booking Header'], 1)
            company = get_field_or_pos(['Company'], 2)
            invoice_no = get_field_or_pos(['Invoice No'], 4) or current_invoice_no
            eo_no = get_field_or_pos(['EONo'], 5)
            booking_ref = get_field_or_pos(['Booking Ref'], 6)
            bkg_type = get_field_or_pos(['Bkg Type', 'Type'], 3)
            inv_date = get_field_or_pos(['Inv Date'], 7)
            client_name = get_field_or_pos(['Client Name'], 8)
            dep_date = get_field_or_pos(['Dep Date'], 9)
            itin_desc = get_field_or_pos(['Itin Description', 'Description'], 10)
            gross_curr = get_field_or_pos(['Gross Curr', 'Currency'], 11) or 'SGD'
            total_gross = get_field_or_pos(['Total Gross'], 12)
            balance = get_field_or_pos(['Balance'], 13)
            status = get_field_or_pos(['Status'], 14)
            consultant = get_field_or_pos(['Invoice Consultant', 'Consultant'], 15)
            consultant = consultant.upper() if consultant else consultant
            contact = get_field_or_pos(['Contact'], 16)
            sales_consultant = get_field_or_pos(['Sales Consultant'], 17)
            sales_consultant = sales_consultant.upper() if sales_consultant else sales_consultant
            adt = get_field_or_pos(['ADT'], 18)
            chd = get_field_or_pos(['CHD'], 19)
            inf = get_field_or_pos(['INF'], 20)

            # 跳过没有 booking_header 的行（汇总行）和没有 invoice_no 的行
            if not booking_header or not invoice_no:
                continue

            # 构建 HID (CSV 中是数字，需要加 H 前缀)
            hid = f"H{booking_header}" if booking_header and not booking_header.startswith('H') else booking_header

            # 使用 invoice_no 作为分组键
            if invoice_no not in invoice_groups:
                invoice_groups[invoice_no] = {
                    'invoice_no': invoice_no,
                    'hid': hid,
                    'company': company,
                    'client_name': client_name,
                    'inv_date': self._parse_date(inv_date),
                    'currency': gross_curr,
                    'status': status,
                    'balance': Decimal('0'),
                    'consultant': consultant,
                    'contact': contact,
                    'sales_consultant': sales_consultant,
                    'total_gross': Decimal('0'),
                    'items': [],
                    'ref_numbers': [],
                }

            # 累加金额
            item_gross = self._parse_decimal(total_gross)
            item_balance = self._parse_decimal(balance)
            invoice_groups[invoice_no]['total_gross'] += item_gross
            invoice_groups[invoice_no]['balance'] = item_balance  # 使用最后一行的 balance

            # 更新状态（使用最后一行有值的状态）
            if status:
                invoice_groups[invoice_no]['status'] = status

            # 添加明细项
            if booking_ref:
                ref_number = f"R{booking_ref}" if not booking_ref.startswith('R') else booking_ref
                invoice_groups[invoice_no]['items'].append({
                    'booking_ref': booking_ref,
                    'ref_number': ref_number,
                    'eo_no': eo_no,
                    'amount': float(item_gross),
                    'client_name': client_name,
                    'itin_desc': itin_desc,
                    'dep_date': dep_date,
                    'bkg_type': bkg_type,
                    'adt': adt,
                    'chd': chd,
                    'inf': inf,
                })
                if ref_number not in invoice_groups[invoice_no]['ref_numbers']:
                    invoice_groups[invoice_no]['ref_numbers'].append(ref_number)

        results = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'details': [],
        }

        for invoice_no, inv_data in invoice_groups.items():
            hid = inv_data['hid']

            # 查找对应的 ProjectHeader
            project_header = ProjectHeader.query.filter_by(hid=hid).first()
            if not project_header:
                results['skipped'] += 1
                results['details'].append({
                    'success': False,
                    'skipped': True,
                    'invoice_no': invoice_no,
                    'message': f'未找到项目 {hid}，跳过发票 {invoice_no}',
                })
                continue

            try:
                # 查找关联的 REF IDs
                ref_ids = []
                for ref_number in inv_data['ref_numbers']:
                    project_ref = ProjectRef.query.filter_by(ref_number=ref_number).first()
                    if project_ref:
                        ref_ids.append(project_ref.id)
                    else:
                        # 尝试通过 extra_info 中的 athina_booking_ref 匹配
                        for ref in project_header.refs:
                            extra_info = json.loads(ref.extra_info) if ref.extra_info else {}
                            athina_ref = extra_info.get('athina_booking_ref', '')
                            if ref_number == f"R{athina_ref}" or ref_number == athina_ref:
                                ref_ids.append(ref.id)
                                break

                # 确定付款状态
                # Unsettled-N → unpaid, Settled-S → paid, P. Settled-PS → partial_paid
                athina_status = inv_data['status'].lower() if inv_data['status'] else ''
                payment_status = 'unpaid'
                if 'settled-s' in athina_status or athina_status == 'settled':
                    payment_status = 'paid'
                elif 'p. settled' in athina_status or 'partial' in athina_status:
                    payment_status = 'partial_paid'

                # 计算已付金额: paid_amount = total_gross - balance
                total_gross = inv_data['total_gross']
                balance = inv_data['balance']
                paid_amount = total_gross - balance if total_gross >= balance else Decimal('0')

                # 检查发票是否已存在
                existing_invoice = ProjectInvoice.query.filter_by(
                    invoice_number=invoice_no
                ).first()

                if existing_invoice:
                    # 更新已存在的发票
                    invoice = existing_invoice
                    invoice.header_id = project_header.id
                    invoice.invoice_date = inv_data['inv_date'] or invoice.invoice_date
                    invoice.amount = total_gross
                    invoice.currency = inv_data['currency'] or invoice.currency
                    invoice.customer_name = inv_data['client_name'] or invoice.customer_name
                    invoice.customer_company = inv_data['company'] or invoice.customer_company
                    invoice.payment_status = payment_status
                    invoice.paid_amount = paid_amount
                    invoice.ref_ids = json.dumps(ref_ids) if ref_ids else invoice.ref_ids
                    invoice.invoice_items = json.dumps(inv_data['items'])
                    invoice.remarks = inv_data['items'][0]['itin_desc'] if inv_data['items'] else invoice.remarks
                    invoice.extra_info = json.dumps({
                        'athina_status': inv_data['status'],
                        'consultant': inv_data['consultant'],
                        'contact': inv_data['contact'],
                        'sales_consultant': inv_data['sales_consultant'],
                        'source': 'csv_import',
                        'updated_at': datetime.utcnow().isoformat(),
                    })

                    # 检查并创建缺失的 InvoiceItem
                    items_created = 0
                    existing_item_ref_ids = {item.ref_id for item in InvoiceItem.query.filter_by(invoice_id=invoice.id).all()}
                    for i, ref_id in enumerate(ref_ids):
                        if ref_id not in existing_item_ref_ids:
                            ref = ProjectRef.query.get(ref_id)
                            if ref:
                                item_data = inv_data['items'][i] if i < len(inv_data['items']) else {}
                                invoice_item = InvoiceItem(
                                    invoice_id=invoice.id,
                                    ref_id=ref_id,
                                    description=item_data.get('itin_desc') or ref.description or f"REF {ref.ref_number}",
                                    quantity=1,
                                    unit_price=Decimal(str(ref.selling_price or 0)),
                                    total_price=Decimal(str(ref.selling_price or 0)),
                                )
                                db.session.add(invoice_item)
                                items_created += 1

                    self.stats['invoices_updated'] = self.stats.get('invoices_updated', 0) + 1
                    results['success'] += 1
                    results['details'].append({
                        'success': True,
                        'invoice_no': invoice_no,
                        'hid': hid,
                        'amount': str(total_gross),
                        'payment_status': payment_status,
                        'items_created': items_created,
                        'message': f'成功更新发票 {invoice_no}' + (f'，新增 {items_created} 个 REF 关联' if items_created else ''),
                    })
                else:
                    # 创建新发票
                    invoice = ProjectInvoice(
                        header_id=project_header.id,
                        invoice_number=invoice_no,
                        invoice_date=inv_data['inv_date'] or datetime.utcnow().date(),
                        amount=total_gross,
                        currency=inv_data['currency'],
                        invoice_type='full',
                        customer_name=inv_data['client_name'],
                        customer_company=inv_data['company'],
                        status='confirmed',  # 导入的发票默认为已确认
                        payment_status=payment_status,
                        paid_amount=paid_amount,
                        ref_ids=json.dumps(ref_ids) if ref_ids else None,
                        invoice_items=json.dumps(inv_data['items']),
                        remarks=inv_data['items'][0]['itin_desc'] if inv_data['items'] else None,
                        extra_info=json.dumps({
                            'athina_status': inv_data['status'],
                            'consultant': inv_data['consultant'],
                            'contact': inv_data['contact'],
                            'sales_consultant': inv_data['sales_consultant'],
                            'source': 'csv_import',
                        }),
                        created_by=inv_data['consultant'],
                    )
                    db.session.add(invoice)
                    db.session.flush()  # 获取 invoice.id

                    # 创建 InvoiceItem 关联 REF
                    items_created = 0
                    for i, ref_id in enumerate(ref_ids):
                        ref = ProjectRef.query.get(ref_id)
                        if ref:
                            # 获取对应的 item 数据（如果有）
                            item_data = inv_data['items'][i] if i < len(inv_data['items']) else {}
                            invoice_item = InvoiceItem(
                                invoice_id=invoice.id,
                                ref_id=ref_id,
                                description=item_data.get('itin_desc') or ref.description or f"REF {ref.ref_number}",
                                quantity=1,
                                unit_price=Decimal(str(ref.selling_price or 0)),
                                total_price=Decimal(str(ref.selling_price or 0)),
                            )
                            db.session.add(invoice_item)
                            items_created += 1

                    self.stats['invoices_created'] += 1
                    results['success'] += 1
                    results['details'].append({
                        'success': True,
                        'invoice_no': invoice_no,
                        'hid': hid,
                        'amount': str(total_gross),
                        'payment_status': payment_status,
                        'ref_count': len(ref_ids),
                        'items_created': items_created,
                        'message': f'成功创建发票 {invoice_no}，关联 {items_created} 个 REF',
                    })

            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'success': False,
                    'invoice_no': invoice_no,
                    'message': f'创建发票失败: {str(e)}',
                })
                self.errors.append(f'创建发票 {invoice_no} 失败: {str(e)}')

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'保存失败: {str(e)}'}

        return {
            'success': True,
            'message': f"发票导入完成: 成功 {results['success']}，跳过 {results['skipped']}，失败 {results['failed']}",
            'results': results,
            'stats': self.stats,
            'warnings': self.warnings,
        }

    def import_receipt_csv(self, file_content):
        """从 Receipt Listing Report.csv 导入收款记录

        实际 CSV 格式:
        行1: ,Receipt_No,Booking_Header,Booking_Ref,Invoice_No,Lead Name,Description,Company,Receipt Date,Pay Type,Cheque,Curr,Amount,... (表头，第一列可能为空)
        行2: Receipt_No: 466 ,,,... (收据分组行)
        行3: ,466,921,1257,11027,WANG MINGMING MR,SIN/TAO/SIN,CASH SALES,09/01/2026,TT,OCBC 09JAN,SGD,580.00,... (数据行)

        注意：CSV 表头第一列可能为空，实际数据列从第二列开始。

        Args:
            file_content: CSV 文件内容

        Returns:
            dict: 导入结果
        """
        import re
        from App_new.business.projects.models.receipt import ReceiptInvoiceAllocation

        # 确保 session 状态干净
        try:
            db.session.rollback()
        except:
            pass

        rows = self._read_csv_file(file_content)
        if not rows:
            return {'success': False, 'message': 'CSV 文件为空或解析失败'}

        # 获取表头字段名列表，用于检测列位置
        header_keys = list(rows[0].keys()) if rows else []

        # 检测第一列表头是否为空，如果是则数据列位置需要调整
        first_col_empty = not header_keys[0].strip() if header_keys else False

        # Pay Type 映射
        PAY_TYPE_MAPPING = {
            'TT': 'bank_transfer',
            'TRANSFER': 'bank_transfer',
            'BANK TRANSFER': 'bank_transfer',
            'VOUCHER': 'other',
            'CASH': 'cash',
            'CHEQUE': 'cheque',
            'CHQ': 'cheque',
            'CC': 'credit_card',
            'CREDIT CARD': 'credit_card',
            'CREDIT': 'credit_card',
        }

        # 按 Receipt_No 分组
        receipt_groups = {}
        current_receipt_no = None

        for row in rows:
            # 获取第一列的值，检查是否是收据分组行 "Receipt_No: 466 "
            first_col_key = list(row.keys())[0] if row else ''
            first_col_val = row.get(first_col_key, '').strip() if row else ''

            # 检查是否是收据分组行
            receipt_match = re.match(r'Receipt_No:\s*(\d+)', first_col_val)
            if receipt_match:
                current_receipt_no = receipt_match.group(1)
                continue

            values = list(row.values())

            # 辅助函数：从字段名或位置获取值
            def get_field_or_pos(field_names, pos_index, default=''):
                """优先从字段名获取，如果失败则从位置获取"""
                if isinstance(field_names, str):
                    field_names = [field_names]
                # 先尝试字段名
                for name in field_names:
                    val = row.get(name, '').strip()
                    if val and 'Receipt_No:' not in val:
                        return val
                # 如果第一列为空，尝试从位置获取
                if first_col_empty and len(values) > pos_index:
                    val = values[pos_index].strip() if values[pos_index] else ''
                    if val and 'Receipt_No:' not in val:
                        return val
                return default

            # CSV 列名可能有下划线或空格，同时支持位置获取
            receipt_no = get_field_or_pos(['Receipt_No', 'Receipt No'], 1) or current_receipt_no
            booking_header = get_field_or_pos(['Booking_Header', 'Booking Header'], 2)
            booking_ref = get_field_or_pos(['Booking_Ref', 'Booking Ref'], 3)
            invoice_no = get_field_or_pos(['Invoice_No', 'Invoice No'], 4)
            lead_name = get_field_or_pos(['Lead Name', 'Lead_Name', 'Pax Name'], 5)
            description = get_field_or_pos(['Description', 'Itin Desc'], 6)
            company = get_field_or_pos(['Company', 'Corporate'], 7)
            receipt_date = get_field_or_pos(['Receipt Date', 'Receipt_Date', 'Date'], 8)
            pay_type = get_field_or_pos(['Pay Type', 'Pay_Type'], 9)
            cheque = get_field_or_pos(['Cheque', 'Pay Details', 'Pay_Details'], 10)
            curr = get_field_or_pos(['Curr', 'Currency'], 11) or 'SGD'
            amount = get_field_or_pos(['Amount'], 12)
            bank_charges = get_field_or_pos(['Bank Charges', 'Bank_Charges'], 13)
            forex = get_field_or_pos(['Forex'], 14)
            gst = get_field_or_pos(['GST'], 15)
            rate = get_field_or_pos(['Rate'], 16)
            offset = get_field_or_pos(['Offset'], 17)
            offset_acc = get_field_or_pos(['Offset Acc', 'Offset_Acc'], 18)
            bank_amount = get_field_or_pos(['Bank Amount', 'Bank_Amount'], 19)

            # 跳过空行或汇总行（Sub Total, Grand Total）
            if not receipt_no or not amount:
                continue
            # 检查 cheque 或 curr 字段是否包含汇总标识
            # Sub Total 出现在 Curr 列（位置11），Grand Total 出现在 Cheque 列（位置10）
            if cheque and ('Sub Total' in cheque or 'Grand Total' in cheque):
                continue
            if curr and ('Sub Total' in curr or 'Grand Total' in curr):
                continue

            # 构建 HID 和 REF 编号
            hid = f"H{booking_header}" if booking_header and not booking_header.startswith('H') else booking_header
            ref_number = f"R{booking_ref}" if booking_ref and not booking_ref.startswith('R') else booking_ref

            # 使用 receipt_no 作为分组键
            if receipt_no not in receipt_groups:
                receipt_groups[receipt_no] = {
                    'receipt_no': receipt_no,
                    'hid': hid,
                    'company': company,
                    'lead_name': lead_name,
                    'receipt_date': self._parse_date(receipt_date),
                    'pay_type': pay_type,
                    'cheque': cheque,
                    'currency': curr,
                    'total_amount': Decimal('0'),
                    'items': [],
                    'ref_numbers': [],
                    'invoice_nos': [],
                }

            # 累加金额
            item_amount = self._parse_decimal(amount)
            receipt_groups[receipt_no]['total_amount'] += item_amount

            # 更新公司和付款人（使用第一个非空值）
            if company and not receipt_groups[receipt_no]['company']:
                receipt_groups[receipt_no]['company'] = company
            if lead_name and not receipt_groups[receipt_no]['lead_name']:
                receipt_groups[receipt_no]['lead_name'] = lead_name

            # 添加明细项
            receipt_groups[receipt_no]['items'].append({
                'booking_header': booking_header,
                'booking_ref': booking_ref,
                'ref_number': ref_number,
                'invoice_no': invoice_no,
                'amount': float(item_amount),
                'lead_name': lead_name,
                'description': description,
                'bank_charges': bank_charges,
                'forex': forex,
                'gst': gst,
                'rate': rate,
                'offset': offset,
                'offset_acc': offset_acc,
                'bank_amount': bank_amount,
            })

            # 收集关联的 REF 和 Invoice
            if ref_number and ref_number not in receipt_groups[receipt_no]['ref_numbers']:
                receipt_groups[receipt_no]['ref_numbers'].append(ref_number)
            if invoice_no and invoice_no not in receipt_groups[receipt_no]['invoice_nos']:
                receipt_groups[receipt_no]['invoice_nos'].append(invoice_no)

        results = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'details': [],
        }

        for receipt_no, rcpt_data in receipt_groups.items():
            hid = rcpt_data['hid']

            # 查找对应的 ProjectHeader
            project_header = ProjectHeader.query.filter_by(hid=hid).first() if hid else None

            if not project_header:
                # 尝试通过第一个 invoice_no 查找
                for inv_no in rcpt_data['invoice_nos']:
                    invoice = ProjectInvoice.query.filter_by(invoice_number=inv_no).first()
                    if invoice:
                        project_header = ProjectHeader.query.get(invoice.header_id)
                        break

            if not project_header:
                results['skipped'] += 1
                results['details'].append({
                    'success': False,
                    'skipped': True,
                    'receipt_no': receipt_no,
                    'message': f'未找到项目 {hid}，跳过收据 {receipt_no}',
                })
                continue

            try:
                # 检查收据是否已存在
                existing_receipt = ProjectReceipt.query.filter_by(
                    receipt_number=receipt_no
                ).first()
                # 查找关联的 REF
                ref_id = None
                for ref_number in rcpt_data['ref_numbers']:
                    project_ref = ProjectRef.query.filter_by(ref_number=ref_number).first()
                    if project_ref:
                        ref_id = project_ref.id
                        break  # 使用第一个匹配的 REF

                # 查找关联的 Invoice
                invoice_id = None
                invoice_allocations = []  # 多个发票分配
                for inv_no in rcpt_data['invoice_nos']:
                    invoice = ProjectInvoice.query.filter_by(invoice_number=inv_no).first()
                    if invoice:
                        if invoice_id is None:
                            invoice_id = invoice.id  # 使用第一个作为主关联
                        # 收集所有发票用于分配
                        for item in rcpt_data['items']:
                            if item['invoice_no'] == inv_no:
                                invoice_allocations.append({
                                    'invoice_id': invoice.id,
                                    'amount': item['amount'],
                                })
                                break

                # 映射付款方式
                pay_type_upper = rcpt_data['pay_type'].upper() if rcpt_data['pay_type'] else ''
                payment_method = PAY_TYPE_MAPPING.get(pay_type_upper, 'other')

                # 解析银行信息
                cheque_info = rcpt_data['cheque'] or ''
                bank_name = None
                transaction_id = None
                if cheque_info:
                    # 格式可能是 "OCBC 09JAN" 或其他
                    parts = cheque_info.split()
                    if parts:
                        bank_name = parts[0]  # 银行名
                        transaction_id = cheque_info  # 完整信息作为交易号

                # 准备 extra_info
                extra_info = {
                    'athina_receipt_no': receipt_no,
                    'pay_type': rcpt_data['pay_type'],
                    'items': rcpt_data['items'],
                    'ref_numbers': rcpt_data['ref_numbers'],
                    'invoice_nos': rcpt_data['invoice_nos'],
                    'source': 'csv_import',
                    'updated_at': datetime.utcnow().isoformat(),
                }

                if existing_receipt:
                    # 更新已存在的收据
                    receipt = existing_receipt
                    receipt.header_id = project_header.id
                    receipt.ref_id = ref_id or receipt.ref_id
                    receipt.invoice_id = invoice_id or receipt.invoice_id
                    receipt.amount = rcpt_data['total_amount']
                    receipt.currency = rcpt_data['currency'] or receipt.currency
                    receipt.payment_method = payment_method
                    receipt.payment_date = rcpt_data['receipt_date'] or receipt.payment_date
                    receipt.payer_name = rcpt_data['lead_name'] or receipt.payer_name
                    receipt.payer_company = rcpt_data['company'] or receipt.payer_company
                    receipt.bank_name = bank_name or receipt.bank_name
                    receipt.transaction_id = transaction_id or receipt.transaction_id
                    receipt.remarks = rcpt_data['items'][0]['description'] if rcpt_data['items'] else receipt.remarks
                    receipt.extra_info = json.dumps(extra_info)
                    self.stats['receipts_updated'] = self.stats.get('receipts_updated', 0) + 1
                    action = '更新'
                else:
                    # 创建新收据
                    receipt = ProjectReceipt(
                        receipt_number=receipt_no,
                        header_id=project_header.id,
                        ref_id=ref_id,
                        invoice_id=invoice_id,
                        amount=rcpt_data['total_amount'],
                        currency=rcpt_data['currency'],
                        payment_method=payment_method,
                        payment_date=rcpt_data['receipt_date'] or datetime.utcnow().date(),
                        payer_name=rcpt_data['lead_name'],
                        payer_company=rcpt_data['company'],
                        bank_name=bank_name,
                        transaction_id=transaction_id,
                        status='confirmed',  # 导入的收据默认为已确认
                        remarks=rcpt_data['items'][0]['description'] if rcpt_data['items'] else None,
                        extra_info=json.dumps(extra_info),
                        created_by='Athina CSV Import',
                    )
                    db.session.add(receipt)
                    db.session.flush()  # 获取 ID
                    self.stats['receipts_created'] += 1
                    action = '创建'

                # 如果有多个发票，创建/更新分配记录
                if len(invoice_allocations) > 1:
                    # 先删除旧的分配记录（如果更新）
                    if existing_receipt:
                        ReceiptInvoiceAllocation.query.filter_by(receipt_id=receipt.id).delete()
                    for alloc in invoice_allocations:
                        allocation = ReceiptInvoiceAllocation(
                            receipt_id=receipt.id,
                            invoice_id=alloc['invoice_id'],
                            allocated_amount=Decimal(str(alloc['amount'])),
                        )
                        db.session.add(allocation)

                # 更新关联发票的已付金额
                if invoice_id:
                    ProjectReceipt.update_invoice_paid_amount(invoice_id)
                for alloc in invoice_allocations:
                    ProjectReceipt.update_invoice_paid_amount_from_allocations(alloc['invoice_id'])

                results['success'] += 1
                results['details'].append({
                    'success': True,
                    'receipt_no': receipt_no,
                    'hid': hid,
                    'amount': str(rcpt_data['total_amount']),
                    'invoice_count': len(rcpt_data['invoice_nos']),
                    'message': f'成功{action}收据 {receipt_no}',
                })

            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'success': False,
                    'receipt_no': receipt_no,
                    'message': f'创建收据失败: {str(e)}',
                })
                self.errors.append(f'创建收据 {receipt_no} 失败: {str(e)}')

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'保存失败: {str(e)}'}

        return {
            'success': True,
            'message': f"收据导入完成: 成功 {results['success']}，跳过 {results['skipped']}，失败 {results['failed']}",
            'results': results,
            'stats': self.stats,
            'warnings': self.warnings,
        }

    def import_payment_voucher_csv(self, file_content):
        """从 Payment Voucher Listing Report.csv 导入付款凭证

        实际 CSV 格式:
        行1: ,Pay No,HID,Ref,Inv,Inv Date,Booking Type,Department,Supplier,... (表头，第一列可能为空)
        行2: Pay No: 5171 ,,,... (付款分组行)
        行3: ,5171,889,1220,10999,03/01/2026,Airline,MAIN,Scoot Airline,... (数据行)
        行4: ,,,,,,,,,,,,,,Sub Total,,2,968.04,... (汇总行)

        注意：CSV 表头第一列可能为空，实际数据列从第二列开始。

        Args:
            file_content: CSV 文件内容

        Returns:
            dict: 导入结果
        """
        import re

        # 确保 session 状态干净
        try:
            db.session.rollback()
        except:
            pass

        rows = self._read_csv_file(file_content)
        if not rows:
            return {'success': False, 'message': 'CSV 文件为空或解析失败'}

        # 按 Pay No 分组
        payment_groups = {}
        current_pay_no = None

        for row in rows:
            # 获取第一列的值，检查是否是付款分组行 "Pay No: 5171 "
            first_col_key = list(row.keys())[0] if row else ''
            first_col_val = row.get(first_col_key, '').strip() if row else ''

            # 检查是否是付款分组行
            pay_match = re.match(r'Pay No:\s*(\d+)', first_col_val)
            if pay_match:
                current_pay_no = pay_match.group(1)
                continue

            values = list(row.values())

            # 辅助函数：从字段名或位置获取值
            def get_field_or_pos(field_names, pos_index, default=''):
                """优先从字段名获取，如果失败则从位置获取"""
                if isinstance(field_names, str):
                    field_names = [field_names]
                # 先尝试字段名
                for name in field_names:
                    val = row.get(name, '').strip()
                    if val and 'Pay No:' not in val:
                        return val
                # 字段名获取失败，尝试从位置获取（处理表头和数据错位的情况）
                if len(values) > pos_index:
                    val = values[pos_index].strip() if values[pos_index] else ''
                    if val and 'Pay No:' not in val:
                        return val
                return default

            # CSV 列名，同时支持位置获取
            pay_no = get_field_or_pos(['Pay No'], 1) or current_pay_no
            hid = get_field_or_pos(['HID'], 2)
            ref = get_field_or_pos(['Ref'], 3)
            inv = get_field_or_pos(['Inv'], 4)
            inv_date = get_field_or_pos(['Inv Date'], 5)
            booking_type = get_field_or_pos(['Booking Type'], 6)
            department = get_field_or_pos(['Department'], 7)
            supplier = get_field_or_pos(['Supplier'], 8)
            sup_inv = get_field_or_pos(['Sup Inv'], 9)
            company = get_field_or_pos(['Company'], 10)
            pay_date = get_field_or_pos(['Date'], 11)
            pay_detail = get_field_or_pos(['Pay Detail'], 12)
            pay_bank = get_field_or_pos(['Pay Bank'], 13)
            lead_name = get_field_or_pos(['Lead Name'], 14)
            curr = get_field_or_pos(['Curr'], 15) or 'SGD'
            amount = get_field_or_pos(['Amount'], 16)
            tax = get_field_or_pos(['Tax'], 17)
            charges = get_field_or_pos(['Charges'], 18)
            eo_no = get_field_or_pos(['EONo'], 19)
            consultant = get_field_or_pos(['Consultant'], 20)
            consultant = consultant.upper() if consultant else consultant
            filing_no = get_field_or_pos(['Filing No'], 21)
            base_amt = get_field_or_pos(['Base Amt'], 22)
            tkt_no = get_field_or_pos(['Tkt No'], 23)
            rate = get_field_or_pos(['Rate'], 24)
            total_amount = get_field_or_pos(['Total Amount'], 25)
            forex = get_field_or_pos(['Forex'], 26)

            # 跳过空行、汇总行 (Sub Total)
            if not pay_no or not amount or 'Sub Total' in lead_name:
                continue

            # 构建 HID 和 REF 编号
            hid_full = f"H{hid}" if hid and not hid.startswith('H') else hid
            ref_number = f"R{ref}" if ref and not ref.startswith('R') else ref

            # 使用 pay_no 作为分组键
            if pay_no not in payment_groups:
                payment_groups[pay_no] = {
                    'pay_no': pay_no,
                    'supplier': supplier,
                    'pay_date': self._parse_date(pay_date),
                    'pay_detail': pay_detail,
                    'pay_bank': pay_bank,
                    'currency': curr,
                    'consultant': consultant,
                    'total_amount': Decimal('0'),
                    'items': [],
                    'eo_numbers': [],
                }

            # 累加金额
            item_amount = self._parse_decimal(amount)
            payment_groups[pay_no]['total_amount'] += item_amount

            # 更新供应商（使用第一个非空值）
            if supplier and not payment_groups[pay_no]['supplier']:
                payment_groups[pay_no]['supplier'] = supplier

            # 添加明细项
            payment_groups[pay_no]['items'].append({
                'hid': hid_full,
                'ref': ref,
                'ref_number': ref_number,
                'inv': inv,
                'inv_date': inv_date,
                'booking_type': booking_type,
                'department': department,
                'supplier': supplier,
                'sup_inv': sup_inv,
                'company': company,
                'lead_name': lead_name,
                'amount': float(item_amount),
                'tax': self._parse_decimal(tax),
                'charges': self._parse_decimal(charges),
                'eo_no': eo_no,
                'tkt_no': tkt_no,
                'total_amount': self._parse_decimal(total_amount),
            })

            # 收集 EO 编号
            if eo_no and eo_no not in payment_groups[pay_no]['eo_numbers']:
                payment_groups[pay_no]['eo_numbers'].append(eo_no)

        results = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'details': [],
        }

        for pay_no, pmt_data in payment_groups.items():
            try:
                # 检查付款记录是否已存在
                existing_payment = SupplierPayment.query.filter_by(
                    payment_no=pay_no
                ).first()

                # 查找供应商
                supplier_id = None
                if pmt_data['supplier']:
                    supplier_id = self._find_supplier(pmt_data['supplier'])

                # 准备备注
                remarks_parts = []
                if pmt_data['pay_detail']:
                    remarks_parts.append(f"付款详情: {pmt_data['pay_detail']}")
                if pmt_data['pay_bank']:
                    remarks_parts.append(f"付款银行: {pmt_data['pay_bank']}")
                remarks = '; '.join(remarks_parts) if remarks_parts else None

                if existing_payment:
                    # 更新已存在的付款记录
                    payment = existing_payment
                    payment.supplier_id = supplier_id or payment.supplier_id
                    payment.payment_date = pmt_data['pay_date'] or payment.payment_date
                    payment.total_amount = pmt_data['total_amount']
                    payment.currency = pmt_data['currency'] or payment.currency
                    payment.eo_count = len(pmt_data['eo_numbers'])
                    payment.remarks = remarks or payment.remarks
                    self.stats['payment_vouchers_updated'] = self.stats.get('payment_vouchers_updated', 0) + 1
                    action = '更新'
                else:
                    # 检查供应商是否有预付账款记录，决定付款方式
                    payment_source = 'bank'
                    prepayment_amount = None
                    if supplier_id:
                        # 查询供应商是否有预付账款
                        has_prepayment = SupplierPrepayment.query.filter_by(
                            supplier_id=supplier_id
                        ).first() is not None
                        if has_prepayment:
                            payment_source = 'prepayment'
                            prepayment_amount = pmt_data['total_amount']

                    # 创建新的付款记录
                    payment = SupplierPayment(
                        payment_no=pay_no,
                        supplier_id=supplier_id,
                        payment_date=pmt_data['pay_date'] or datetime.utcnow().date(),
                        total_amount=pmt_data['total_amount'],
                        currency=pmt_data['currency'],
                        payment_source=payment_source,
                        prepayment_amount=prepayment_amount,
                        payment_voucher_no=pay_no,  # 使用 pay_no 作为凭证号
                        eo_count=len(pmt_data['eo_numbers']),
                        status='confirmed',
                        remarks=remarks,
                        created_by=pmt_data['consultant'] or 'Athina CSV Import',
                    )
                    db.session.add(payment)
                    db.session.flush()  # 获取 ID
                    self.stats['payment_vouchers_created'] += 1
                    action = '创建'

                # 更新关联的 EO
                eos_updated = 0
                for eo_no in pmt_data['eo_numbers']:
                    eo = ProjectEO.query.filter_by(eo_number=eo_no).first()
                    if eo:
                        # 找到对应的明细项获取金额
                        item_amount = None
                        for item in pmt_data['items']:
                            if item['eo_no'] == eo_no:
                                item_amount = Decimal(str(item['amount']))
                                break

                        eo.payment_record_id = payment.id
                        eo.payment_no = pay_no
                        eo.payment_voucher_no = pay_no
                        eo.paid_date = pmt_data['pay_date']
                        if item_amount:
                            eo.pay_amount = item_amount
                        eo.status = 'paid'
                        eo.payment_remarks = json.dumps({
                            'athina_pay_no': pay_no,
                            'pay_detail': pmt_data['pay_detail'],
                            'pay_bank': pmt_data['pay_bank'],
                            'source': 'csv_import',
                            'updated_at': datetime.utcnow().isoformat(),
                        })
                        eos_updated += 1
                        self.stats['eos_updated'] += 1

                results['success'] += 1
                results['details'].append({
                    'success': True,
                    'pay_no': pay_no,
                    'supplier': pmt_data['supplier'],
                    'amount': str(pmt_data['total_amount']),
                    'eo_count': len(pmt_data['eo_numbers']),
                    'eos_updated': eos_updated,
                    'message': f'成功{action}付款记录 {pay_no}，更新 {eos_updated} 个 EO',
                })

            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'success': False,
                    'pay_no': pay_no,
                    'message': f'创建付款记录失败: {str(e)}',
                })
                self.errors.append(f'创建付款记录 {pay_no} 失败: {str(e)}')

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'保存失败: {str(e)}'}

        return {
            'success': True,
            'message': f"付款凭证导入完成: 成功 {results['success']}，跳过 {results['skipped']}，失败 {results['failed']}",
            'results': results,
            'stats': self.stats,
            'warnings': self.warnings,
        }
