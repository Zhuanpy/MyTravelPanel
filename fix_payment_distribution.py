# -*- coding: utf-8 -*-
"""
修复项目收款分配问题
自动重新分配项目级别收款记录
"""

from App_new.app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.receipt import ProjectReceipt
import json

def fix_payment_distribution(project_id, distribution_method='proportional'):
    """
    修复项目收款分配
    
    distribution_method: 
    - 'proportional': 按售价比例分配
    - 'equal': 平均分配
    - 'by_unpaid': 按未收款金额分配（优先分配给未收款多的REF）
    """
    app = create_app()
    
    with app.app_context():
        # 获取项目
        header = ProjectHeader.query.get(project_id)
        if not header:
            print(f"项目 {project_id} 不存在")
            return
        
        print(f"\n{'='*80}")
        print(f"修复项目 {header.hid} (ID: {project_id}) 的收款分配")
        print(f"分配方式: {distribution_method}")
        print(f"{'='*80}\n")
        
        # 获取所有有售价的REF
        refs = [ref for ref in header.refs if ref.selling_price]
        if not refs:
            print("没有找到有售价的REF")
            return
        
        # 获取项目级别收款记录
        project_receipts = ProjectReceipt.query.filter_by(
            header_id=project_id,
            ref_id=None,
            status='confirmed'
        ).all()
        
        if not project_receipts:
            print("没有项目级别的收款记录")
            return
        
        print(f"找到 {len(project_receipts)} 条项目级别收款记录\n")
        
        # 重新分配每条收款记录
        for receipt in project_receipts:
            amount = float(receipt.amount)
            print(f"处理收款记录 {receipt.receipt_number}: {amount:.2f}")
            
            # 计算每个REF的已收款和未收款
            ref_data = []
            total_selling = 0
            
            for ref in refs:
                selling_price = float(ref.selling_price)
                total_selling += selling_price
                
                # 计算当前已收款（不包括这条项目级别收款）
                current_received = ProjectReceipt.get_ref_total_received(ref.id, project_id)
                
                # 如果这条收款已经分配过，需要减去
                if receipt.extra_info:
                    try:
                        dist_info = json.loads(receipt.extra_info)
                        if 'distribution' in dist_info:
                            for alloc in dist_info['distribution']:
                                if alloc.get('ref_id') == ref.id:
                                    current_received -= alloc.get('amount', 0)
                    except:
                        pass
                
                unpaid = selling_price - current_received
                
                ref_data.append({
                    'ref': ref,
                    'selling_price': selling_price,
                    'current_received': current_received,
                    'unpaid': unpaid
                })
            
            # 根据分配方式计算分配
            distribution = []
            
            if distribution_method == 'proportional':
                # 按售价比例分配
                for data in ref_data:
                    if total_selling > 0:
                        ratio = data['selling_price'] / total_selling
                        alloc_amount = amount * ratio
                    else:
                        alloc_amount = 0
                    distribution.append({
                        'ref_id': data['ref'].id,
                        'amount': round(alloc_amount, 2)
                    })
            
            elif distribution_method == 'equal':
                # 平均分配
                per_ref = amount / len(ref_data) if ref_data else 0
                for data in ref_data:
                    distribution.append({
                        'ref_id': data['ref'].id,
                        'amount': round(per_ref, 2)
                    })
            
            elif distribution_method == 'by_unpaid':
                # 按未收款金额分配（优先分配给未收款多的REF）
                total_unpaid = sum(data['unpaid'] for data in ref_data if data['unpaid'] > 0)
                
                if total_unpaid > 0:
                    for data in ref_data:
                        if data['unpaid'] > 0:
                            ratio = data['unpaid'] / total_unpaid
                            alloc_amount = min(amount * ratio, data['unpaid'])
                        else:
                            alloc_amount = 0
                        distribution.append({
                            'ref_id': data['ref'].id,
                            'amount': round(alloc_amount, 2)
                        })
                else:
                    # 如果所有REF都已收款，按比例分配
                    for data in ref_data:
                        if total_selling > 0:
                            ratio = data['selling_price'] / total_selling
                            alloc_amount = amount * ratio
                        else:
                            alloc_amount = 0
                        distribution.append({
                            'ref_id': data['ref'].id,
                            'amount': round(alloc_amount, 2)
                        })
            
            # 调整分配以确保总和等于收款金额
            total_allocated = sum(d['amount'] for d in distribution)
            if abs(total_allocated - amount) > 0.01:
                # 调整最后一个REF的金额以匹配总和
                diff = amount - total_allocated
                if distribution:
                    distribution[-1]['amount'] = round(distribution[-1]['amount'] + diff, 2)
            
            # 更新收款记录的分配信息
            dist_info = {
                'distribution_method': distribution_method,
                'distribution': distribution,
                'total_amount': amount,
                'remaining_amount': 0
            }
            receipt.extra_info = json.dumps(dist_info)
            
            print(f"  分配明细:")
            for dist in distribution:
                ref = ProjectRef.query.get(dist['ref_id'])
                print(f"    - {ref.ref_number}: {dist['amount']:.2f}")
            
            db.session.flush()
        
        # 更新所有REF的payment_status
        print(f"\n更新REF付款状态...")
        for ref in refs:
            total_received = ProjectReceipt.get_ref_total_received(ref.id, project_id)
            selling_price = float(ref.selling_price)
            
            if total_received >= selling_price:
                ref.payment_status = 'paid'
            elif total_received > 0:
                ref.payment_status = 'partial'
            else:
                ref.payment_status = 'unpaid'
            
            print(f"  {ref.ref_number}: 已收款 {total_received:.2f} / {selling_price:.2f} -> {ref.payment_status}")
        
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
            print(f"  {status_icon} {ref.ref_number}: 未收款 {unpaid:.2f}")

if __name__ == '__main__':
    # 使用按未收款金额分配的方式（优先分配给未收款多的REF）
    fix_payment_distribution(485, distribution_method='by_unpaid')

