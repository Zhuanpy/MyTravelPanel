-- =======================================================================
-- 修复 US-BANGLA AIRLINES LTD 预付账款使用记录 (简化版)
-- supplier_id = 227
-- =======================================================================

-- =====================
-- 步骤1：查询当前数据
-- =====================

-- 1.1 预付款列表
SELECT id, prepayment_number, amount, balance_amount, payment_date, status
FROM supplier_prepayments
WHERE supplier_id = 227
ORDER BY payment_date, id;

-- 1.2 已付款EO列表（按时间排序）
SELECT
    eo.id AS eo_id,
    eo.ref_id,
    eo.eo_number,
    COALESCE(eo.pay_amount, ref.cost_price) AS amount,
    COALESCE(eo.paid_date, DATE(eo.created_at)) AS eo_date
FROM project_eos eo
JOIN project_refs ref ON eo.ref_id = ref.id
WHERE ref.supplier_id = 227
  AND eo.status = 'paid'
ORDER BY COALESCE(eo.paid_date, DATE(eo.created_at)), eo.id;

-- 1.3 当前使用记录数量
SELECT COUNT(*) AS usage_count
FROM prepayment_usages
WHERE prepayment_id IN (SELECT id FROM supplier_prepayments WHERE supplier_id = 227);


-- =====================
-- 步骤2：清除并重置（开启事务）
-- =====================

START TRANSACTION;

-- 2.1 删除现有使用记录
DELETE FROM prepayment_usages
WHERE prepayment_id IN (
    SELECT id FROM supplier_prepayments WHERE supplier_id = 227
);

-- 2.2 重置预付款余额
UPDATE supplier_prepayments
SET balance_amount = amount,
    status = 'confirmed',
    updated_at = NOW()
WHERE supplier_id = 227;

-- 确认结果（所有余额应等于充值金额）
SELECT id, prepayment_number, amount, balance_amount, status
FROM supplier_prepayments WHERE supplier_id = 227 ORDER BY payment_date, id;

-- 确认无误后执行:
COMMIT;

-- 如果有问题执行:
-- ROLLBACK;


-- =====================
-- 步骤3：按FIFO分配
-- =====================

-- 调用存储过程
CALL fix_usbangla_prepayment_fifo();


-- =====================
-- 步骤4：验证最终结果
-- =====================

-- 4.1 预付款最终状态
SELECT
    id, prepayment_number, amount, balance_amount,
    amount - balance_amount AS used_amount,
    ROUND((amount - balance_amount) / amount * 100, 2) AS usage_pct,
    payment_date, status
FROM supplier_prepayments
WHERE supplier_id = 227
ORDER BY payment_date, id;

-- 4.2 使用记录明细
SELECT
    pu.id, sp.prepayment_number, eo.eo_number,
    pu.amount, pu.usage_date
FROM prepayment_usages pu
JOIN supplier_prepayments sp ON pu.prepayment_id = sp.id
JOIN project_eos eo ON pu.eo_id = eo.id
WHERE sp.supplier_id = 227
ORDER BY sp.payment_date, pu.usage_date, pu.id;

-- 4.3 汇总验证
SELECT
    SUM(amount) AS total_prepaid,
    SUM(balance_amount) AS total_balance,
    SUM(amount - balance_amount) AS total_used
FROM supplier_prepayments WHERE supplier_id = 227;
