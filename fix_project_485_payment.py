# -*- coding: utf-8 -*-
"""
修复项目485的收款分配问题
根据实际未收款金额重新分配
"""

from App_new.app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.receipt import ProjectReceipt
import json

def fix_project_485():
    """修复项目485的收款分配"""
    app = create_app()
    project_id = 485
    
    with app.app_context():
        # 获取项目
        header = ProjectHeader.query.get(project_id)
        if not header:
            print(f"项目 {project_id} 不存在")
            return
        
        print(f"\n{'='*80}")
        print(f"修复项目 {header.hid} (ID: {project_id}) 的收款分配")
        print(f"{'='*80}\n")
        
        # 获取所有有售价的REF
        refs = [ref for ref in header.refs if ref.selling_price]
        refs.sort(key=lambda x: x.id)  # 按ID排序
        
        print(f"REF列表:")
        for ref in refs:
            selling_price = float(ref.selling_price)
            current_received = ProjectReceipt.get_ref_total_received(ref.id, project_id)
            unpaid = selling_price - current_received
            print(f"  {ref.ref_number}: 售价 {selling_price:.2f}, 已收款 {current_received:.2f}, 未收款 {unpaid:.2f}")
        
        # 获取项目级别收款记录
        project_receipts = ProjectReceipt.query.filter_by(
            header_id=project_id,
            ref_id=None,
            status='confirmed'
        ).all()
        
        if not project_receipts:
            print("\n没有项目级别的收款记录")
            return
        
        total_project_receipt = sum(float(r.amount) for r in project_receipts)
        print(f"\n项目级别收款总额: {total_project_receipt:.2f}")
        print(f"项目总销售: {header.total_selling_amount:.2f}")
        print(f"项目总已收款: {header.total_paid_amount:.2f}")
        print(f"项目总未收款: {header.total_unpaid_amount:.2f}")
        
        # 计算每个REF的当前未收款（不包括项目级别分配）
        ref_unpaid_before = {}
        total_direct_received = 0
        
        for ref in refs:
            # 只计算直接关联的收款
            direct_receipts = ProjectReceipt.query.filter_by(
                ref_id=ref.id,
                status='confirmed'
            ).all()
            direct_total = sum(float(r.amount) for r in direct_receipts)
            total_direct_received += direct_total
            
            selling_price = float(ref.selling_price)
            unpaid_before = selling_price - direct_total
            ref_unpaid_before[ref.id] = unpaid_before
        
        print(f"\n直接收款总额: {total_direct_received:.2f}")
        print(f"需要项目级别分配: {total_project_receipt:.2f}")
        
        # 重新分配：优先分配给未收款多的REF
        # 将所有项目级别收款合并，然后按未收款比例分配
        total_unpaid = sum(ref_unpaid_before.values())
        
        print(f"\n总未收款（不包括项目级别分配）: {total_unpaid:.2f}")
        
        if total_unpaid <= 0.01:
            print("所有REF都已收款，按售价比例分配")
            total_selling = sum(float(ref.selling_price) for ref in refs)
            for receipt in project_receipts:
                amount = float(receipt.amount)
                distribution = []
                for ref in refs:
                    selling_price = float(ref.selling_price)
                    if total_selling > 0:
                        ratio = selling_price / total_selling
                        alloc_amount = amount * ratio
                    else:
                        alloc_amount = 0
                    distribution.append({
                        'ref_id': ref.id,
                        'amount': round(alloc_amount, 2)
                    })
                
                # 调整最后一个以确保总和正确
                total_allocated = sum(d['amount'] for d in distribution)
                if abs(total_allocated - amount) > 0.01:
                    diff = amount - total_allocated
                    distribution[-1]['amount'] = round(distribution[-1]['amount'] + diff, 2)
                
                # 更新收款记录
                dist_info = {
                    'distribution_method': 'proportional',
                    'distribution': distribution,
                    'total_amount': amount,
                    'remaining_amount': 0
                }
                receipt.extra_info = json.dumps(dist_info)
                db.session.flush()
        else:
            # 按未收款比例分配
            print("按未收款比例分配项目级别收款")
            
            # 将所有项目级别收款合并分配
            for receipt in project_receipts:
                amount = float(receipt.amount)
                distribution = []
                
                for ref in refs:
                    unpaid = ref_unpaid_before[ref.id]
                    if total_unpaid > 0 and unpaid > 0:
                        ratio = unpaid / total_unpaid
                        # 分配金额不能超过未收款金额
                        alloc_amount = min(amount * ratio, unpaid)
                    else:
                        alloc_amount = 0
                    distribution.append({
                        'ref_id': ref.id,
                        'amount': round(alloc_amount, 2)
                    })
                
                # 调整分配以确保总和等于收款金额
                total_allocated = sum(d['amount'] for d in distribution)
                if abs(total_allocated - amount) > 0.01:
                    # 将差额分配给未收款最多的REF
                    diff = amount - total_allocated
                    if diff > 0:
                        # 找到未收款最多的REF
                        max_unpaid_ref = max(refs, key=lambda r: ref_unpaid_before[r.id])
                        for d in distribution:
                            if d['ref_id'] == max_unpaid_ref.id:
                                d['amount'] = round(d['amount'] + diff, 2)
                                break
                
                # 更新收款记录
                dist_info = {
                    'distribution_method': 'by_unpaid',
                    'distribution': distribution,
                    'total_amount': amount,
                    'remaining_amount': 0
                }
                receipt.extra_info = json.dumps(dist_info)
                
                print(f"\n收款记录 {receipt.receipt_number} ({amount:.2f}) 分配:")
                for dist in distribution:
                    ref = ProjectRef.query.get(dist['ref_id'])
                    print(f"  {ref.ref_number}: {dist['amount']:.2f}")
                
                db.session.flush()
        
        # 更新所有REF的payment_status
        print(f"\n更新REF付款状态...")
        for ref in refs:
            total_received = ProjectReceipt.get_ref_total_received(ref.id, project_id)
            selling_price = float(ref.selling_price)
            unpaid = selling_price - total_received
            
            if total_received >= selling_price:
                ref.payment_status = 'paid'
            elif total_received > 0:
                ref.payment_status = 'partial'
            else:
                ref.payment_status = 'unpaid'
            
            print(f"  {ref.ref_number}: 已收款 {total_received:.2f} / {selling_price:.2f}, 未收款 {unpaid:.2f} -> {ref.payment_status}")
        
        # 提交更改
        db.session.commit()
        
        print(f"\n{'='*80}")
        print(f"✅ 修复完成！")
        print(f"{'='*80}\n")
        
        # 验证结果
        header = ProjectHeader.query.get(project_id)
        print(f"修复后验证:")
        print(f"  总销售: {header.total_selling_amount:.2f}")
        print(f"  总已收款: {header.total_paid_amount:.2f}")
        print(f"  总未收款: {header.total_unpaid_amount:.2f}")
        
        print(f"\n各REF未收款明细:")
        for ref in refs:
            total_received = ProjectReceipt.get_ref_total_received(ref.id, project_id)
            unpaid = float(ref.selling_price) - total_received
            status_icon = "✅" if unpaid <= 0.01 else "⚠️"
            print(f"  {status_icon} {ref.ref_number}: 未收款 {unpaid:.2f} (状态: {ref.payment_status})")

if __name__ == '__main__':
    fix_project_485()

