# -*- coding: utf-8 -*-
"""
修复REF付款状态脚本
用于检查和修复项目485中REF的payment_status字段与实际收款情况不一致的问题
"""

from App_new.app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.receipt import ProjectReceipt

def fix_ref_payment_status(project_id):
    """修复指定项目的所有REF的payment_status"""
    app = create_app()
    
    with app.app_context():
        # 获取项目
        header = ProjectHeader.query.get(project_id)
        if not header:
            print(f"项目 {project_id} 不存在")
            return
        
        print(f"\n开始修复项目 {header.hid} (ID: {project_id}) 的REF付款状态...")
        print(f"总销售金额: {header.total_selling_amount}")
        print(f"总已收款: {header.total_paid_amount}")
        print(f"总未收款: {header.total_unpaid_amount}")
        print("-" * 80)
        
        # 遍历所有REF
        refs = ProjectRef.query.filter_by(header_id=project_id).all()
        print(f"找到 {len(refs)} 个REF记录\n")
        
        fixed_count = 0
        for ref in refs:
            if not ref.selling_price:
                print(f"REF {ref.ref_number}: 无售价，跳过")
                continue
            
            # 计算实际已收款总额（包括项目级别分配）
            total_received = ProjectReceipt.get_ref_total_received(ref.id, project_id)
            selling_price = float(ref.selling_price)
            unpaid_amount = selling_price - total_received
            
            # 确定应该的状态
            if total_received >= selling_price:
                should_status = 'paid'
            elif total_received > 0:
                should_status = 'partial'
            else:
                should_status = 'unpaid'
            
            # 检查当前状态
            current_status = ref.payment_status
            status_changed = current_status != should_status
            
            print(f"REF {ref.ref_number}:")
            print(f"  售价: {selling_price}")
            print(f"  已收款: {total_received}")
            print(f"  未收款: {unpaid_amount}")
            print(f"  当前状态: {current_status}")
            print(f"  应该状态: {should_status}")
            
            if status_changed:
                ref.payment_status = should_status
                fixed_count += 1
                print(f"  ✅ 状态已更新: {current_status} -> {should_status}")
            else:
                print(f"  ✓ 状态正确")
            
            # 如果未收款金额显示异常
            if unpaid_amount > 0.01 and header.total_unpaid_amount <= 0.01:
                print(f"  ⚠️  警告: 项目总余额为0，但此REF仍有未收款 {unpaid_amount}")
                print(f"     可能原因: 项目级别收款未正确分配给此REF")
            
            print()
        
        # 提交更改
        if fixed_count > 0:
            db.session.commit()
            print(f"\n✅ 已修复 {fixed_count} 个REF的付款状态")
        else:
            print(f"\n✓ 所有REF的付款状态都是正确的")
        
        # 再次检查项目总余额
        header = ProjectHeader.query.get(project_id)  # 重新查询以获取最新数据
        print(f"\n修复后检查:")
        print(f"总销售金额: {header.total_selling_amount}")
        print(f"总已收款: {header.total_paid_amount}")
        print(f"总未收款: {header.total_unpaid_amount}")
        
        # 检查每个REF的未收款金额
        print(f"\n各REF未收款明细:")
        for ref in refs:
            if ref.selling_price:
                total_received = ProjectReceipt.get_ref_total_received(ref.id, project_id)
                unpaid = float(ref.selling_price) - total_received
                status_icon = "✅" if unpaid <= 0.01 else "⚠️"
                print(f"  {status_icon} {ref.ref_number}: 未收款 {unpaid:.2f} (状态: {ref.payment_status})")

if __name__ == '__main__':
    # 修复项目485
    fix_ref_payment_status(485)

