"""将所有银行交易记录的 tx_fingerprint 迁移到新的 MD5 算法

步骤：
1. 计算所有记录的新指纹
2. 识别重复记录（相同新指纹的多条记录）
3. 保留已确认/较早的记录，删除重复项
4. 更新所有保留记录的指纹为新格式

原因：旧指纹算法对金额尾零处理不一致（如 452.9 和 452.90 生成不同指纹），
     改用 MD5 哈希 + 统一2位小数格式化，确保导入去重可靠。
"""
import sys
import os
import hashlib
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.finance.models.statement import BankTransaction, BankStatement

app = create_app()


def compute_new_fingerprint(tx, bank_name):
    """根据交易记录计算新的MD5指纹"""
    date_str = str(tx.transaction_date)
    description = tx.description or ''

    amount_val = float(tx.amount) if tx.amount else 0.0
    if bank_name in ('UOB', 'OCBC'):
        if tx.transaction_type == 'debit':
            amount_str = f'{amount_val:.2f}|0.00'
        else:
            amount_str = f'0.00|{amount_val:.2f}'
    else:
        amount_str = f'{amount_val:.2f}'

    balance_val = float(tx.balance) if tx.balance is not None else 0.0
    balance_str = f'{balance_val:.2f}'

    raw_id = f"{date_str}|{description}|{amount_str}|{balance_str}"
    return hashlib.md5(raw_id.strip().lower().encode()).hexdigest()[:16]


with app.app_context():
    # 获取所有交易记录
    transactions = db.session.query(BankTransaction).join(
        BankStatement, BankTransaction.statement_id == BankStatement.id
    ).add_columns(BankStatement.bank_name).all()

    total = len(transactions)
    print(f"共 {total} 条交易记录")

    # 第一步：计算所有新指纹，按指纹分组
    fingerprint_groups = defaultdict(list)  # new_fp -> [(tx, bank_name), ...]

    for tx, bank_name in transactions:
        try:
            new_fp = compute_new_fingerprint(tx, bank_name)
            fingerprint_groups[new_fp].append((tx, bank_name))
        except Exception as e:
            print(f"  计算指纹错误 (ID={tx.id}): {e}")

    # 第二步：处理重复组 - 保留最优记录，删除重复项
    duplicates_to_delete = []
    duplicate_groups = 0

    for fp, group in fingerprint_groups.items():
        if len(group) <= 1:
            continue

        duplicate_groups += 1

        # 排序优先级：已确认 > 未确认，同状态下取较早创建的
        group.sort(key=lambda item: (
            not item[0].is_confirmed,  # 已确认的排前面
            item[0].is_reconciled != True,  # 已核对的排前面
            item[0].matched_receipt_id is None and item[0].eo_id is None,  # 有匹配的排前面
            item[0].created_at or item[0].id  # 较早的排前面
        ))

        keep = group[0][0]
        remove = [tx for tx, _ in group[1:]]

        if len(group) <= 3:  # 只打印较少的重复组详情
            print(f"\n  重复组 (指纹={fp}):")
            print(f"    保留: ID={keep.id} | 确认={keep.is_confirmed} | 核对={keep.is_reconciled} | 匹配EO={keep.eo_id} | 创建={keep.created_at}")
            for r in remove:
                print(f"    删除: ID={r.id} | 确认={r.is_confirmed} | 核对={r.is_reconciled} | 匹配EO={r.eo_id} | 创建={r.created_at}")

        duplicates_to_delete.extend(remove)

    print(f"\n发现 {duplicate_groups} 组重复记录，共 {len(duplicates_to_delete)} 条需要删除")

    if duplicates_to_delete:
        # 检查待删除记录中是否有已确认/已核对/有匹配的，给出警告
        risky = [t for t in duplicates_to_delete if t.is_confirmed or t.is_reconciled or t.matched_receipt_id or t.eo_id]
        if risky:
            print(f"\n  警告: {len(risky)} 条待删除记录有确认/核对/匹配状态:")
            for t in risky:
                print(f"    ID={t.id} | 确认={t.is_confirmed} | 核对={t.is_reconciled} | 匹配收款={t.matched_receipt_id} | 匹配EO={t.eo_id}")
            print("  这些记录的状态信息将丢失，但保留的记录已包含相同交易。")

        # 执行删除
        for tx in duplicates_to_delete:
            db.session.delete(tx)
        print(f"  已删除 {len(duplicates_to_delete)} 条重复记录")

    # 第三步：更新保留记录的指纹
    updated = 0
    errors = 0

    # 重新查询（因为删除了一些记录）
    db.session.flush()
    remaining = db.session.query(BankTransaction).join(
        BankStatement, BankTransaction.statement_id == BankStatement.id
    ).add_columns(BankStatement.bank_name).all()

    for tx, bank_name in remaining:
        try:
            new_fp = compute_new_fingerprint(tx, bank_name)
            if tx.tx_fingerprint != new_fp:
                tx.tx_fingerprint = new_fp
                updated += 1
        except Exception as e:
            errors += 1
            print(f"  更新错误 (ID={tx.id}): {e}")

    db.session.commit()

    print(f"\n迁移完成:")
    print(f"  - 原始记录数: {total}")
    print(f"  - 删除重复: {len(duplicates_to_delete)}")
    print(f"  - 剩余记录: {total - len(duplicates_to_delete)}")
    print(f"  - 指纹已更新: {updated}")
    print(f"  - 更新错误: {errors}")
