# -*- coding: utf-8 -*-
"""
诊断项目收款分配问题
检查项目485的收款记录分配情况
"""

from App_new.app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.receipt import ProjectReceipt
import json

def diagnose_payment_distribution(project_id):
    """诊断项目收款分配问题"""
    app = create_app()
    
    with app.app_context():
        # 获取项目
        header = ProjectHeader.query.get(project_id)
        if not header:
            print(f"项目 {project_id} 不存在")
            return
        
        print(f"\n{'='*80}")
        print(f"诊断项目 {header.hid} (ID: {project_id}) 的收款分配问题")
        print(f"{'='*80}\n")
        
        print(f"项目总销售金额: {header.total_selling_amount}")
        print(f"项目总已收款: {header.total_paid_amount}")
        print(f"项目总未收款: {header.total_unpaid_amount}")
        print(f"\n{'='*80}\n")
        
        # 获取所有REF
        refs = ProjectRef.query.filter_by(header_id=project_id).order_by(ProjectRef.id).all()
        print(f"REF列表 ({len(refs)} 个):")
        print("-" * 80)
        
        total_selling = 0
        total_received = 0
        
        for ref in refs:
            if not ref.selling_price:
                continue
                
            selling_price = float(ref.selling_price)
            total_selling += selling_price
            
            # 计算已收款（包括项目级别分配）
            ref_received = ProjectReceipt.get_ref_total_received(ref.id, project_id)
            total_received += ref_received
            
            unpaid = selling_price - ref_received
            
            print(f"\nREF {ref.ref_number}:")
            print(f"  售价: {selling_price:.2f}")
            print(f"  已收款: {ref_received:.2f}")
            print(f"  未收款: {unpaid:.2f}")
            print(f"  状态: {ref.payment_status}")
            
            # 检查直接关联的收款
            direct_receipts = ProjectReceipt.query.filter_by(
                ref_id=ref.id, 
                status='confirmed'
            ).all()
            direct_total = sum(float(r.amount) for r in direct_receipts)
            
            if direct_receipts:
                print(f"  直接收款: {direct_total:.2f} (来自 {len(direct_receipts)} 条记录)")
                for r in direct_receipts:
                    print(f"    - {r.receipt_number}: {r.amount}")
            
            # 检查项目级别分配
            project_allocation = ref_received - direct_total
            if project_allocation > 0.01:
                print(f"  项目级别分配: {project_allocation:.2f}")
            elif project_allocation < -0.01:
                print(f"  ⚠️  警告: 项目级别分配为负值 {project_allocation:.2f}，可能有问题")
        
        print(f"\n{'='*80}")
        print(f"汇总:")
        print(f"  总销售: {total_selling:.2f}")
        print(f"  总已收款: {total_received:.2f}")
        print(f"  总未收款: {total_selling - total_received:.2f}")
        print(f"{'='*80}\n")
        
        # 检查项目级别收款记录
        print(f"\n{'='*80}")
        print(f"项目级别收款记录:")
        print(f"{'='*80}\n")
        
        project_receipts = ProjectReceipt.query.filter_by(
            header_id=project_id,
            ref_id=None,
            status='confirmed'
        ).all()
        
        if not project_receipts:
            print("  没有项目级别的收款记录")
        else:
            total_project_receipt = 0
            total_allocated = 0
            
            for receipt in project_receipts:
                amount = float(receipt.amount)
                total_project_receipt += amount
                
                print(f"\n收款记录 {receipt.receipt_number}:")
                print(f"  金额: {amount:.2f}")
                print(f"  日期: {receipt.payment_date}")
                
                if receipt.extra_info:
                    try:
                        dist_info = json.loads(receipt.extra_info)
                        print(f"  分配方式: {dist_info.get('distribution_method', 'unknown')}")
                        
                        if 'distribution' in dist_info:
                            allocations = dist_info['distribution']
                            print(f"  分配明细 ({len(allocations)} 个REF):")
                            
                            for alloc in allocations:
                                ref_id = alloc.get('ref_id')
                                alloc_amount = alloc.get('amount', 0)
                                total_allocated += alloc_amount
                                
                                ref = ProjectRef.query.get(ref_id) if ref_id else None
                                ref_num = ref.ref_number if ref else f"REF#{ref_id}"
                                
                                print(f"    - {ref_num}: {alloc_amount:.2f}")
                        else:
                            print(f"  ⚠️  警告: 没有分配信息")
                    except (json.JSONDecodeError, KeyError, TypeError) as e:
                        print(f"  ❌ 错误: 无法解析分配信息: {e}")
                else:
                    print(f"  ⚠️  警告: 没有分配信息 (extra_info为空)")
            
            print(f"\n项目级别收款汇总:")
            print(f"  总收款: {total_project_receipt:.2f}")
            print(f"  已分配: {total_allocated:.2f}")
            print(f"  未分配: {total_project_receipt - total_allocated:.2f}")
            
            if abs(total_project_receipt - total_allocated) > 0.01:
                print(f"  ⚠️  警告: 有 {total_project_receipt - total_allocated:.2f} 未分配")
        
        print(f"\n{'='*80}")
        print(f"诊断完成")
        print(f"{'='*80}\n")

if __name__ == '__main__':
    diagnose_payment_distribution(485)

