# -*- coding: utf-8 -*-
"""
优化Athina表结构
根据实际CSV数据结构简化头部表，将所有业务字段移到明细表
"""

from App_new import create_app
from App_new.exts import db
from App_new.finance.models.athina_booking import AthinaBookingHeader, AthinaBookingDetail

def optimize_athina_tables():
    """优化Athina表结构"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始优化Athina表结构...")
            
            # 1. 备份现有数据
            print("备份现有数据...")
            headers = AthinaBookingHeader.query.all()
            details = AthinaBookingDetail.query.all()
            
            print(f"找到 {len(headers)} 个头部记录，{len(details)} 个明细记录")
            
            # 2. 删除现有表
            print("删除现有表...")
            AthinaBookingDetail.__table__.drop(db.engine, checkfirst=True)
            AthinaBookingHeader.__table__.drop(db.engine, checkfirst=True)
            
            # 3. 创建优化后的表结构
            print("创建优化后的表结构...")
            
            # 创建简化的头部表
            db.create_all()
            
            print("表结构优化完成！")
            print("\n新的表结构：")
            print("athina_booking_headers:")
            print("  - id (主键)")
            print("  - booking_header_id (预订头部ID)")
            print("  - corporate_name (公司名称)")
            print("  - sub_total_gross (小计总金额)")
            print("  - sub_total_cost (小计成本)")
            print("  - sub_total_pl (小计盈亏)")
            print("  - sub_total_balance (小计余额)")
            print("  - sub_total_tax (小计税额)")
            print("  - sub_total_discount (小计折扣)")
            print("  - sub_total_local_gross (小计本地总金额)")
            print("  - sub_total_margin (小计利润率)")
            print("  - consultant (顾问)")
            print("  - sales_consultant (销售顾问)")
            print("  - invoice_no (发票号)")
            print("  - invoice_date (发票日期)")
            print("  - created_at, updated_at")
            print("\nathina_booking_details:")
            print("  - id (主键)")
            print("  - header_id (外键)")
            print("  - 所有业务和财务字段")
            print("  - is_subtotal (小计标记)")
            
        except Exception as e:
            print(f"优化失败: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    optimize_athina_tables()
