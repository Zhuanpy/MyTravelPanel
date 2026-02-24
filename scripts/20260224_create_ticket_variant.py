# -*- coding: utf-8 -*-
"""
创建 products_ticket_variant 表，并将现有子产品数据迁移到新表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    # 1. 创建表
    create_sql = """
    CREATE TABLE IF NOT EXISTS products_ticket_variant (
        id INT AUTO_INCREMENT PRIMARY KEY,
        product_id INT NOT NULL COMMENT '所属主产品ID',
        variant_name VARCHAR(200) NOT NULL COMMENT '变体名称（中文）',
        variant_name_en VARCHAR(200) NULL COMMENT '变体名称（英文）',
        description TEXT NULL COMMENT '变体描述',
        sort_order INT DEFAULT 0 COMMENT '排序权重',
        is_active TINYINT(1) DEFAULT 1 COMMENT '是否激活',
        adult_selling_price DECIMAL(12,2) NULL COMMENT '成人售价',
        adult_cost_price DECIMAL(12,2) NULL COMMENT '成人成本价',
        child_selling_price DECIMAL(12,2) NULL COMMENT '儿童售价',
        child_cost_price DECIMAL(12,2) NULL COMMENT '儿童成本价',
        currency VARCHAR(10) DEFAULT 'SGD' COMMENT '币种',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
        INDEX idx_product_id (product_id),
        CONSTRAINT fk_variant_product FOREIGN KEY (product_id) REFERENCES products_unified(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='门票产品变体表'
    """

    try:
        db.session.execute(db.text(create_sql))
        db.session.commit()
        print("1. 成功创建 products_ticket_variant 表")
    except Exception as e:
        db.session.rollback()
        if 'already exists' in str(e).lower():
            print("1. 表已存在，跳过创建")
        else:
            print(f"1. 创建表失败: {e}")
            sys.exit(1)

    # 2. 迁移现有子产品数据到新表
    # 查找 parent_id 不为空的门票子产品
    child_rows = db.session.execute(db.text("""
        SELECT pu.id, pu.parent_id, pu.product_name, pu.product_name_en,
               pu.description, pu.product_status, pu.sort_order
        FROM products_unified pu
        WHERE pu.parent_id IS NOT NULL AND pu.product_category = 'ticket'
    """)).fetchall()

    migrated = 0
    for row in child_rows:
        child_id = row[0]
        parent_id = row[1]
        variant_name = row[2]
        variant_name_en = row[3]
        description = row[4]
        is_active = 1 if row[5] == 'active' else 0
        sort_order = row[6] or 0

        # 获取成人价格
        adult_price = db.session.execute(db.text("""
            SELECT selling_price, cost_price FROM products_price
            WHERE product_id = :pid AND people_type = 'adult' AND is_active = 1
            LIMIT 1
        """), {'pid': child_id}).fetchone()

        # 获取儿童价格
        child_price = db.session.execute(db.text("""
            SELECT selling_price, cost_price FROM products_price
            WHERE product_id = :pid AND people_type = 'child' AND is_active = 1
            LIMIT 1
        """), {'pid': child_id}).fetchone()

        # 检查是否已迁移过（避免重复）
        existing = db.session.execute(db.text("""
            SELECT id FROM products_ticket_variant
            WHERE product_id = :parent_id AND variant_name = :name
        """), {'parent_id': parent_id, 'name': variant_name}).fetchone()

        if existing:
            continue

        db.session.execute(db.text("""
            INSERT INTO products_ticket_variant
            (product_id, variant_name, variant_name_en, description, sort_order, is_active,
             adult_selling_price, adult_cost_price, child_selling_price, child_cost_price)
            VALUES (:product_id, :name, :name_en, :desc, :sort, :active,
                    :a_sell, :a_cost, :c_sell, :c_cost)
        """), {
            'product_id': parent_id,
            'name': variant_name,
            'name_en': variant_name_en,
            'desc': description,
            'sort': sort_order,
            'active': is_active,
            'a_sell': adult_price[0] if adult_price else None,
            'a_cost': adult_price[1] if adult_price else None,
            'c_sell': child_price[0] if child_price else None,
            'c_cost': child_price[1] if child_price else None,
        })
        migrated += 1

    db.session.commit()
    print(f"2. 迁移了 {migrated} 条子产品数据到 products_ticket_variant")

    # 3. 删除旧的子产品的价格记录和子产品本身
    if child_rows:
        child_ids = [row[0] for row in child_rows]
        placeholders = ','.join([str(cid) for cid in child_ids])

        # 删除子产品的价格
        db.session.execute(db.text(f"DELETE FROM products_price WHERE product_id IN ({placeholders})"))
        # 删除子产品的扩展表记录
        db.session.execute(db.text(f"DELETE FROM products_ticket_ext WHERE product_id IN ({placeholders})"))
        # 删除子产品本身
        db.session.execute(db.text(f"DELETE FROM products_unified WHERE id IN ({placeholders})"))
        db.session.commit()
        print(f"3. 清理了 {len(child_ids)} 条旧子产品记录")
    else:
        print("3. 无需清理旧数据")

    print("迁移完成！")
